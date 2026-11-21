"""Apply Gazette-checked OCR line corrections to a NEW directory.

Put this script and odhikar_batch2_gazette_review_30.csv in C:\\Odhikar_Bd.
Run: python apply_odhikar_ocr_batch2.py

This does not alter the original OCR or existing verified_unicode files.
"""
from pathlib import Path
import csv
import json
import sys

PROJECT = Path.cwd()
SOURCE = PROJECT / 'data/processed/verified_unicode/road_transport_act_2018'
TARGET = PROJECT / 'data/processed/verified_unicode_batch2/road_transport_act_2018'
REVIEW = PROJECT / 'odhikar_batch2_gazette_review_30.csv'

if not REVIEW.is_file():
    sys.exit(f'Missing review CSV: {REVIEW}')
if TARGET.exists():
    sys.exit(f'ABORT: target already exists, will not overwrite: {TARGET}')

with REVIEW.open('r', encoding='utf-8-sig', newline='') as f:
    review = list(csv.DictReader(f))
if len(review) != 30:
    sys.exit(f'ABORT: expected 30 review rows, got {len(review)}')

pages = {}
for page in range(1, 48):
    path = SOURCE / f'page_{page:03d}.txt'
    if not path.is_file():
        sys.exit(f'ABORT: missing source {path}')
    pages[page] = path.read_text(encoding='utf-8').splitlines(keepends=True)

# Validate the exact old line at every indicated location BEFORE writing.
keys = set()
planned = []
for row in review:
    page = int(row['pdf_page'])
    line_no = int(row['line_number'])
    key = (page, line_no)
    if key in keys:
        sys.exit(f'ABORT: duplicate review location {key}')
    keys.add(key)
    if not 1 <= page <= 47 or not 1 <= line_no <= len(pages[page]):
        sys.exit(f'ABORT: invalid line location {key}')
    original = pages[page][line_no - 1].rstrip('\r\n')
    expected = row['suspicious_line']
    if original != expected:
        sys.exit(f'ABORT: source mismatch at page {page}, line {line_no}; no files changed')
    status = row['review_status']
    if status == 'verified_passage_correction':
        replacement = row['verified_correction']
        if not replacement or replacement == expected or '\n' in replacement:
            sys.exit(f'ABORT: invalid replacement at {key}')
        planned.append((page, line_no, replacement, row['review_id']))
    elif status != 'unchanged_valid_english':
        sys.exit(f'ABORT: unapproved review status at {key}: {status}')

# Keep exact line endings; make replacements in memory only.
for page, line_no, replacement, _ in planned:
    old = pages[page][line_no - 1]
    ending = '\r\n' if old.endswith('\r\n') else ('\n' if old.endswith('\n') else '')
    pages[page][line_no - 1] = replacement + ending

TARGET.mkdir(parents=True, exist_ok=False)
for page in range(1, 48):
    (TARGET / f'page_{page:03d}.txt').write_text(
        ''.join(pages[page]), encoding='utf-8', newline=''
    )
combined = []
for page in range(1, 48):
    combined.append(f"\n\n{'=' * 20}\nPDF PAGE {page}\n{'=' * 20}\n\n")
    combined.append(''.join(pages[page]))
(TARGET / 'full_corrected_unicode.txt').write_text(
    ''.join(combined), encoding='utf-8'
)
(TARGET / 'batch2_correction_log.json').write_text(
    json.dumps({
        'source': str(SOURCE),
        'review_file': REVIEW.name,
        'reviewed_lines': len(review),
        'corrected_lines': len(planned),
        'unchanged_lines': len(review)-len(planned),
        'amendments_checked': False,
        'rag_ready': False,
        'changes': [
            {'pdf_page': p, 'line_number': n, 'review_id': rid}
            for p, n, _, rid in planned
        ]
    }, indent=2, ensure_ascii=True), encoding='utf-8'
)
print('BATCH 2 COMPLETE')
print('REVIEWED LINES:', len(review))
print('CORRECTED LINES:', len(planned))
print('UNCHANGED VALID LINES:', len(review)-len(planned))
print('PAGES SAVED:', len(pages))
print('PREVIOUS VERIFIED UNICODE: UNCHANGED')
print('STATUS: PARTIALLY VERIFIED - NOT RAG READY')
print('OUTPUT:', TARGET)
