# Validation record — November 8, 2026

- Node 24.22.1: 26 automated engine/validation tests passed locally.
- Strict TypeScript checking and Vite production build passed.
- CLI regenerated the example report for engine 1.1.0; baseline 7/12 and candidate 10/12 passes, 2 regressions, 1 critical regression. Default decision remains hold.
- Added regression coverage for invalid gate types/ranges, missing critical-regression policy, numeric overflow in imported costs, and invalid review notes.
- Committed static build and CLI report are compared with regenerated outputs in `.github/workflows/tracebench.yml`.
- Browser regression procedure is `tests/browser_smoke.py` at the repository root; CI runs it through `.github/workflows/portfolio-browser.yml`. It checks file selection, failed-import state preservation, downloaded report contents and SHA-256, critical-gate controls, and prototype-like case IDs. Inspect the Actions run for its execution result.

The local Chromium launch was blocked by the execution environment's Unix-socket restriction; no new local browser pass is claimed. Browser checks are delegated to the repository's CI runner, not treated as passing until its workflow succeeds.

No audited WCAG conformance, real-device testing, production load benchmark, real-model evaluation or security audit is claimed. Synthetic and supplied measurements retain their documented limitations.
