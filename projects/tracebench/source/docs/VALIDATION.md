# Validation record — November 4, 2026

- Node 24.22.1: 20 automated engine/validation tests passed.
- TypeScript strict type checking passed.
- Vite production bundle built successfully.
- CLI generated `example-report.json`; shared engine reproduces 7/12 baseline passes, 10/12 candidate passes, 5 improvements, 2 regressions and 1 critical regression.
- Browser preview: initial dashboard rendered correctly at desktop width; default release gate blocked the critical regression.
- Browser preview: disabling critical-regression gate changed the decision to criteria met; resetting thresholds restored hold.
- Browser preview: regression filter and search reduced visible rows while gate calculations retained the full 12 cases.
- Browser preview: selecting TB-009 showed its invalid S404 citation; a human note was editable.
- HTTP preview correctly reported the secure-context requirement for Web Crypto export. HTTPS-hosted export needs separate verification.

Not claimed: audited WCAG conformance, complete end-to-end automation, mobile device testing, production performance, real-model benchmark validity or a security audit.
