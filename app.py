import datetime
import io
import json
import os
import re
import unicodedata
from xml.sax.saxutils import escape

from flask import Flask, Response, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import KeepTogether, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEN_ED_FILE = os.path.join(BASE_DIR, "gen_ed.json")
DEGREES_DIR = os.path.join(BASE_DIR, "degrees")

GRADE_SCORES = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0, "NONE": -1}

MAX_SEMESTERS = 30  # Safety cap to prevent infinite loops

# Categories whose courses require a C or higher.
# Business Core and Information Systems Analytics are major courses, so they
# follow the "Major core requires C" rule described in get_min_passing_score.
C_REQUIRED_CATEGORIES = {
    "Engineering", "Mathematics", "Physics",
    "Chemistry", "Chemistry Electives", "Computer Science",
    "Biology Core", "Biology Electives", "Pre-Health Science", "Pre-Health Electives",
    "Business Core", "Information Systems Analytics",
}

# Default "credits completed before you may take this" by catalog level
# (first digit of the 4-digit course number). Override per course with a
# "min_credits" field in the JSON.
LEVEL_MIN_CREDITS = {3: 30, 4: 60}

# Categories with no course number that are known to be upper-level.
CATEGORY_MIN_CREDITS = {"Chemistry Electives": 60}

# Free-text student fields and their maximum lengths.
STUDENT_FIELDS = {
    "student_first": 80, "student_last": 80, "student_id": 30, "student_email": 120,
    "advisor_name": 120, "advisor_email": 120, "catalog_year": 20, "minor": 120,
    "notes": 3000,
}
PLAN_FILE_FIELDS = {"degree", "start_term", "start_year", "max_credits", "transfer_credits"} | set(STUDENT_FIELDS)
MAX_PLAN_FILE_BYTES = 1_000_000


# --------------------------------------------------------------------------
# Catalog loading
# --------------------------------------------------------------------------
def load_json_file(file_path):
    """Safely loads a JSON dictionary file."""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to parse {file_path}: {e}")
        return {}


def discover_degree_programs():
    """Dynamically finds all JSON files inside the 'degrees' directory."""
    programs = {}
    if not os.path.exists(DEGREES_DIR):
        os.makedirs(DEGREES_DIR)

    for file_name in sorted(os.listdir(DEGREES_DIR)):
        if file_name.endswith(".json"):
            degree_key = file_name.replace(".json", "").replace("courses_", "")
            file_path = os.path.join(DEGREES_DIR, file_name)
            data = load_json_file(file_path)

            meta = data.get("_metadata", {})
            degree_name = meta.get("name", degree_key.replace("_", " ").title())

            programs[degree_key] = {
                "name": degree_name,
                "file": file_path,
            }
    return programs


def load_combined_course_catalog(degree_key):
    """Merges shared Gen Ed courses with degree-specific courses."""
    gen_ed_courses = load_json_file(GEN_ED_FILE)

    programs = discover_degree_programs()
    if degree_key not in programs:
        degree_key = next(iter(programs.keys())) if programs else ""

    degree_file = programs.get(degree_key, {}).get("file", "")
    degree_courses = load_json_file(degree_file) if degree_file else {}

    full_catalog = {**gen_ed_courses, **degree_courses}
    full_catalog.pop("_metadata", None)

    return full_catalog, degree_key


def group_catalog_by_category(catalog):
    categories = {}
    for code, details in catalog.items():
        cat = details.get("category", "General Education")
        categories.setdefault(cat, []).append((code, details))
    return categories


# --------------------------------------------------------------------------
# Rules and helpers
# --------------------------------------------------------------------------
def get_min_passing_score(category):
    """
    STEM & Major core courses require 'C or higher' (score 2).
    General Education and General Electives require 'D or higher' (score 1).
    """
    if category in C_REQUIRED_CATEGORIES:
        return "C", 2
    return "D", 1


