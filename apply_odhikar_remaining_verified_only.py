"""Apply ONLY Gazette-image-verified changes; retain 43 pending OCR lines unchanged.
Run from C:\\Odhikar_Bd with this script and odhikar_remaining_31_pages_review_status.csv
placed in project root. Python 3.9+.
"""
from pathlib import Path
from collections import Counter
import csv, json, difflib

project=Path.cwd()
csv_path=project/'odhikar_remaining_31_pages_review_status.csv'
source=project/'data/processed/verified_unicode_batch4/road_transport_act_2018'
target=project/'data/processed/verified_unicode_batch5/road_transport_act_2018'

with csv_path.open('r',encoding='utf-8-sig',newline='') as f:
    records=list(csv.DictReader(f))
assert len(records)==63, f'Expected 63 review records, got {len(records)}'
status=Counter(r['review_status'] for r in records)
assert status=={'verified_change':11,'verified_retain':9,'pending_manual_visual_check':43},status
assert not target.exists(),f'Target already exists; refusing overwrite: {target}'
original={}
for page in range(1,48):
    p=source/f'page_{page:03d}.txt'
    original[page]=p.read_text(encoding='utf-8')
modified=dict(original)
log=[]
for r in records:
    if r['review_status']!='verified_change':
        continue
    page=int(r['pdf_page']); line_no=int(r['line_number'])
    old=r['old_fragment'];new=r['new_fragment'];orig_line=r['original_line'];new_line=r['corrected_line']
    lines=modified[page].splitlines(keepends=True)
    assert 1<=line_no<=len(lines),(page,line_no,len(lines))
    line=lines[line_no-1]
    assert line.rstrip('\r\n')==orig_line,(page,line_no,'source line changed; stop')
    assert old and line.count(old)==1,(page,line_no,'fragment mismatch')
    changed=line.replace(old,new,1)
    assert changed.rstrip('\r\n')==new_line,(page,line_no,'unexpected replacement')
    lines[line_no-1]=changed
    modified[page]=''.join(lines)
    log.append({'page':page,'line_number':line_no,'old_fragment':old,'new_fragment':new,'original_line':orig_line,'corrected_line':new_line,'source_pdf':r['source_pdf'],'notes':r['review_notes']})

assert len(log)==11
changed_pages=sorted(p for p in original if original[p]!=modified[p])
# All changes must be exactly on approved lines. Detect accidental line changes.
approved={(x['page'],x['line_number']) for x in log}
actual=set()
for p in original:
    a=original[p].splitlines();b=modified[p].splitlines()
    assert len(a)==len(b),(p,'line count changed')
    actual|={(p,i) for i,(old,new) in enumerate(zip(a,b),1) if old!=new}
assert actual==approved,(actual-approved,approved-actual)
# Only after full validation, create the target. All source pages stay unmodified.
target.mkdir(parents=True,exist_ok=False)
for p in range(1,48):
    (target/f'page_{p:03d}.txt').write_text(modified[p],encoding='utf-8')
combined=''.join(f'\n\n{"="*20}\nPDF PAGE {p}\n{"="*20}\n\n{modified[p]}' for p in range(1,48))
(target/'full_corrected_unicode.txt').write_text(combined,encoding='utf-8')
(target/'verified_changes_log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
(target/'review_status_summary.json').write_text(json.dumps({'reviewed_lines':63,'verified_changes':11,'verified_retain':9,'pending':43,'changed_pages':changed_pages,'rag_ready':False},indent=2),encoding='utf-8')
print('COMBINED REVIEW SAFE APPLY COMPLETE')
print('REVIEWED:',len(records))
print('VERIFIED CHANGES:',len(log))
print('VERIFIED RETAIN:',status['verified_retain'])
print('PENDING UNCHANGED:',status['pending_manual_visual_check'])
print('CHANGED PAGES:',changed_pages)
print('PAGES PRESERVED:',len(modified))
print('BATCH 4 SOURCE: UNCHANGED')
print('STATUS: PARTIALLY VERIFIED - NOT RAG READY')
print('OUTPUT:',target)
