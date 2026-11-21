"""Apply manually Gazette-checked Batch 3 corrections without touching original OCR / Batch 2.

Place this script and odhikar_batch3_review_verified_41_44.csv in C:\\Odhikar_Bd.
Run: python .\\apply_odhikar_ocr_batch3.py
"""
from pathlib import Path
from collections import Counter
import csv
import json
import sys

PROJECT = Path(__file__).resolve().parent
BASE = PROJECT / 'data/processed/verified_unicode_batch2/road_transport_act_2018'
DEST = PROJECT / 'data/processed/verified_unicode_batch3/road_transport_act_2018'
CSV = PROJECT / 'odhikar_batch3_review_verified_41_44.csv'

with CSV.open('r', encoding='utf-8-sig', newline='') as f:
    review = list(csv.DictReader(f))
if len(review) != 19:
    raise RuntimeError(f'Expected 19 review rows, got {len(review)}. Nothing written.')

pages = {}
for num in range(1, 48):
    path = BASE / f'page_{num:03d}.txt'
    if not path.is_file():
        raise FileNotFoundError(f'Missing Batch 2 page: {path}')
    pages[num] = path.read_text(encoding='utf-8').splitlines(keepends=True)

changes = []
seen = set()
statuses = Counter()
for r in review:
    page, line_num = int(r['pdf_page']), int(r['line_number'])
    key = (page, line_num)
    if key in seen or not (41 <= page <= 44):
        raise RuntimeError(f'Invalid or duplicate review key {key}; no output written')
    seen.add(key)
    lines = pages[page]
    if not 1 <= line_num <= len(lines):
        raise RuntimeError(f'Out-of-range line {key}; no output written')
    actual = lines[line_num-1].rstrip('\r\n')
    expected = r['suspicious_line']
    if actual != expected:
        raise RuntimeError(f'SOURCE MISMATCH page {page} line {line_num}: Dataset differs from review CSV. No output written.')
    status = r['review_status']
    statuses[status] += 1
    revised = r['verified_line']
    if status == 'correction_verified_against_2018_gazette':
        if revised == expected:
            raise RuntimeError(f'No change in correction row {key}')
        changes.append((page, line_num, expected, revised))
    elif status == 'valid_english_legal_reference_no_change':
        if revised != expected:
            raise RuntimeError(f'Unchanged row unexpectedly changes text at {key}')
    else:
        raise RuntimeError(f'Unknown review status: {status}')
if len(changes) != 13 or statuses['valid_english_legal_reference_no_change'] != 6:
    raise RuntimeError(f'Unexpected review counts: {dict(statuses)}')

# After ALL checks, modify only an in-memory copy
for page, line_num, old, new in changes:
    existing = pages[page][line_num-1]
    ending = '\r\n' if existing.endswith('\r\n') else ('\n' if existing.endswith('\n') else '')
    pages[page][line_num-1] = new + ending

DEST.mkdir(parents=True, exist_ok=True)
for num in range(1,48):
    (DEST / f'page_{num:03d}.txt').write_text(''.join(pages[num]), encoding='utf-8', newline='')

# Generate merged text from all pages while retaining the prior pipeline's page markers
merged = ''.join(
    f'\n\n{"="*20}\nPDF PAGE {num}\n{"="*20}\n\n' + ''.join(pages[num])
    for num in range(1,48)
)
(DEST / 'full_corrected_unicode.txt').write_text(merged,encoding='utf-8')
(DEST / 'batch3_correction_log.json').write_text(
    json.dumps([
        dict(pdf_page=page, line_number=line, old_text=old, corrected_text=new,
             source='Road Transport Act 2018, Gazette PDF', verification_scope='selected OCR line only')
        for page,line,old,new in changes
    ],ensure_ascii=False,indent=2),encoding='utf-8'
)
print('BATCH 3 COMPLETE')
print('REVIEWED LINES:',len(review))
print('CORRECTED LINES:',len(changes))
print('UNCHANGED LEGAL REFERENCE LINES:',statuses['valid_english_legal_reference_no_change'])
print('CHANGED PAGES:',sorted({x[0] for x in changes}))
print('PAGES SAVED:',len(pages))
print('BATCH 2 SOURCE: UNCHANGED')
print('STATUS: PARTIALLY VERIFIED - NOT RAG READY')
print('OUTPUT:',DEST)
