"""SAU Degree Planner.

Data files
  gen_ed.json        shared General Education courses
  degrees/*.json     one file per degree: course entries plus "_metadata" and optional "_groups"
  offerings.json     optional, {"MATH1525": ["Fall", "Spring"], ...}: seasons each course is taught

Optional per-course fields in the JSON files
  "offered":     ["Fall"]  seasons the course is taught (Spring, Summer, Fall)
  "min_credits": 60        earned credits required before the course may be taken
  "difficulty":  1-3       1 light, 2 moderate, 3 heavy (estimated when missing)

Optional per-degree "_groups" for "choose N of these" requirements
  "_groups": [{"id": "is_electives", "name": "IS Electives", "choose": 2, "courses": ["IS 3003", "IS 3413"]}]

Run
  python app.py          start the planner
  python app.py check    check the data files for mistakes

Environment (local testing with python app.py): PLANNER_HOST (default 127.0.0.1), PLANNER_PORT (default 5067), PLANNER_DEBUG=0 to turn debug off.
Hosting (Render): run "gunicorn app:app --bind 0.0.0.0:$PORT"; python app.py is not used there.
Legal pages (/privacy, /terms, /cookies, /accessibility) need who runs the planner. Fill in OPERATOR_NAME and CONTACT_EMAIL near the top of this file, or set these environment variables:
  PLANNER_OPERATOR   name of the person or organization responsible for the planner
  PLANNER_CONTACT    contact email for privacy and other questions
  PLANNER_LAW        governing law wording for the Terms, for example "the State of Arkansas"
  PLANNER_UPDATED    date the legal pages were last reviewed, for example "October 11, 2026"
Request logging is off so no addresses are written to disk; set PLANNER_ACCESS_LOG=1 to turn it on (and update /privacy).
"""
import datetime
import io
import json
import logging
import math
import os
import re
import sys
import unicodedata
from xml.sax.saxutils import escape

from flask import Flask, Response, render_template, render_template_string, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import KeepTogether, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # saved-plan uploads are tiny; refuse anything larger

# ---------------------------------------------------------------------------
# EDIT THESE: who runs this planner. The Privacy, Terms, Cookies and Accessibility pages show them.
# (Optional: environment variables PLANNER_OPERATOR, PLANNER_CONTACT, PLANNER_LAW and PLANNER_UPDATED
#  override these, for example on Render.)
# ---------------------------------------------------------------------------
OPERATOR_NAME = "Nasif Ahmed"                           # for example "Nasif Ahmed"
CONTACT_EMAIL = "naahmed6556@muleriders.saumag.edu"                           # for example "you@example.com" (shown publicly on the legal pages)
GOVERNING_LAW = "the State of Arkansas"      # used in the Terms
LEGAL_UPDATED = "October 12, 2026"           # change this whenever you change the legal wording
SOURCE_URL = "https://github.com/naahmed09/SAUDegPlanner"                              # link to the public GitHub repository, for example "https://github.com/you/degree-planner"
SOURCE_LICENSE = "MIT"                          # the license in your repository's LICENSE file, for example "MIT"

OPERATOR = {
    "name": os.environ.get("PLANNER_OPERATOR", OPERATOR_NAME).strip(),
    "contact": os.environ.get("PLANNER_CONTACT", CONTACT_EMAIL).strip(),
    "law": os.environ.get("PLANNER_LAW", GOVERNING_LAW).strip(),
    "updated": os.environ.get("PLANNER_UPDATED", LEGAL_UPDATED).strip(),
    "source": os.environ.get("PLANNER_SOURCE_URL", SOURCE_URL).strip(),
    "license": os.environ.get("PLANNER_SOURCE_LICENSE", SOURCE_LICENSE).strip(),
}
if not OPERATOR["source"].lower().startswith("https://"):
    OPERATOR["source"] = ""   # only a plain https link is ever shown
OPERATOR["configured"] = bool(OPERATOR["name"] and OPERATOR["contact"])
ACCESS_LOG = os.environ.get("PLANNER_ACCESS_LOG") == "1"
if not ACCESS_LOG:
    logging.getLogger("werkzeug").setLevel(logging.WARNING)  # the default log line includes each visitor's IP address

# Everything the page loads comes from this server: no third-party scripts, fonts, analytics or ads.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
    "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEN_ED_FILE = os.path.join(BASE_DIR, "gen_ed.json")
DEGREES_DIR = os.path.join(BASE_DIR, "degrees")
OFFERINGS_FILE = os.path.join(BASE_DIR, "offerings.json")

# CR = credit without a grade (transfer, AP, dual credit, pass); it satisfies any minimum grade but is left out of GPA.
GRADE_SCORES = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0, "CR": 5, "NONE": -1}
GRADE_POINTS = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}

SEASON_ORDER = {"Spring": 0, "Summer": 1, "Fall": 2}
TERM_RE = re.compile(r"^(Spring|Summer|Fall) (\d{4})$")

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

# Used to estimate how demanding a course is when the JSON has no "difficulty" field.
HEAVY_CATEGORIES = {
    "Engineering", "Mathematics", "Physics", "Chemistry", "Chemistry Electives",
    "Computer Science", "Biology Core", "Biology Electives",
}
MAJOR_CATEGORIES = {"Business Core", "Information Systems Analytics", "Information Systems Analytics Electives"}
DIFFICULTY_LABELS = {1: "Light", 2: "Moderate", 3: "Heavy"}

# Free-text student fields and their maximum lengths.
STUDENT_FIELDS = {
    "student_first": 80, "student_last": 80, "student_id": 30,
    "advisor_name": 120, "catalog_year": 20, "minor": 120,
    "notes": 3000,
}
SETTING_FIELDS = {
    "degree", "start_term", "start_year", "max_credits", "transfer_credits", "include_summer",
    "summer_credits", "balance", "tuition_per_credit", "fees_per_term",
}
PLAN_FILE_FIELDS = SETTING_FIELDS | set(STUDENT_FIELDS)
PLAN_PREFIXES = ("grade_", "pref_", "pin_", "pick_")
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

            meta = data.get("_metadata", {}) if isinstance(data, dict) else {}
            degree_name = meta.get("name", degree_key.replace("_", " ").title())

            programs[degree_key] = {
                "name": degree_name,
                "file": file_path,
            }
    return programs


