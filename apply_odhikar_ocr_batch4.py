"""Odhikar BD: Apply manually Gazette-reviewed Batch 4 lines.
Run from C:\\Odhikar_Bd with CSV in project root.
Never overwrites the input or an existing Batch 4 output.
"""
from pathlib import Path
import csv
import json
import shutil
from collections import Counter

ROOT = Path('data/processed')
SOURCE = ROOT / 'verified_unicode_batch3' / 'road_transport_act_2018'
TARGET = ROOT / 'verified_unicode_batch4' / 'road_transport_act_2018'
CSV_PATH = Path('odhikar_batch4_review_verified.csv')
EXPECTED_PAGES = {15, 16, 17, 18, 20}
EXPECTED_REVIEWED = 19
EXPECTED_CORRECTED = 16

if TARGET.exists():
    raise SystemExit(f'ERROR: Output already exists; refusing to overwrite: {TARGET}')
if not CSV_PATH.is_file():
    raise SystemExit(f'ERROR: Missing review CSV in project root: {CSV_PATH}')

with CSV_PATH.open(encoding='utf-8-sig', newline='') as file:
    entries = list(csv.DictReader(file))
if len(entries) != EXPECTED_REVIEWED:
    raise SystemExit(f'ERROR: Expected {EXPECTED_REVIEWED} review entries; got {len(entries)}')

pages = {}
for page_num in range(1, 48):
    path = SOURCE / f'page_{page_num:03d}.txt'
    if not path.is_file():
        raise FileNotFoundError(path)
    pages[page_num] = path.read_text(encoding='utf-8').splitlines(keepends=True)

seen = set()
changed = []
for entry in entries:
    page = int(entry['pdf_page'])
    line = int(entry['line_number'])
    key = (page, line)
    if page not in EXPECTED_PAGES or key in seen or line < 1 or line > len(pages[page]):
        raise RuntimeError(f'Invalid/duplicate page-line: {key}')
    seen.add(key)
    old = entry['original_line']
    new = entry['verified_line']
    status = entry['review_status']
    current = pages[page][line - 1].rstrip('\r\n')
    if current != old:
        raise RuntimeError(f'MISMATCH at page {page}, line {line}. No output files created.\nExpected: {old!r}\nFound: {current!r}')
    if status == 'correct':
        if new == old:
            raise RuntimeError(f'No change specified for corrected item {key}')
        changed.append(key)
    elif status == 'keep_unchanged':
        if new != old:
            raise RuntimeError(f'Unchanged item unexpectedly differs: {key}')
    else:
        raise RuntimeError(f'Unexpected status {status!r} at {key}')

if len(changed) != EXPECTED_CORRECTED:
    raise RuntimeError(f'Expected {EXPECTED_CORRECTED} corrected lines, got {len(changed)}')

# All checks passed. Apply ONLY the confirmed line replacements.
for entry in entries:
    if entry['review_status'] != 'correct':
        continue
    p, ln = int(entry['pdf_page']), int(entry['line_number'])
    original_with_eol = pages[p][ln - 1]
    eol = '\r\n' if original_with_eol.endswith('\r\n') else ('\n' if original_with_eol.endswith('\n') else '')
    pages[p][ln - 1] = entry['verified_line'] + eol

TARGET.mkdir(parents=True, exist_ok=False)
try:
    for p in range(1, 48):
        (TARGET / f'page_{p:03d}.txt').write_text(''.join(pages[p]), encoding='utf-8')
    combined = []
    for p in range(1, 48):
        combined.append(f"\n\n{'=' * 20}\nPDF PAGE {p}\n{'=' * 20}\n\n{''.join(pages[p])}")
    (TARGET / 'full_corrected_unicode.txt').write_text(''.join(combined), encoding='utf-8')
    (TARGET / 'batch4_correction_log.json').write_text(json.dumps(entries, ensure_ascii=True, indent=2), encoding='utf-8')
except Exception:
    shutil.rmtree(TARGET)
    raise

print('BATCH 4 COMPLETE')
print('REVIEWED LINES:', len(entries))
print('CORRECTED LINES:', len(changed))
print('UNCHANGED VALID LINES:', len(entries) - len(changed))
print('CHANGED PAGES:', sorted(set(p for p, _ in changed)))
print('PAGES SAVED:', len(pages))
print('BATCH 3 SOURCE: UNCHANGED')
print('STATUS: PARTIALLY VERIFIED - NOT RAG READY')
print('OUTPUT:', TARGET.resolve())
