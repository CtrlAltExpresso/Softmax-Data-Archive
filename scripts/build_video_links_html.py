#!/usr/bin/env python3
"""Build a beautiful HTML page grouping 42k+ videos by subject."""

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

INPUT_JSON = Path("/home/sakib2/softmax_dbg/downloads/video_metadata/all_videos_42468.json")
OUTPUT_HTML = Path("/home/sakib2/softmax_dbg/downloads/video_links.html")

GENERIC_TAGS = {
    "DUET", "DUET MCQ", "Civil Job", "SSC-Mathematics", "HSC-Mathematics",
    "Bangla JOB", "Bangla SAE JOB", "MCQ", "English JOB", "English SAE JOB",
    "ICT-HSC", "Physics HSC", "Chemistry HSC", "Bangla HSC", "English HSC",
    "BCS", "BCS MCQ", "SSC-Bangla", "SSC-English", "SSC-Physics",
    "SSC-Chemistry", "HSC-Bangla", "HSC-English", "HSC-Physics",
    "HSC-Chemistry", "SSC-Biology", "HSC-Biology", "Bangla (Job)",
    "English (Job)", "Bangla SAE", "English SAE",
}

CHAPTER_PREFIXES = ("অধ্যায়", "Chapter", "chapter", "Lecture", "lecture", "Class", "class")

# Patterns that indicate a tag is NOT a subject name
NOT_SUBJECT_RE = re.compile(
    r"^\d+$"                           # pure numeric
    r"|^[A-Z0-9]{6,}$"                 # long codes like 600021304
    r"|[।,.?]"                         # sentence punctuation → problem statement
    r"|(?:km|ms|m\/s|ft|kg)\s"         # units → physics problem
)


def is_numeric_tag(t: str) -> bool:
    return bool(re.fullmatch(r"[\d\s]+", t))


def is_chapter_tag(t: str) -> bool:
    return any(t.startswith(p) for p in CHAPTER_PREFIXES)


def is_generic_tag(t: str) -> bool:
    return t in GENERIC_TAGS or t.upper() in {g.upper() for g in GENERIC_TAGS}


def looks_like_subject(tag: str) -> bool:
    """Heuristic: subject names are short-ish, no sentence punctuation."""
    if len(tag) > 80:
        return False
    if NOT_SUBJECT_RE.search(tag):
        return False
    return True


def tag_score(tag: str):
    """Higher = better subject candidate."""
    t = tag.strip()
    if is_numeric_tag(t):
        return 0
    if is_generic_tag(t):
        return 1
    if is_chapter_tag(t):
        return 1
    if not looks_like_subject(t):
        return 0
    # Prefer shorter tags (more likely a subject name, less likely a description)
    length_penalty = min(len(t) / 100.0, 1.0)  # 0..1, lower is better
    return 5 - length_penalty


def pick_subject(video: dict) -> str:
    """Pick subject: bunny_collection.label is primary, tags are fallback."""
    # Primary: use curated bunny_collection label
    bc = video.get("bunny_collection")
    if bc and bc.get("label"):
        return bc["label"]

    # Fallback: pick best tag
    tags = video.get("tags", [])
    best_tag = None
    best_score = -1
    for t in tags:
        score = tag_score(t)
        if score > best_score:
            best_score = score
            best_tag = t

    if best_tag and best_score >= 3:
        return best_tag

    # Last resort: title
    return video.get("title", "Unknown")[:60]


def unicode_sort_key(s: str):
    """Sort: Bangla first (based on unicode block), then English, then others."""
    normalized = unicodedata.normalize("NFC", s)
    if not normalized:
        return (2, normalized)
    first_char = normalized[0]
    cp = ord(first_char)
    # Bengali block: U+0980–U+09FF
    if 0x0980 <= cp <= 0x09FF:
        return (0, normalized)
    # Basic Latin
    if cp < 0x0250:
        return (1, normalized)
    return (2, normalized)


def format_duration(minutes: float) -> str:
    total_secs = int(minutes * 60)
    m = total_secs // 60
    s = total_secs % 60
    return f"{m:02d}:{s:02d}"