def clean_seasons(value):
    """A list of valid season names from a JSON value (string or list), or [] when nothing valid."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [s for s in value if s in SEASON_ORDER]


def load_offerings():
    """Optional offerings.json overlay: course code -> seasons taught."""
    data = load_json_file(OFFERINGS_FILE)
    offerings = {}
    if isinstance(data, dict):
        for code, seasons in data.items():
            if str(code).startswith("_"):
                continue
            seasons = clean_seasons(seasons)
            if seasons:
                offerings[code] = seasons
    return offerings


def normalize_groups(raw_groups, catalog):
    """Valid "choose N" groups: only courses that exist, each course in at most one group."""
    groups, seen, used_ids = [], set(), set()
    if not isinstance(raw_groups, list):
        return groups
    for index, raw in enumerate(raw_groups):
        if not isinstance(raw, dict):
            continue
        courses = []
        for code in raw.get("courses", []) if isinstance(raw.get("courses"), list) else []:
            if isinstance(code, str) and code in catalog and code not in seen and code not in courses:
                courses.append(code)
        if not courses:
            continue
        seen.update(courses)
        choose = to_int(raw.get("choose"), 1, 1, len(courses))
        gid = re.sub(r"[^A-Za-z0-9_-]", "", str(raw.get("id") or "")) or f"group{index + 1}"
        while gid in used_ids:
            gid += "x"
        used_ids.add(gid)
        groups.append({
            "id": gid,
            "name": str(raw.get("name") or f"Choose {choose}")[:80],
            "choose": choose,
            "courses": courses,
            "category": catalog[courses[0]].get("category", "General Education"),
        })
    return groups


def load_degree(degree_key):
    """Everything about one degree: merged catalog (gen ed + degree + offerings), its groups and name."""
    programs = discover_degree_programs()
    if degree_key not in programs:
        degree_key = next(iter(programs.keys())) if programs else ""

    gen_ed = load_json_file(GEN_ED_FILE)
    degree_data = load_json_file(programs[degree_key]["file"]) if degree_key else {}
    if not isinstance(gen_ed, dict):
        gen_ed = {}
    if not isinstance(degree_data, dict):
        degree_data = {}

    catalog = {}
    for code, details in {**gen_ed, **degree_data}.items():
        if str(code).startswith("_") or not isinstance(details, dict):
            continue
        details = dict(details)
        credits = details.get("credits", 3)
        if isinstance(credits, bool) or not isinstance(credits, (int, float)) or credits <= 0:
            details["credits"] = 3
        if not isinstance(details.get("prereqs"), list):
            details["prereqs"] = []
        if "offered" in details:
            details["offered"] = clean_seasons(details["offered"])
        catalog[code] = details

    for code, seasons in load_offerings().items():
        if code in catalog:
            catalog[code]["offered"] = seasons

    return {
        "key": degree_key,
        "name": programs.get(degree_key, {}).get("name", "No degree selected"),
        "programs": programs,
        "catalog": catalog,
        "groups": normalize_groups(degree_data.get("_groups", []), catalog),
    }


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


def to_int(value, default, low, high):
    """Parses an int from form input and clamps it, falling back to default."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def to_float(value, default, low, high):
    """Parses a number from form input ('$1,250.50' works) and clamps it."""
    try:
        number = float(str(value).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return default
    if number != number:  # NaN
        return default
    return max(low, min(high, number))


def money(value):
    return f"${value:,.0f}"


app.jinja_env.filters["money"] = money


def next_term(season, year, include_summer):
    if season == "Fall":
        return "Spring", year + 1
    if season == "Spring":
        return ("Summer", year) if include_summer else ("Fall", year)
    return "Fall", year  # Summer -> Fall


def term_sequence(start_term, start_year, count, include_summer):
    """Consecutive term labels such as 'Fall 2026', 'Spring 2027', ..."""
    season, year = start_term, int(start_year)
    labels = []
    for _ in range(count):
        labels.append(f"{season} {year}")
        season, year = next_term(season, year, include_summer)
    return labels


def generate_upcoming_terms(start_term="Fall", start_year=2026, count=12, include_summer=False):
    return term_sequence(start_term, start_year, count, include_summer)


def term_rank(term_label):
    """Converts 'Fall 2026' into an integer so terms can be compared chronologically."""
    match = TERM_RE.match(term_label or "")
    if not match:
        return 0
    return int(match.group(2)) * 3 + SEASON_ORDER[match.group(1)]


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


def course_difficulty(code, details):
    """1 light, 2 moderate, 3 heavy. The JSON "difficulty" field wins; otherwise a rough estimate."""
    value = details.get("difficulty")
    if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 3:
        return value
    credits = details.get("credits", 3)
    category = details.get("category", "")
    number = course_number(code)
    level = number // 1000 if number != 9999 else 0
    if credits <= 2:
        return 1
    if category in HEAVY_CATEGORIES:
        return 3 if (credits >= 5 or level >= 3) else 2
    if category in MAJOR_CATEGORIES:
        return 2 if level >= 3 else 1
    return 1


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


def unlock_counts(catalog):
    """How many courses (directly or through a chain) wait on each course."""
    children = {code: [] for code in catalog}
    for code, details in catalog.items():
        for p in details.get("prereqs", []):
            if p in children:
                children[p].append(code)
    counts = {}
    for code in catalog:
        seen, stack = set(), list(children[code])
        while stack:
            current = stack.pop()
            if current in seen or current == code:
                continue
            seen.add(current)
            stack.extend(children[current])
        counts[code] = len(seen)
    return counts


# --------------------------------------------------------------------------
# "Choose N of these" requirement groups
# --------------------------------------------------------------------------
def resolve_groups(catalog, groups, passed, picks):
    """
    Decides which courses of each group are part of the plan.
    Passed courses count first; then the student's own picks; then the planner fills any
    remaining slots, preferring courses that other courses depend on, then easier prerequisites.
    Returns (group info list, set of courses left out of the plan).
    """
    direct_dependents = {code: [] for code in catalog}
    for code, details in catalog.items():
        for p in details.get("prereqs", []):
            if p in direct_dependents:
                direct_dependents[p].append(code)

    info, excluded = [], set()
    for group in groups:
        members = set(group["courses"])
        done = [c for c in group["courses"] if c in passed]
        needed = max(0, group["choose"] - len(done))
        candidates = [c for c in group["courses"] if c not in passed]
        chosen = [c for c in candidates if c in picks][:needed]
        auto = []
        if len(chosen) < needed:
            rest = [c for c in candidates if c not in chosen]

            def fill_key(code):
                needed_by_others = sum(1 for d in direct_dependents[code] if d not in members)
                unmet = sum(1 for p in catalog[code].get("prereqs", []) if p not in passed)
                return (-needed_by_others, unmet, course_number(code), group["courses"].index(code))

            rest.sort(key=fill_key)
            auto = rest[: needed - len(chosen)]
        kept = set(chosen) | set(auto)
        skipped = [c for c in candidates if c not in kept]
        excluded.update(skipped)
        info.append({
            **group,
            "done": done,
            "needed": needed,
            "chosen": chosen,
            "auto": auto,
            "excluded": skipped,
            "selected": [c for c in group["courses"] if c in kept or c in done],
        })
    return info, excluded


# --------------------------------------------------------------------------
# Scheduler
# --------------------------------------------------------------------------
def build_context(catalog, excluded=()):
    """Per-request data the scheduler reuses on every run (it may run hundreds of times)."""
    excluded = set(excluded)
    active = {code: details for code, details in catalog.items() if code not in excluded}
    depth = chain_lengths(active)
    number = {code: course_number(code) for code in active}
    order = sorted(active, key=lambda c: (-depth.get(c, 1), number[c], -active[c].get("credits", 3), c))
    return {
        "catalog": active,
        "all": catalog,
        "excluded": excluded,
        "depth": depth,
        "order": order,
        "difficulty": {code: course_difficulty(code, details) for code, details in active.items()},
        "required": {code: required_credits(code, details) for code, details in active.items()},
    }


def pin_term_problem(label, start_rank, include_summer):
    match = TERM_RE.match(label or "")
    if not match:
        return "that is not a valid term"
    if match.group(1) == "Summer" and not include_summer:
        return "summer terms are turned off"
    if term_rank(label) < start_rank:
        return "that term is before your start term"
    return ""


def explain_unscheduled(ctx, code, remaining, completed, pending_pins, settings):
    catalog = ctx["catalog"]
    details = catalog[code]
    reasons = []
    prereqs = details.get("prereqs", [])
    missing = [p for p in prereqs if p not in catalog and p not in completed and p not in ctx["excluded"]]
    skipped = [p for p in prereqs if p in ctx["excluded"]]
    waiting = [p for p in prereqs if p in remaining]
    credits = details.get("credits", 3)
    seasons = {"Spring", "Fall"} | ({"Summer"} if settings["include_summer"] else set())
    if missing:
        reasons.append("prerequisite not in catalog: " + ", ".join(missing))
    if skipped:
        reasons.append("needs " + ", ".join(skipped) + ", which is not part of your plan (an unselected choice)")
    top_cap = max(settings["max_credits"], settings["summer_credits"] if settings["include_summer"] else 0)
    if credits > top_cap:
        reasons.append(f"needs {credits} credits, more than the {top_cap}-credit semester limit")
    offered = details.get("offered")
    if offered and not (set(offered) & seasons):
        reasons.append("only offered in " + "/".join(offered) + (", but summer terms are off" if "Summer" in offered else ""))
    if waiting:
        reasons.append("waiting on unscheduled prerequisite: " + ", ".join(waiting))
    if code in pending_pins:
        reasons.append(f"pinned to {pending_pins[code]}, which is beyond the planning window")
    if not reasons:
        reasons.append(f"could not be placed within {MAX_SEMESTERS} terms (check Earliest Term and offering rules)")
    return "; ".join(reasons)


def run_schedule(ctx, completed_courses, settings, preferred_terms=None, pins=None, extra_credits=0,
                 heavy_cap=None, soft_cap=None):
    """
    One scheduling pass. Returns {"schedule", "unscheduled", "conflicts"}.

    Courses are placed in order of the longest chain of courses depending on them, so a course that
    unlocks many others (Calculus I) is never crowded out by free-standing ones (gen eds).
    pins:      {course: "Fall 2027"} places a course in exactly that term when it is allowed there
    heavy_cap: most heavy (difficulty 3) courses per term; soft_cap: credit target per regular term
    """
    catalog = ctx["catalog"]
    preferred_terms = preferred_terms or {}
    include_summer = settings["include_summer"]

    completed = set(completed_courses)
    remaining = {code for code in catalog if code not in completed}
    credits_done = sum(catalog[c].get("credits", 3) for c in completed if c in catalog) + extra_credits

    season, year = settings["start_term"], int(settings["start_year"])
    start_rank = term_rank(f"{season} {year}")

    conflicts, pending = [], {}
    for code, label in (pins or {}).items():
        if code not in remaining:
            continue
        reason = pin_term_problem(label, start_rank, include_summer)
        if reason:
            conflicts.append({"code": code, "term": label, "reason": reason})
        else:
            pending[code] = label

    latest_constraint = max(
        [term_rank(t) for t in pending.values()]
        + [term_rank(preferred_terms[c]) for c in remaining if preferred_terms.get(c, "AUTO") != "AUTO"]
        + [0]
    )

    schedule = []
    empty_streak = 0
    for _ in range(MAX_SEMESTERS):
        if not remaining:
            break
        label = f"{season} {year}"
        rank = term_rank(label)
        hard_cap = settings["summer_credits"] if season == "Summer" else settings["max_credits"]
        cap = hard_cap if (soft_cap is None or season == "Summer") else min(hard_cap, soft_cap)

        placed, placed_codes = [], set()
        state = {"used": 0, "heavy": 0}

        def problem(code, limit):
            details = catalog[code]
            missing = [p for p in details.get("prereqs", []) if p not in completed]
            if missing:
                return "it needs " + ", ".join(missing) + " completed first"
            pref = preferred_terms.get(code, "AUTO")
            if pref != "AUTO" and rank < term_rank(pref):
                return f"its Earliest Term is {pref}"
            offered = details.get("offered")
            if offered and season not in offered:
                return f"it is not offered in {season}"
            if credits_done < ctx["required"][code]:
                return f"it needs {ctx['required'][code]} earned credits first"
            if state["used"] + details.get("credits", 3) > limit:
                return f"it would go over the {limit}-credit limit"
            return ""

        def place(code, pinned=False):
            details = catalog[code]
            credits = details.get("credits", 3)
            placed.append({
                "code": code, "name": details.get("name", code), "credits": credits,
                "difficulty": ctx["difficulty"][code], "pinned": pinned,
            })
            placed_codes.add(code)
            state["used"] += credits
            if ctx["difficulty"][code] >= 3:
                state["heavy"] += 1

        for code in [c for c in ctx["order"] if pending.get(c) == label]:
            why = problem(code, hard_cap)
            if why:
                conflicts.append({"code": code, "term": label, "reason": why})
                del pending[code]
            else:
                del pending[code]
                place(code, pinned=True)

        for code in ctx["order"]:
            if code not in remaining or code in placed_codes or code in pending:
                continue
            if problem(code, cap):
                continue
            if heavy_cap is not None and ctx["difficulty"][code] >= 3 and state["heavy"] >= heavy_cap:
                continue
            place(code)

        if placed:
            for item in placed:
                completed.add(item["code"])
                remaining.discard(item["code"])
            credits_done += state["used"]
            schedule.append({"term": label, "credits": state["used"], "heavy": state["heavy"], "courses": placed})
            empty_streak = 0
        else:
            empty_streak += 1

        season, year = next_term(season, year, include_summer)
        if remaining and empty_streak >= 6 and rank > latest_constraint:
            break

    unscheduled = [
        {
            "code": code,
            "name": details.get("name", code),
            "credits": details.get("credits", 3),
            "reason": explain_unscheduled(ctx, code, remaining, completed, pending, settings),
        }
        for code, details in catalog.items() if code in remaining
    ]
    return {"schedule": schedule, "unscheduled": unscheduled, "conflicts": conflicts}


def completion_rank(result):
    if result["unscheduled"]:
        return 10 ** 9
    return term_rank(result["schedule"][-1]["term"]) if result["schedule"] else 0


def balance_score(result):
    """Lower is better: even credits from term to term, and few heavy courses stacked together."""
    regular = [s["credits"] for s in result["schedule"] if not s["term"].startswith("Summer")]
    if not regular:
        return 0.0
    mean = sum(regular) / len(regular)
    deviation = math.sqrt(sum((c - mean) ** 2 for c in regular) / len(regular))
    return deviation + 1.5 * max(s["heavy"] for s in result["schedule"])


def plan_with_mode(ctx, completed, settings, preferred, pins, extra_credits, coarse=False):
    """
    The plan for the chosen mode. "fastest" packs each term. "balanced" evens out credits and spreads
    heavy courses, but only accepts a plan that finishes in the same term as the fastest one.
    The result carries "params" (the heavy/soft caps used) and "mode".
    """
    base = run_schedule(ctx, completed, settings, preferred, pins, extra_credits)
    base["params"] = {"heavy_cap": None, "soft_cap": None}
    base["mode"] = "fastest"
    if settings["balance"] != "balanced" or not base["schedule"] or base["unscheduled"]:
        return base

    target = completion_rank(base)
    total = sum(s["credits"] for s in base["schedule"])
    low = max(1, math.ceil(total / len(base["schedule"])))
    heavy_options = (2, None) if coarse else (1, 2, 3, None)
    soft_values = range(low, settings["max_credits"] + 1, 2 if coarse else 1)

    best, best_score = base, balance_score(base)
    for heavy in heavy_options:
        for soft in soft_values:
            result = run_schedule(ctx, completed, settings, preferred, pins, extra_credits, heavy_cap=heavy, soft_cap=soft)
            if result["unscheduled"] or completion_rank(result) > target:
                continue
            score = balance_score(result)
            if score < best_score - 1e-9:
                best, best_score = result, score
                best["params"] = {"heavy_cap": heavy, "soft_cap": soft}
    if best is not base:
        best["mode"] = "balanced"
    return best


def analyze_plan(ctx, completed, settings, preferred, pins, extra_credits, plan):
    """
    unlocks:  how many courses wait on each course
    critical: for courses whose one-term delay pushes the finish later, the old and new finish terms
    """
    unlocks = unlock_counts(ctx["catalog"])
    critical = {}
    schedule = plan["schedule"]
    if not schedule or plan["unscheduled"]:
        return {"unlocks": unlocks, "critical": critical}

    sequence = term_sequence(settings["start_term"], settings["start_year"], MAX_SEMESTERS + 12, settings["include_summer"])
    position = {label: i for i, label in enumerate(sequence)}
    base_last = schedule[-1]["term"]
    for sem in schedule:
        for course in sem["courses"]:
            code = course["code"]
            if course["pinned"] or position.get(sem["term"], 10 ** 6) + 1 >= len(sequence):
                continue
            later = sequence[position[sem["term"]] + 1]
            alt_preferred = dict(preferred)
            if term_rank(alt_preferred.get(code, "AUTO")) < term_rank(later):
                alt_preferred[code] = later
            alt_pins = {k: v for k, v in pins.items() if k != code}
            result = run_schedule(ctx, completed, settings, alt_preferred, alt_pins, extra_credits, **plan["params"])
            if result["unscheduled"] or not result["schedule"]:
                continue
            new_last = result["schedule"][-1]["term"]
            cost = position.get(new_last, 0) - position[base_last]
            if cost > 0:
                critical[code] = {"cost": cost, "from": base_last, "to": new_last, "term": sem["term"], "name": course["name"]}
    return {"unlocks": unlocks, "critical": critical}


def plan_cost(plan, settings, failed, catalog):
    """Tuition estimate from the student's own per-credit rate and per-semester fees; None when neither is set."""
    rate, fees = settings["tuition_per_credit"], settings["fees_per_term"]
    if rate <= 0 and fees <= 0:
        return None
    credits = sum(s["credits"] for s in plan["schedule"])
    terms = len(plan["schedule"])
    return {
        "rate": rate, "fees": fees, "credits": credits, "terms": terms,
        "tuition": credits * rate, "fees_total": terms * fees, "total": credits * rate + terms * fees,
        "retake": sum(catalog[c].get("credits", 3) for c, _, _ in failed if c in catalog) * rate,
    }


def what_if_scenarios(ctx, completed, settings, preferred, pins, extra_credits, plan):
    """Finish term for other credit loads, with and without summers. The current setting reuses the real plan."""
    caps = sorted({c for c in (12, 15, 18, settings["max_credits"]) if 6 <= c <= 24})
    rows = []
    for summer in (False, True):
        for cap in caps:
            current = cap == settings["max_credits"] and summer == settings["include_summer"]
            if current:
                result = plan
            else:
                alt = {**settings, "include_summer": summer, "max_credits": cap}
                if alt["start_term"] == "Summer" and not summer:
                    alt["start_term"] = "Fall"
                result = plan_with_mode(ctx, completed, alt, preferred, pins, extra_credits, coarse=True)
            schedule = result["schedule"]
            total = sum(s["credits"] for s in schedule)
            rows.append({
                "cap": cap, "summer": summer, "current": current,
                "terms": len(schedule),
                "finish": schedule[-1]["term"] if schedule and not result["unscheduled"] else "Not reachable" if result["unscheduled"] else "Done",
                "rank": completion_rank(result),
                "credits": total,
                "cost": total * settings["tuition_per_credit"] + len(schedule) * settings["fees_per_term"],
            })
    reachable = [r["rank"] for r in rows if r["rank"] < 10 ** 9]
    best = min(reachable) if reachable else None
    for row in rows:
        row["earliest"] = best is not None and row["rank"] == best
    return rows


# --------------------------------------------------------------------------
# Prerequisite map
# --------------------------------------------------------------------------
def build_course_map(catalog, completed, failed, schedule, unscheduled, meta=None):
    """
    Data for the prerequisite map: one node per course (with its column "level",
    the longest prerequisite chain leading to it) and one edge per prerequisite.
    Status is "none" until a schedule has been generated.
    """
    meta = meta or {}
    unlocks, critical, difficulty = meta.get("unlocks", {}), meta.get("critical", {}), meta.get("difficulty", {})
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
            "unlocks": unlocks.get(code, 0),
            "critical": critical.get(code, {}).get("cost", 0),
            "load": DIFFICULTY_LABELS.get(difficulty.get(code, 0), ""),
        })
        for p in details.get("prereqs", []):
            if p in catalog:
                edges.append([p, code])
    return {"nodes": nodes, "edges": edges}


