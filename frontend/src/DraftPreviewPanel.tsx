
import { useState, type FormEvent } from "react";

const API_URL = "http://127.0.0.1:8001/api/draft-preview";

type Citation = {
  chunk_id: string;
  section: number;
  pdf_pages: number[];
  source_pdf?: string;
  verification_state: string;
};

type PreviewResult = {
  status: string;
  answer: string;
  citations: Citation[];
  blocked_reason: string | null;
  production_approved: boolean;
};

export default function DraftPreviewPanel() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<PreviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const question = query.trim();

    if (!question || loading) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: question }),
      });

      if (!response.ok) {
        throw new Error(`Backend error: HTTP ${response.status}`);
      }

      const data: PreviewResult = await response.json();

      if (
        data.status !== "DRAFT_ONLY_NOT_LEGAL_ADVICE" ||
        data.production_approved !== false ||
        !Array.isArray(data.citations) ||
        typeof data.answer !== "string"
      ) {
        throw new Error("Unexpected API response or safety status");
      }

      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Connection failed"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f8f7fc",
        padding: "40px 20px",
        color: "#211733",
      }}
    >
      <div
        style={{
          maxWidth: 760,
          margin: "0 auto",
          background: "#ffffff",
          borderRadius: 18,
          padding: 28,
          boxShadow: "0 8px 30px rgba(58, 35, 99, 0.08)",
        }}
      >
        <h1 style={{ color: "#7044B7" }}>
          Odhikar BD
        </h1>

        <h2>Draft AI Retrieval Demo</h2>

        <p
          style={{
            padding: 12,
            background: "#fff7ed",
            color: "#9a3412",
            borderRadius: 8,
          }}
        >
          DRAFT ONLY — This is not verified legal advice.
          Do not use these results to determine fines or penalties.
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="draft-question">
            Ask a Bangla or Banglish question
          </label>

          <textarea
            id="draft-question"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="license chara gari chalano jabe?"
            maxLength={800}
            rows={4}
            style={{
              display: "block",
              width: "100%",
              marginTop: 10,
              padding: 12,
              border: "1px solid #d6c6ec",
              borderRadius: 10,
              boxSizing: "border-box",
              font: "inherit",
            }}
          />

          <button
            type="submit"
            disabled={loading || !query.trim()}
            style={{
              marginTop: 12,
              padding: "12px 20px",
              background: "#7044B7",
              color: "#ffffff",
              border: "none",
              borderRadius: 10,
              cursor: "pointer",
            }}
          >
            {loading ? "Searching..." : "Search Draft"}
          </button>
        </form>

        {error && (
          <p role="alert" style={{ color: "#b91c1c" }}>
            {error}
          </p>
        )}

        {result && (
          <section style={{ marginTop: 28 }}>
            <h3>Retrieval Result</h3>

            <div
              style={{
                background: "#f4f0fa",
                padding: 18,
                borderRadius: 10,
                whiteSpace: "pre-wrap",
                lineHeight: 1.8,
              }}
            >
              {result.answer}
            </div>

            {result.blocked_reason && (
              <p style={{ color: "#b45309" }}>
                Blocked: {result.blocked_reason}
              </p>
            )}

            {result.citations.length > 0 && (
              <>
                <h3>Draft Source References</h3>

                <ul>
                  {result.citations.map((citation) => (
                    <li
                      key={citation.chunk_id}
                      style={{ marginBottom: 10 }}
                    >
                      ধারা {citation.section}
                      {" — PDF পৃষ্ঠা "}
                      {citation.pdf_pages.join("–")}
                      {" — "}
                      {citation.chunk_id}
                    </li>
                  ))}
                </ul>
              </>
            )}

            <p style={{ fontSize: 13, color: "#92400e" }}>
              Source documents are unverified.
              Production legal advice is disabled.
            </p>
          </section>
        )}

        <p style={{ marginTop: 28 }}>
          <a href="/" style={{ color: "#7044B7" }}>
            Back to Odhikar BD
          </a>
        </p>
      </div>
    </div>
  );
}
