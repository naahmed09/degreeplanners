import io
import json
import os
import re
from xml.sax.saxutils import escape

from flask import Flask, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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
# Scheduler
# --------------------------------------------------------------------------
def optimize_degree_plan(catalog, completed_courses, preferred_terms=None, max_credits=18, start_term="Fall", start_year=2026):
    """
    Returns (schedule, unscheduled).

    Courses are placed in order of the longest chain of courses depending on them,
    so a course that unlocks many others (Calculus I) is never crowded out by
    free-standing ones (gen eds). Optional per-course JSON fields:
      "offered":     ["Fall"] or ["Spring"]  - seasons the course is offered
      "min_credits": 60                      - credits needed before taking it
    """
    if preferred_terms is None:
        preferred_terms = {}

    completed = set(completed_courses)
    remaining = {code: data for code, data in catalog.items() if code not in completed}
    depth = chain_lengths(catalog)
    credits_done = sum(catalog[c].get("credits", 3) for c in completed if c in catalog)

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
# Routes
# --------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    degree_programs = discover_degree_programs()
    selected_degree = request.form.get("degree", next(iter(degree_programs.keys()), ""))

    catalog, selected_degree = load_combined_course_catalog(selected_degree)
    categorized_catalog = group_catalog_by_category(catalog)
    degree_name = degree_programs.get(selected_degree, {}).get("name", "No degree selected")

    settings = {"max_credits": 18, "start_term": "Fall", "start_year": 2026}
    schedule, unscheduled = [], []
    user_grades, preferred_terms = {}, {}
    completed_courses, failed_courses = [], []

    if request.method == "POST":
        settings = read_settings(request.form)
        user_grades, preferred_terms, passed, failed = read_grades(request.form, catalog)

        # Switching the degree dropdown re-submits the form without the
        # "generate" action, so it only reloads the course list.
        if request.form.get("action") == "generate" and catalog:
            completed_courses, failed_courses = passed, failed
            schedule, unscheduled = optimize_degree_plan(
                catalog, completed_courses, preferred_terms,
                settings["max_credits"], settings["start_term"], settings["start_year"],
            )

    upcoming_terms = generate_upcoming_terms(settings["start_term"], settings["start_year"], count=12)

    return render_template(
        "index.html",
        degree_programs=degree_programs,
        selected_degree=selected_degree,
        degree_name=degree_name,
        catalog=catalog,
        categorized_catalog=categorized_catalog,
        schedule=schedule,
        unscheduled=unscheduled,
        user_grades=user_grades,
        preferred_terms=preferred_terms,
        upcoming_terms=upcoming_terms,
        completed_courses=completed_courses,
        failed_courses=failed_courses,
        max_credits=settings["max_credits"],
        start_term=settings["start_term"],
        start_year=settings["start_year"],
        get_min_passing_score=get_min_passing_score,
    )


@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    degree_programs = discover_degree_programs()
    catalog, selected_degree = load_combined_course_catalog(request.form.get("degree", ""))
    degree_name = degree_programs.get(selected_degree, {}).get("name", "Degree Plan")

    settings = read_settings(request.form)
    _, preferred_terms, completed_courses, failed_courses = read_grades(request.form, catalog)
    schedule, unscheduled = optimize_degree_plan(
        catalog, completed_courses, preferred_terms,
        settings["max_credits"], settings["start_term"], settings["start_year"],
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=11)

    story = []

    title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontSize=18, leading=22, textColor=colors.HexColor("#0f2942"))
    story.append(Paragraph(f"Optimized Degree Schedule: {escape(degree_name)}", title_style))
    story.append(Spacer(1, 12))

    total_credits = sum(sem["credits"] for sem in schedule)
    meta_text = (
        f"<b>Start Term:</b> {settings['start_term']} {settings['start_year']} | "
        f"<b>Max Credits / Term:</b> {settings['max_credits']} | "
        f"<b>Remaining Credits Scheduled:</b> {total_credits} | "
        "<b>SAU Rules:</b> Major/STEM C or higher, Gen Ed D or higher"
    )
    story.append(Paragraph(meta_text, styles["Normal"]))
    story.append(Spacer(1, 16))

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
        story.append(Paragraph(f"<b>{sem['term']}</b> ({sem['credits']} Total Credits)", styles["Heading2"]))
        story.append(Spacer(1, 6))

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
        story.append(t)
        story.append(Spacer(1, 14))

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{selected_degree}_Plan_{settings['start_term']}_{settings['start_year']}.pdf",
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    # Change host to "0.0.0.0" to allow external connections over Tailscale
    app.run(host="0.0.0.0", port=5067, debug=True)
