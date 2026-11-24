
"""Quarantined hybrid retriever for the Odhikar BD DRAFT corpus.

Offline retrieval:
    1. BM25 lexical retrieval
    2. Character n-gram TF-IDF retrieval (pure Python)
    3. Reciprocal Rank Fusion (RRF)

No SciPy, NumPy or scikit-learn dependency is required.

Optional Qdrant dense retrieval in draft mode uses SentenceTransformers.
This module never writes to production collections or calls an LLM.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

CHUNKS = ROOT / "rag_data" / "chunks_DRAFT.jsonl"

DIGIT_MAP = str.maketrans(
    "০১২৩৪৫৬৭৮৯",
    "0123456789"
)

TOKEN_RE = re.compile(
    r"[\u0980-\u09ff]+|[a-z0-9]+",
    re.I
)

SECTION_RE = re.compile(
    r"(?:ধারা|section|§)\s*([০-৯0-9]{1,3})",
    re.I
)


# ============================================================
# 2. TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:

    if not isinstance(text, str):
        return ""

    return text.lower().translate(DIGIT_MAP)


def tokens(text: str) -> list[str]:

    return TOKEN_RE.findall(
        normalize_text(text)
    )


# ============================================================
# 3. LOAD AND VERIFY DRAFT CORPUS
# ============================================================

def load_chunks(
    path: Path = CHUNKS
) -> list[dict[str, Any]]:

    if not path.exists():
        raise FileNotFoundError(
            f"Draft corpus not found: {path}"
        )

    data = [
        json.loads(line)
        for line in path.read_text(
            encoding="utf-8-sig"
        ).splitlines()
        if line.strip()
    ]

    if not data:
        raise ValueError("Empty draft corpus")

    ids = [record["id"] for record in data]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs")

    required_fields = (
        "id",
        "text_bn",
        "text_sha256",
        "section",
        "pdf_page_start",
        "pdf_page_end",
        "source_pdf",
        "official_reference_url",
        "verification_state",
        "production_approved",
    )

    for record in data:

        missing = [
            field
            for field in required_fields
            if field not in record
        ]

        if missing:
            raise ValueError(
                f"Missing fields in {record.get('id')}: {missing}"
            )

        if record["production_approved"] is not False:
            raise ValueError(
                "Production-approved content found. "
                "Refusing mixed corpus."
            )

        if not str(
            record["verification_state"]
        ).startswith("DRAFT"):

            raise ValueError(
                "Non-DRAFT content found. "
                "Refusing mixed corpus."
            )

        actual_hash = hashlib.sha256(
            record["text_bn"].encode("utf-8")
        ).hexdigest()

        if actual_hash != record["text_sha256"]:

            raise ValueError(
                f"Text checksum mismatch: {record['id']}"
            )

    return data


# ============================================================
# 4. BM25 RETRIEVAL
# ============================================================

class BM25Index:

    def __init__(
        self,
        docs: list[str],
        k1: float = 1.5,
        b: float = 0.75
    ):

        self.tokenized = [
            tokens(text)
            for text in docs
        ]

        self.freqs = [
            Counter(document)
            for document in self.tokenized
        ]

        self.lengths = [
            len(document)
            for document in self.tokenized
        ]

        self.n = len(docs)

        self.avgdl = (
            sum(self.lengths) / self.n
            if self.n
            else 0.0
        )

        self.k1 = k1
        self.b = b

        self.df = Counter(
            term
            for document in self.freqs
            for term in document
        )

    def rank(
        self,
        question: str
    ) -> list[tuple[int, float]]:

        query_terms = list(
            dict.fromkeys(tokens(question))
        )

        results = []

        for index, frequencies in enumerate(self.freqs):

            score = 0.0

            for term in query_terms:

                frequency = frequencies.get(term, 0)

                if frequency == 0:
                    continue

                document_frequency = self.df[term]

                idf = math.log(
                    1 + (
                        self.n - document_frequency + 0.5
                    ) / (
                        document_frequency + 0.5
                    )
                )

                denominator = frequency + self.k1 * (
                    1 - self.b
                    + self.b * self.lengths[index]
                    / max(self.avgdl, 1)
                )

                score += idf * (
                    frequency * (self.k1 + 1)
                    / denominator
                )

            if score > 0:
                results.append((index, score))

        return sorted(
            results,
            key=lambda item: (-item[1], item[0])
        )


# ============================================================
# 5. PURE PYTHON CHARACTER N-GRAM TF-IDF
# ============================================================

class LocalVectorIndex:
    """
    Pure-Python character n-gram TF-IDF index.

    Reproduces the important behavior of:

    TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5),
        min_df=1,
        sublinear_tf=True
    )

    Uses sparse dictionaries and an inverted index.

    No NumPy, SciPy or scikit-learn required.
    """

    def __init__(
        self,
        docs: list[str],
        min_n: int = 2,
        max_n: int = 5
    ):

        if not 1 <= min_n <= max_n:
            raise ValueError(
                "Invalid character n-gram range."
            )

        self.min_n = min_n
        self.max_n = max_n

        self.n = len(docs)

        self.document_frequency = Counter()

        document_counts = []

        # Step 1: Extract character n-grams
        for document in docs:

            normalized = normalize_text(document)

            counts = self._extract_ngrams(normalized)

            document_counts.append(counts)

            self.document_frequency.update(
                counts.keys()
            )

        # Step 2: Calculate smoothed IDF
        self.idf = {

            term: math.log(
                (1 + self.n) / (1 + frequency)
            ) + 1

            for term, frequency
            in self.document_frequency.items()

        }

        # Step 3: Build sparse inverted index
        self.inverted_index = defaultdict(list)

        for doc_index, counts in enumerate(document_counts):

            vector = self._create_vector(counts)

            for term, weight in vector.items():

                self.inverted_index[term].append(
                    (doc_index, weight)
                )

    def _extract_ngrams(
        self,
        text: str
    ) -> Counter:

        counts = Counter()

        text_length = len(text)

        for n in range(
            self.min_n,
            min(self.max_n, text_length) + 1
        ):

            for start in range(
                text_length - n + 1
            ):

                gram = text[start:start + n]

                counts[gram] += 1

        return counts

    def _create_vector(
        self,
        counts: Counter
    ) -> dict[str, float]:

        weighted = {}

        for term, frequency in counts.items():

            idf = self.idf.get(term)

            if idf is None:
                continue

            # Sublinear term frequency
            tf = 1.0 + math.log(frequency)

            weighted[term] = tf * idf

        # L2 normalization
        norm = math.sqrt(
            sum(
                weight * weight
                for weight in weighted.values()
            )
        )

        if norm == 0:
            return {}

        return {
            term: weight / norm
            for term, weight in weighted.items()
        }

    def rank(
        self,
        question: str
    ) -> list[tuple[int, float]]:

        if not isinstance(question, str) or not question.strip():
            return []

        normalized = normalize_text(question)

        query_counts = self._extract_ngrams(
            normalized
        )

        query_vector = self._create_vector(
            query_counts
        )

        if not query_vector:
            return []

        scores = defaultdict(float)

        # Sparse cosine similarity
        for term, query_weight in query_vector.items():

            for doc_index, document_weight in (
                self.inverted_index.get(term, [])
            ):

                scores[doc_index] += (
                    query_weight * document_weight
                )

        return sorted(
            (
                (index, score)
                for index, score in scores.items()
                if score > 0
            ),
            key=lambda item: (-item[1], item[0])
        )


# ============================================================
# 6. RECIPROCAL RANK FUSION
# ============================================================

def reciprocal_rank_fusion(
    rankings: list[list[tuple[int, float]]],
    k: int = 60
) -> dict[int, float]:

    combined = defaultdict(float)

    for ranking in rankings:

        for rank, (doc_index, _) in enumerate(
            ranking,
            start=1
        ):

            combined[doc_index] += 1 / (k + rank)

    return dict(combined)


# ============================================================
# 7. HYBRID RETRIEVER
# ============================================================

class HybridRetriever:

    def __init__(
        self,
        docs: list[dict[str, Any]] | None = None
    ):

        self.docs = (
            docs
            if docs is not None
            else load_chunks()
        )

        if not self.docs:
            raise ValueError("Empty draft corpus")

        texts = [
            record["text_bn"]
            for record in self.docs
        ]

        self.bm25 = BM25Index(texts)

        self.vector = LocalVectorIndex(texts)

    def search(
        self,
        query: str,
        top: int = 5
    ) -> list[dict[str, Any]]:

        if not isinstance(query, str) or not query.strip():
            return []

        # BM25 ranking
        lexical = self.bm25.rank(query)

        # Character TF-IDF ranking
        vector = self.vector.rank(query)

        # Combine both rankings
        scores = reciprocal_rank_fusion(
            [lexical, vector]
        )

        # Explicit section matching
        match = SECTION_RE.search(query)

        if match:

            section = int(
                match.group(1).translate(DIGIT_MAP)
            )

            for index, item in enumerate(self.docs):

                try:
                    item_section = int(
                        str(item["section"]).translate(DIGIT_MAP)
                    )
                except (ValueError, TypeError):
                    continue

                if item_section == section:

                    scores[index] = (
                        scores.get(index, 0.0) + 1.0
                    )

        # Select top results
        limit = max(1, min(int(top), 20))

        selected = sorted(
            scores,
            key=lambda index: (
                -scores[index],
                index
            )
        )[:limit]

        results = []

        for index in selected:

            item = self.docs[index]

            results.append({

                "id": item["id"],

                "section": item["section"],

                "pdf_page_start": item["pdf_page_start"],

                "pdf_page_end": item["pdf_page_end"],

                "source_pdf": item["source_pdf"],

                "official_reference_url": item["official_reference_url"],

                "verification_state": item["verification_state"],

                "production_approved": False,

                "score": round(
                    scores[index],
                    6
                ),

                "text_bn": item["text_bn"]

            })

        return results

# Backward compatibility
BanglishRetriever = HybridRetriever
# ============================================================
# 8. COMMAND LINE INTERFACE
# ============================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Odhikar BD quarantined hybrid search preview"
        )
    )

    parser.add_argument(
        "query"
    )

    parser.add_argument(
        "--top",
        type=int,
        default=5
    )

    parser.add_argument(
        "--json",
        action="store_true"
    )

    args = parser.parse_args()

    try:

        retriever = HybridRetriever()

        results = retriever.search(
            args.query,
            args.top
        )

    except (
        FileNotFoundError,
        ValueError,
        KeyError,
        json.JSONDecodeError
    ) as exc:

        print(
            f"Retrieval error: {exc}",
            file=sys.stderr
        )

        return 1

    if args.json:

        print(
            json.dumps(
                {
                    "status": "DRAFT_ONLY_NOT_LEGAL_ADVICE",
                    "results": results
                },
                ensure_ascii=False,
                indent=2
            )
        )

    else:

        print(
            "WARNING: QUARANTINED DRAFT — "
            "NOT VERIFIED LEGAL ADVICE. "
            "NEVER USE FOR PENALTIES."
        )

        if not results:
            print("No matching draft documents found.")
            return 0

        for result in results:

            print(
                f"\n{result['id']} | "
                f"Section {result['section']} | "
                f"PDF p.{result['pdf_page_start']}"
                f"-{result['pdf_page_end']} | "
                f"RRF={result['score']:.5f}"
            )

            print(
                result["text_bn"][:450].replace(
                    "\n",
                    " "
                )
            )

    return 0


# ============================================================
# 9. ENTRY POINT
# ============================================================

if __name__ == "__main__":

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace"
        )

    sys.exit(main())
