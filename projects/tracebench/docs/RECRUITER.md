# Recruiter / engineering walkthrough

## What to inspect

| Evidence | What it demonstrates |
|---|---|
| `source/src/engine.ts` | Typed domain modeling, independent runtime validation, deterministic checks, paired comparisons and configurable decision rules |
| `source/src/main.tsx` | React state, derived results, reusable output cards, import/export workflow, accessible form controls |
| `source/tests/engine.test.ts` | Boundary conditions, malformed inputs, duplicate identifiers, safety regression gates and documented evaluator blind spots |
| `source/scripts/evaluate.ts` | Shared CLI evaluator and a reproducible input fingerprint |
| `docs/example-report.json` | Inspectable evaluation artifacts instead of unsupported benchmark claims |

## Why this project exists

Many demo dashboards show only an aggregate success rate. TraceBench makes a different engineering decision: preserve the paired case and its evidence so an apparently better candidate cannot hide a critical regression. In the authored fixture, 5 improvements and 2 regressions produce a higher average. One critical regression still blocks release.

## Interview discussion prompts

1. Why use deterministic checks before introducing an LLM judge? They are inexpensive, reproducible and inspectable, but incomplete.
2. Why do citation-ID checks not prove grounding? A citation can exist yet fail to support the claim. The inspector exposes both answer and source for review.
3. Why do release gates use all cases rather than the visible filter? A view filter must not silently change a deployment decision.
4. What does a hash prove? Equality of serialized inputs, not authenticity or model provenance.
5. How would this grow? Add separately versioned human labels, agreement measurements, a provider runner with server-held keys, measured telemetry, immutable run storage and authorization. None of those are claimed implemented.

## Résumé wording supported by this implementation

**TraceBench — AI Evaluation Workbench | React, TypeScript, Node.js**
- Built a responsive evaluation interface comparing paired AI outputs, exposing case-level regressions and applying configurable quality, latency, cost and critical-regression gates.
- Implemented validated JSON imports, citation-reference and lexical checks, human review notes, and reproducible reports with dataset SHA-256 fingerprints; shared the evaluation engine between the UI and CLI.
- Verified core evaluation and validation behavior with 20 automated tests; documented synthetic data, evaluator blind spots and the distinction between supplied and measured metrics.

Use under **Independent Projects**, not employment. This was built with AI assistance. Kaya should walk through the code, reproduce the tests and explain the limitations before using it in technical interviews. Do not claim production deployment, real-model accuracy improvements, a trained model, or measured inference savings.
