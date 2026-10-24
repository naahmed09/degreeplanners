# Degree Planner - degreeplanners

A free, open source web app that helps college students turn their degree requirements into a clear semester-by-semester plan, from the first semester to graduation.

**Live at [degreeplanner.com](https://degreeplanner.com).**

The course data in this repository is currently tuned to Southern Arkansas University (SAU) courses. This project is not officially affiliated with, endorsed by or sponsored by SAU. The code is open for anyone to download and adapt to their own school (see [Adapt it for your school](#adapt-it-for-your-school)).

Students pick a degree, mark the courses they have already finished, and the planner builds a schedule that respects prerequisites, credit limits and when courses are offered. They can then adjust it, compare options, and bring a finished plan to their advisor.

> **This is a planning aid, not an official record.** Course data, prerequisites and offerings may be incomplete or out of date. Always confirm your plan with your advisor and the official catalog of your school before you register.

## Features

- **Schedule builder.** Places every remaining course in the earliest semester where its prerequisites are done, ordering courses so the ones that unlock the most later courses come first.
- **Prerequisite map.** An interactive diagram of how courses depend on each other. It works with a mouse or a keyboard.
- **Real constraints.** Credit limits per semester, summer terms, upper-level eligibility (credits earned), and optional "offered in Fall/Spring/Summer" data.
- **Choose-N requirements.** For rules like "pick 3 of these 9 electives."
- **Balanced or fastest.** Spread heavy courses across semesters, or finish as soon as possible.
- **Move courses.** Pin a course to a semester you prefer. The planner says when a move is not possible and why.
- **What-if comparison.** See finish dates for 12, 15 or 18 credits per semester, with and without summers.
- **Keep-on-schedule list.** Shows which courses would delay graduation if they slipped one semester.
- **Progress and estimates.** Percent complete, progress by category, GPA from the grades you enter, and a cost estimate from tuition and fee rates you type in.
- **PDF export and save/load.** Download a printable plan, or save the plan to a file and load it later.
- **Light and dark mode.**

## Privacy and accessibility

- No accounts, no cookies, no analytics, no ads and no third-party requests. Everything the page loads comes from this server.
- What a student types is used to build the plan and is not stored on the server.
- Saving work in the browser is **off** unless the student ticks "Remember my work on this device."
- Only the information the planner needs is requested. Personal details such as name and advisor are optional.
- The app includes Privacy Policy, Terms and Conditions, Cookies and Browser Storage, and Accessibility pages, and works with a keyboard and screen readers. It aims to meet WCAG 2.2 Level AA.

The wording of these pages describes how the planner works as written. If you run your own copy, have them reviewed by a lawyer or your institution.

## Run it locally

You need Python 3.9 or newer.

```bash
git clone <your-repo-url>
cd <your-repo-folder>

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python3 app.py
```

Open http://127.0.0.1:5067. Locally, the app runs in debug mode so edits reload automatically. Set `PLANNER_DEBUG=0` to turn that off, `PLANNER_PORT` to change the port, or `PLANNER_HOST=0.0.0.0` to reach it from other devices (debug is switched off automatically when you do).

`requirements.txt` should contain:

```
flask
reportlab
gunicorn
```

## Project layout

```
app.py                  the Flask app, scheduler and PDF export
gen_ed.json             General Education courses shared by every degree
degrees/                one JSON file per degree
templates/              index.html (planner) and the legal and accessibility pages
static/                 degreeplanners.png (logo) and static/vendor/tailwind.js
```

`static/vendor/tailwind.js` is a copy of Tailwind's browser build, served from this app so visitors' browsers never contact another site. It is required for the planner page to be styled.

## Settings

Near the top of `app.py`, fill in:

| Setting | What it is for |
| --- | --- |
| `OPERATOR_NAME` | Who runs this copy of the planner. Shown on the legal pages. |
| `CONTACT_EMAIL` | Contact address shown on the legal pages. |
| `GOVERNING_LAW` | Governing law named in the Terms, for example `the State of Arkansas`. |
| `LEGAL_UPDATED` | Date of the last legal wording change. Changing it asks visitors to agree to the Terms again. |
| `SOURCE_URL` | Link to this repository (must start with `https://`). |
| `SOURCE_LICENSE` | The license in your `LICENSE` file, for example `MIT`. |

Each can also be set as an environment variable, which overrides the file: `PLANNER_OPERATOR`, `PLANNER_CONTACT`, `PLANNER_LAW`, `PLANNER_UPDATED`, `PLANNER_SOURCE_URL`, `PLANNER_SOURCE_LICENSE`. Request logging is off by default; `PLANNER_ACCESS_LOG=1` turns it on (and the Privacy Policy should then be updated).

## Deploy on Render

1. Push this repository to GitHub.
2. In Render, create a **Web Service** from the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Add any environment variables from the table above under **Environment**.
6. Optional custom domain: under **Settings > Custom Domains**, add your domain (and its `www` version), then create the DNS records Render shows you. Render issues the HTTPS certificate automatically once DNS resolves.

Render provides HTTPS. `python3 app.py` is for local testing only.

## Course data

Degrees live in `degrees/*.json`, and shared General Education courses in `gen_ed.json`. Each course is an entry like:

```json
{
  "_metadata": { "name": "BS Engineering" },
  "MATH1525": {
    "name": "Calculus I",
    "credits": 5,
    "category": "Mathematics",
    "prereqs": []
  },
  "MATH1545": {
    "name": "Calculus II",
    "credits": 5,
    "category": "Mathematics",
    "prereqs": ["MATH1525"],
    "offered": ["Fall", "Spring"],
    "min_credits": 30,
    "difficulty": 3
  }
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `name`, `credits`, `category` | yes | Shown in the planner. |
| `prereqs` | yes | Course codes that must be finished in an earlier semester. |
| `offered` | no | Seasons the course is taught (`Fall`, `Spring`, `Summer`). Assumed every semester if missing. |
| `min_credits` | no | Credits a student must have earned first. Upper-level courses default to 30 (3000 level) and 60 (4000 level). |
| `difficulty` | no | 1 light, 2 moderate, 3 heavy. Estimated from the course level and subject if missing. |

**Choose-N requirements.** Add a `_groups` list to a degree file:

```json
"_groups": [
  { "id": "electives", "name": "IS Electives", "choose": 3,
    "courses": ["IS 3003", "IS 3063", "IS 3413", "IS 3983"] }
]
```

**Term offerings.** An optional `offerings.json` can hold seasons for many courses in one place: `{"MATH1525": ["Fall", "Spring"]}`.

### Check your data

```bash
python3 app.py check
```

reports missing prerequisites, circular prerequisites, credit totals that look wrong, duplicate course names under different codes, mixed code formats and courses with no offering data. The same report is at `/data-check` while the app runs.

## Adapt it for your school

The included course data (`gen_ed.json` and `degrees/*.json`) describes SAU programs. Nothing in the planner's logic is tied to SAU, so anyone can download the code and swap in their own school's courses. An AI coding assistant can do most of the data entry for you.

1. **Course data.** Replace the files in `degrees/` with one JSON file per degree at your school, and update `gen_ed.json` (see the format under Course data).
2. **School rules.** In `app.py`, review the settings marked `SCHOOL-SPECIFIC`: the categories that need a C or higher (`C_REQUIRED_CATEGORIES`, `get_min_passing_score`) and the earned credits needed for 3000 and 4000 level courses (`LEVEL_MIN_CREDITS`).
3. **Term offerings.** Optionally add `offerings.json` so courses are only placed in the terms they are taught.
4. **Check your work.** Run `python3 app.py check` to catch missing prerequisites, circular prerequisites and credit totals that look wrong.
5. **Make it yours.** Change the "Course data tuned to ..." and "not affiliated" wording in `templates/index.html`, the legal pages and the PDF footnote in `app.py` so they name your school. Add your own logo in `static/` (only a logo you have permission to use), and fill in the operator settings above. Have the legal pages reviewed for your situation.

A prompt you can give an AI assistant, along with this repository and your school's catalog pages:

```
Replace the SAU course data in this repository with the degree programs and general
education courses from <your school's catalog URL or pasted text>. Follow the JSON format in
the README, keep course codes consistent, add prerequisites, then run `python3 app.py check`
and fix every error it reports.
```

## Contributing and auditing

The code is public so that anyone can read it, check what it does with student information, and suggest improvements. Issues and pull requests are welcome, especially corrections to course data. If you spot a problem with the privacy or accessibility claims above, please open an issue.

## License

Add a `LICENSE` file to this repository and name the license in the setting above. The license covers the code only. University names and catalog information belong to their owners and are not covered by it. This project is independent and not officially affiliated with, endorsed by or sponsored by Southern Arkansas University (SAU).