def generate_upcoming_terms(start_term="Fall", start_year=2026, count=12):
    """Generates a list of future semester labels."""
    terms = []
    curr_t, curr_y = start_term, int(start_year)
    for _ in range(count):
        terms.append(f"{curr_t} {curr_y}")
        if curr_t == "Fall":
            curr_t = "Spring"
            curr_y += 1
        else:
            curr_t = "Fall"
    return terms


def term_rank(term_label):
    """Converts 'Fall 2026' or 'Spring 2027' into an integer rank for chronological comparison."""
    if not term_label or term_label == "AUTO":
        return 0
    parts = term_label.split()
    if len(parts) != 2:
        return 0
    try:
        season, year = parts[0], int(parts[1])
    except ValueError:
        return 0
    return year * 2 + (1 if season == "Fall" else 0)


def to_int(value, default, low, high):
    """Parses an int from form input and clamps it, falling back to default."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def required_credits(code, details):
    """Credits a student must have completed before taking this course."""
    if "min_credits" in details:
        return to_int(details["min_credits"], 0, 0, 200)
    match = re.search(r"\d{4}", code)
    if match:
        return LEVEL_MIN_CREDITS.get(int(match.group(0)) // 1000, 0)
    return CATEGORY_MIN_CREDITS.get(details.get("category", ""), 0)


def course_number(code):
    """First 4-digit number in a course code, or a large value for choice slots like FA_HUM1."""
    match = re.search(r"\d{4}", code)
    return int(match.group(0)) if match else 9999


def chain_lengths(catalog):
    """For each course, the length of the longest chain of courses that depend on it (itself included)."""
    dependents = {code: [] for code in catalog}
    for code, details in catalog.items():
        for p in details.get("prereqs", []):
            if p in dependents:
                dependents[p].append(code)

    memo = {}
    visiting = set()

    def depth(code):
        if code in memo:
            return memo[code]
        if code in visiting:  # guard against circular prereqs
            return 0
        visiting.add(code)
        memo[code] = 1 + max((depth(d) for d in dependents[code]), default=0)
        visiting.discard(code)
        return memo[code]

    for code in catalog:
        depth(code)
    return memo


def explain_unscheduled(code, details, catalog, remaining, completed, max_credits):
    reasons = []
    prereqs = details.get("prereqs", [])
    missing = [p for p in prereqs if p not in catalog and p not in completed]
    waiting = [p for p in prereqs if p in remaining]
    if missing:
        reasons.append("prerequisite not in catalog: " + ", ".join(missing))
    if details.get("credits", 3) > max_credits:
        reasons.append(f"needs {details.get('credits', 3)} credits, more than the {max_credits}-credit semester limit")
    if waiting:
        reasons.append("waiting on unscheduled prerequisite: " + ", ".join(waiting))
    if not reasons:
        reasons.append(f"could not be placed within {MAX_SEMESTERS} semesters (check preferred term or offering rules)")
    return "; ".join(reasons)


# --------------------------------------------------------------------------
# Prerequisite map
# --------------------------------------------------------------------------
def build_course_map(catalog, completed, failed, schedule, unscheduled):
    """
    Data for the prerequisite map: one node per course (with its column "level",
    the longest prerequisite chain leading to it) and one edge per prerequisite.
    Status is "none" until a schedule has been generated.
    """
    passed = set(completed)
    failed_codes = {code for code, _, _ in failed}
    term_of = {c["code"]: sem["term"] for sem in schedule for c in sem["courses"]}
    unscheduled_codes = {u["code"] for u in unscheduled}

    levels = {}
    visiting = set()

    def level(code):
        if code in levels:
            return levels[code]
        if code in visiting:  # circular prereqs: stop descending
            return 0
        visiting.add(code)
        parents = [p for p in catalog[code].get("prereqs", []) if p in catalog]
        levels[code] = 1 + max((level(p) for p in parents), default=-1)
        visiting.discard(code)
        return levels[code]

    nodes, edges = [], []
    for code, details in catalog.items():
        if code in passed:
            status = "passed"
        elif code in failed_codes:
            status = "failed"
        elif code in term_of:
            status = "scheduled"
        elif code in unscheduled_codes:
            status = "unscheduled"
        else:
            status = "none"
        nodes.append({
            "code": code,
            "name": details.get("name", code),
            "credits": details.get("credits", 3),
            "category": details.get("category", "General Education"),
            "level": level(code),
            "status": status,
            "term": term_of.get(code, ""),
        })
        for p in details.get("prereqs", []):
            if p in catalog:
                edges.append([p, code])
    return {"nodes": nodes, "edges": edges}


# --------------------------------------------------------------------------
# Scheduler
# --------------------------------------------------------------------------
def optimize_degree_plan(catalog, completed_courses, preferred_terms=None, max_credits=18, start_term="Fall", start_year=2026, extra_credits=0):
    """
    Returns (schedule, unscheduled).

    Courses are placed in order of the longest chain of courses depending on them,
    so a course that unlocks many others (Calculus I) is never crowded out by
    free-standing ones (gen eds). Optional per-course JSON fields:
      "offered":     ["Fall"] or ["Spring"]  - seasons the course is offered
      "min_credits": 60                      - credits needed before taking it
    extra_credits (transfer, AP, dual credit) count toward "min_credits" eligibility.
    """
    if preferred_terms is None:
        preferred_terms = {}

    completed = set(completed_courses)
    remaining = {code: data for code, data in catalog.items() if code not in completed}
    depth = chain_lengths(catalog)
    credits_done = sum(catalog[c].get("credits", 3) for c in completed if c in catalog) + extra_credits

    schedule = []
    current_term = start_term
    current_year = int(start_year)

    semester_count = 0
    while remaining and semester_count < MAX_SEMESTERS:
        semester_count += 1
        current_term_label = f"{current_term} {current_year}"
        curr_rank = term_rank(current_term_label)

        current_semester = []
        current_credits = 0
        scheduled_this_round = []

        # Longest dependency chain first, then lower course numbers (freshman
        # courses before upper-level), then bigger courses.
        candidates = sorted(
            remaining.items(),
            key=lambda kv: (-depth.get(kv[0], 1), course_number(kv[0]), -kv[1].get("credits", 3), kv[0]),
        )

        for code, details in candidates:
            course_credits = details.get("credits", 3)

            if not all(p in completed for p in details.get("prereqs", [])):
                continue

            pref_term = preferred_terms.get(code, "AUTO")
            if pref_term != "AUTO" and curr_rank < term_rank(pref_term):
                continue

            offered = details.get("offered")
            if offered and current_term not in offered:
                continue

            if credits_done < required_credits(code, details):
                continue

            if current_credits + course_credits > max_credits:
                continue

            current_semester.append({"code": code, "name": details.get("name", code), "credits": course_credits})
            current_credits += course_credits
            scheduled_this_round.append(code)

        if scheduled_this_round:
            for code in scheduled_this_round:
                completed.add(code)
                del remaining[code]
            credits_done += current_credits

            schedule.append({
                "term": current_term_label,
                "credits": current_credits,
                "courses": current_semester,
            })

        # Advance semester
        if current_term == "Fall":
            current_term = "Spring"
            current_year += 1
        else:
            current_term = "Fall"

    unscheduled = [
        {
            "code": code,
            "name": details.get("name", code),
            "credits": details.get("credits", 3),
            "reason": explain_unscheduled(code, details, catalog, remaining, completed, max_credits),
        }
        for code, details in remaining.items()
    ]
    return schedule, unscheduled


# --------------------------------------------------------------------------
# Shared form parsing
# --------------------------------------------------------------------------
def read_settings(form):
    start_term = form.get("start_term", "Fall")
    if start_term not in ("Fall", "Spring"):
        start_term = "Fall"
    return {
        "max_credits": to_int(form.get("max_credits"), 18, 6, 24),
        "start_term": start_term,
        "start_year": to_int(form.get("start_year"), 2026, 2025, 2032),
    }


def read_grades(form, catalog):
    """Returns grades, preferred terms, passed courses and courses that missed the minimum grade."""
    user_grades, preferred_terms = {}, {}
    completed, failed = [], []

    for code, details in catalog.items():
        grade = form.get(f"grade_{code}", "NONE")
        if grade not in GRADE_SCORES:
            grade = "NONE"
        user_grades[code] = grade
        preferred_terms[code] = form.get(f"pref_{code}", "AUTO")

        req_grade_str, min_score = get_min_passing_score(details.get("category", ""))
        score = GRADE_SCORES[grade]
        if score >= min_score:
            completed.append(code)
        elif score != -1:
            failed.append((code, grade, req_grade_str))

    return user_grades, preferred_terms, completed, failed


# --------------------------------------------------------------------------
# Student information, summary and saved plans
# --------------------------------------------------------------------------
def read_student(form):
    """Free-text student/advisor fields (trimmed and length-limited) plus other earned credits."""
    student = {key: (form.get(key, "") or "").strip()[:limit] for key, limit in STUDENT_FIELDS.items()}
    student["transfer_credits"] = to_int(form.get("transfer_credits"), 0, 0, 150)
    student["full_name"] = " ".join(p for p in (student["student_first"], student["student_last"]) if p)
    return student


def classification(credits):
    if credits >= 90:
        return "Senior"
    if credits >= 60:
        return "Junior"
    if credits >= 30:
        return "Sophomore"
    return "Freshman"


def build_summary(student, catalog, passed, schedule, unscheduled, generated):
    """Numbers shown in the summary card and the PDF header."""
    earned = sum(catalog[c].get("credits", 3) for c in passed if c in catalog) + student["transfer_credits"]
    summary = {
        "credits_earned": earned,
        "classification": classification(earned),
        "credits_remaining": None,
        "semesters": None,
        "projected_graduation": "",
    }
    if generated:
        summary["credits_remaining"] = sum(sem["credits"] for sem in schedule) + sum(u["credits"] for u in unscheduled)
        summary["semesters"] = len(schedule)
        if unscheduled:
            summary["projected_graduation"] = "Not reachable until unscheduled courses are fixed"
        elif schedule:
            summary["projected_graduation"] = schedule[-1]["term"]
        else:
            summary["projected_graduation"] = "All listed courses are complete"
    return summary


def file_name_part(text, fallback):
    """Safe piece of a download filename; accents are folded (María -> Maria)."""
    ascii_text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "", ascii_text.replace(" ", "_"))
    return cleaned[:40] or fallback


def parse_plan_file(upload):
    """Reads a saved plan (.json). Returns a dict of form fields, or None if it is not a valid plan."""
    raw = upload.read(MAX_PLAN_FILE_BYTES + 1)
    if len(raw) > MAX_PLAN_FILE_BYTES:
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    fields = data.get("fields") if isinstance(data, dict) else None
    if not isinstance(fields, dict):
        return None
    clean = {}
    for key, value in fields.items():
        if not isinstance(key, str) or isinstance(value, (dict, list)):
            continue
        if key in PLAN_FILE_FIELDS or key.startswith(("grade_", "pref_")):
            clean[key] = str(value)
    return clean or None


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    degree_programs = discover_degree_programs()

    # A plan can be loaded from a file saved earlier; it replaces the form values.
    form, plan_error, loaded_plan = request.form, "", False
    upload = request.files.get("plan_file")
    if request.method == "POST" and upload and upload.filename:
        fields = parse_plan_file(upload)
        if fields is None:
            plan_error = "That file is not a saved degree plan, so nothing was loaded."
        else:
            form, loaded_plan = fields, True

    selected_degree = form.get("degree", next(iter(degree_programs.keys()), ""))
    catalog, selected_degree = load_combined_course_catalog(selected_degree)
    categorized_catalog = group_catalog_by_category(catalog)
    degree_name = degree_programs.get(selected_degree, {}).get("name", "No degree selected")

    settings = {"max_credits": 18, "start_term": "Fall", "start_year": 2026}
    student = read_student({})
    schedule, unscheduled = [], []
    user_grades, preferred_terms = {}, {}
    passed, completed_courses, failed_courses = [], [], []
    generated = False

    if request.method == "POST" and not plan_error:
        settings = read_settings(form)
        student = read_student(form)
        user_grades, preferred_terms, passed, failed = read_grades(form, catalog)

        # Switching the degree dropdown re-submits the form without the
        # "generate" action, so it only reloads the course list.
        generated = (form.get("action") == "generate" or loaded_plan) and bool(catalog)
        if generated:
            completed_courses, failed_courses = passed, failed
            schedule, unscheduled = optimize_degree_plan(
                catalog, completed_courses, preferred_terms,
                settings["max_credits"], settings["start_term"], settings["start_year"],
                student["transfer_credits"],
            )

    summary = build_summary(student, catalog, passed, schedule, unscheduled, generated)
    upcoming_terms = generate_upcoming_terms(settings["start_term"], settings["start_year"], count=12)

    # Without a generated schedule every course shows as neutral; once one is
    # generated, passed/failed/scheduled/unscheduled statuses are filled in.
    course_map = build_course_map(catalog, completed_courses, failed_courses, schedule, unscheduled)

    return render_template(
        "index.html",
        degree_programs=degree_programs,
        selected_degree=selected_degree,
        degree_name=degree_name,
        catalog=catalog,
        categorized_catalog=categorized_catalog,
        schedule=schedule,
        unscheduled=unscheduled,
        course_map=course_map,
        user_grades=user_grades,
        preferred_terms=preferred_terms,
        upcoming_terms=upcoming_terms,
        completed_courses=completed_courses,
        failed_courses=failed_courses,
        max_credits=settings["max_credits"],
        start_term=settings["start_term"],
        start_year=settings["start_year"],
        student=student,
        summary=summary,
        generated=generated,
        plan_error=plan_error,
        get_min_passing_score=get_min_passing_score,
    )


@app.route("/save_plan", methods=["POST"])
def save_plan():
    """Downloads every form field as a .json file that can be loaded back later."""
    fields = {k: v for k, v in request.form.items() if k in PLAN_FILE_FIELDS or k.startswith(("grade_", "pref_"))}
    student = read_student(request.form)
    payload = {"app": "sau-degree-planner", "version": 1, "saved": datetime.date.today().isoformat(), "fields": fields}
    name = f"plan_{file_name_part(student['student_last'], 'student')}_{file_name_part(student['student_first'], 'plan')}.json"
    return Response(
        json.dumps(payload, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    degree_programs = discover_degree_programs()
    catalog, selected_degree = load_combined_course_catalog(request.form.get("degree", ""))
    degree_name = degree_programs.get(selected_degree, {}).get("name", "Degree Plan")

    settings = read_settings(request.form)
    student = read_student(request.form)
    _, preferred_terms, completed_courses, failed_courses = read_grades(request.form, catalog)
    schedule, unscheduled = optimize_degree_plan(
        catalog, completed_courses, preferred_terms,
        settings["max_credits"], settings["start_term"], settings["start_year"],
        student["transfer_credits"],
    )
    summary = build_summary(student, catalog, completed_courses, schedule, unscheduled, True)

    today = datetime.date.today()
    prepared = f"{today:%B} {today.day}, {today.year}"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=44)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=11)
    label_style = ParagraphStyle("Label", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.HexColor("#0f2942"))

    def field(text):
        return Paragraph(escape(text) if text else "&mdash;", cell_style)

    story = []

    title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontSize=18, leading=22, textColor=colors.HexColor("#0f2942"))
    story.append(Paragraph(f"Degree Plan: {escape(degree_name)}", title_style))
    story.append(Spacer(1, 8))

    info = Table([
        [Paragraph("Student", label_style), field(student["full_name"]), Paragraph("Student ID", label_style), field(student["student_id"])],
        [Paragraph("Email", label_style), field(student["student_email"]), Paragraph("Class standing", label_style), field(f"{summary['classification']} ({summary['credits_earned']} credits earned)")],
        [Paragraph("Advisor", label_style), field(student["advisor_name"]), Paragraph("Advisor email", label_style), field(student["advisor_email"])],
        [Paragraph("Major", label_style), field(degree_name), Paragraph("Catalog year", label_style), field(student["catalog_year"])],
        [Paragraph("Minor / concentration", label_style), field(student["minor"]), Paragraph("Prepared", label_style), field(prepared)],
    ], colWidths=[100, 160, 90, 170])
    info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f9ff")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bae6fd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(info)
    story.append(Spacer(1, 10))

    total_credits = sum(sem["credits"] for sem in schedule)
    meta_text = (
        f"<b>Start Term:</b> {settings['start_term']} {settings['start_year']} | "
        f"<b>Max Credits / Term:</b> {settings['max_credits']} | "
        f"<b>Remaining Credits Scheduled:</b> {total_credits} | "
        f"<b>Projected Completion:</b> {escape(summary['projected_graduation'])}"
    )
    story.append(Paragraph(meta_text, styles["Normal"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>SAU Rules:</b> Major/STEM C or higher, Gen Ed D or higher", styles["Normal"]))
    story.append(Spacer(1, 12))

    if student["notes"]:
        story.append(Paragraph("<b>Notes</b>", styles["Normal"]))
        story.append(Spacer(1, 3))
        notes_box = Table([[Paragraph(escape(student["notes"]).replace("\n", "<br/>"), cell_style)]], colWidths=[520])
        notes_box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#fcd34d")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(notes_box)
        story.append(Spacer(1, 12))

    if failed_courses:
        story.append(Paragraph("<b>Minimum grade not met (must retake):</b>", styles["Normal"]))
        for code, grade, req in failed_courses:
            story.append(Paragraph(f"&bull; {escape(code)}: received {grade}, requires {req} or higher", styles["Normal"]))
        story.append(Spacer(1, 14))

    if unscheduled:
        story.append(Paragraph("<b>Could not be scheduled:</b>", styles["Normal"]))
        for item in unscheduled:
            story.append(Paragraph(f"&bull; {escape(item['code'])} ({escape(item['name'])}): {escape(item['reason'])}", styles["Normal"]))
        story.append(Spacer(1, 14))

    for sem in schedule:
        block = [Paragraph(f"<b>{sem['term']}</b> ({sem['credits']} Total Credits)", styles["Heading2"]), Spacer(1, 6)]

        table_data = [["Course Code", "Course Title", "Credits"]]
        for c in sem["courses"]:
            table_data.append([Paragraph(escape(c["code"]), cell_style), Paragraph(escape(c["name"]), cell_style), str(c["credits"])])

        t = Table(table_data, colWidths=[110, 330, 80])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bae6fd")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f2942")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fcd34d")),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        block.append(t)
        block.append(Spacer(1, 14))
        story.append(KeepTogether(block))

    # Signature lines for the advising meeting
    sign = Table(
        [["", "", "", ""], ["Student signature", "", "Date", ""], ["", "", "", ""], ["Advisor signature", "", "Date", ""]],
        colWidths=[110, 230, 40, 120], rowHeights=[16, 14, 16, 14],
    )
    sign.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#475569")),
        ("LINEABOVE", (1, 1), (1, 1), 0.5, colors.black), ("LINEABOVE", (3, 1), (3, 1), 0.5, colors.black),
        ("LINEABOVE", (1, 3), (1, 3), 0.5, colors.black), ("LINEABOVE", (3, 3), (3, 3), 0.5, colors.black),
    ]))
    story.append(KeepTogether([Spacer(1, 16), sign]))

    footer_label = f"{student['full_name'] + ' - ' if student['full_name'] else ''}{degree_name}"

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(36, 24, footer_label[:90])
        canvas.drawRightString(letter[0] - 36, 24, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)

    name = f"{file_name_part(student['student_last'], selected_degree)}_Plan_{settings['start_term']}_{settings['start_year']}.pdf"
    return send_file(buffer, as_attachment=True, download_name=name, mimetype="application/pdf")


if __name__ == "__main__":
    # Change host to "0.0.0.0" to allow external connections over Tailscale
    app.run(host="0.0.0.0", port=5167, debug=True)