def format_total_duration(total_minutes: float) -> str:
    hours = int(total_minutes // 60)
    mins = int(total_minutes % 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def build_html(subjects: dict, total_videos: int, total_duration_min: float) -> str:
    sorted_subjects = sorted(subjects.keys(), key=unicode_sort_key)
    num_subjects = len(sorted_subjects)

    # Build TOC
    toc_items = []
    for subj in sorted_subjects:
        count = len(subjects[subj])
        safe_id = re.sub(r"[^a-zA-Z0-9\u0980-\u09FF]+", "-", subj).strip("-")
        toc_items.append(
            f'<a class="toc-item" href="#section-{safe_id}" data-subject="{safe_id}">'
            f'<span class="toc-name">{subj}</span>'
            f'<span class="toc-count">{count}</span></a>'
        )
    toc_html = "\n".join(toc_items)

    # Build sections
    sections = []
    for subj in sorted_subjects:
        vids = sorted(subjects[subj], key=lambda v: v.get("order", 0))
        count = len(vids)
        safe_id = re.sub(r"[^a-zA-Z0-9\u0980-\u09FF]+", "-", subj).strip("-")

        rows = []
        for v in vids:
            title = v.get("title", "Untitled")
            link = v.get("youtube_link", "#")
            dur = format_duration(v.get("duration", 0))
            order = v.get("order", 0)
            rows.append(
                f'<tr>'
                f'<td class="vid-order">{order}</td>'
                f'<td class="vid-title"><a href="{link}" target="_blank" rel="noopener">{title}</a></td>'
                f'<td class="vid-dur">{dur}</td>'
                f'</tr>'
            )
        rows_html = "\n".join(rows)

        sections.append(
            f'<div class="subject-section" id="section-{safe_id}" data-subject="{safe_id}">'
            f'<div class="section-header" onclick="toggleSection(this)">'
            f'<h2><span class="collapse-icon">&#9660;</span> {subj}</h2>'
            f'<span class="section-count">{count} videos</span>'
            f'</div>'
            f'<div class="section-body">'
            f'<table class="video-table">'
            f'<thead><tr><th class="th-order">#</th><th class="th-title">Title</th><th class="th-dur">Duration</th></tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table>'
            f'</div>'
            f'</div>'
        )
    sections_html = "\n".join(sections)

    total_dur_str = format_total_duration(total_duration_min)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>42,468 Videos — Organized by Subject</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg: #1a1a2e;
  --card: #16213e;
  --text: #e0e0e0;
  --text-dim: #8892a0;
  --accent: #0f3460;
  --link: #4fc3f7;
  --link-hover: #81d4fa;
  --border: #2a3a5e;
  --hover-bg: #1e2d50;
  --sidebar-w: 300px;
}}

body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  display: flex;
  min-height: 100vh;
}}

/* Sidebar */
.sidebar {{
  width: var(--sidebar-w);
  min-width: var(--sidebar-w);
  background: var(--card);
  border-right: 1px solid var(--border);
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  z-index: 100;
}}

.sidebar-header {{
  padding: 16px;
  border-bottom: 1px solid var(--border);
  font-weight: 700;
  font-size: 14px;
  color: var(--link);
  text-transform: uppercase;
  letter-spacing: 1px;
}}

.sidebar-search {{
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
}}

.sidebar-search input {{
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  outline: none;
}}

.sidebar-search input:focus {{
  border-color: var(--link);
}}

.toc {{
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}}

.toc-item {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 7px 16px;
  color: var(--text-dim);
  text-decoration: none;
  font-size: 13px;
  transition: all 0.15s;
  border-left: 3px solid transparent;
}}

.toc-item:hover {{
  background: var(--hover-bg);
  color: var(--text);
}}

.toc-item.active {{
  background: var(--hover-bg);
  color: var(--link);
  border-left-color: var(--link);
}}

.toc-name {{
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}}

.toc-count {{
  background: var(--accent);
  color: var(--text-dim);
  padding: 1px 7px;
  border-radius: 10px;
  font-size: 11px;
  margin-left: 8px;
  flex-shrink: 0;
}}

/* Main content */
.main {{
  flex: 1;
  min-width: 0;
  padding: 24px 32px;
}}

/* Header */
.header {{
  margin-bottom: 24px;
}}

.header h1 {{
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
}}

.header h1 span {{
  color: var(--link);
}}

.stats {{
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-top: 8px;
}}

.stat {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 20px;
  min-width: 140px;
}}

.stat-value {{
  font-size: 24px;
  font-weight: 700;
  color: var(--link);
}}

.stat-label {{
  font-size: 12px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}

/* Search */
.search-box {{
  margin-bottom: 20px;
}}

.search-box input {{
  width: 100%;
  max-width: 600px;
  padding: 10px 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
  color: var(--text);
  font-size: 15px;
  outline: none;
}}

.search-box input:focus {{
  border-color: var(--link);
  box-shadow: 0 0 0 2px rgba(79, 195, 247, 0.15);
}}

.search-info {{
  font-size: 13px;
  color: var(--text-dim);
  margin-top: 6px;
  display: none;
}}

/* Sections */
.subject-section {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  margin-bottom: 12px;
  overflow: hidden;
}}