# --------------------------------------------------------------------------
# Shared form parsing
# --------------------------------------------------------------------------
def read_settings(form):
    include_summer = form.get("include_summer") == "1"
    start_term = form.get("start_term", "Fall")
    if start_term not in SEASON_ORDER or (start_term == "Summer" and not include_summer):
        start_term = "Fall"
    balance = form.get("balance", "fastest")
    return {
        "max_credits": to_int(form.get("max_credits"), 18, 6, 24),
        "start_term": start_term,
        "start_year": to_int(form.get("start_year"), 2026, 2025, 2032),
        "include_summer": include_summer,
        "summer_credits": to_int(form.get("summer_credits"), 6, 1, 12),
        "balance": balance if balance in ("fastest", "balanced") else "fastest",
        "tuition_per_credit": to_float(form.get("tuition_per_credit"), 0.0, 0.0, 5000.0),
        "fees_per_term": to_float(form.get("fees_per_term"), 0.0, 0.0, 20000.0),
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


def read_pins(form, catalog):
    """Courses the student fixed to a specific term (by moving them on the schedule)."""
    pins = {}
    for code in catalog:
        label = form.get(f"pin_{code}", "")
        if TERM_RE.match(label or ""):
            pins[code] = label
    return pins


def read_picks(form, catalog):
    """Courses the student ticked in a "choose N" group."""
    return {code for code in catalog if form.get(f"pick_{code}") == "1"}


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


def estimate_gpa(grades, catalog):
    """Credit-weighted GPA of the letter grades entered; None when there are none."""
    points = credits = 0.0
    for code, grade in grades.items():
        if grade in GRADE_POINTS and code in catalog:
            weight = catalog[code].get("credits", 3)
            points += GRADE_POINTS[grade] * weight
            credits += weight
    return round(points / credits, 2) if credits else None


def build_progress(active, passed, schedule):
    """Credits done / planned / total for each category and overall, from the courses in the plan."""
    done_codes = set(passed)
    planned_codes = {c["code"] for sem in schedule for c in sem["courses"]}
    categories = {}
    for code, details in active.items():
        entry = categories.setdefault(details.get("category", "General Education"), {"total": 0, "done": 0, "planned": 0})
        credits = details.get("credits", 3)
        entry["total"] += credits
        if code in done_codes:
            entry["done"] += credits
        elif code in planned_codes:
            entry["planned"] += credits
    rows = []
    for name, entry in categories.items():
        total = entry["total"] or 1
        rows.append({
            "name": name, **entry,
            "done_pct": round(100 * entry["done"] / total),
            "planned_pct": round(100 * entry["planned"] / total),
        })
    overall = {key: sum(r[key] for r in rows) for key in ("total", "done", "planned")}
    total = overall["total"] or 1
    overall["done_pct"] = round(100 * overall["done"] / total)
    overall["planned_pct"] = round(100 * overall["planned"] / total)
    return {"rows": rows, "overall": overall}


def build_summary(student, active, passed, plan, generated, gpa):
    """Numbers shown in the summary card and the PDF header."""
    schedule, unscheduled = plan["schedule"], plan["unscheduled"]
    earned = sum(active[c].get("credits", 3) for c in passed if c in active) + student["transfer_credits"]
    summary = {
        "credits_earned": earned,
        "classification": classification(earned),
        "credits_remaining": None,
        "semesters": None,
        "projected_graduation": "",
        "percent": None,
        "gpa": gpa,
    }
    if generated:
        remaining = sum(sem["credits"] for sem in schedule) + sum(u["credits"] for u in unscheduled)
        summary["credits_remaining"] = remaining
        summary["semesters"] = len(schedule)
        summary["percent"] = round(100 * earned / (earned + remaining)) if earned + remaining else 100
        if unscheduled:
            summary["projected_graduation"] = "Not reachable until unscheduled courses are fixed"
        elif schedule:
            summary["projected_graduation"] = schedule[-1]["term"]
        else:
            summary["projected_graduation"] = "All listed courses are complete"
    return summary


def build_model(form, generate):
    """Everything the page and the PDF need, from one set of form values."""
    deg = load_degree(form.get("degree") or "")
    catalog = deg["catalog"]
    settings = read_settings(form)
    student = read_student(form)
    grades, preferred, passed, failed_all = read_grades(form, catalog)
    picks = read_picks(form, catalog)
    pins = read_pins(form, catalog)

    group_info, excluded = resolve_groups(catalog, deg["groups"], set(passed), picks)
    ctx = build_context(catalog, excluded)
    active = ctx["catalog"]
    passed_active = [c for c in passed if c in active]
    failed = [f for f in failed_all if f[0] in active]
    generated = bool(generate and active)

    plan = {"schedule": [], "unscheduled": [], "conflicts": [], "params": {"heavy_cap": None, "soft_cap": None}, "mode": "fastest"}
    analysis = {"unlocks": unlock_counts(active), "critical": {}}
    what_if = []
    if generated:
        plan = plan_with_mode(ctx, passed_active, settings, preferred, pins, student["transfer_credits"])
        analysis = analyze_plan(ctx, passed_active, settings, preferred, pins, student["transfer_credits"], plan)
        what_if = what_if_scenarios(ctx, passed_active, settings, preferred, pins, student["transfer_credits"], plan)
        honored = {c["code"]: sem["term"] for sem in plan["schedule"] for c in sem["courses"] if c["pinned"]}
        pins = {code: label for code, label in pins.items() if honored.get(code) == label}

    sequence = term_sequence(settings["start_term"], settings["start_year"], 40, settings["include_summer"])
    last_index = sequence.index(plan["schedule"][-1]["term"]) if plan["schedule"] else 0
    move_terms = sequence[: max(last_index + 4, 8)]
    upcoming_terms = sequence[: 16 if settings["include_summer"] else 12]

    gaps = sum(1 for sem in plan["schedule"] for c in sem["courses"] if not active[c["code"]].get("offered"))
    return {
        "deg": deg, "catalog": catalog, "active": active, "ctx": ctx,
        "settings": settings, "student": student,
        "grades": grades, "preferred": preferred, "passed": passed_active, "failed": failed,
        "picks": picks, "pins": pins,
        "group_info": group_info, "excluded": excluded,
        "generated": generated, "plan": plan, "analysis": analysis, "what_if": what_if,
        "summary": build_summary(student, active, passed_active, plan, generated, estimate_gpa(grades, catalog)),
        "progress": build_progress(active, passed_active, plan["schedule"]),
        "cost": plan_cost(plan, settings, failed, active) if generated else None,
        "move_terms": move_terms, "upcoming_terms": upcoming_terms,
        "offering_gaps": gaps,
        "scheduled_courses": sum(len(s["courses"]) for s in plan["schedule"]),
    }


def file_name_part(text, fallback):
    """Safe piece of a download filename; accents are folded (María -> Maria)."""
    ascii_text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "", ascii_text.replace(" ", "_"))
    return cleaned[:40] or fallback


