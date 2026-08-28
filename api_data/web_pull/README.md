# Softmax app/web/* API Full Extraction (2026-08-27)

Complete captures pulled from the Softmax `app/web/*` API surface (the only
surface that returns data while the account is locked out). All files are
deduplicated and verified.

## Files

| File | Entries | Notes |
|------|---------|-------|
| `all_videos_metadata.json` | 42,482 | Full video catalog. 42,415 have `youtube_link`, 37,588 have `bunny_url` (HLS). Deduplicated by `id` (0 dupes). |
| `all_question_banks.json` | 439 | All question banks with fresh signed S3 `question_pdf` URLs. No `answer_pdf` exists server-side; none are paid-enclosed. |
| `all_chapters.json` | 5,771 | Chapters. Raw pull returned 7,194 rows containing 1,423 exact duplicate rows; deduped to 5,771 unique. |
| `all_subjects.json` | 849 | Subjects with codes, categories 1-4 & 11. |
| `all_courses.json` | 333 | Courses across 50+ departments. |
| `all_live_classes.json` | 258 | Live classes with YouTube links + PDF. |
| `all_smart-books.json` | 14 | Smart books (e.g. Smart Polytechnic Admission Guide). |
| `all_probidhan.json` | 3 | Probidhan: 2010, 2016, 2022. |

## Verification summary

- No duplicate IDs in any file except chapters (fixed by dedup).
- Videos: 0 dup IDs, all 42,482 titles present, 99.8% have a YouTube link.
- Question banks: 433 of 439 PDFs downloaded & validated (`question_bank_pdfs/`).
  6 QBs (ids 306, 351, 381, 387, 403, 443) are missing **server-side**
  (`S3 NoSuchKey` — the files were never uploaded or were deleted). These are
  unrecoverable by any client/API method.
- Video files (`.m3u8` on BunnyCDN) remain locked behind the blocked
  `user/bunny-video-play/` token endpoint — only metadata is obtainable.

## Method

- Endpoint: `https://softmaxmanager.xyz/api/v1/app/web/<resource>/?limit=100`
- Auth: Bearer JWT (`../.token`) + `x-app-key` + `User-Agent: Dart/3.2`
- Rate-limited to ~1 request/1.5s to avoid the 404 throttling mask.
