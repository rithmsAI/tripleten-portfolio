# TraceBench · AI Evaluation Workbench

**A release decision should survive inspection.** TraceBench compares two sets of AI outputs, makes case-level regressions visible, and exports the evidence behind a configurable release gate.

Independent portfolio project by **Kaya Robinson / rithmsAI**, built with AI assistance. This is evaluation tooling, not a trained model or a production AI service.

[Live demo](https://rithmsai.github.io/tripleten-portfolio/projects/tracebench/) · [Technical tour](docs/RECRUITER.md) · [Architecture & limits](docs/ARCHITECTURE.md) · [Example report](docs/example-report.json)

## The memorable experiment

The 12-case fixture improves pass rate from **7/12 to 10/12** while introducing **two regressions, one critical**. The candidate meets the default numerical thresholds but fails the critical-regression gate. This is a deliberately authored example—not a measured model benchmark.

## Try it in two minutes

1. Compare category scores and inspect TB-003: the candidate fails the expected abstention flag on an undocumented override request.
2. Filter to regressions; inspect TB-009's unknown citation ID.
3. Write a human review note. Automated scores remain unchanged.
4. Disable the critical-regression blocker to see why a higher average alone can permit release. Restore it afterward.
5. Increase the minimum pass rate to 90%; the quality gate also blocks release.
6. Export the JSON report. It includes the complete input dataset, checks, thresholds, notes, engine version and dataset SHA-256 fingerprint.
7. Download the example dataset, edit an output, and re-import it. Invalid schemas or duplicate IDs are rejected without replacing the current run.

## Run locally

Requires Node.js 22.12+ (tested with 24.22.1).

```sh
npm ci
npm test
npm run build
npm run dev
# Or evaluate a file without opening the UI:
npm run evaluate -- public/example-dataset.json report.json
```

The CLI and React UI share the same typed evaluation engine. The CLI uses the default gates; the browser exports its currently selected gates. Export fingerprint is SHA-256 of `JSON.stringify(validatedDataset)` (order-sensitive JSON serialization, not a universal canonical-JSON scheme).

## What is implemented

- React + TypeScript comparison dashboard, category bars, searchable/filterable case table and side-by-side evidence inspector.
- Strict runtime checks on imported JSON: byte/count/text limits, unique IDs, valid types, nonnegative finite costs/latencies, and source-reference configuration.
- Deterministic phrase, citation-ID and abstention-metadata checks; paired improvement/regression classification.
- Adjustable pass-rate, p95 latency, total-cost and critical-regression gates over the complete dataset.
- Human review annotations and reproducible JSON export, including input provenance and a dataset fingerprint.
- Shared command-line evaluation, 20 automated tests, strict type checking and a reproducible locked dependency build.
- Responsive layout, labeled inputs, visible keyboard focus, semantic tables, status announcements and no HTML injection of imported text.

## Honest boundaries

All bundled prompts, sources, outputs, latency and cost figures are synthetic and hand-authored. No model provider is called. External outputs can be imported in the same schema, but their origin and measurements are supplied by the person importing them—not independently verified.

Phrase inclusion does **not** establish correctness (a negated answer may still match). Valid citation IDs do **not** prove that an answer is supported. Abstention uses a supplied boolean, not semantic refusal detection. Tests intentionally document these blind spots. Release criteria are illustrative decision aids, not safety certification.

Files and notes remain in tab memory; reload clears them. Export JSON to preserve a review. No backend, accounts, API keys, telemetry or database. Never import secrets or private employer/customer data. Static hosting receives normal page requests; fonts are fetched from Google Fonts. No imported file content is intentionally transmitted. The SHA-256 fingerprint detects changes to serialized inputs; it is not a signature or proof of who produced them.

## Repository layout

This project lives at `projects/tracebench/` in the public portfolio repository. `source/` contains the editable application, lockfile, tests and CLI; `index.html`, `assets/` and `example-dataset.json` alongside it are the committed static build for GitHub Pages. Run the commands above from `source/`. The `docs/` directory is mirrored beside the public build for direct review.

To refresh the public build, run `npm run build` in `source/`, replace the sibling `assets/` with `dist/assets/`, and copy `dist/index.html` and `dist/example-dataset.json` to the parent project directory. The CI workflow rebuilds and compares these files so stale public artifacts fail validation.
