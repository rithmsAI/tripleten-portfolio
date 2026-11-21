# Access Control Lab | Docker and defensive application security

Independent, AI-assisted project by Kaya Robinson. A small Python standard-library HTTP service with role-based authorization, constrained event input, SQLite audit transactions and a restricted Docker configuration. The exercises relate to Security+ topics; **they do not award or imply a Security+ certification**.

## Run locally

```sh
python server.py --generate-tokens
python -m unittest -v
python server.py
```

Default bind is 127.0.0.1:8080. Keep `tokens.local.json` private; it is gitignored. It contains independent generated analyst/admin tokens, not published example credentials. Use your chosen token as `Authorization: Bearer ...` from an HTTP client.

| Request | Anonymous | Analyst | Admin |
| --- | --- | --- | --- |
| GET /health | 200 | 200 | 200 |
| GET /events | 401 | 200 | 200 |
| POST /events | 401 | 403 | 201 with valid body |

POST requires `Content-Type: application/json`, one Content-Length <=1,024 bytes and exactly `{"category":"auth","severity":3}`. Category is lowercase letters/digits/underscore/hyphen, starts with a letter, at most 32 characters. Severity is an integer 1..5; booleans are rejected. GET returns at most the latest 100 events. Unknown routes return 404; unsupported methods use the standard handler's 501 response.

## Run with Docker Compose

```sh
python server.py --generate-tokens  # once only; preserves any existing token file
docker compose up --build -d
docker compose ps
docker compose down
```

Compose binds only localhost, uses numeric non-root UID 10001, read-only root, dropped Linux capabilities, no-new-privileges, process/memory/CPU limits and tmpfs state. The secret is mounted rather than baked into the image. `.dockerignore` allowlists only application/test files. **Compose state is ephemeral** and disappears when the container is removed; native SQLite state survives restarts. A full tmpfs yields failure, not successful unaudited writes. The local file secret is not encrypted secret management. Image tags are not digest-pinned; CI builds the image, but vulnerability scanning/signing are future work.

## Threat model and exercises

Assets: lab tokens, event integrity, audit integrity, host isolation. Boundaries: HTTP input, authorization decision, database transaction, container/host. Authentication hashes provided tokens and compares digests using `hmac.compare_digest`; roles come from server configuration, never request fields. Audit records retain fixed actions/roles/status, not tokens or submitted raw strings. Event creation and success audit share one transaction. Storage failures return 503 and roll back.

Sixteen HTTP/configuration tests cover unauthorized and forbidden actions, malformed schema, over-limit bodies, unsupported media types, response headers, persistence, audit content and forced audit failure rollback. CI additionally executes these tests inside the restricted image without an external network.

| Security learning area | Implemented evidence | Remaining production work |
| --- | --- | --- |
| Identity and least privilege | analyst/admin authorization matrix | OIDC, expiring credentials, rotation/revocation |
| Secure development | bounded bodies, strict fields, parameterized SQL | fuzzing and broader parser review |
| Monitoring and incident response | atomic event/audit writes, denied-operation logs | central tamper-resistant logs and retention |
| Systems hardening | non-root, read-only, capability/process/resource limits | digest pins, SBOM, image scans and runtime policy |

No TLS, rate limiting, robust production HTTP server, CSRF/browser UI, external identity provider, multi-tenant isolation or compliance certification. The standard-library server is for this local exercise; do not publish it to the internet. Compose bridge networking does not block egress. The isolated CI test uses `--network none` instead. No host scans or offensive actions are performed.

Reference: [Docker Compose service controls](https://docs.docker.com/reference/compose-file/services/).
