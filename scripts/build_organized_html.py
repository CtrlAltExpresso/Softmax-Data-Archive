#!/usr/bin/env python3
"""Organize all 42,468 Softmax videos into Department → Semester → Subject → Videos hierarchy and generate HTML."""

import json
import re
import unicodedata
from difflib import SequenceMatcher
from collections import defaultdict
from pathlib import Path

BASE = Path("/home/sakib2/softmax_dbg")
VIDEOS_PATH = BASE / "downloads/video_metadata/all_videos_42468.json"
COURSE_MAP_PATH = BASE / "api_data/course_subjects_map.json"
SUBJECTS_PATH = BASE / "api_data/subjects_849.json"
OUTPUT_PATH = BASE / "downloads/video_links_organized.html"


def load_data():
    with open(VIDEOS_PATH, "r", encoding="utf-8") as f:
        videos = json.load(f)
    with open(COURSE_MAP_PATH, "r", encoding="utf-8") as f:
        course_map = json.load(f)
    with open(SUBJECTS_PATH, "r", encoding="utf-8") as f:
        subjects_list = json.load(f)
    return videos, course_map, subjects_list


def build_subject_to_course(course_map):
    """subject_id → {dept_name, course_name, course_id}"""
    mapping = {}
    for course_id, course in course_map.items():
        for s in course["subjects"]:
            sid = s["value"]
            mapping[sid] = {
                "subject_label": s["label"],
                "dept_name": course["dept_name"],
                "course_name": course["name"],
                "course_id": course_id,
            }
    return mapping


def strip_suffixes(label):
    """Strip common suffixes like (CT) 5th Semester, (16), (SAE), numbers, etc."""
    s = label.strip()
    # Remove trailing parenthetical patterns like (CT) 5th Semester, (16), (SAE) JOB, etc.
    s = re.sub(r'\s*\((?:CT|SAE|CMT|ET|MT|EEE|ME|CE|PT|ST|FPT|ADT|AT|AGT|RT|IIT|BME|PST|ESE|ECE|EEPE|AE|EWE|BT|FT|WET|ARC|URP|CST)\)\s*(?:\d+(?:st|nd|rd|th)\s*Semester)?\s*(?:JOB)?\s*$', '', s, flags=re.IGNORECASE)
    # Remove trailing (NUMBER) or (Job) or (New) etc.
    s = re.sub(r'\s*\(\d+\)\s*$', '', s)
    s = re.sub(r'\s*\((?:Job|New|Update|JOB)\)\s*$', '', s, flags=re.IGNORECASE)
    # Remove trailing semester references
    s = re.sub(r'\s*\d+(?:st|nd|rd|th)\s*Semester\s*$', '', s, flags=re.IGNORECASE)
    # Remove trailing (YYYY)
    s = re.sub(r'\s*\(\d{4}\)\s*$', '', s)
    # Remove trailing numbers like "01", "02"
    s = re.sub(r'\s+\d{1,2}\s*$', '', s)
    return s.strip()


def normalize(text):
    return text.strip().lower()