.section-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}}

.section-header:hover {{
  background: var(--hover-bg);
}}

.section-header h2 {{
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}}

.collapse-icon {{
  font-size: 11px;
  transition: transform 0.2s;
  display: inline-block;
  color: var(--text-dim);
  width: 14px;
}}

.section-header.collapsed .collapse-icon {{
  transform: rotate(-90deg);
}}

.section-count {{
  font-size: 12px;
  color: var(--text-dim);
  background: var(--bg);
  padding: 3px 10px;
  border-radius: 12px;
  white-space: nowrap;
}}

.section-body {{
  max-height: 600px;
  overflow-y: auto;
  transition: max-height 0.3s ease;
}}

.section-body.collapsed {{
  max-height: 0;
  overflow: hidden;
}}

/* Table */
.video-table {{
  width: 100%;
  border-collapse: collapse;
}}

.video-table thead th {{
  position: sticky;
  top: 0;
  background: var(--accent);
  padding: 8px 12px;
  text-align: left;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-dim);
  z-index: 1;
}}

.th-order {{ width: 50px; text-align: center; }}
.th-title {{ }}
.th-dur {{ width: 80px; text-align: right; }}

.video-table tbody tr {{
  border-top: 1px solid var(--border);
  transition: background 0.1s;
}}

.video-table tbody tr:hover {{
  background: var(--hover-bg);
}}

.video-table td {{
  padding: 8px 12px;
  font-size: 14px;
  vertical-align: middle;
}}

.vid-order {{
  text-align: center;
  color: var(--text-dim);
  font-size: 12px;
}}

.vid-title a {{
  color: var(--link);
  text-decoration: none;
}}

.vid-title a:hover {{
  color: var(--link-hover);
  text-decoration: underline;
}}

.vid-dur {{
  text-align: right;
  color: var(--text-dim);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}}

/* Search highlight */
.search-hidden {{ display: none !important; }}
.highlight {{ background: rgba(79, 195, 247, 0.25); border-radius: 2px; }}

/* Mobile toggle */
.sidebar-toggle {{
  display: none;
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 200;
  background: var(--link);
  color: var(--bg);
  border: none;
  border-radius: 50%;
  width: 48px;
  height: 48px;
  font-size: 20px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}}

