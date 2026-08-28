#!/usr/bin/env python3
"""
Refresh expired S3 URLs and download resource/e-chapter PDFs.
Must run within 1 hour of fetching (S3 signed URLs expire after 3600s).
"""
import json, subprocess, os, sys, concurrent.futures
from pathlib import Path

BASE_DIR = Path("/home/sakib2/softmax_dbg")
TOKEN_FILE = BASE_DIR / "api_data/.token"
KEY_FILE = BASE_DIR / "api_data/.key"
BASE_URL = "https://softmaxmanager.xyz/api/v1"
UA = "user-agent: Dart/3.2 (dart:io)"

def fetch_json(url):
    cmd = [
        "curl", "-s", "-m", "30", url,
        "-H", f"authorization: Bearer {open(TOKEN_FILE).read().strip()}",
        "-H", f"x-app-key: {open(KEY_FILE).read().strip()}",
        "-H", UA, "-H", "accept: application/json"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout) if r.stdout.strip() else None

def download_pdf(item):
    url, path = item
    if os.path.exists(path) and os.path.getsize(path) > 500:
        return "skip"
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", "60", "-L", "-o", path, url],
            capture_output=True, timeout=65
        )
        sz = os.path.getsize(path) if os.path.exists(path) else 0
        if sz > 500:
            return f"ok {sz/1024:.0f}k"
        else:
            os.remove(path) if os.path.exists(path) else None
            return "fail"
    except:
        return "timeout"

def download_pdfs(urls, output_dir, label, workers=10):
    output_dir.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(download_pdf, item): item for item in urls}
        for i, f in enumerate(concurrent.futures.as_completed(futures)):
            r = f.result()
            if r.startswith("ok"): ok += 1
            else: fail += 1
            if (i+1) % 100 == 0:
                print(f"  [{i+1}/{len(urls)}] ok={ok} fail={fail}")
    total_mb = sum(
        os.path.getsize(str(p))
        for p in output_dir.iterdir() if p.is_file()
    ) / 1024 / 1024
    print(f"{label}: {ok} downloaded, {fail} failed, {total_mb:.1f}MB")
    return ok, fail

def main():
    print("=== Refreshing S3 URLs from API ===")
    
    # Fetch fresh resources
    print("\nFetching resources...")
    resources = []
    offset = 0
    while True:
        data = fetch_json(f"{BASE_URL}/app/web/chapters/?limit=100&offset={offset}")
        if not data or not data.get("results"):
            break
        # Resources are embedded in chapter_description IDs, not direct PDFs
        # The actual resource PDFs come from a different source
        break  # chapters don't contain PDF URLs directly
    
    # The resource PDFs were fetched from a specific endpoint on Aug 21
    # We need to find and re-hit that endpoint
    print("NOTE: Resource/e-chapter endpoints need to be re-discovered.")
    print("The S3 URLs in api_data/ files are EXPIRED (from Aug 21).")
    print("New URLs must be fetched via the app API and downloaded within 1 hour.")
    
    # For now, verify what we have
    echapter_dir = BASE_DIR / "downloads/e_chapters"
    resource_dir = BASE_DIR / "downloads/resource_pdfs"
    
    ech_valid = sum(1 for p in echapter_dir.iterdir() if p.is_file() and p.stat().st_size > 500)
    res_valid = sum(1 for p in resource_dir.iterdir() if p.is_file() and p.stat().st_size > 500)
    
    print(f"\nCurrent valid downloads:")
    print(f"  E-chapters: {ech_valid} valid files")
    print(f"  Resource PDFs: {res_valid} valid files")
    print(f"\nTo download remaining, the S3 URLs must be refreshed via the Softmax API.")

if __name__ == "__main__":
    main()
