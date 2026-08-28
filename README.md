# Softmax Complete Data Archive

## Structure
```
softmax_dbg/
├── api_data/                          # All API metadata (104MB, 33 files)
│   ├── .token                         # Active JWT (expires ~2027)
│   ├── .key                           # x-app-key: l0dtpwvzzmM
│   ├── 00_env_config.env              # Full .env with all endpoint paths
│   ├── 01-04_*                        # Departments(49), Courses(265), Categories(5), Sessions(9)
│   ├── 05_department_books_1381.json  # 1,381 department books
│   ├── 06_question_banks_439.json     # 439 question banks with PDF URLs
│   ├── 07_exam_questions_21055.json   # 21,055 exam questions (44MB)
│   ├── 08_live_classes_254.json       # 254 live classes with YouTube
│   ├── 09_smartbooks.json             # 4 smart books (paid)
│   ├── 10_ebooks_subjects.json        # Ebook/pass book listings
│   ├── 11-17_exam_*.json              # Exam metadata (DUET/SAE/admission)
│   ├── 18_live_class_pdfs.json        # 182 live class PDF URLs
│   ├── 19_chapters_7190.json          # 7,190 chapters (867 with descriptions)
│   ├── 20_resources_1000.json         # 1,000 resources
│   ├── 21_resources_pdf_480.json      # 480 resource PDF URLs (S3 EXPIRED)
│   ├── 22_videos_42600.json           # 42,600 videos with YouTube+BunnyCDN URLs
│   ├── 23_e_chapters_2400.json        # 2,400 e-chapters (S3 EXPIRED)
│   ├── 24_ueb_books.json             # 3 UEB books
│   ├── 25_category_ebooks_82.json     # 82 category ebooks with fresh URLs
│   ├── 26_pass_books.json             # User's pass books
│   ├── 28_home_ebooks.json            # Home ebook suggestions
│   ├── 31_referred_subjects.json      # Referred subjects
│   ├── 32_ebook_chapters_fresh.json   # Fresh ebook chapter URLs
│   ├── 33_ebook_details_all.json      # All 82 ebook details
│   │
│   └── web_pull/                      # ✅ NEW (2026-08) clean full captures via app/web/* API
│       ├── all_videos_metadata.json   # 42,482 videos (42,415 YT + 37,588 Bunny) 47MB, deduped
│       ├── all_question_banks.json    # 439 QBs with fresh signed PDF URLs
│       ├── all_chapters.json          # 5,771 unique chapters (deduped from 7,194)
│       ├── all_subjects.json          # 849 subjects
│       ├── all_courses.json           # 333 courses
│       ├── all_live_classes.json      # 258 live classes
│       ├── all_smart-books.json       # 14 smart books
│       └── all_probidhan.json         # 3 probidhan (2010, 2016, 2022)
│
├── downloads/                         # All downloaded content
│   ├── question_bank_pdfs/            # 433 PDFs, 59MB ✅ COMPLETE (6 server-missing: NoSuchKey)
│   │                                   #   names: qb_<id>_<year>_<institute>_<subject>.pdf (readable)
│   ├── question_bank_pdfs_by_subject/ # 74 PDFs, all QBs merged by subject (689 pages) ✅
│   ├── live_class_pdfs/               # 179 PDFs, 1.2GB ✅ COMPLETE (names: lc_<seq>.pdf → title in JSON)
│   ├── pass_books/                    # 105 PDFs, 678MB ✅ COMPLETE
│   ├── ebook_previews/                # 84 PDFs, 191MB ✅ COMPLETE (all 82 ebooks)
│   ├── e_chapters/                    # 93 PDFs, 110MB (from archive)
│   ├── e_chapters_purchased/          # 50 PDFs, 32MB ✅ (4 purchased books)
│   ├── resource_pdfs/                 # 43 PDFs, 91MB (from archive)
│   ├── ueb_books/                     # 3 PDFs, 12MB ✅ COMPLETE
│   ├── videos/                        # ⬇️ DOWNLOADING (~42,600 videos)
│   ├── video_metadata/                # 42,600 video entries, 33MB
│   ├── INVENTORY.json                 # Auto-generated inventory
│   ├── youtube_links_42600.json       # All YouTube links
│   └── video_download.log             # Download progress log
│
├── archive/                           # Original APK decompilation (4GB)
│   ├── books/                         # 105 PDFs + 101 extracted book dirs (1099 pages)
│   ├── e_chapters/                    # 93 e-chapter PDFs
│   ├── resources/                     # 43 resource PDFs
│   ├── ueb_books/                     # 3 UEB book PDFs
│   └── sos_demo/books/               # 96 pass book PDFs (source)
│
└── scripts/                           # Download utilities
    ├── download_videos_youtube.py     # Batch YouTube downloader (android client)
    └── refresh_and_download.py        # S3 URL refresher
```

## Content Summary
| Content | Total | Downloaded | Size | Status |
|---------|-------|------------|------|--------|
| Question Bank PDFs | 439 | 433 | 59MB | ✅ (6 server-missing) |
| Live Class PDFs | 182 | 179 | 1.2GB | ✅ |
| Pass Books | 105+ | 105 | 678MB | ✅ |
| Ebook Previews | 82 | 84 | 191MB | ✅ |
| Purchased E-Chapter PDFs | 50 | 50 | 32MB | ✅ |
| UEB Books | 3 | 3 | 12MB | ✅ |
| Archive E-Chapter PDFs | 2400 | 93 | 110MB | ⚠️ |
| Archive Resource PDFs | 480 | 43 | 91MB | ⚠️ |
| Videos (metadata) | 42,600 | 42,600 | 33MB | ✅ |
| Videos (MP4 download) | 42,600 | downloading | ~4GB+ | ⬇️ |
| Exam Questions | 21,055 | in JSON | 44MB | ✅ |

## API Credentials
- JWT: `api_data/.token` (phone +8801569125659, expires ~2027)
- x-app-key: `l0dtpwvzzmM`
- Base URL: `https://softmaxmanager.xyz/api/v1/`
- User-Agent: `Dart/3.2 (dart:io)` (bypasses Cloudflare)

## Download Commands
```bash
# Videos (background, already running)
python3 scripts/download_videos_youtube.py --workers 3

# Monitor video download
tail -f downloads/video_download.log

# Resume interrupted download (skips existing)
python3 scripts/download_videos_youtube.py --workers 3
```
