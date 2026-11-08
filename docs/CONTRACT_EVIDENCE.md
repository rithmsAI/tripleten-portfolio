# Rithms & Consulting LLC — technical portfolio evidence

Prepared November 8, 2026 for prospective teaming partners and technical reviewers.

The examples below are independent portfolio projects by Kaya Robinson / rithmsAI, developed with AI assistance. They demonstrate implemented software behavior and documented experiments. They are not paid client references, government past performance, production deployments, or evidence of compliance certification.

## Proposed contribution to an analytics-platform team

A scoped package of Python API components, data-validation routines, dashboard components, automated tests, and technical documentation. Final deliverables, acceptance tests, staffing, schedule, and price must be agreed with the lead contractor against the actual statement of work.

| Buyer need | Inspectable evidence | What this does not establish |
|---|---|---|
| Validate data at an API boundary | Transaction Anomaly Lab's strict schema, bounds and rejected-input tests | Traffic-stop schema coverage or a production ingestion pipeline |
| Avoid duplicate work on retries | Original stored decisions, conflict rejection, concurrent retry tests | Distributed exactly-once processing or high throughput |
| Preserve workflow and audit integrity | Incident Workbench's atomic state/audit writes, rollback injection, stale-version checks across two service instances | Tamper-proof audit storage or an authenticated multi-tenant service |
| Make results inspectable | TraceBench's comparison dashboard, filters, source context, notes and JSON reports | Statistically validated traffic-stop analysis or real-model effectiveness |
| Support reproducible review | Versioned engine, dataset fingerprint, shared CLI/UI rules and automated checks | Signed provenance, external measurement verification or a security certification |
| Explain methods and limitations | Per-project walkthroughs, explicit synthetic-data labels, test records and architecture notes | A substitute for domain expertise or customer references |

## 1. Transaction Anomaly Lab — API and persistence reliability

[Repository](https://github.com/rithmsAI/transaction-anomaly-lab) · [Interactive case study](https://rithmsai.github.io/tripleten-portfolio/projects/transactions/) · [Service contract](https://github.com/rithmsAI/transaction-anomaly-lab/blob/main/docs/SERVICE.md)

**Implemented:** authenticated local FastAPI service, typed inputs, frozen calibration thresholds, parameterized SQLite storage, repeat-request deduplication, conflict responses and storage failure handling. The accompanying ML experiment compares a fixed rules baseline with Isolation Forest on synthetic data.

**Reviewer demonstration:**

1. Start the service locally using its service guide and a generated local key.
2. Submit one fictional event; record its model version and decision.
3. Submit the identical event again; confirm the same decision and one unique stored event.
4. Change the features while keeping the ID; confirm HTTP 409.
5. Run the API tests to inspect concurrent conflicts, a stored retry while inference is forced to fail, and an aborted SQL insert followed by recovery.

**Relevant deliverable:** a validated processing endpoint with documented retry and failure semantics plus executable acceptance tests.

**Boundary:** single-node, shared-key demonstration; scores are not fraud probabilities. New scoring is serialized inside a database write transaction. Production identity, tenancy, traffic limits, monitoring and scale design remain separate work.

## 2. Incident Response Workbench — workflow and investigation records

[Live demo](https://rithmsai.github.io/tripleten-portfolio/projects/incidents/) · [Source and local API](../projects/incidents/) · [API tests](../projects/incidents/test_workbench.py)

**Implemented:** staged investigation, required rationale, verification before resolution, plain-text export, durable local API records, and atomic incident/audit updates. The public browser demonstration and the local API are separate implementations.

**Reviewer demonstration:**

1. Open INC-1042 and assign a fictional investigator.
2. Record a hypothesis and move through investigating and mitigated.
3. Attempt resolution before completing the checklist; observe the rejection.
4. Complete verification and export the investigation record.
5. Reset the demonstration and confirm the original scenarios return.
6. Inspect API tests that force an audit-write failure and race two independent service instances against the same incident version.

**Relevant deliverable:** an analyst workflow with explicit state transitions, review records, failure handling and tested concurrency rules.

**Boundary:** verification is self-attested against fictional logs. No production incident response, authentication, agency isolation or tamper-proof audit is claimed. Browser persistence is editable localStorage; the API must remain local until appropriate controls are implemented.

## 3. TraceBench — dashboard and evaluation evidence

[Live demo](https://rithmsai.github.io/tripleten-portfolio/projects/tracebench/) · [Source](../projects/tracebench/source/) · [Architecture](../projects/tracebench/docs/ARCHITECTURE.md)

**Implemented:** React/TypeScript comparison dashboard, validated JSON imports, paired regressions, configurable release criteria, human notes and exportable reports with dataset fingerprints. Engine 1.1.0 rejects malformed release policies, aggregate cost overflow and invalid review notes.

**Reviewer demonstration:**

1. Inspect the authored example: the candidate's average improves while a critical regression remains.
2. Filter to regressions and inspect the evidence behind the decision.
3. Change the critical-regression setting and reset it; confirm the decision follows the explicit policy.
4. Import the example JSON and add a review note.
5. Export a report and reproduce its checks with the CLI.

**Relevant deliverable:** dashboard components and validation/reporting logic that make a decision inspectable and reproducible.

**Boundary:** no model is called. Phrase inclusion and citation-ID checks cannot establish factual correctness or causal/statistical validity. Supplied latency and cost are not measured by the app. Notes remain in tab memory until exported; this is not a shared case-management system.

## Verification and delivery gaps

The November 8 local runs passed 30 Transaction Anomaly Lab tests, 17 Incident Workbench API tests, 22 Workbench JavaScript assertions and 26 TraceBench engine tests. TraceBench type checking, production build and regenerated CLI report also passed. Project-specific validation records distinguish local tests from CI and browser results; inspect the current GitHub Actions run before relying on a green build claim.

The portfolio browser workflow exercises both public-app builds using local fictional fixtures. It verifies workflow gating and reset, import preservation, download content and report hashing. These checks do not constitute a security audit, WCAG conformance assessment or production load test.

For an agency analytics deployment, the delivery team still needs qualified statistical/domain review, production identity and agency isolation, accessible-design validation, realistic data-volume and concurrency testing, backups and recovery, hosting operations, user training, and support commitments. Customer-reference and procurement requirements must be satisfied by the actual proposing team; these portfolio demonstrations do not replace them.

No agency endorsement, award, teaming agreement or guaranteed contract eligibility is implied.
