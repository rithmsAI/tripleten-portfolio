# Incident Response Workbench

A fictional incident investigation application by Kaya Robinson / rithmsAI. It turns an incident queue, sample logs, a working hypothesis, verification steps and status changes into an exportable investigation record.

**[Open the public workbench](https://rithmsai.github.io/tripleten-portfolio/projects/incidents/)** · [Portfolio](https://rithmsai.github.io/tripleten-portfolio/)

## What this demonstrates

This project connects enterprise support experience to application engineering: explicit workflow rules, input validation, persistence, evidence filtering, transaction boundaries, stale-write detection and readable operational records. It complements the portfolio's ML benchmark and sustainability analysis with a task-oriented application.

## Two-minute walkthrough

1. Choose INC-1042 and assign a fictional investigator display name.
2. Filter the evidence stream to ERROR. Compare cached keyset k17 with deployed k18.
3. Save a hypothesis linking that mismatch to the sign-in failures.
4. Write a rationale and move through investigating and mitigated.
5. Try resolving before checking the runbook: the application blocks it.
6. Complete the three verification steps, resolve, and export a plain-text report.

The recovery log is a fixed fixture, not evidence that clicking a button executed a mitigation. Runbook completion is self-attested. Reset asks for confirmation and affects only browser-local demo state.

## Architectures and honest boundaries

| Public browser demo | Local API reference |
|---|---|
| HTML/CSS/JavaScript, no installation | Python, FastAPI, SQLite |
| State stored under a dedicated localStorage key | Durable SQLite incident and audit tables |
| Runs without sending notes to a server | POST commands update state and append an audit row in one transaction |
| UI enforces staged transitions | Server independently validates commands and rejects stale versions |
| One browser; no shared collaboration | Local demonstration; no authentication or production tenancy |

These are separate implementations; the public UI is **not connected** to the local API. The test suites exercise both implementations' transition and verification rules. The API has no network integrations and must be bound to loopback. Do not expose it publicly without authentication, authorization, request-size/rate controls, production logging and a deployment threat review.

The UI uses textContent for user-generated content, rather than injecting HTML. Reports are plain text, avoiding HTML interpretation and CSV formula execution. localStorage is not a secure store: browser users can alter or clear it. API audit records are append-only through the exposed routes, but a database owner can change them; neither audit mechanism is cryptographically tamper-proof. The local API uses BEGIN IMMEDIATE, a version check and parameterized SQL. A failed command rolls back when its connection closes.

## Reproduce the public demo

From the portfolio repository root:

```sh
python -m http.server 8765 --bind 127.0.0.1
```

Open `http://127.0.0.1:8765/projects/incidents/`. The shared typography and light/midnight assets live at the repository's `assets/` directory. Opening the HTML directly as a file will not reliably load its JSON fixtures.

## Run the local API

From `projects/incidents` (or the standalone source folder):

```sh
python -m venv .venv
# Activate .venv using your platform's activation command.
python -m pip install -r requirements.txt
python -m uvicorn app:create_app --factory --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/docs` for the interactive API. A database is created on startup, not on import. Set `WORKBENCH_DB` to choose another local database path; its parent directory must already exist. No paid services, API keys or cloud accounts are required.

```sh
curl http://127.0.0.1:8000/incidents/INC-1042
curl -X POST http://127.0.0.1:8000/incidents/INC-1042/commands -H "Content-Type: application/json" -d '{"version":0,"kind":"transition","text":"investigating\nInspecting key mismatch in sample logs."}'
curl http://127.0.0.1:8000/incidents/INC-1042/report
```

Every command includes the current incident `version`; use the updated version returned by each response. Reusing an old version returns HTTP 409. Allowed command kinds: `owner`, `hypothesis`, `note`, `check`, `transition`. A check requires index 0–2 and a boolean `checked`. A transition uses the target state, newline and rationale in `text`. Unknown IDs return 404; invalid commands return 422.

## Validation

```sh
python -m unittest discover -s . -p 'test_workbench.py' -v
node test_frontend.cjs
```

10 API tests cover ordered transitions, verification gating, terminal state, stale writes, transactional non-mutation on failure, persistence/idempotent seeding, incident isolation, parameterized SQL, text payloads, validation, missing records and report headers. The JavaScript suite has 11 assertions covering log filters, transition rules and report content.

Manual browser checks: invalid transition rationale, investigator assignment, hypothesis saving, error filtering, blocked premature resolution, all verification steps, successful resolution, disabled editing after resolution, persistence after reload and downloaded report. See TEST_RESULTS.txt for the executed results.

## Data provenance

All three scenarios, timestamps, service names, log events and metrics were authored as fictional fixtures for this project. They are not employer records, public incident datasets or claims about real systems. `domain.py` is the fixture source; `fixtures.json` is its serialized browser copy. No Modern Habit or Santol code, data or product plans are included.

This is an operational reliability training application, not a security forensic tool or production incident management service. There is no ML model: deterministic workflow rules are appropriate for the small authored dataset. AI-assisted development was used; implemented behavior and limitations are documented and tested.

## Suggested next increments

Connect the UI to the API behind authentication; add per-user authorization, a migration strategy, pagination, structured metrics and failure injection. Evaluate any future AI summarizer against grounded human-written incident summaries before adding it to the investigation path.

## License

The original workbench source and fictional fixtures in this directory are MIT licensed; see LICENSE. Shared portfolio assets outside this directory retain their existing terms. Third-party dependencies retain their own licenses.
