#!/bin/bash
TOKEN=$(cat /home/sakib2/softmax_dbg/api_data/.token)
KEY=$(cat /home/sakib2/softmax_dbg/api_data/.key)
B="https://softmaxmanager.xyz/api/v1/"
UA="Dart/3.2 (dart:io)"
OUTDIR="/home/sakib2/softmax_dbg/api_data/questions_all"
mkdir -p "$OUTDIR"
BASE="$B/exam/questions/?limit=200"
OFFSET=0
PAGE=0
while :; do
  PAGE=$((PAGE+1))
  FILE="$OUTDIR/questions_$(printf '%05d' $PAGE).json"
  /usr/bin/curl -s "$BASE&offset=$OFFSET" -H "Authorization: Bearer $TOKEN" -H "x-app-key: $KEY" -H "User-Agent: $UA" -H "Referer: yes" -o "$FILE"
  # parse count + results len
  RESULT=$(python3 -c "
import json,sys
try:
  d=json.load(open('$FILE'))
except Exception as e:
  print('ERR'); sys.exit()
print(d.get('count',0), len(d.get('results',[])))
")
  COUNT=$(echo $RESULT | cut -d' ' -f1)
  N=$(echo $RESULT | cut -d' ' -f2)
  echo "page $PAGE offset $OFFSET fetched $N (count=$COUNT)"
  OFFSET=$((OFFSET+N))
  if [ "$N" -lt 200 ] || [ "$OFFSET" -ge "$COUNT" ]; then echo "DONE at $OFFSET"; break; fi
  sleep 0.3
done