def plan_field(key):
    return key in PLAN_FILE_FIELDS or key.startswith(PLAN_PREFIXES)


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
        if plan_field(key):
            clean[key] = str(value)
    return clean or None


# --------------------------------------------------------------------------
# Data checker: finds mistakes in the JSON catalog files
# --------------------------------------------------------------------------
def find_cycle(catalog):
    state, stack = {}, []

    def visit(code):
        state[code] = 1
        stack.append(code)
        for p in catalog[code].get("prereqs", []) if isinstance(catalog[code].get("prereqs"), list) else []:
            if p not in catalog:
                continue
            if state.get(p) == 1:
                return stack[stack.index(p):] + [p]
            if p not in state:
                found = visit(p)
                if found:
                    return found
        stack.pop()
        state[code] = 2
        return None

    for code in catalog:
        if code not in state:
            found = visit(code)
            if found:
                return found
    return None


def check_catalogs():
    """List of {"level": error|warning|info, "scope", "message"} for every degree file."""
    issues = []

    def add(level, scope, message):
        issues.append({"level": level, "scope": scope, "message": message})

    gen_ed = load_json_file(GEN_ED_FILE)
    gen_ed = {k: v for k, v in gen_ed.items() if isinstance(gen_ed, dict) and not k.startswith("_")} if isinstance(gen_ed, dict) else {}
    programs = discover_degree_programs()
    offerings_raw = load_json_file(OFFERINGS_FILE)
    if not gen_ed:
        add("error", "gen_ed.json", "No general education courses were found.")
    if not programs:
        add("error", "degrees/", "No degree files were found.")

    def check_fields(scope, courses):
        for code, d in courses.items():
            if not isinstance(d, dict):
                add("error", scope, f"{code}: entry is not an object.")
                continue
            for field in ("name", "credits", "category"):
                if field not in d:
                    add("error", scope, f"{code}: missing \"{field}\".")
            credits = d.get("credits")
            if "credits" in d and (isinstance(credits, bool) or not isinstance(credits, (int, float)) or credits <= 0):
                add("error", scope, f"{code}: credits must be a positive number (found {credits!r}).")
            elif isinstance(credits, (int, float)) and credits > 6:
                add("warning", scope, f"{code}: {credits} credits cannot be scheduled if a student sets the semester limit below {credits}.")
            if "prereqs" in d and not isinstance(d["prereqs"], list):
                add("error", scope, f"{code}: \"prereqs\" must be a list.")
            if "offered" in d and not clean_seasons(d["offered"]):
                add("warning", scope, f"{code}: \"offered\" has no valid season (use Spring, Summer, Fall).")
            if "difficulty" in d and d["difficulty"] not in (1, 2, 3):
                add("warning", scope, f"{code}: \"difficulty\" must be 1, 2 or 3.")
            if "min_credits" in d and (isinstance(d["min_credits"], bool) or not isinstance(d["min_credits"], int) or d["min_credits"] < 0):
                add("warning", scope, f"{code}: \"min_credits\" must be a whole number of credits.")

    check_fields("gen_ed.json", gen_ed)

    by_code, by_name, code_formats = {}, {}, {}
    for key, program in programs.items():
        raw = load_json_file(program["file"])
        scope = program["name"]
        if not isinstance(raw, dict):
            add("error", scope, "File is not a JSON object.")
            continue
        own = {k: v for k, v in raw.items() if not k.startswith("_")}
        check_fields(scope, own)
        merged = {k: v for k, v in {**gen_ed, **own}.items() if isinstance(v, dict)}

        for code, d in merged.items():
            by_code.setdefault(code, []).append((scope, d))
            if isinstance(d.get("name"), str):
                by_name.setdefault(d["name"].strip().lower(), set()).add(code)
        code_formats[scope] = any(" " in c for c in own)

        for code, d in merged.items():
            for p in d.get("prereqs", []) if isinstance(d.get("prereqs"), list) else []:
                if p not in merged:
                    add("error", scope, f"{code}: prerequisite \"{p}\" is not in the catalog, so {code} can never be scheduled.")
        cycle = find_cycle(merged)
        if cycle:
            add("error", scope, "Circular prerequisites: " + " -> ".join(cycle))

        # Credit total, counting only N courses for each "choose N" group
        groups_raw = raw.get("_groups", [])
        groups = normalize_groups(groups_raw, merged)
        if isinstance(groups_raw, list):
            for g in groups_raw:
                if not isinstance(g, dict) or not isinstance(g.get("courses"), list):
                    add("error", scope, "A group in \"_groups\" needs a \"courses\" list.")
                    continue
                unknown = [c for c in g["courses"] if c not in merged]
                if unknown:
                    add("error", scope, f"Group \"{g.get('name', g.get('id', '?'))}\" lists courses that do not exist: " + ", ".join(map(str, unknown)))
                if isinstance(g.get("choose"), int) and g["choose"] > len(g["courses"]):
                    add("warning", scope, f"Group \"{g.get('name', '?')}\" chooses {g['choose']} but lists only {len(g['courses'])} courses.")
        in_group = {c for g in groups for c in g["courses"]}
        total = sum(d.get("credits", 0) for c, d in merged.items() if c not in in_group and isinstance(d.get("credits"), (int, float)))
        for g in groups:
            smallest = sorted(merged[c].get("credits", 0) for c in g["courses"])
            total += sum(smallest[: g["choose"]])
        expected = (raw.get("_metadata") or {}).get("total_credits")
        if isinstance(expected, int) and total != expected:
            add("warning", scope, f"Required credits add up to {total}, but _metadata says {expected}.")
        elif not isinstance(expected, int) and total < 120:
            add("warning", scope, f"Required credits (including general education) add up to only {total}, below the usual 120 for a bachelor's degree. Check for missing courses or electives.")
        elif not isinstance(expected, int) and total > 132:
            add("info", scope, f"Required credits add up to {total}, which is high for a bachelor's degree. Some courses may be alternatives (see \"_groups\").")
        else:
            add("info", scope, f"Required credits add up to {total}.")

        # Categories that look like "pick some of these" but have no group
        cats = {}
        for code, d in own.items():
            if isinstance(d, dict):
                cats.setdefault(d.get("category", ""), []).append(code)
        for cat, codes in cats.items():
            if "elective" in cat.lower() and len(codes) >= 3 and not all(c in in_group for c in codes):
                add("info", scope, f"\"{cat}\" has {len(codes)} courses and every one is required. If students only pick some of them, define a group in \"_groups\".")

        missing_offer = sum(1 for c, d in merged.items() if not clean_seasons(d.get("offered")) and c not in load_offerings())
        add("info", scope, f"{missing_offer} of {len(merged)} courses have no term-offering data, so plans assume they are offered every term. Fill in \"offered\" or offerings.json.")

    for code, entries in by_code.items():
        names = {str(d.get("name", "")).strip() for _, d in entries}
        credits = {d.get("credits") for _, d in entries}
        if len(names) > 1:
            add("warning", "All degrees", f"{code} has different names in different files: " + "; ".join(sorted(names)))
        if len(credits) > 1:
            add("warning", "All degrees", f"{code} has different credit values in different files: " + ", ".join(map(str, sorted(credits, key=str))))
    for name, codes in by_name.items():
        if len(codes) > 1:
            add("warning", "All degrees", f"\"{name.title()}\" appears under different codes: " + ", ".join(sorted(codes)) + ". Use one code so plans line up.")
    if len(set(code_formats.values())) > 1:
        spaced = [s for s, v in code_formats.items() if v]
        add("info", "All degrees", "Course codes are written two ways (with a space like \"ECON 2103\" and without like \"MATH1525\"). Files with spaces: " + ", ".join(spaced) + ".")

    if isinstance(offerings_raw, dict):
        known = set(by_code)
        for code, seasons in offerings_raw.items():
            if str(code).startswith("_"):
                continue
            if code not in known:
                add("warning", "offerings.json", f"{code} is not in any degree or gen ed file.")
            if not clean_seasons(seasons):
                add("warning", "offerings.json", f"{code}: no valid season (use Spring, Summer, Fall).")

    order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: order[i["level"]])
    return issues


