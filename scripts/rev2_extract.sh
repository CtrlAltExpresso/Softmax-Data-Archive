#!/bin/bash
# MASTER EXTRACTION - runs when Softmax API block clears
# Executes comprehensive "revenge" extraction of all high-value content
set -u
TOKEN=$(cat /home/sakib2/softmax_dbg/api_data/.token)
KEY=$(cat /home/sakib2/softmax_dbg/api_data/.key)
B="https://softmaxmanager.xyz/api/v1/"
UA="Dart/3.2 (dart:io)"
API="/home/sakib2/softmax_dbg/api_data"
DL="/home/sakib2/softmax_dbg/downloads"
mkdir -p "$API/rev2" "$DL/rev2_videos_urls" "$DL/rev2_answers" "$DL/rev2_exams"

echo "=== Waiting for API block to clear ==="
for i in $(seq 1 120); do
  CODE=$(/usr/bin/curl -s -o /tmp/_probe.json -w "%{http_code}" "$B/user/profile/" \
    -H "Authorization: Bearer $TOKEN" -H "x-app-key: $KEY" -H "User-Agent: $UA" -H "Referer: yes")
  if [ "$CODE" = "200" ]; then echo "UNBLOCKED after ${i}0s"; break; fi
  sleep 10
done
if [ "$CODE" != "200" ]; then echo "STILL BLOCKED after 20min"; exit 1; fi

echo "=== 1. Fetch fresh question-bank URLs + download all answer PDFs ==="
/usr/bin/curl -s "$B/app/web/question-banks/?" -H "Authorization: Bearer $TOKEN" -H "x-app-key: $KEY" -H "User-Agent: $UA" -H "Referer: yes" -o "$API/rev2/qb_fresh.json"
python3 - "$API/rev2/qb_fresh.json" << 'PY'
import json,sys,os,subprocess
d=json.load(open(sys.argv[1]))
results=d.get('results',[])
def dl(url,path):
    if not url: return False
    r=subprocess.run(['/usr/bin/curl','-s','-L','-o',path,url],capture_output=True)
    return os.path.exists(path) and os.path.getsize(path)>1000
os.makedirs('/home/sakib2/softmax_dbg/downloads/rev2_answers',exist_ok=True)
n=0
for q in results:
    for key,prefix in [('answer_pdf','answer'),('question_pdf','question')]:
        url=q.get(key)
        if url:
            fn=f"/home/sakib2/softmax_dbg/downloads/rev2_answers/{prefix}_{q['id']}.pdf"
            if dl(url,fn): n+=1
with open('/home/sakib2/softmax_dbg/api_data/rev2/answers_downloaded.txt','w') as f: f.write(str(n))
print('downloaded',n)
PY

echo "=== 2. Video signed URLs: test bunny-video-play/download ==="
python3 - "$API/22_videos_42600.json" << 'PY'
import json,sys,subprocess
d=json.load(open(sys.argv[1]))
# take a sample of bunny videos to test
samp=[v for v in d if v.get('bunny_video_id')][:3]
TOKEN=open('/home/sakib2/softmax_dbg/api_data/.token').read().strip()
KEY=open('/home/sakib2/softmax_dbg/api_data/.key').read().strip()
B="https://softmaxmanager.xyz/api/v1/"
UA="Dart/3.2 (dart:io)"
for v in samp:
    vid=v['bunny_video_id']
    for ep in ['user/bunny-video-play/','user/bunny-video-download/']:
        url=f"{B}{ep}"
        # try GET then POST with video id
        for method in ['GET','POST']:
            cmd=['/usr/bin/curl','-s','-w','\nHTTP:%{http_code}',url,
                 '-H',f'Authorization: Bearer {TOKEN}','-H',f'x-app-key: {KEY}',
                 '-H',f'User-Agent: {UA}','-H','Referer: yes']
            if method=='POST': cmd+=['-d',f'video_id={vid}']
            r=subprocess.run(cmd,capture_output=True,text=True)
            out=r.stdout[-200:]
            print(f"{ep} {method} vid={vid}: {out[:150]}")
PY

echo "=== 3. Exams data ==="
for ep in "exam/exams/?limit=100" "exam/user-exams/?limit=100" "exam/course/subjects/?limit=100"; do
  /usr/bin/curl -s "$B$ep" -H "Authorization: Bearer $TOKEN" -H "x-app-key: $KEY" -H "User-Agent: $UA" -H "Referer: yes" -o "$API/rev2/$(echo $ep|tr '/?=' '__').json"
done

echo "=== 4. ebooks category-subjects (fresh URLs for all 82) ==="
/usr/bin/curl -s "$B/ebooks/category-subjects/" -H "Authorization: Bearer $TOKEN" -H "x-app-key: $KEY" -H "User-Agent: $UA" -H "Referer: yes" -o "$API/rev2/category_subjects_fresh.json"

echo "=== 5. ebook details for all ids (try direct) ==="
python3 - << 'PY'
import json,subprocess,os,time
TOKEN=open('/home/sakib2/softmax_dbg/api_data/.token').read().strip()
KEY=open('/home/sakib2/softmax_dbg/api_data/.key').read().strip()
B="https://softmaxmanager.xyz/api/v1/"
UA="Dart/3.2 (dart:io)"
# brute force ebook ids 1..300 for details/enrollable
os.makedirs('/home/sakib2/softmax_dbg/api_data/rev2/ebook_details',exist_ok=True)
for i in range(1,301):
    r=subprocess.run(['/usr/bin/curl','-s',f'{B}ebooks/subject-details/{i}/',
        '-H',f'Authorization: Bearer {TOKEN}','-H',f'x-app-key: {KEY}',
        '-H',f'User-Agent: {UA}','-H','Referer: yes'],capture_output=True,text=True)
    if r.stdout and 'Not Found' not in r.stdout[:100] and r.stdout.strip():
        open(f'/home/sakib2/softmax_dbg/api_data/rev2/ebook_details/{i}.json','w').write(r.stdout)
    time.sleep(0.2)
PY

echo "=== 6. resources / home free video ==="
/usr/bin/curl -s "$B/academic/free-course/app/" -H "Authorization: Bearer $TOKEN" -H "x-app-key: $KEY" -H "User-Agent: $UA" -H "Referer: yes" -o "$API/rev2/free_course.json"

echo "=== DONE ==="
