import json, subprocess, time, os, sys
TOKEN=open('/home/sakib2/softmax_dbg/api_data/.token').read().strip()
OUT='/home/sakib2/softmax_dbg/api_data/web_pull'
os.makedirs(OUT, exist_ok=True)
HDRS=['-H',f'Authorization: Bearer {TOKEN}','-H','User-Agent: Dart/3.2 (dart:io)','-H','Referer: yes','-H','x-app-key: l0dtpwvzzmM']
LOG=os.path.join(OUT,'pull_web_remaining.log')

def log(m):
    print(m, flush=True)
    with open(LOG,'a') as f: f.write(m+'\n')

EPISODES=['chapters','subjects','courses','smart-books','probidhan']

def get_count(ep):
    url=f'https://softmaxmanager.xyz/api/v1/app/web/{ep}/?limit=1'
    subprocess.run(['/usr/bin/curl','-s','-o','/tmp/c.json']+HDRS+[url],capture_output=True)
    try: return json.load(open('/tmp/c.json')).get('count',0)
    except: return 0

def pull(ep):
    total=get_count(ep)
    log(f"[{ep}] total={total}")
    allres=[]
    off=0
    stall=0
    while off < total:
        url=f'https://softmaxmanager.xyz/api/v1/app/web/{ep}/?limit=100&offset={off}'
        subprocess.run(['/usr/bin/curl','-s','-o','/tmp/p.json']+HDRS+[url],capture_output=True)
        try:
            d=json.load(open('/tmp/p.json'))
            res=d.get('results')
        except Exception as e:
            res=None
        if isinstance(res,list) and len(res)>0 and d.get('count') is not None:
            allres.extend(res)
            log(f"[{ep}] offset {off} +{len(res)} (total {len(allres)})")
            off+=len(res)
            stall=0
            time.sleep(1.4)
        else:
            stall+=1
            log(f"[{ep}] MASK offset {off}; backoff {20*stall}s")
            time.sleep(20*stall)
    out=f'{OUT}/all_{ep}.json'
    json.dump(allres, open(out,'w'), ensure_ascii=False)
    log(f"[{ep}] DONE {len(allres)} -> {out}")
    time.sleep(2)

for ep in EPISODES:
    pull(ep)
log("ALL WEB REMAINING DONE")
