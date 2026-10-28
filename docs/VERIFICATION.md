# Verification record

Local checks performed on 2026-10-28, Asia/Jerusalem. These are observed checks, not a substitute for the student's own classroom rehearsal.

| Requirement | Evidence |
| --- | --- |
| Three Docker images | Successful `docker compose up --build -d --wait`; `gatehouse-web`, `gatehouse-api`, `gatehouse-redis` built |
| Running local app | Three healthy services in `docker compose ps`; Nginx published on `127.0.0.1:8080`; API and Redis have no host ports |
| API and real Redis | `docker compose exec -T api python -m unittest discover -s tests -v`; eleven cases including concurrent final-space admission |
| HTTP interface | `python scripts/check_demo.py` passed dashboard, health, POST, GET, invalid input, duplicate, release, and missing-car checks |
| Persistence | Seeded `P-86F2BF89`, recreated all containers with ordinary down/up, and verified the identical active record and arrival timestamp in history; released only the seeded car afterward |
| Live UI | Registered five cars without reloading; sixth admission showed full-lot rejection; release reopened the gate and preserved history |
| Keyboard input | Enter submitted `KEY-123`; release succeeded afterward |
| API outage | Stopped API; browser showed Reconnecting and stale-data message; restarted API; browser returned to Live automatically |
| Redis outage | Stopped Redis; after retry fix, HTTP request returned JSON 503; restored all services |
| Responsive layout | Browser screenshots inspected at 390, 900, and 1440 pixel viewport widths; no horizontal page overflow in mobile/tablet DOM measurements |
| Browser validation | HTML pattern compiled under modern RegExp `v` semantics, accepted `123-45-678`, and rejected markup |
| Source check | `node --check web/app.js` passed |

## Review corrections

An independent read-only source review identified excessive Redis retries and the modern HTML pattern escape. The retry-policy regression failed before the explicit no-retry policy and passed after it. The real outage check first observed HTML 504 and later JSON 503, verifying the user-visible correction. Details are in `AI_USAGE.md`.

## GitHub release evidence

The initial source push passed [GitHub Actions run 40708681732](https://github.com/liamlz11/DevOps-Project/actions/runs/40708681732). That run built the images, ran the API/storage and HTTP checks, and verified persistence on an Ubuntu hosted runner.

[Release run 40708984794](https://github.com/liamlz11/DevOps-Project/actions/runs/40708984794) completed successfully for tag `v1.0.0` at source commit `64657573cd332c8f714a3b0dc91eee77bdba538e`. The test job passed, all three matrix publishing jobs passed, and each authenticated `docker buildx imagetools inspect` step read back the published manifest.

| Published version | Verified manifest digest |
| --- | --- |
| `ghcr.io/liamlz11/devops-project-web:v1.0.0` | `sha256:ad370f48c73b82ea2194b427fe3739cd78a4fcdacbc2f2e4eee0837ab34db818` |
| `ghcr.io/liamlz11/devops-project-api:v1.0.0` | `sha256:d2ddf83bf6a449b3843818021c0629066a04adc9c381b1f2f3bae6757cde5b8f` |
| `ghcr.io/liamlz11/devops-project-redis:v1.0.0` | `sha256:d19ffc02a9db39f415b1baaa6d1215c5e5bc1290784cc767954770d9d06d651f` |

The private repository contains the source, original assignment, plan, tests, workflow, and documentation. No virtual environment, local test state, credentials, or Docker volume contents are committed. Local deployment remains running independently of GitHub, with two intentionally entered demo cars (`123-45-678` and `876-54-321`) and three free spaces.

## Human presentation step

The app, documentation, and automated checks can be delivered by the assistant. The student must still read the code, rehearse the presentation, and answer the teacher's review questions personally. `docs/DEMO.md` provides the exact sequence and explanations.
