"""Odhikar BD: safe incremental OCR patch; requires Batch 5 folder."""
from pathlib import Path
import csv, json, shutil

project = Path(__file__).resolve().parent
source = project / 'data/processed/verified_unicode_batch5/road_transport_act_2018'
target = project / 'data/processed/verified_unicode_batch6/road_transport_act_2018'
review = project / 'odhikar_pending_43_review_batch6.csv'

with review.open(encoding='utf-8-sig',newline='') as f:
    rows=list(csv.DictReader(f))
changes=[r for r in rows if r['review_status']=='verified_change_batch6']
pending=[r for r in rows if r['review_status']=='pending_manual_visual_check']
assert len(rows)==63 and len(changes)==8 and len(pending)==35, 'Unexpected review counts'
assert len({(r['pdf_page'],r['line_number']) for r in changes})==8

pages={}
for n in range(1,48):
    path=source / f'page_{n:03d}.txt'
    if not path.is_file(): raise FileNotFoundError(path)
    pages[n]=path.read_text(encoding='utf-8')

# Every source line must match EXACTLY before writing anything.
for r in changes:
    p=int(r['pdf_page']); line=int(r['line_number']); lines=pages[p].splitlines(keepends=True)
    if not 1<=line<=len(lines): raise RuntimeError(f'Invalid line number {p}:{line}')
    raw=lines[line-1].rstrip('\r\n')
    if raw!=r['original_line']:
        raise RuntimeError(f'Source line mismatch at PDF page {p}, OCR line {line}. No files written.')
    if raw.count(r['old_fragment'])!=1:
        raise RuntimeError(f'Fragment not unique at {p}:{line}. No files written.')

# Change only the reviewed line, preserve exact newline endings.
updated=pages.copy()
for p in sorted({int(r['pdf_page']) for r in changes}):
    lines=updated[p].splitlines(keepends=True)
    for r in [r for r in changes if int(r['pdf_page'])==p]:
        i=int(r['line_number'])-1
        assert r['original_line'] in lines[i]
        lines[i]=lines[i].replace(r['old_fragment'],r['new_fragment'],1)
        if lines[i].rstrip('\r\n')!=r['corrected_line']:
            raise RuntimeError(f'Post-patch mismatch at page {p}, line {i+1}')
    updated[p]=''.join(lines)

# Never overwrite existing batch6 output.
if target.exists():
    raise FileExistsError(f'Target already exists: {target}; refusing to overwrite')
target.mkdir(parents=True)
for n in range(1,48):
    (target/f'page_{n:03d}.txt').write_text(updated[n],encoding='utf-8',newline='')
combined=[]
for n in range(1,48):
    combined.append(f'\n\n====================\nPDF PAGE {n}\n====================\n\n{updated[n]}')
(target/'full_corrected_unicode.txt').write_text(''.join(combined),encoding='utf-8')
(target/'batch6_correction_log.json').write_text(json.dumps([{k:r[k] for k in ['pdf_page','line_number','old_fragment','new_fragment','original_line','corrected_line','review_notes']} for r in changes],ensure_ascii=False,indent=2),encoding='utf-8')
print('BATCH 6 COMPLETE')
print('VERIFIED CHANGES:',len(changes))
print('PENDING REVIEW:',len(pending))
print('PAGES PRESERVED:',len(updated))
print('CHANGED PAGES:', sorted({int(r['pdf_page']) for r in changes}))
print('BATCH 5 SOURCE: UNCHANGED')
print('STATUS: PARTIALLY VERIFIED - NOT RAG READY')
print('OUTPUT:',target)
