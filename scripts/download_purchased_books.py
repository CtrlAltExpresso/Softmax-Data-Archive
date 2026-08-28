#!/usr/bin/env python3
"""
Download all purchased pass books from Softmax API.
Fetches eChapters with signed S3 URLs from ebooks/esubject/user/,
downloads each chapter PDF, and merges into full book PDFs.

Usage:
  python3 download_purchased_books.py

Output:
  /home/sakib2/softmax_dbg/downloads/purchased_books_full/  (merged PDFs)
  /home/sakib2/softmax_dbg/downloads/purchased_book_chapters/ (individual chapters)
"""
import json, subprocess, time, os, sys
from pathlib import Path

BASE_DIR = Path("/home/sakib2/softmax_dbg")
TOKEN_FILE = BASE_DIR / "api_data/.token"
KEY_FILE = BASE_DIR / "api_data/.key"
BASE_URL = "https://softmaxmanager.xyz/api/v1"
UA = "User-Agent: Dart/3.2 (dart:io)"

CHAPTERS_DIR = BASE_DIR / "downloads/purchased_book_chapters"
MERGED_DIR = BASE_DIR / "downloads/purchased_books_full"

def fetch_json(url):
    cmd = [
        "curl", "-s", "-m", "15", url,
        "-H", f"authorization: Bearer {TOKEN_FILE.read_text().strip()}",
        "-H", f"x-app-key: {KEY_FILE.read_text().strip()}",
        "-H", UA, "-H", "accept: application/json"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    try:
        return json.loads(r.stdout)
    except:
        return None

def download_pdf(url, path):
    if path.exists() and path.stat().st_size > 500:
        return True
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", "30", "-L", "-o", str(path), url],
            capture_output=True, timeout=35
        )
        if path.exists() and path.stat().st_size > 500:
            return True
        path.unlink(missing_ok=True)
        return False
    except:
        path.unlink(missing_ok=True)
        return False

def main():
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching purchased books from API...")
    data = fetch_json(f"{BASE_URL}/ebooks/esubject/user/")
    if not data:
        print("ERROR: Could not fetch ebooks/esubject/user/")
        sys.exit(1)

    books = []
    for sem in data.get("active_semester_books", []) + data.get("others_semester_books", []):
        chapters = sem.get("eChapters", [])
        if chapters:
            books.append({"id": sem["id"], "title": sem["title"], "chapters": chapters})

    if not books:
        print("No purchased books with chapters found.")
        sys.exit(0)

    new_downloads = 0
    for book in books:
        book_dir = CHAPTERS_DIR / f"{book['id']}_{book['title'].replace(' ', '_')[:40]}"
        book_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nBook {book['id']}: {book['title']} ({len(book['chapters'])} chapters)")
        for ch in book["chapters"]:
            url = ch.get("eChapterPreview")
            if not url:
                continue
            serial = ch.get("serial", 0)
            ch_title = ch.get("title", f"ch_{serial}").replace(" ", "_")[:30]
            filename = f"{serial:02d}_{ch_title}.pdf"
            filepath = book_dir / filename

            if download_pdf(url, filepath):
                if filepath.stat().st_size > 1000:
                    print(f"  OK: {filename} ({filepath.stat().st_size/1024:.0f}KB)")
                new_downloads += 1
            else:
                print(f"  FAIL: {filename}")
            time.sleep(0.05)

        # Merge chapters into single PDF
        merged_path = MERGED_DIR / f"{book['id']}_{book['title'].replace(' ', '_')[:40]}.pdf"
        chapters_sorted = sorted(book_dir.glob("*.pdf"))
        if chapters_sorted:
            try:
                from PyPDF2 import PdfMerger
                merger = PdfMerger()
                for ch_file in chapters_sorted:
                    merger.append(str(ch_file))
                merger.write(str(merged_path))
                merger.close()
                sz = merged_path.stat().st_size
                r = subprocess.run(["pdfinfo", str(merged_path)], capture_output=True, text=True, timeout=10)
                pages = "?"
                for line in r.stdout.split("\n"):
                    if line.startswith("Pages:"):
                        pages = line.split(":")[1].strip()
                print(f"  MERGED: {merged_path.name} ({sz/1024/1024:.1f}MB, {pages} pages)")
            except Exception as e:
                print(f"  MERGE FAILED: {e}")

    print(f"\n=== Done. {new_downloads} new chapters downloaded. ===")
    print(f"Merged books: {MERGED_DIR}")

if __name__ == "__main__":
    main()