def fuzzy_match(label, subject_name, threshold=0.55):
    """Check if label matches subject_name."""
    nlabel = normalize(label)
    nsub = normalize(subject_name)

    # Exact match
    if nlabel == nsub:
        return True, 1.0

    # One contains the other
    if nsub in nlabel or nlabel in nsub:
        return True, 0.9

    # Strip suffixes and try again
    stripped = normalize(strip_suffixes(label))
    if stripped == nsub:
        return True, 0.95
    if nsub in stripped or stripped in nsub:
        return True, 0.85

    # SequenceMatcher
    ratio = SequenceMatcher(None, nlabel, nsub).ratio()
    if ratio > threshold:
        return True, ratio

    ratio2 = SequenceMatcher(None, stripped, nsub).ratio()
    if ratio2 > threshold:
        return True, ratio2

    # Also try matching stripped label against subject name parts
    # Some labels have extra words; try removing common extra words
    cleaned = re.sub(r'\b(SAE|JOB|CT|CMT|ET|MT|Dreamer|New|Update|Polytechnic)\b', '', nlabel, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    ratio3 = SequenceMatcher(None, cleaned, nsub).ratio()
    if ratio3 > threshold:
        return True, ratio3

    cleaned2 = normalize(strip_suffixes(cleaned))
    ratio4 = SequenceMatcher(None, cleaned2, nsub).ratio()
    if ratio4 > threshold:
        return True, ratio4

    return False, ratio


def extract_semester(course_name):
    """Extract semester number from course name like '3rd-Semester (CST)'."""
    m = re.search(r'(\d+)(?:st|nd|rd|th)\s*[- ]?[Ss]emester', course_name)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*[- ]?[Ss]em', course_name)
    if m:
        return int(m.group(1))
    # "Department (ET)" or similar → semester 0 (dept-level)
    return 0


def bangla_sort_key(text):
    """Sort key that handles Bangla and English, putting Bangla first."""
    text = text.strip()
    # Check if first meaningful char is Bangla
    for ch in text:
        if ch.isalpha():
            cat = unicodedata.category(ch)
            # Bangla characters are in range 0x0980-0x09FF
            if '\u0980' <= ch <= '\u09FF':
                return (0, text.lower())
            else:
                return (1, text.lower())
    return (1, text.lower())


def build_mapping_and_match(videos, subject_to_course, subjects_list):
    """Match each video's bunny_collection label to a subject."""
    # Build subject name lookup from subjects_list
    subjects_by_id = {s["id"]: s["name"] for s in subjects_list}
    subjects_by_name = {}
    for s in subjects_list:
        subjects_by_name[normalize(s["name"])] = s

    # All subject labels from course map
    all_subject_labels = {}  # normalized_label → subject_info from course map
    for sid, info in subject_to_course.items():
        nl = normalize(info["subject_label"])
        if nl not in all_subject_labels:
            all_subject_labels[nl] = info

    # Also build from subjects list
    all_subject_names = set()
    for s in subjects_list:
        all_subject_names.add(s["name"])

    # Collect unique collection labels
    unique_labels = set()
    for v in videos:
        bc = v.get("bunny_collection")
        lbl = bc.get("label") if bc else None
        if lbl:
            unique_labels.add(lbl)

    print(f"Unique collection labels to match: {len(unique_labels)}")

    # Match each label
    label_to_match = {}  # label → {dept_name, course_name, semester, subject_label, subject_id} or None
    for lbl in unique_labels:
        best_match = None
        best_score = 0
        stripped = strip_suffixes(lbl)
        nstripped = normalize(stripped)

        for sid, info in subject_to_course.items():
            sub_name = info["subject_label"]
            matched, score = fuzzy_match(lbl, sub_name)
            if matched and score > best_score:
                best_score = score
                semester = extract_semester(info["course_name"])
                best_match = {
                    "dept_name": info["dept_name"],
                    "course_name": info["course_name"],
                    "semester": semester,
                    "subject_label": sub_name,
                    "subject_id": sid,
                }

        label_to_match[lbl] = best_match
        if best_match:
            pass  # matched
        else:
            pass  # unmatched

    # Stats
    matched_labels = sum(1 for v in label_to_match.values() if v is not None)
    unmatched_labels = sum(1 for v in label_to_match.values() if v is None)
    print(f"Matched labels: {matched_labels}, Unmatched labels: {unmatched_labels}")

    # Show some unmatched
    if unmatched_labels > 0:
        print("\nSample unmatched labels:")
        count = 0
        for lbl, m in label_to_match.items():
            if m is None:
                print(f"  - {lbl}")
                count += 1
                if count >= 20:
                    break

    return label_to_match


def organize_videos(videos, label_to_match):
    """Build hierarchy: dept → semester → subject → videos."""
    # hierarchy[dept_name][semester][subject_key] = [videos]
    hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    unmatched_videos = []

    for v in videos:
        bc = v.get("bunny_collection")
        lbl = bc.get("label") if bc else None

        if lbl is None:
            unmatched_videos.append(v)
            continue

        match = label_to_match.get(lbl)
        if match is None:
            # Put in Uncategorized
            key = (f"Uncategorized: {lbl}", 0)
            hierarchy["Uncategorized"][0][key].append(v)
        else:
            dept = match["dept_name"]
            sem = match["semester"]
            sub_key = f"{match['subject_label']}"
            # Use (subject_label, subject_id) as key to avoid collisions
            sub_id = match["subject_id"]
            hierarchy[dept][sem][(sub_key, sub_id)].append(v)

    return hierarchy, unmatched_videos


def sort_videos(videos):
    """Sort videos by order field."""
    return sorted(videos, key=lambda v: v.get("order", 0))


def format_duration(seconds):
    """Format duration in mm:ss."""
    if not seconds:
        return "0:00"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


def generate_html(hierarchy, unmatched_videos, total_videos, label_to_match):
    """Generate the organized HTML file."""
    # Count stats
    all_depts = set()
    all_sems = set()
    all_subjects = set()
    matched_count = 0
    unmatched_count = 0

    for dept, sems in hierarchy.items():
        all_depts.add(dept)
        for sem, subjects in sems.items():
            if dept != "Uncategorized":
                all_sems.add(sem)
            for sub_key, vids in subjects.items():
                all_subjects.add((dept, sem, sub_key[0]))
                matched_count += len(vids)
    unmatched_count = len(unmatched_videos)

    num_depts = len(all_depts)
    num_sems = len(all_sems)
    num_subjects = len(all_subjects)

    print(f"\nStats:")
    print(f"  Departments: {num_depts}")
    print(f"  Semesters: {num_sems}")
    print(f"  Subjects: {num_subjects}")
    print(f"  Matched videos: {matched_count}")
    print(f"  Unmatched videos: {unmatched_count}")
    print(f"  Total videos: {total_videos}")

    # Sort departments
    dept_list = sorted(hierarchy.keys(), key=bangla_sort_key)

    # Build sidebar and content
    sidebar_html = []
    content_html = []

    for dept in dept_list:
        dept_id = re.sub(r'[^a-zA-Z0-9]', '-', dept.lower())
        sidebar_html.append(f'<div class="sidebar-dept">')
        sidebar_html.append(f'<div class="sidebar-dept-title" onclick="toggleDept(\'{dept_id}\')">{dept}</div>')
        sidebar_html.append(f'<div class="sidebar-dept-list" id="dept-{dept_id}">')

        sems = hierarchy[dept]
        sem_list = sorted(sems.keys())
        # Put semester 0 (uncategorized) last
        sem_list_sorted = sorted([s for s in sem_list if s > 0]) + ([0] if 0 in sem_list else [])

        for sem in sem_list_sorted:
            if sem == 0:
                sem_label = "Other"
                sem_id = f"{dept_id}-other"
            else:
                sem_label = f"{sem}{'st' if sem==1 else 'nd' if sem==2 else 'rd' if sem==3 else 'th'} Semester"
                sem_id = f"{dept_id}-sem{sem}"

            sidebar_html.append(f'<div class="sidebar-sem">')
            sidebar_html.append(f'<div class="sidebar-sem-title" onclick="toggleSem(\'{sem_id}\')">{sem_label}</div>')
            sidebar_html.append(f'<div class="sidebar-sem-list" id="sem-{sem_id}">')

            subjects = sems[sem]
            sub_list = sorted(subjects.keys(), key=lambda x: bangla_sort_key(x[0]))

            for sub_key, sub_id in sub_list:
                vids = sort_videos(subjects[(sub_key, sub_id)])
                sub_id_html = re.sub(r'[^a-zA-Z0-9]', '-', sub_key.lower()) + f"-{sub_id}"
                sidebar_html.append(f'<div class="sidebar-sub"><a href="#sub-{sub_id_html}">{sub_key} ({len(vids)})</a></div>')

            sidebar_html.append(f'</div></div>')
        sidebar_html.append(f'</div></div>')

        # Content
        content_html.append(f'<div class="dept-section" id="dept-{dept_id}">')
        content_html.append(f'<h2 class="dept-header">{dept}</h2>')

        for sem in sem_list_sorted:
            if sem == 0:
                sem_label = "Other"
                sem_id = f"{dept_id}-other"
            else:
                sem_label = f"{sem}{'st' if sem==1 else 'nd' if sem==2 else 'rd' if sem==3 else 'th'} Semester"
                sem_id = f"{dept_id}-sem{sem}"

            content_html.append(f'<div class="sem-section" id="sem-{sem_id}">')
            content_html.append(f'<h3 class="sem-header">{sem_label}</h3>')

            subjects = sems[sem]
            sub_list = sorted(subjects.keys(), key=lambda x: bangla_sort_key(x[0]))

            for sub_key, sub_id in sub_list:
                vids = sort_videos(subjects[(sub_key, sub_id)])
                sub_id_html = re.sub(r'[^a-zA-Z0-9]', '-', sub_key.lower()) + f"-{sub_id}"
                content_html.append(f'<div class="sub-section" id="sub-{sub_id_html}">')
                content_html.append(f'<h4 class="sub-header">{sub_key} <span class="video-count">({len(vids)} videos)</span></h4>')
                content_html.append(f'<div class="video-list">')

                for vi, vid in enumerate(vids):
                    link = vid.get("youtube_link", "#")
                    title = vid.get("title", "Untitled").replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
                    order = vid.get("order", vi + 1)
                    dur = format_duration(vid.get("duration"))
                    yt_thumb = ""
                    content_html.append(f'<a href="{link}" target="_blank" class="video-item" data-title="{title.lower()}">')
                    content_html.append(f'<span class="vid-order">#{order}</span>')
                    content_html.append(f'<span class="vid-title">{title}</span>')
                    content_html.append(f'<span class="vid-duration">{dur}</span>')
                    content_html.append(f'</a>')

                content_html.append(f'</div></div>')
            content_html.append(f'</div>')
        content_html.append(f'</div>')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Softmax Videos — Organized</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0d1117; color:#c9d1d9; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
a {{ color:#58a6ff; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}

.header {{ background:#161b22; border-bottom:1px solid #30363d; padding:16px 24px; position:sticky; top:0; z-index:100; }}
.header h1 {{ font-size:1.3em; color:#f0f6fc; margin-bottom:6px; }}
.header .stats {{ font-size:0.85em; color:#8b949e; }}
.header .stats span {{ color:#58a6ff; font-weight:600; }}

.search-bar {{ width:100%; max-width:600px; padding:8px 14px; background:#0d1117; border:1px solid #30363d; border-radius:6px; color:#c9d1d9; font-size:14px; margin-top:8px; }}
.search-bar:focus {{ border-color:#1f6feb; outline:none; box-shadow:0 0 0 3px rgba(31,111,235,0.3); }}

.search-results {{ display:none; background:#161b22; border:1px solid #30363d; border-radius:6px; max-height:400px; overflow-y:auto; margin-top:4px; }}
.search-results.active {{ display:block; }}
.search-result-item {{ padding:8px 14px; border-bottom:1px solid #21262d; cursor:pointer; font-size:13px; }}
.search-result-item:hover {{ background:#1c2128; }}
.search-result-item .sr-breadcrumb {{ color:#8b949e; font-size:11px; }}
.search-result-item .sr-title {{ color:#c9d1d9; }}
.search-result-item .sr-title em {{ color:#58a6ff; font-style:normal; font-weight:600; }}
.no-results {{ padding:14px; color:#8b949e; text-align:center; }}

.layout {{ display:flex; min-height:calc(100vh - 100px); }}

.sidebar {{ width:300px; min-width:300px; background:#0d1117; border-right:1px solid #21262d; overflow-y:auto; position:sticky; top:100px; height:calc(100vh - 100px); padding:8px 0; }}
.sidebar-dept-title {{ padding:8px 16px; font-weight:600; color:#f0f6fc; cursor:pointer; font-size:13px; user-select:none; }}
.sidebar-dept-title:hover {{ background:#161b22; }}
.sidebar-dept-list {{ display:none; }}
.sidebar-dept-list.open {{ display:block; }}
.sidebar-sem-title {{ padding:6px 16px 6px 28px; color:#8b949e; cursor:pointer; font-size:12px; user-select:none; }}
.sidebar-sem-title:hover {{ background:#161b22; }}
.sidebar-sem-list {{ display:none; }}
.sidebar-sem-list.open {{ display:block; }}
.sidebar-sub {{ padding:3px 16px 3px 40px; }}
.sidebar-sub a {{ font-size:12px; color:#58a6ff; }}
.sidebar-sub a:hover {{ text-decoration:underline; }}

.main {{ flex:1; padding:24px 32px; overflow-x:auto; }}

.dept-section {{ margin-bottom:40px; }}
.dept-header {{ font-size:1.4em; color:#f0f6fc; border-bottom:2px solid #1f6feb; padding-bottom:8px; margin-bottom:16px; }}
.sem-section {{ margin-bottom:24px; margin-left:12px; }}
.sem-header {{ font-size:1.1em; color:#c9d1d9; margin-bottom:10px; padding-left:8px; border-left:3px solid #30363d; }}
.sub-section {{ margin-bottom:16px; margin-left:12px; }}
.sub-header {{ font-size:0.95em; color:#c9d1d9; margin-bottom:6px; }}
.video-count {{ font-size:0.8em; color:#8b949e; font-weight:normal; }}
.video-list {{ display:flex; flex-direction:column; gap:2px; }}
.video-item {{ display:flex; align-items:center; padding:6px 10px; border-radius:4px; color:#c9d1d9; font-size:13px; gap:10px; }}
.video-item:hover {{ background:#161b22; text-decoration:none; }}
.vid-order {{ color:#8b949e; min-width:36px; font-size:12px; }}
.vid-title {{ flex:1; }}
.vid-duration {{ color:#8b949e; font-size:12px; min-width:40px; text-align:right; }}

.hamburger {{ display:none; background:none; border:none; color:#c9d1d9; font-size:24px; cursor:pointer; padding:4px 8px; }}
@media (max-width:768px) {{
  .sidebar {{ position:fixed; left:-300px; top:0; height:100vh; z-index:200; transition:left 0.3s; }}
  .sidebar.open {{ left:0; }}
  .hamburger {{ display:inline-block; }}
  .main {{ padding:16px; }}
  .overlay {{ display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:199; }}
  .overlay.active {{ display:block; }}
}}
</style>
</head>
<body>

<div class="header">
  <div style="display:flex;align-items:center;gap:12px;">
    <button class="hamburger" onclick="toggleSidebar()">&#9776;</button>
    <div>
      <h1>Softmax Videos &mdash; Assembled by Department &amp; Semester</h1>
      <div class="stats">
        <span>{num_depts}</span> departments &middot;
        <span>{num_sems}</span> semesters &middot;
        <span>{num_subjects}</span> subjects &middot;
        <span>{total_videos}</span> videos
        &nbsp;&nbsp;(<span>{matched_count}</span> matched, <span>{unmatched_count}</span> unmatched)
      </div>
    </div>
  </div>
  <input type="text" class="search-bar" placeholder="Search videos..." id="searchBar" oninput="doSearch(this.value)" autocomplete="off">
  <div class="search-results" id="searchResults"></div>
</div>

<div class="overlay" id="overlay" onclick="toggleSidebar()"></div>

<div class="layout">
  <nav class="sidebar" id="sidebar">
    {''.join(sidebar_html)}
  </nav>
  <div class="main">
    {''.join(content_html)}
  </div>
</div>

<script>
function toggleSidebar() {{
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('active');
}}
function toggleDept(id) {{
  var el = document.getElementById('dept-'+id);
  if(el) el.classList.toggle('open');
}}
function toggleSem(id) {{
  var el = document.getElementById('sem-'+id);
  if(el) el.classList.toggle('open');
}}

// Search
var videoData = [];
document.querySelectorAll('.video-item').forEach(function(a) {{
  var sub = a.closest('.sub-section');
  var sem = a.closest('.sem-section');
  var dept = a.closest('.dept-section');
  videoData.push({{
    el: a,
    title: a.getAttribute('data-title') || '',
    dept: dept ? dept.querySelector('.dept-header').textContent : '',
    sem: sem ? sem.querySelector('.sem-header').textContent : '',
    sub: sub ? sub.querySelector('.sub-header').textContent.replace(/\\(\\d+ videos\\)/,'').trim() : '',
    href: a.getAttribute('href') || '#'
  }});
}});

function doSearch(q) {{
  var res = document.getElementById('searchResults');
  if (!q.trim()) {{ res.classList.remove('active'); res.innerHTML=''; return; }}
  var ql = q.toLowerCase();
  var matches = videoData.filter(function(v) {{ return v.title.indexOf(ql) >= 0 || v.sub.toLowerCase().indexOf(ql)>=0; }}).slice(0, 50);
  if (!matches.length) {{ res.innerHTML='<div class="no-results">No results</div>'; res.classList.add('active'); return; }}
  var html = matches.map(function(v) {{
    var idx = v.title.indexOf(ql);
    var t = v.title;
    if(idx>=0) t = v.title.substring(0,idx)+'<em>'+v.title.substring(idx,idx+q.length)+'</em>'+v.title.substring(idx+q.length);
    return '<a href="'+v.href+'" target="_blank" class="search-result-item"><div class="sr-breadcrumb">'+v.dept+' &rsaquo; '+v.sem+' &rsaquo; '+v.sub+'</div><div class="sr-title">'+t+'</div></a>';
  }}).join('');
  res.innerHTML = html; res.classList.add('active');
}}

document.addEventListener('click', function(e) {{
  if (!e.target.closest('.search-bar') && !e.target.closest('.search-results'))
    document.getElementById('searchResults').classList.remove('active');
}});
</script>
</body>
</html>"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nHTML written to: {OUTPUT_PATH}")


def main():
    print("Loading data...")
    videos, course_map, subjects_list = load_data()
    print(f"  Videos: {len(videos)}, Courses: {len(course_map)}, Subjects: {len(subjects_list)}")

    print("\nBuilding subject-to-course mapping...")
    subject_to_course = build_subject_to_course(course_map)
    print(f"  Mapped {len(subject_to_course)} subject IDs to courses")

    print("\nMatching video collections to subjects...")
    label_to_match = build_mapping_and_match(videos, subject_to_course, subjects_list)

    print("\nOrganizing videos into hierarchy...")
    hierarchy, unmatched_videos = organize_videos(videos, label_to_match)

    print(f"  Unmatched videos (no collection): {len(unmatched_videos)}")

    print("\nGenerating HTML...")
    total = len(videos)
    generate_html(hierarchy, unmatched_videos, total, label_to_match)

    print("\nDone!")


if __name__ == "__main__":
    main()