CHECK_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catalog data check</title>
<style>
  :root { color-scheme: light dark; --bg:#f0f9ff; --card:#fff; --ink:#0f2942; --mut:#475569; --line:#bae6fd; }
  @media (prefers-color-scheme: dark) { :root { --bg:#0e1826; --card:#1e2c40; --ink:#e2e8f0; --mut:#a0aec0; --line:#263e5c; } }
  body { margin:0; padding:24px; background:var(--bg); color:var(--ink); font:14px/1.5 system-ui, sans-serif; }
  main { max-width:56rem; margin:0 auto; } h1 { font-size:1.4rem; margin:0 0 4px; } p.sub { color:var(--mut); margin:0 0 16px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:4px 16px; margin-bottom:16px; }
  .row { display:flex; gap:10px; padding:10px 0; border-bottom:1px solid var(--line); } .row:last-child { border-bottom:0; }
  .tag { flex:none; font-size:11px; font-weight:700; padding:2px 8px; border-radius:999px; height:fit-content; text-transform:uppercase; }
  .error { background:#fecdd3; color:#881337; } .warning { background:#fde68a; color:#78350f; } .info { background:#bae6fd; color:#0c4a6e; }
  .scope { font-weight:700; } a { color:inherit; }
</style></head><body><main>
<h1>Catalog data check</h1>
<p class="sub">{{ counts.error }} errors, {{ counts.warning }} warnings, {{ counts.info }} notes. <a href="/">Back to the planner</a></p>
{% for level in ["error", "warning", "info"] %}{% if groups[level] %}
<div class="card">
  {% for item in groups[level] %}<div class="row"><span class="tag {{ level }}">{{ level }}</span><div><span class="scope">{{ item.scope }}</span><br>{{ item.message }}</div></div>{% endfor %}
</div>{% endif %}{% endfor %}
{% if not issues %}<p>No problems found.</p>{% endif %}
</main></body></html>"""


def run_cli_check():
    issues = check_catalogs()
    for level in ("error", "warning", "info"):
        for item in [i for i in issues if i["level"] == level]:
            print(f"[{level.upper():7}] {item['scope']}: {item['message']}")
    errors = sum(1 for i in issues if i["level"] == "error")
    warnings = sum(1 for i in issues if i["level"] == "warning")
    print(f"\n{errors} errors, {warnings} warnings.")
    return 1 if errors else 0


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    # A plan can be loaded from a file saved earlier; it replaces the form values.
    form, plan_error, loaded_plan = request.form, "", False
    upload = request.files.get("plan_file")
    if request.method == "POST" and upload and upload.filename:
        fields = parse_plan_file(upload)
        if fields is None:
            plan_error = "That file is not a saved degree plan, so nothing was loaded."
            form = {}
        else:
            form, loaded_plan = fields, True

    posted = request.method == "POST" and not plan_error
    generate = posted and (form.get("action") == "generate" or loaded_plan)
    # Switching the degree dropdown re-submits the form without the "generate" action,
    # so it only reloads the course list.
    m = build_model(form if posted else {}, generate)
    deg, plan, settings = m["deg"], m["plan"], m["settings"]

    group_of, picked, auto_picked = {}, set(), set()
    for g in m["group_info"]:
        for code in g["courses"]:
            group_of[code] = g
        picked.update(g["selected"])
        auto_picked.update(g["auto"])
    groups_by_category = {}
    for g in m["group_info"]:
        groups_by_category.setdefault(g["category"], []).append(g)

    catalog_json = {
        "courses": {c: {"n": d.get("name", c), "p": d.get("prereqs", []), "c": d.get("credits", 3)} for c, d in m["catalog"].items()},
        "groups": [{"id": g["id"], "choose": g["choose"], "courses": g["courses"]} for g in m["group_info"]],
    }
    critical = sorted(m["analysis"]["critical"].items(), key=lambda kv: (-kv[1]["cost"], kv[1]["term"]))

    course_map = build_course_map(
        m["active"], m["passed"] if m["generated"] else [], m["failed"] if m["generated"] else [],
        plan["schedule"], plan["unscheduled"],
        {"unlocks": m["analysis"]["unlocks"], "critical": m["analysis"]["critical"], "difficulty": m["ctx"]["difficulty"]},
    )

    return render_template(
        "index.html",
        degree_programs=deg["programs"],
        selected_degree=deg["key"],
        degree_name=deg["name"],
        catalog=m["catalog"],
        categorized_catalog=group_catalog_by_category(m["catalog"]),
        schedule=plan["schedule"],
        unscheduled=plan["unscheduled"],
        pin_conflicts=plan["conflicts"],
        plan_mode=plan["mode"],
        course_map=course_map,
        user_grades=m["grades"],
        preferred_terms=m["preferred"],
        pins=m["pins"],
        upcoming_terms=m["upcoming_terms"],
        move_terms=m["move_terms"],
        completed_courses=m["passed"] if m["generated"] else [],
        failed_courses=m["failed"] if m["generated"] else [],
        max_credits=settings["max_credits"],
        start_term=settings["start_term"],
        start_year=settings["start_year"],
        settings=settings,
        student=m["student"],
        summary=m["summary"],
        progress=m["progress"],
        cost=m["cost"],
        what_if=m["what_if"],
        critical=critical,
        unlocks=m["analysis"]["unlocks"],
        group_of=group_of,
        groups_by_category=groups_by_category,
        picked=picked,
        auto_picked=auto_picked,
        offering_gaps=m["offering_gaps"],
        scheduled_courses=m["scheduled_courses"],
        difficulty_labels=DIFFICULTY_LABELS,
        catalog_json=catalog_json,
        generated=m["generated"],
        posted=posted,
        plan_error=plan_error,
        get_min_passing_score=get_min_passing_score,
    )


@app.route("/save_plan", methods=["POST"])
def save_plan():
    """Downloads every form field as a .json file that can be loaded back later."""
    fields = {k: v for k, v in request.form.items() if plan_field(k)}
    student = read_student(request.form)
    payload = {"app": "sau-degree-planner", "version": 1, "saved": datetime.date.today().isoformat(), "fields": fields}
    name = f"plan_{file_name_part(student['student_last'], 'student')}_{file_name_part(student['student_first'], 'plan')}.json"
    return Response(
        json.dumps(payload, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.route("/data-check")
def data_check():
    """Read-only report on the catalog files, for whoever maintains them."""
    issues = check_catalogs()
    counts = {level: sum(1 for i in issues if i["level"] == level) for level in ("error", "warning", "info")}
    groups = {level: [i for i in issues if i["level"] == level] for level in counts}
    return render_template_string(CHECK_PAGE, issues=issues, counts=counts, groups=groups)


@app.context_processor
def inject_operator():
    return {"operator": OPERATOR}


@app.after_request
def privacy_headers(response):
    """Keep plan data out of caches and referrers, and stop the browser contacting any other site."""
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), interest-cohort=()"
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/cookies")
def cookies():
    return render_template("cookies.html")


@app.route("/accessibility")
def accessibility():
    return render_template("accessibility.html")


@app.errorhandler(413)
def too_large(_error):
    return "That upload is too large. Saved plans are small .json files.", 413


@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    m = build_model(request.form, True)
    deg, plan, settings, student, summary = m["deg"], m["plan"], m["settings"], m["student"], m["summary"]
    schedule, unscheduled = plan["schedule"], plan["unscheduled"]
    degree_name = deg["name"] if deg["key"] else "Degree Plan"

    today = datetime.date.today()
    prepared = f"{today:%B} {today.day}, {today.year}"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=44)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=11)
    note_style = ParagraphStyle("Note", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#475569"))
    label_style = ParagraphStyle("Label", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.HexColor("#0f2942"))

    def field(text):
        return Paragraph(escape(text) if text else "&mdash;", cell_style)

    story = []

    title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontSize=18, leading=22, textColor=colors.HexColor("#0f2942"))
    story.append(Paragraph(f"Degree Plan: {escape(degree_name)}", title_style))
    story.append(Spacer(1, 8))

    gpa_text = f"{summary['gpa']:.2f}" if summary["gpa"] is not None else ""
    info = Table([
        [Paragraph("Student", label_style), field(student["full_name"]), Paragraph("Student ID", label_style), field(student["student_id"])],
        [Paragraph("Advisor", label_style), field(student["advisor_name"]), Paragraph("Class standing", label_style), field(f"{summary['classification']} ({summary['credits_earned']} credits earned)")],
        [Paragraph("Major", label_style), field(degree_name), Paragraph("Catalog year", label_style), field(student["catalog_year"])],
        [Paragraph("Minor / concentration", label_style), field(student["minor"]), Paragraph("Estimated GPA", label_style), field(gpa_text)],
        [Paragraph("Prepared", label_style), field(prepared), Paragraph("Plan style", label_style), field(("Balanced" if plan["mode"] == "balanced" else "Fastest") + (", with summers" if settings["include_summer"] else ""))],
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

    if m["cost"]:
        cost = m["cost"]
        parts = [f"{cost['credits']} credits x {money(cost['rate'])} = {money(cost['tuition'])}"]
        if cost["fees"] > 0:
            parts.append(f"{cost['terms']} terms x {money(cost['fees'])} fees = {money(cost['fees_total'])}")
        text = f"<b>Estimated remaining cost: {money(cost['total'])}</b> ({'; '.join(parts)})."
        if cost["retake"] > 0:
            text += f" Retaking courses below the minimum grade accounts for {money(cost['retake'])} of this."
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Paragraph("Estimate from the per-credit rate and fees entered by the student; it does not include books or other costs.", note_style))
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

    if m["failed"]:
        story.append(Paragraph("<b>Minimum grade not met (must retake):</b>", styles["Normal"]))
        for code, grade, req in m["failed"]:
            story.append(Paragraph(f"&bull; {escape(code)}: received {grade}, requires {req} or higher", styles["Normal"]))
        story.append(Spacer(1, 14))

    if unscheduled:
        story.append(Paragraph("<b>Could not be scheduled:</b>", styles["Normal"]))
        for item in unscheduled:
            story.append(Paragraph(f"&bull; {escape(item['code'])} ({escape(item['name'])}): {escape(item['reason'])}", styles["Normal"]))
        story.append(Spacer(1, 14))

    if plan["conflicts"]:
        story.append(Paragraph("<b>Moves that could not be applied:</b>", styles["Normal"]))
        for c in plan["conflicts"]:
            story.append(Paragraph(f"&bull; {escape(c['code'])} to {escape(c['term'])}: {escape(c['reason'])}", styles["Normal"]))
        story.append(Spacer(1, 14))

    if m["group_info"]:
        story.append(Paragraph("<b>Requirement choices</b>", styles["Normal"]))
        for g in m["group_info"]:
            picked = "; ".join(f"{escape(c)}{' (planner choice)' if c in g['auto'] else ''}" for c in g["selected"]) or "none"
            story.append(Paragraph(f"&bull; {escape(g['name'])}, choose {g['choose']} of {len(g['courses'])}: {picked}", styles["Normal"]))
        story.append(Spacer(1, 12))

    critical = sorted(m["analysis"]["critical"].items(), key=lambda kv: (-kv[1]["cost"], kv[1]["term"]))[:8]
    if critical:
        story.append(Paragraph("<b>Courses to keep on schedule</b>", styles["Normal"]))
        for code, c in critical:
            story.append(Paragraph(
                f"&bull; {escape(code)} ({escape(c['term'])}): pushing it back one term moves graduation from {escape(c['from'])} to {escape(c['to'])}.",
                styles["Normal"]))
        story.append(Spacer(1, 12))

    for sem in schedule:
        term_cost = f", about {money(sem['credits'] * settings['tuition_per_credit'] + settings['fees_per_term'])}" if m["cost"] else ""
        block = [Paragraph(f"<b>{sem['term']}</b> ({sem['credits']} Total Credits{term_cost})", styles["Heading2"]), Spacer(1, 6)]

        table_data = [["Course Code", "Course Title", "Credits", "Load"]]
        for c in sem["courses"]:
            title = escape(c["name"]) + (" <i>(pinned)</i>" if c["pinned"] else "")
            table_data.append([Paragraph(escape(c["code"]), cell_style), Paragraph(title, cell_style), str(c["credits"]), DIFFICULTY_LABELS[c["difficulty"]]])

        t = Table(table_data, colWidths=[110, 280, 55, 75])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bae6fd")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f2942")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (2, 0), (3, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fcd34d")),
            ("ALIGN", (2, 0), (3, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        block.append(t)
        block.append(Spacer(1, 14))
        story.append(KeepTogether(block))

    footnotes = ["Load is an estimate of how demanding each course is (Light, Moderate, Heavy)."]
    if m["offering_gaps"]:
        footnotes.append(f"Term availability is not recorded for {m['offering_gaps']} of {m['scheduled_courses']} scheduled courses, so they are assumed to be offered every term. Confirm against the course schedule before registering.")
    story.append(Paragraph(" ".join(footnotes), note_style))

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

    name = f"{file_name_part(student['student_last'], deg['key'] or 'Degree')}_Plan_{settings['start_term']}_{settings['start_year']}.pdf"
    return send_file(buffer, as_attachment=True, download_name=name, mimetype="application/pdf")


def serve():
    """Local testing only (python app.py). On Render, Gunicorn runs the app instead: gunicorn app:app --bind 0.0.0.0:$PORT"""
    if not OPERATOR["configured"]:
        print("Reminder: fill in OPERATOR_NAME and CONTACT_EMAIL near the top of app.py so the Privacy, Terms and Cookies pages say who runs this planner.")
    if not OPERATOR["source"]:
        print("Reminder: set SOURCE_URL and SOURCE_LICENSE near the top of app.py so the open source notice links to your code.")
    host = os.environ.get("PLANNER_HOST", "127.0.0.1")   # this computer only; set PLANNER_HOST=0.0.0.0 to reach it from other devices
    port = int(os.environ.get("PLANNER_PORT", "5067"))
    debug = os.environ.get("PLANNER_DEBUG", "1") != "0"  # on locally so edits reload; the debugger is unsafe on a public host
    if debug and host != "127.0.0.1":
        print("Debug mode is only allowed on 127.0.0.1; turning it off because PLANNER_HOST is set to another address.")
        debug = False
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        sys.exit(run_cli_check())
    serve()
