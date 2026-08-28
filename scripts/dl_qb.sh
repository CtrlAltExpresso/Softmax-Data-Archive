#!/bin/bash
python3 - << 'PY'
import json,subprocess,os,concurrent.futures,time
d=json.load(open('/home/sakib2/softmax_dbg/api_data/web_pull/all_question_banks.json'))
outdir='/home/sakib2/softmax_dbg/downloads/question_bank_pdfs_all'
os.makedirs(outdir,exist_ok=True)
def safe(s):
    return ''.join(c if c.isalnum() or c in '._-' else '_' for c in s)
def dl(item):
    url=item.get('question_pdf')
    if not url: return None
    name=f"qb_{item['id']:04d}_{item.get('year','')}_{safe(item.get('institute_name',''))}_{safe(item.get('subject_name',''))}.pdf"
    path=os.path.join(outdir,name)
    if os.path.exists(path) and os.path.getsize(path)>5000: return (name,'already')
    try:
        r=subprocess.run(['/usr/bin/curl','-s','-L','--max-time','60','-o',path,url],capture_output=True)
        ok=os.path.exists(path) and open(path,'rb').read(5)==b'%PDF'
        os.remove(path) if os.path.exists(path) and not ok else None
        return (name,'ok' if ok else 'fail')
    except Exception as e:
        return (name,f'err {e}')
items=[x for x in d if x.get('question_pdf')]
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    for r in ex.map(dl,items):
        results.append(r)
from collections import Counter
print(Counter(x[1] for x in results))
open('/home/sakib2/softmax_dbg/api_data/web_pull/qb_dl_result.json','w').write(json.dumps(results))
print('failed:',[x[0] for x in results if x[1]!='ok'])
PY
