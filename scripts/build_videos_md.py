#!/usr/bin/env python3
"""Build Videos/ folder structure matching the Softmax app: Department → Course → Subject → Videos."""

import json, os, re
from difflib import SequenceMatcher
from collections import defaultdict

BASE = '/home/sakib2/softmax_dbg/FreeMax/Videos'
VIDEOS_JSON = '/home/sakib2/softmax_dbg/downloads/video_metadata/all_videos_42468.json'
COURSES_MAP = '/home/sakib2/softmax_dbg/api_data/course_subjects_map.json'

DEPT_EMOJI = {
    'ARCHITECTURE': '\U0001f3db\ufe0f',
    'AUTOMOBILE': '\U0001f697',
    'AIRCRAFT': '\u2708\ufe0f',
    'CIVIL': '\U0001f3d7\ufe0f',
    'CERAMIC': '\U0001f3a8',
    'CHEMICAL': '\U0001f9ea',
    'COMPUTER': '\U0001f4bb',
    'DATA TELECOMMUNICATION': '\U0001f4e1',
    'ELECTRICAL': '\u26a1',
    'ELECTRONICS': '\U0001f4e1',
    'ELECTRO MEDICAL': '\U0001fa7a',
    'ENVIRONMENTAL': '\U0001f33f',
    'FOOD': '\U0001f35c',
    'GRAPHICS': '\U0001f3a8',
    'GLASS': '\U0001f48e',
    'INSTRUMENTATION': '\U0001f527',
    'MARINE': '\u26f5',
    'MECHANICAL': '\U0001f527',
    'MECHATRONICS': '\U0001f916',
    'MINING': '\u26cf\ufe0f',
    'POWER': '\U0001f50c',
    'PRINTING': '\U0001f5a8\ufe0f',
    'REFRIGERATION': '\u2744\ufe0f',
    'SHIPBUILDING': '\U0001f6a2',
    'SURVEYING': '\U0001f4cd',
    'TELECOMMUNICATION': '\U0001f4e1',
    'CONSTRUCTION': '\U0001f3d7\ufe0f',
    'AGRICULTURE': '\U0001f33e',
    'FORESTRY': '\U0001f332',
    'FOOTWEAR': '\U0001f45f',
    'POLYTECHNIC': '\U0001f3eb',
    'TEXTILE': '\U0001f9f5',
}

def clean_name(s):
    s = s.strip()
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = s.replace('&', 'and')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def clean_course_name(name, dept_name=''):
    """Turn a course name into a clean folder name.
    e.g. '3rd-Semester (CST)' -> 'Semester 3'
         'BUET Pattern' -> 'BUET Pattern'
         'DUET Dreamer (CSE)-2025' -> 'DUET Dreamer 2025'
         'Department (CT)' -> 'SAE Job'
         'NON-Department (CT)' -> 'General (Job)'
    """
    name = name.strip()
    # Semester courses (standard)
    m = re.match(r'(\d)(?:st|nd|rd|th)[\s-]*[Ss]emester', name)
    if m:
        return f"Semester {m.group(1)}"
    # 7h-Semester (typo in API)
    m = re.match(r'(\d)h[\s-]*[Ss]emester', name)
    if m:
        return f"Semester {m.group(1)}"

    # "Department (XX)" = SAE department course (job/BUET/etc subjects)
    if re.match(r'^Department\s*\(', name):
        # Look for known patterns in subject names or use dept abbreviation
        dept_short = re.search(r'\(([A-Z]+)\)', name)
        if dept_short:
            code = dept_short.group(1)
            pattern_map = {
                'CT': 'Civil SAE', 'ET': 'Electrical SAE', 'MT': 'Mechanical SAE',
                'CMT': 'Computer SAE', 'ENT': 'Electronics SAE',
            }
            return pattern_map.get(code, f'SAE ({code})')
        return 'SAE Job'

    # "NON-Department (XX)" = general job prep subjects
    if re.match(r'^NON-Department', name):
        return 'General (Job)'

    out = name
    # Remove trailing dept codes like (CT), (ET), (MT), (CMT), etc.
    out = re.sub(r'\s*\(([A-Z\s]{2,4})\)\s*$', '', out)
    # Clean up Dreamer year suffixes: "DUET Dreamer (CE)-2025" -> "DUET Dreamer 2025"
    out = re.sub(r'\s*\(([A-Z]+)\)\s*-(\d{4})$', r' \2', out)
    out = re.sub(r'\(([A-Z]+)\)\s*-(\d{4})$', r' \2', out)
    out = re.sub(r'\s+', ' ', out).strip()
    return out

