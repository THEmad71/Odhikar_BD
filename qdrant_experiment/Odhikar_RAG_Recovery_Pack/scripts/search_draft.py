"""Offline lexical retrieval demo. Quarantined OCR only; do NOT use to answer legal advice."""
import argparse,json,math,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIGITS=str.maketrans('০১২৩৪৫৬৭৮৯','0123456789')
STOP={'কি','কী','এর','এই','এবং','বা','কোন','করে','হলে','জন্য','হয়','হবে','আমার','বাংলাদেশে','আইন','আইনে','ধারা'}
def tokens(text):
    text=text.lower().translate(DIGITS)
    return [x for x in re.findall(r'[\u0980-\u09ff\w]+',text) if len(x)>1 and x not in STOP]
def grams(text,n=3):
    text=re.sub(r'\s+',' ',text.lower().translate(DIGITS))
    return set(text[i:i+n] for i in range(max(0,len(text)-n+1)))
def search(query,top=5):
    data=[json.loads(line) for line in (ROOT/'rag_data'/'chunks_DRAFT.jsonl').read_text(encoding='utf8').splitlines() if line.strip()]
    q=set(tokens(query)); g=grams(query)
    scored=[]
    for item in data:
        words=set(tokens(item['text_bn']))
        intersection=len(q & words)
        overlaps=len(g & grams(item['text_bn']))
        score=3*intersection/(len(q) or 1)+overlaps/(len(g) or 1)
        if str(item['section']) in query.translate(DIGITS) and re.search(r'ধারা\s*[০-৯0-9]+',query): score+=0.3
        if score>0:scored.append((score,item))
    scored.sort(key=lambda x:x[0],reverse=True)
    return scored[:top]
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('question');p.add_argument('--top',type=int,default=5);a=p.parse_args()
    print('⚠️ DRAFT OCR RETRIEVAL: NOT VERIFIED LEGAL ADVICE. DO NOT USE FOR FINES OR PENALTIES.')
    for score,item in search(a.question,max(1,min(a.top,10))):
        print(f"\n{item['id']} | §{item['section']} | PDF p.{item['pdf_page_start']}–{item['pdf_page_end']} | score={score:.3f} | {item['verification_state']}")
        print(item['text_bn'][:500].replace('\n',' '))
