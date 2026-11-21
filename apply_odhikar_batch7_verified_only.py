from pathlib import Path
import csv
import json
import shutil
import difflib

project = Path(__file__).resolve().parent
root = project / 'data' / 'processed'
source = root / 'verified_unicode_batch6' / 'road_transport_act_2018'
target = root / 'verified_unicode_batch7' / 'road_transport_act_2018'
csv_path = project / 'odhikar_batch7_pending_review_status.csv'

if not csv_path.is_file():
    raise FileNotFoundError(csv_path)
if target.exists():
    raise FileExistsError(f'Target already exists; refusing to overwrite: {target}')

with csv_path.open(encoding='utf-8-sig', newline='') as fh:
    rows = list(csv.DictReader(fh))
fixes = [r for r in rows if r.get('review_status') == 'verified_correction_batch7']
if len(rows) != 63 or len(fixes) != 2:
    raise ValueError('CSV counts changed; expected 63 total and 2 verified fixes')

pages = {}
for page in range(1, 48):
    file = source / f'page_{page:03d}.txt'
    if not file.is_file():
        raise FileNotFoundError(file)
    pages[page] = file.read_text(encoding='utf-8')

# Confirm exact line numbers and contents BEFORE writing anything.
changed_lines = {}
for row in fixes:
    page = int(row['pdf_page'])
    lineno = int(row['line_number'])
    lines = pages[page].splitlines(keepends=True)
    if lineno < 1 or lineno > len(lines):
        raise ValueError(f'Invalid line {lineno} in page {page}')
    current = lines[lineno - 1].rstrip('\r\n')
    if current != row['suspicious_line']:
        raise ValueError(f'Page {page} line {lineno} differs from review CSV')
    old = row['old_fragment']
    new = row['new_fragment']
    if not old or current.count(old) != 1:
        raise ValueError(f'Page {page} line {lineno} fragment does not occur exactly once')
    if current.replace(old, new, 1) != row['corrected_line']:
        raise ValueError(f'Corrected line mismatch at page {page}, line {lineno}')
    key = (page, lineno)
    if key in changed_lines:
        raise ValueError(f'Duplicate correction location: {key}')
    changed_lines[key] = row

updated = {}
for page, text in pages.items():
    lines = text.splitlines(keepends=True)
    for (p, n), row in changed_lines.items():
        if p == page:
            lines[n - 1] = lines[n - 1].replace(row['old_fragment'], row['new_fragment'], 1)
    updated[page] = ''.join(lines)

# Verify that only the two intended lines changed.
actual = []
for page in range(1, 48):
    a = pages[page].splitlines()
    b = updated[page].splitlines()
    if len(a) != len(b):
        raise RuntimeError(f'Unexpected line count change on page {page}')
    actual.extend((page, i) for i, (x, y) in enumerate(zip(a, b), 1) if x != y)
if sorted(actual) != sorted(changed_lines):
    raise RuntimeError(f'Unexpected changes: {actual}')

# Commit to a new target only after all validations pass.
target.mkdir(parents=True, exist_ok=False)
for page in range(1, 48):
    (target / f'page_{page:03d}.txt').write_text(updated[page], encoding='utf-8')
combined = ''.join(f'\n\n{"="*20}\nPDF PAGE {p}\n{"="*20}\n\n{updated[p]}' for p in range(1, 48))
(target / 'full_corrected_unicode.txt').write_text(combined, encoding='utf-8')
(target / 'batch7_correction_log.json').write_text(json.dumps(fixes, ensure_ascii=False, indent=2), encoding='utf-8')
print('BATCH 7 COMPLETE')
print('VERIFIED CHANGES:', len(actual))
print('PENDING REVIEW:', sum(r.get('review_status','').startswith('pending') for r in rows))
print('CHANGED PAGES:', sorted(set(p for p, _ in actual)))
print('PAGES PRESERVED:', len(updated))
print('BATCH 6 SOURCE: UNCHANGED')
print('STATUS: PARTIALLY VERIFIED - NOT RAG READY')
print('OUTPUT:', target)
