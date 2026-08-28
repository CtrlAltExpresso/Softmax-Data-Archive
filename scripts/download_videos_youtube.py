#!/usr/bin/env python3
"""
Batch download ALL 42,600 Softmax videos from YouTube via yt-dlp.
Uses android player client to bypass 403 errors.
Improved: max retries, failed-id tracking, streaming submission.
"""
import json, subprocess, os, sys, argparse, time, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path("/home/sakib2/softmax_dbg")
VIDEOS_JSON = BASE_DIR / "downloads/video_metadata/all_videos_42468.json"
OUTPUT_DIR = BASE_DIR / "downloads/videos"
LOG_FILE = BASE_DIR / "downloads/video_download_log.jsonl"
FAILED_FILE = BASE_DIR / "downloads/video_download_failed.jsonl"
MAX_RETRIES = 2

def download_video(entry, output_dir):
    vid_id = entry["id"]
    url = entry.get("youtube_link", "")
    if not url:
        return f"skip {vid_id}"
    title = entry.get("title", f"video_{vid_id}")
    safe_title = "".join(c if c.isalnum() or c in ' _-' else '_' for c in title)[:80]
    outpath = output_dir / f"{vid_id}_{safe_title}.mp4"

    if outpath.exists() and outpath.stat().st_size > 10000:
        return f"skip {vid_id}"

    for attempt in range(MAX_RETRIES):
        try:
            cmd = [
                "yt-dlp", "-f", "18",
                "--extractor-args", "youtube:player_client=android",
                "-o", str(outpath),
                "--no-overwrites",
                "--socket-timeout", "60",
                "--retries", "3",
                "--retry-sleep", "2",
                "--quiet", "--no-warnings",
                "--no-check-certificates",
                url
            ]
            r = subprocess.run(cmd, capture_output=True, timeout=300)
            if outpath.exists() and outpath.stat().st_size > 10000:
                sz_mb = outpath.stat().st_size / 1024 / 1024
                return f"ok {vid_id} {sz_mb:.1f}MB"
            if outpath.exists():
                os.remove(outpath)
        except subprocess.TimeoutExpired:
            if outpath.exists():
                os.remove(outpath)
        except Exception as e:
            if outpath.exists():
                os.remove(outpath)
        if attempt < MAX_RETRIES - 1:
            time.sleep(2)

    stderr = ""
    try:
        stderr = r.stderr.decode()[:200]
    except:
        pass
    return f"fail {vid_id}: {stderr}"

def main():
    parser = argparse.ArgumentParser(description="Download ALL Softmax videos")
    parser.add_argument("--free-only", action="store_true")
    parser.add_argument("--subject", type=str)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    videos = json.load(open(VIDEOS_JSON))
    print(f"Total videos in metadata: {len(videos)}")

    if args.free_only:
        videos = [v for v in videos if v.get("free_preview")]
    if args.subject:
        videos = [v for v in videos if any(args.subject in t for t in v.get("tags", []))]
    if args.limit > 0:
        videos = videos[:args.limit]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    existing = set()
    for f in OUTPUT_DIR.iterdir():
        if f.suffix == '.mp4' and f.stat().st_size > 10000:
            try:
                vid_id = int(f.name.split('_')[0])
                existing.add(vid_id)
            except: pass

    failed_ids = set()
    if FAILED_FILE.exists():
        for line in FAILED_FILE.read_text().splitlines():
            if line.strip():
                try:
                    obj = json.loads(line)
                    fid = int(obj.get("result", "").split()[1] if " " in obj.get("result", "") else -1)
                    if fid > 0:
                        failed_ids.add(fid)
                except: pass

    to_download = [v for v in videos if v['id'] not in existing and v['id'] not in failed_ids]
    print(f"Already downloaded: {len(existing)}")
    print(f"Previously failed: {len(failed_ids)}")
    print(f"To download: {len(to_download)}")

    ok = fail = skip = timeout_count = 0
    total_mb = 0
    t0 = time.time()
    log_fh = open(LOG_FILE, "a")
    fail_fh = open(FAILED_FILE, "a")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(download_video, v, OUTPUT_DIR): v for v in to_download}

        for i, f in enumerate(as_completed(futures)):
            result = f.result()
            if result.startswith("ok"):
                ok += 1
                try:
                    mb = float(result.split()[2].replace("MB", ""))
                    total_mb += mb
                except: pass
            elif result.startswith("skip"):
                skip += 1
            elif result.startswith("timeout") or result.startswith("fail"):
                fail += 1
                fail_fh.write(json.dumps({"result": result}) + "\n")
                fail_fh.flush()
            else:
                fail += 1

            done = ok + fail + skip
            if done % 50 == 0:
                elapsed = time.time() - t0
                rate = ok / elapsed * 60 if elapsed > 0 else 0
                remaining = len(to_download) - done
                eta_min = remaining / rate if rate > 0 else 0
                print(f"  [{done}/{len(to_download)}] ok={ok} fail={fail} | {total_mb:.0f}MB | {rate:.1f}/min | ETA {eta_min:.0f}min")
                log_fh.flush()

    log_fh.close()
    fail_fh.close()
    elapsed = time.time() - t0
    print(f"\nDONE in {elapsed/60:.1f} min: ok={ok} skip={skip} fail={fail} total={total_mb:.1f}MB")

if __name__ == "__main__":
    main()