/* Responsive */
@media (max-width: 900px) {{
  .sidebar {{
    position: fixed;
    left: -100%;
    top: 0;
    height: 100vh;
    width: 85vw;
    max-width: 320px;
    transition: left 0.3s ease;
    z-index: 150;
  }}
  .sidebar.open {{
    left: 0;
  }}
  .sidebar-toggle {{
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .main {{
    padding: 16px;
  }}
  .stats {{
    gap: 12px;
  }}
  .stat {{
    min-width: 100px;
    padding: 8px 14px;
  }}
  .stat-value {{
    font-size: 18px;
  }}
}}

@media (max-width: 600px) {{
  .header h1 {{
    font-size: 16px;
  }}
  .stats {{
    gap: 8px;
  }}
  .stat {{
    min-width: 80px;
    padding: 6px 10px;
  }}
  .video-table td, .video-table th {{
    padding: 6px 8px;
  }}
}}
</style>
</head>
<body>

<aside class="sidebar" id="sidebar">
  <div class="sidebar-header">Subjects ({num_subjects})</div>
  <div class="sidebar-search">
    <input type="text" id="sidebarSearch" placeholder="Filter subjects..." autocomplete="off">
  </div>
  <nav class="toc" id="toc">
    {toc_html}
  </nav>
</aside>

<button class="sidebar-toggle" id="sidebarToggle" aria-label="Toggle sidebar">&#9776;</button>

<main class="main">
  <div class="header">
    <h1><span>42,468</span> Videos &mdash; Organized by Subject</h1>
    <div class="stats">
      <div class="stat">
        <div class="stat-value">{num_subjects:,}</div>
        <div class="stat-label">Subjects</div>
      </div>
      <div class="stat">
        <div class="stat-value">{total_videos:,}</div>
        <div class="stat-label">Videos</div>
      </div>
      <div class="stat">
        <div class="stat-value">{total_dur_str}</div>
        <div class="stat-label">Total Duration</div>
      </div>
    </div>
  </div>

  <div class="search-box">
    <input type="text" id="searchInput" placeholder="Search videos across all subjects..." autocomplete="off">
    <div class="search-info" id="searchInfo"></div>
  </div>

  <div id="sections">
    {sections_html}
  </div>
</main>

<script>
(function() {{
  const searchInput = document.getElementById('searchInput');
  const searchInfo = document.getElementById('searchInfo');
  const sidebarSearch = document.getElementById('sidebarSearch');
  const toc = document.getElementById('toc');
  const tocItems = toc.querySelectorAll('.toc-item');
  const sections = document.querySelectorAll('.subject-section');
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');

  // Sidebar toggle
  sidebarToggle.addEventListener('click', () => {{
    sidebar.classList.toggle('open');
  }});

  // Close sidebar on link click (mobile)
  tocItems.forEach(item => {{
    item.addEventListener('click', () => {{
      if (window.innerWidth <= 900) sidebar.classList.remove('open');
    }});
  }});

  // Sidebar subject filter
  sidebarSearch.addEventListener('input', () => {{
    const q = sidebarSearch.value.toLowerCase();
    tocItems.forEach(item => {{
      const name = item.querySelector('.toc-name').textContent.toLowerCase();
      item.style.display = name.includes(q) ? '' : 'none';
    }});
  }});

  // Collapse/expand
  window.toggleSection = function(header) {{
    header.classList.toggle('collapsed');
    const body = header.nextElementSibling;
    body.classList.toggle('collapsed');
  }};

  // Scroll spy
  function updateActiveTOC() {{
    let current = '';
    sections.forEach(sec => {{
      if (sec.classList.contains('search-hidden')) return;
      const rect = sec.getBoundingClientRect();
      if (rect.top <= 120) current = sec.id;
      if (sec.querySelector('.section-body.collapsed') &&
          sec.querySelector('.section-body.collapsed') === sec.querySelector('.section-body')) return;
    }});
    tocItems.forEach(item => {{
      item.classList.toggle('active', item.getAttribute('href') === '#' + current);
    }});
  }}
  window.addEventListener('scroll', updateActiveTOC, {{ passive: true }});

  // Search
  searchInput.addEventListener('input', () => {{
    const q = searchInput.value.trim().toLowerCase();
    if (!q) {{
      sections.forEach(sec => sec.classList.remove('search-hidden'));
      document.querySelectorAll('.video-table tr').forEach(r => r.style.display = '');
      document.querySelectorAll('.section-header.collapsed').forEach(h => {{
        h.classList.remove('collapsed');
        h.nextElementSibling.classList.remove('collapsed');
      }});
      searchInfo.style.display = 'none';
      return;
    }}
    let totalMatch = 0;
    let matchSubjects = 0;
    sections.forEach(sec => {{
      const rows = sec.querySelectorAll('.video-table tbody tr');
      let secMatch = 0;
      rows.forEach(row => {{
        const title = row.querySelector('.vid-title').textContent.toLowerCase();
        if (title.includes(q)) {{
          row.style.display = '';
          secMatch++;
        }} else {{
          row.style.display = 'none';
        }}
      }});
      if (secMatch > 0) {{
        sec.classList.remove('search-hidden');
        const header = sec.querySelector('.section-header');
        header.classList.remove('collapsed');
        sec.querySelector('.section-body').classList.remove('collapsed');
        matchSubjects++;
      }} else {{
        sec.classList.add('search-hidden');
      }}
      totalMatch += secMatch;
    }});
    searchInfo.style.display = 'block';
    searchInfo.textContent = `Found ${{totalMatch.toLocaleString()}} videos in ${{matchSubjects}} subjects`;
  }});
}})();
</script>
</body>
</html>"""
    return html


def main():
    print(f"Reading {INPUT_JSON} ...")
    with open(INPUT_JSON) as f:
        videos = json.load(f)
    print(f"  Loaded {len(videos):,} videos")

    # Group by subject
    subjects = defaultdict(list)
    for v in videos:
        subj = pick_subject(v)
        subjects[subj].append(v)

    # Stats
    total_dur = sum(v.get("duration", 0) for v in videos)
    num_subjects = len(subjects)
    largest = max(subjects.items(), key=lambda x: len(x[1]))

    print(f"\n  Subjects found: {num_subjects:,}")
    print(f"  Largest subject: \"{largest[0]}\" ({len(largest[1]):,} videos)")
    print(f"  Total videos: {len(videos):,}")
    print(f"  Total duration: {format_total_duration(total_dur)}")

    # Build HTML
    print(f"\nGenerating HTML ...")
    html = build_html(subjects, len(videos), total_dur)
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"  Written to {OUTPUT_HTML} ({len(html):,} bytes)")

    # Show top 10 subjects
    print(f"\n  Top 10 subjects by video count:")
    for subj, vids in sorted(subjects.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"    {len(vids):5d}  {subj}")


if __name__ == "__main__":
    main()
