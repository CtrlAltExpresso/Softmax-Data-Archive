#!/usr/bin/env python3
"""
Re-fetch ALL video metadata from Softmax API.
API has 42,468 unique videos (IDs 1-43675, some gaps).
Previous fetch had pagination bug — only captured 200 unique.
"""
import json, subprocess, time, sys
from pathlib import Path

DIR = Path("/home/sakib2/softmax_dbg")
TOKEN = open(DIR / "api_data/.token").read().strip()
KEY = open(DIR / "api_data/.key").read().strip()
BASE = "https://softmaxmanager.xyz/api/v1"
UA = "user-agent: Dart/3.2 (dart:io)"
OUT = DIR / "downloads/video_metadata/all_videos_42468.json"
PAGE_SIZE = 200

def fetch_page(offset, limit=PAGE_SIZE):
    url = f"{BASE}/app/web/videos/?limit={limit}&offset={offset}"
    cmd = [
        "curl", "-s", "-m", "30",
        url,
        "-H", f"authorization: Bearer {TOKEN}",
        "-H", f"x-app-key: {KEY}",
        "-H", UA,
        "-H", "accept: application/json"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    try:
        return json.loads(r.stdout)
    except:
        return None

def main():
    # Get total count
    first = fetch_page(0, 1)
    if not first:
        print("Failed to fetch first page")
        sys.exit(1)
    total = first["count"]
    print(f"Total videos: {total}")

    all_videos = []
    offset = 0
    errors = 0
    t0 = time.time()

    while offset < total:
        data = fetch_page(offset)
        if not data or "results" not in data:
            errors += 1
            if errors > 10:
                print(f"Too many errors at offset {offset}, stopping")
                break
            time.sleep(2)
            continue

        results = data["results"]
        all_videos.extend(results)
        errors = 0

        elapsed = time.time() - t0
        rate = len(all_videos) / elapsed if elapsed > 0 else 0
        pct = len(all_videos) / total * 100
        eta = (total - len(all_videos)) / rate / 60 if rate > 0 else 0
        print(f"  [{len(all_videos)}/{total}] {pct:.1f}% | {rate:.0f}/s | ETA {eta:.0f}min", end='\r')

        offset += PAGE_SIZE
        time.sleep(0.3)  # Rate limit courtesy

    print(f"\nFetched {len(all_videos)} videos in {time.time()-t0:.0f}s, {errors} errors")

    # Deduplicate by ID
    seen = set()
    unique = []
    for v in all_videos:
        if v["id"] not in seen:
            seen.add(v["id"])
            unique.append(v)
    print(f"Unique videos: {len(unique)}")

    # Save
    json.dump(unique, open(OUT, "w"), ensure_ascii=False)
    print(f"Saved to {OUT}")

if __name__ == "__main__":
    main()
