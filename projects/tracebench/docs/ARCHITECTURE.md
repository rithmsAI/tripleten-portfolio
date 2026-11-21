# Architecture, threat model and design decisions

## Data flow

JSON fixture or user-selected file → runtime validation → typed Dataset → pure evaluation engine → summaries + paired results + release checks → React views / CLI JSON report.

Review notes are separate from automated results. Table filters do not alter the dataset passed to release gates. All evaluation is synchronous in memory, bounded to 1 MB and 200 cases. Browser exports use Web Crypto; CLI exports use Node crypto. Both hash UTF-8 bytes of the same JSON serialization.

## Decisions

- **React + TypeScript:** demonstrates a component-based interface without coupling domain rules to rendering. TypeScript protects trusted code; runtime validation protects the import boundary.
- **No backend in v1:** reviewers can inspect the application without accounts or API credentials. This is not shared collaboration or durable storage.
- **Deterministic checks first:** phrase inclusion, source-ID integrity and explicit abstention labels are repeatable. Human reviewers still inspect semantics. No learned evaluator or classifier is implied.
- **Nearest-rank p95:** `sorted[ceil(.95*n)-1]`. On 12 cases it equals the maximum. These supplied fixture numbers are not statistically reliable performance measurements.
- **Critical paired regressions:** gate checks specifically block baseline-pass/candidate-fail critical cases. Existing critical failures are reflected in pass rate but are not categorized as regressions; a real policy may require zero critical failures. This policy choice is deliberate and explicit.
- **Reports include inputs:** permits reproduction but also means exports include any imported text and review notes. Use fictional/public information only.
- **No averaging arbitrary check scores:** a case passes only when every check passes, making the decision rule simple to inspect.

## Threats and limits

| Risk | Implemented control | Remaining limitation |
|---|---|---|
| Untrusted JSON | Schema, length/count/type and uniqueness checks | Not a sandbox for hostile large-scale ingestion |
| Markup in output/notes | React text rendering; no `dangerouslySetInnerHTML` | No formal browser security audit |
| Spreadsheet formula execution | JSON-only export | Consumers must handle exported strings safely |
| Exfiltration / accidental key exposure | No provider calls or key field; no file upload to backend | Hosting and external font services see normal web requests |
| Invalid release policy | Finite bounded gate values and explicit boolean critical-regression policy | Valid thresholds can still be poorly chosen |
| Numeric overflow | Import rejects nonfinite aggregate costs | Supplied measurements remain unverified |
| Misleading aggregate quality | Paired regression views and critical gate | Synthetic labels can be wrong; checks miss semantic errors |
| False reproducibility claims | Full inputs and engine version in report | Hash is order-sensitive and not signed; no provenance attestation |
| Losing notes | Export includes annotations | Reload loses tab-memory state; no autosave |

## Evaluation validity

The fixture is a scenario demonstration, not a representative dataset. Categories have only 2–5 cases. There is no confidence interval, train/test split, measured model run, semantic correctness score, or evidence of production effectiveness. Phrase checks can pass negated or copied phrases. A source ID match can be used with an unrelated claim. An abstention boolean can contradict the prose. The test suite makes these limitations visible.

## Verification

Executed locally on 2026-11-08: 26 Node test cases passed, TypeScript strict checking passed, Vite production build passed, and CLI example report generated. Browser QA and hosted status are recorded separately in `VALIDATION.md` when completed.

Documentation references: [React](https://react.dev/learn), [Vite relative builds](https://vite.dev/guide/build#relative-base), [Node test runner](https://nodejs.org/api/test.html), [Web Crypto digest](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest).