def fuzzy_match(a, b, threshold=0.55):
    a_low = a.lower().strip()
    b_low = b.lower().strip()
    if a_low == b_low:
        return 1.0
    if a_low in b_low or b_low in a_low:
        return 0.85
    return SequenceMatcher(None, a_low, b_low).ratio()

def main():
    videos = json.load(open(VIDEOS_JSON))
    courses_map = json.load(open(COURSES_MAP))

    # Build subject_id → {dept_name, course_name} map
    subj_to_course = {}
    for cid, info in courses_map.items():
        dept = info.get('dept_name', 'Unknown')
        cname = info.get('name', '')
        for s in info.get('subjects', []):
            sid = s.get('value')
            if sid:
                subj_to_course[sid] = {
                    'subject_name': s.get('label', ''),
                    'dept_name': dept,
                    'course_name': cname,
                }

    # Collect videos by bunny_collection label
    from collections import defaultdict
    coll_videos = defaultdict(list)
    for v in videos:
        bc = v.get('bunny_collection')
        if bc and isinstance(bc, dict):
            label = bc.get('label', '')
            if label:
                coll_videos[label].append(v)

    # Match collection labels to subjects
    matched = {}
    for label, vids in coll_videos.items():
        best_score = 0
        best_match = None
        for sid, info in subj_to_course.items():
            score = fuzzy_match(label, info['subject_name'])
            if score > best_score:
                best_score = score
                best_match = info
        if best_score > 0.5:
            matched[label] = {
                'subject_name': best_match['subject_name'],
                'dept_name': best_match['dept_name'],
                'course_name': best_match['course_name'],
                'videos': vids,
            }

    print(f"Matched: {len(matched)}/{len(coll_videos)}")

    # Group by department → course → subject
    hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for label, info in matched.items():
        dept = info['dept_name']
        course = info['course_name']
        subj = info['subject_name']
        hierarchy[dept][course][subj].extend(info['videos'])

    sorted_depts = sorted(hierarchy.keys())

    # Create files
    total_files = 0
    for dept in sorted_depts:
        emoji = ''
        for dk, dv in DEPT_EMOJI.items():
            if dk in dept.upper():
                emoji = dv
                break
        dept_folder = clean_name(f"{emoji} {dept}" if emoji else dept)

        for course_name in sorted(hierarchy[dept].keys()):
            course_folder = clean_name(clean_course_name(course_name, dept))
            course_path = os.path.join(BASE, dept_folder, course_folder)
            os.makedirs(course_path, exist_ok=True)

            subjects = hierarchy[dept][course_name]
            for subj_name in sorted(subjects.keys()):
                vids = subjects[subj_name]
                vids.sort(key=lambda v: v.get('order', 9999))

                subj_clean = clean_name(subj_name)
                md_path = os.path.join(course_path, f"{subj_clean}.md")

                lines = [
                    f"# {subj_name}",
                    "",
                    f"> {len(vids)} videos | {dept}",
                    "",
                    "| # | Title | Duration | Link |",
                    "|---|-------|----------|------|",
                ]
                for v in vids:
                    title = v.get('title', 'Untitled')
                    dur = int(v.get('duration') or 0)
                    mins = dur // 60
                    secs = dur % 60
                    dur_str = f"{mins}:{secs:02d}" if dur > 0 else "-"
                    yt = v.get('youtube_link', '')
                    order = v.get('order', 0)
                    lines.append(f"| {order} | {title} | {dur_str} | [Watch]({yt}) |")
                lines.append("")
                lines.append(f"*{len(vids)} videos total*")
                lines.append("")

                with open(md_path, 'w') as f:
                    f.write('\n'.join(lines))
                total_files += 1

    print(f"Created {total_files} markdown files")

    # Summary
    print("\n=== Summary ===")
    for dept in sorted_depts:
        courses = hierarchy[dept]
        total_vids = sum(len(v) for c in courses.values() for v in c.values())
        total_subjs = sum(len(c) for c in courses.values())
        course_names = sorted(courses.keys())
        print(f"\n  {dept[:55]} ({total_subjs} subjects, {total_vids} videos)")
        for cn in course_names:
            cv = sum(len(v) for v in courses[cn].values())
            print(f"    └─ {clean_course_name(cn, dept)[:50]:50s} {len(courses[cn]):2d} subjects {cv:5d} videos")


if __name__ == '__main__':
    main()
