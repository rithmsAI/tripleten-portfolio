# AuthLog | C++20 authentication-event analyzer

Independent, AI-assisted defensive engineering project by Kaya Robinson. Reads a deliberately restricted CSV stream, detects five failures per principal in a rolling 60-second window, and emits deterministic JSON. No real logs or customer data.

```sh
make test
make sanitize
./authlog < example.csv
```

Requires GCC/Clang with C++20, Make and Python 3 for the black-box tests. Input header must be exactly `timestamp,principal,outcome`; LF-separated rows, monotonically nondecreasing unsigned 64-bit timestamps, principal `[A-Za-z0-9_.-]{1,64}`, outcome `success` or `failure`. Quoted CSV, CRLF, blank rows and extra fields are rejected. No automatic normalization of ambiguous input.

## Decisions

- Per-account deques expire failures at age >=60 seconds: window `(t-60,t]`. A success does not erase failures. Emit once while at least five failures remain; re-arm when a later event for that principal observes fewer than five before insertion.
- Bound lines before appending (256 bytes), total input (8 MiB), rows (100,000) and accounts (4,096). Output only after the whole input validates, so rejection never leaks partial JSON.
- Validate timestamps with `std::from_chars`, use subtraction after checking ordering, and restrict identifiers so JSON cannot be injected. RAII containers own memory.
- Ten black-box tests cover thresholds, expiry boundaries, suppression, re-arming, account isolation, success events, malformed rows, uint64 overflow and resource caps. Sanitizer execution is recorded separately in VALIDATION.md.

## Limits

This is an offline rule, not a production SIEM. It does not parse vendor log formats, correlate devices, infer intent, persist checkpoints or measure real detection accuracy. An attacker who spreads failures across accounts or beyond the window can evade this rule. Each retained failure uses memory; fixed caps intentionally trade capacity for a bounded exercise. No throughput claims are made.

Complexity: O(n log a) account lookup plus amortized O(n) expiry for n events and a accounts. Memory O(n+a), bounded by input caps. Extend with vendor adapters, event-time watermark handling and measured benchmarks before considering live ingestion.
