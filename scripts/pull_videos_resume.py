import json, subprocess, time, os, re
TOKEN=open('/home/sakib2/softmax_dbg/api_data/.token').read().strip()
OUTDIR='/home/sakib2/softmax_dbg/api_data/web_pull/videos'
LOG='/home/sakib2/softmax_dbg/api_data/web_pull/pull_videos.log'
HDRS=['-H',f'Authorization: Bearer {TOKEN}','-H','User-Agent: Dart/3.2 (dart:io)','-H','Referer: yes','-H','x-app-key: l0dtpwvzzmM']
TOTAL=42482

def log(m):
    print(m, flush=True)
    with open(LOG,'a') as f: f.write(m+'\n')

valid=[]
for fn in os.listdir(OUTDIR):
    m=re.match(r'page_(\d+).json',fn)
    if not m: continue
    pg=int(m.group(1))
    try:
        json.load(open(os.path.join(OUTDIR,fn)))
        valid.append(pg)
    except Exception:
        pass
valid.sort()
max_page = valid[-1] if valid else 0
start_off = max_page*100          # next offset to fetch
start_page = max_page + 1         # next page number to name
log(f"resume: offset {start_off}, page {start_page}  (already have pages 1..{max_page})")

off=start_off
page=start_page
ok=0
while off < TOTAL:
    url=f'https://softmaxmanager.xyz/api/v1/app/web/videos/?limit=100&offset={off}'
    r=subprocess.run(['/usr/bin/curl','-s','-w','\n%{http_code}','-o','/tmp/vpage.json']+HDRS+[url],capture_output=True)
    code=r.stdout.decode().strip().split('\n')[-1] if r.stdout else 'ERR'
    try:
        d=json.load(open('/tmp/vpage.json'))
        results=d.get('results')
        if isinstance(results,list) and len(results)>0 and code=='200':
            out=f'{OUTDIR}/page_{page:04d}.json'
            open(out,'w').write(open('/tmp/vpage.json').read())
            ok+=len(results)
            log(f"page {page}: offset {off} -> {len(results)} (run total {ok})")
            page+=1; off+=len(results)
            time.sleep(1.5)
        else:
            log(f"page {page}: MASK offset {off} code={code} len={len(results) if isinstance(results,list) else 0}; backoff 25s")
            time.sleep(25)
    except Exception as e:
        log(f"page {page}: parse err {e} offset {off}; backoff 25s")
        time.sleep(25)
log(f"DONE captured {ok} more (offset now {off})")
