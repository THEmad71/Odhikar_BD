"""Build a provenance-preserving, QUARANTINED Bengali legal retrieval dataset.
No source file is edited. No chunk is marked production-approved automatically.
Requires Python 3.10+; no third-party libraries.
"""
from __future__ import annotations
import csv, hashlib, json, re, sys
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]
DIGIT = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
SECTION_RE = re.compile(r'^\s*([০-৯]{1,3})[।.]\s*(.+)')
MAX_CHARS = 1900

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dumpjson(path, obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def build():
    page_lines = {}; files={}; positions=[]
    for p in range(1,48):
        f=ROOT/'source_pages'/f'page_{p:03d}.txt'
        if not f.exists(): raise RuntimeError(f'Missing source page: {f}')
        lines=f.read_text(encoding='utf-8-sig').splitlines()
        page_lines[p]=lines; files[f.name]=digest(f)
        for line_num, line in enumerate(lines,1):
            positions.append({'page':p,'line':line_num,'text':line})
    starts=[]
    for ix,ln in enumerate(positions):
        m=SECTION_RE.match(ln['text'])
        if m:
            sec=int(m.group(1).translate(DIGIT))
            if 1<=sec<=126: starts.append((sec,ix))
    numbers=[n for n,_ in starts]
    if numbers!=list(range(1,127)):
        raise RuntimeError(f'Section numbering failed: {numbers}; expected 1..126')
    with (ROOT/'reports'/'batch11_review_decisions.csv').open(encoding='utf-8-sig',newline='') as f:
        decisions=list(csv.DictReader(f))
    outcomes=Counter(d.get('audit_outcome','') for d in decisions)
    # Retain all source issue decisions. A manually fixed item is not proof of full-line certification.
    by_pos={}
    for d in decisions:
        try:key=(int(d['pdf_page']),int(d['line_number']))
        except (ValueError,KeyError):continue
        by_pos.setdefault(key,[]).append(d)
    chunks=[]; section_index=[]; section_blocks=[]
    preamble=positions[:starts[0][1]]
    dumpjson(ROOT/'rag_data'/'preamble_DRAFT.json', {
       'status':'DRAFT_UNVERIFIED_FULL_TEXT', 'page_start':1, 'page_end':preamble[-1]['page'] if preamble else 1,
       'text_bn':'\n'.join(v['text'] for v in preamble), 'production_approved':False})
    for j,(sec,start) in enumerate(starts):
        end=starts[j+1][1] if j+1<len(starts) else len(positions)
        block=positions[start:end]
        section_blocks.append((sec,block))
        # section can span pages; 1900 char max allows reasonable vector chunking later.
        slices=[]; working=[]; count=0
        for ln in block:
            length=len(ln['text'])+1
            if working and count+length>MAX_CHARS:
                slices.append(working); working=[];count=0
            working.append(ln);count+=length
        if working:slices.append(working)
        section_index.append({'section':sec,'first_page':block[0]['page'],'last_page':block[-1]['page'], 'line_count':len(block),'parts':len(slices)})
        for k,part in enumerate(slices,1):
            # Issues may be logged against original OCR line numbers; location mapping is a clue, not a verification certificate.
            flags=[{'review_id':d.get('review_id'), 'outcome':d.get('audit_outcome'), 'issue_type':d.get('issue_type'), 'pdf_page':ln['page'],'line':ln['line']}
                for ln in part for d in by_pos.get((ln['page'],ln['line']),[])]
            text='\n'.join(ln['text'] for ln in part)
            record={'id':f'RTA2018-S{sec:03d}-P{k:02d}', 'act_id':'BD-RTA-2018-47',
                'act_title_bn':'সড়ক পরিবহণ আইন, ২০১৮', 'section':sec, 'part':k,
                'pdf_page_start':part[0]['page'], 'pdf_page_end':part[-1]['page'],
                'line_start':part[0]['line'], 'line_end':part[-1]['line'],
                'text_bn':text, 'text_sha256':hashlib.sha256(text.encode()).hexdigest(),
                'source_pdf':'road_transport_act_2018_OFFICIAL_SOURCE.pdf',
                'official_reference_url':'https://bdlaws.minlaw.gov.bd/act-print-1262.html',
                'audit_flags':flags,
                'verification_state':'DRAFT_UNVERIFIED_FULL_TEXT',
                'production_approved':False, 'amendment_currency_checked':False,
                'legal_penalty_verified':False}
            chunks.append(record)
    out=ROOT/'rag_data'/'chunks_DRAFT.jsonl'
    with out.open('w',encoding='utf-8') as f:
        for ch in chunks:f.write(json.dumps(ch,ensure_ascii=False)+'\n')
    with (ROOT/'rag_data'/'section_index.json').open('w',encoding='utf-8') as f:
        json.dump(section_index,f,ensure_ascii=False,indent=2)
    src_pdf=ROOT/'source_pages'/'road_transport_act_2018_OFFICIAL_SOURCE.pdf'
    if not src_pdf.exists(): raise RuntimeError('Missing original Gazette PDF')
    sha={'pdf_sha256':digest(src_pdf),'page_sha256':files}
    dumpjson(ROOT/'reports'/'sha256_source_manifest.json',sha)
    dumpjson(ROOT/'reports'/'release_gate.json',{
       'release_status':'BLOCKED_NOT_PRODUCTION_RAG_READY',
       'basis':'Batch11 targeted source-corrected OCR, not full-passage certified',
       'source_pages':47,'sections_found':len(section_index),'chunks_created':len(chunks),
       'audit_review_records':len(decisions),'audit_outcomes':dict(outcomes),
       'unresolved_review_count':outcomes['requires_visual_source_review'],
       'partial_latin_matches_not_full_verification':outcomes['english_terms_present_in_source'],
       'production_approved_chunks':0,
       'required_before_release':['Resolve outstanding source review and certify all relevant full passages',
          'Compare all penalties / imprisonment with Gazette and current authoritative law',
          'Check subsequent amendment and effective-date history',
          'Validate every chunk page/section alignment and cross-page completeness',
          'Build and test production embedding + BM25 indexes',
          'Run cited-answer faithfulness, abstention and regression evaluations',
          'Security and production integration tests']})
    print(json.dumps({'sections':len(section_index),'chunks':len(chunks),'status':'DRAFT_ONLY','audit':dict(outcomes)},ensure_ascii=False))
    return chunks
if __name__=='__main__': build()
