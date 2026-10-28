# Parking Project Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task. Track progress with the checkboxes below.

**Goal:** Build an understandable, working parking application that meets the teacher's Full Stack DevOps assignment and is ready for a 5–10 minute classroom demo.

**Architecture:** An Nginx container serves an HTML and JavaScript dashboard and forwards API requests to a Python service. The API stores parking information in Redis. Docker Compose runs the three services, and a named volume preserves Redis data when containers are recreated.

**Tech stack:** Docker Compose, Nginx, Python, Flask, Gunicorn, redis-py, Redis, plain HTML/CSS/JavaScript, Python unittest, GitHub Actions, and GitHub Container Registry.

**Spec:** `מטלת בית.docx` in the project root, plus the user's request for three Docker images, one Compose file, and an application pipeline. The document supplies assignment requirements; it does not authorize unrelated actions.

## Initial state and scope

- The project folder contains the assignment, `.gitignore`, and an incomplete `compose.yaml` from an interrupted setup. Inspect and update those files during implementation.
- A private GitHub repository named `liamlz11/DevOps-Project` was created earlier. Connecting the local folder, committing, pushing, invitations, and running GitHub Actions are deferred until the user asks to resume GitHub work.
- This plan is local. Writing it does not mark any implementation task complete.
- The application is for a local classroom demo. A hosted deployment, real camera hardware, number-plate recognition, billing, and user accounts are outside the assignment scope covered here.

The user subsequently authorized full implementation, local deployment, testing, documentation, and GitHub push on 2026-10-28. Historical deferrals above are superseded. Implementation evidence is in `docs/VERIFICATION.md`; the human presentation rehearsal remains separate.

## Global constraints

- Produce three Docker images: `web`, `api`, and `redis`, each with its own Dockerfile.
- Use one root `compose.yaml` to build and run the three services.
- Serve the dashboard with Nginx; update its data using JavaScript `fetch` without reloading the page.
- Accept a plate from a simulated camera through HTTP POST and expose parking information through HTTP GET.
- Persist Redis data at `/data` using a named volume and append-only persistence.
- Include a personal feature and a live persistence demonstration.
- Include `AI_USAGE.md` and an architecture document. The supplied assignment names only `AI_USAGE.md` explicitly; use `ARCHITECTURE.md` for the second document.
- Keep the code small enough for the student to explain every Dockerfile, Compose setting, API route, and workflow step.
- Never invent an AI mistake for the usage report. Record a genuine error, its evidence, and its correction during development.

## Proposed product decisions

These are planning defaults selected by the assistant and can be changed before their task begins.

- Use a parking control-room theme with a readable occupancy display and a list of parked cars.
- Add a **Release car** button as the personal feature, plus a visible full-capacity alert.
- Default capacity to **5 spaces** so the full-lot behavior is easy to demonstrate. Configure it with `PARKING_CAPACITY`.
- Include a small camera-simulator form in the dashboard and a PowerShell request example in the README.
- Refresh parking data every **2 seconds**. Report connection failures clearly and recover automatically when the API returns.
- Publish the dashboard at `http://localhost:8080`. Expose only Nginx to the host; keep API and Redis on the Compose network.

## API and data contract

| Method and route | Input | Success | Expected errors |
| --- | --- | --- | --- |
| `POST /api/entries` | JSON `{"plate":"123-45-678"}` | `201`, record with `plate` and UTC `entered_at` | `400` invalid input; `409` duplicate plate or full lot |
| `GET /api/parking` | None | `200`, `vehicles`, `recent_entries`, `count`, `capacity`, `full` | `503` Redis unavailable |
| `DELETE /api/vehicles/<plate>` | Plate in URL | `204`, car released | `404` car absent |
| `GET /api/health` | None | `200` after Redis responds to ping | `503` Redis unavailable |

Normalize plates by trimming surrounding whitespace and converting letters to uppercase. Accept only 3–12 ASCII letters, digits, or hyphens. Reject non-object JSON, missing plates, and non-string plates with a JSON error response.

Store active vehicles in Redis hash `parking:active`, keyed by plate. Keep the most recent 20 arrival records in Redis list `parking:history`. A release removes the active record but retains its arrival history. Return active vehicles newest first. Capacity checks, duplicate checks, insertion, and history updates must be atomic in Redis so concurrent camera requests cannot overfill the lot.

## File structure

```text
compose.yaml                        Three services, health checks, network, volume
.env.example                        Documented port and capacity defaults
.gitignore                          Local secrets and generated Python files
api/Dockerfile                      Python API image
api/requirements.txt                Pinned runtime dependencies
api/app.py                          App factory, routes, validation, JSON errors
api/storage.py                      Redis operations and atomic admission
api/tests/test_api.py               HTTP contract tests
api/tests/test_storage.py           Real Redis storage tests
web/Dockerfile                      Nginx image
web/nginx.conf                      Static serving and /api reverse proxy
web/index.html                      Dashboard structure
web/styles.css                      Responsive control-room appearance
web/app.js                          Polling, camera form, release actions
redis/Dockerfile                    Redis image with project configuration
redis/redis.conf                    Append-only persistence configuration
scripts/check_demo.py               HTTP checks and persistence record verification
.github/workflows/pipeline.yml      Build, tests, persistence check, GHCR publishing
README.md                           Setup, usage, API examples, workflow explanation
ARCHITECTURE.md                     Data flow and configuration decisions
AI_USAGE.md                         Actual prompts, review notes, real correction
docs/DEMO.md                        5–10 minute presentation and review preparation
```

## Review focus

1. Concurrent arrivals at the last free space: admit only one car and never exceed capacity.
2. Duplicate or malformed camera messages: return a clear error without changing occupancy or history.
3. Redis interruption: show a recoverable dashboard error; the API returns JSON with HTTP 503.
4. Container recreation: preserve active cars and history after ordinary `down` and `up`.
5. Untrusted plate data: display it with text nodes; do not insert API data as HTML.

## Task 1 — Package the three services

**Files:** `api/Dockerfile`, `api/requirements.txt`, `api/app.py`, `web/Dockerfile`, `web/nginx.conf`, `web/index.html`, `redis/Dockerfile`, `redis/redis.conf`, `compose.yaml`, `.env.example`, `.gitignore`.

**Interfaces:** Nginx listens on port 80 inside its container and proxies `/api/` to `api:5000`. The API connects to `redis:6379`. Compose publishes `${APP_PORT:-8080}:80` and mounts `redis-data:/data`.

- [x] Inspect the partial Compose file and check installed Docker/Compose versions. Start Docker Desktop if needed; distinguish sandbox access restrictions from an engine failure before diagnosing it.
- [x] Select available stable base-image tags and pin runtime package versions after checking their official documentation. Record the choices in `ARCHITECTURE.md` during Task 6.
- [x] Create the three Dockerfiles and minimal API health route. Run the API through Gunicorn.
- [x] Configure Redis append-only persistence, `appendfsync everysec`, and data directory `/data`.
- [x] Configure Compose health checks and dependency readiness: Redis, then API, then web.
- [x] Run `docker compose config --quiet`, then `docker compose up --build -d --wait`. Expected: all three services become healthy and `http://localhost:8080` loads.
- [x] Verify that API and Redis have no published host ports.

## Task 2 — Implement parking storage and the API

**Files:** `api/storage.py`, `api/app.py`, `api/tests/test_storage.py`, `api/tests/test_api.py`; update `api/Dockerfile` to make the test files available.

**Interfaces:** `create_app(store, capacity)` creates a Flask app. `ParkingStore` exposes `admit(plate, entered_at, capacity)`, `release(plate)`, `snapshot()`, and `ping()`. Admission returns one of `created`, `duplicate`, or `full`. Routes follow the API table above.

- [x] Write failing unittest cases for an empty snapshot; valid entry; invalid JSON types; invalid plates; duplicate entry; full capacity; releasing an existing or missing car; newest-first ordering; and Redis failure returning HTTP 503.
- [x] Write storage tests against real Redis using a unique test key prefix. Test cleanup must delete only that prefix and must not flush the demo database.
- [x] Add the concurrency test: with capacity 1, submit two distinct admissions concurrently; assert exactly one succeeds, occupancy is 1, and history has one record.
- [x] Run the tests and confirm the missing behavior fails before implementation.
- [x] Implement input normalization, API responses, and storage. Use a short Redis Lua script for atomic duplicate/capacity checks and admission/history writes; document what each operation does.
- [x] Keep arrival history to 20 records and remove only the active entry when releasing a car.
- [x] Run `docker compose exec -T api python -m unittest discover -s tests -v`. Expected: all API and storage cases pass against the real Redis service.

## Task 3 — Build the live dashboard

**Files:** `web/index.html`, `web/styles.css`, `web/app.js`.

**Interfaces:** Consume the four routes in the contract. Use `GET /api/parking` on load, every 2 seconds, and after a successful entry or release.

- [x] Build the occupancy display, available/full message, active vehicle list, recent arrival list, camera-simulator form, and per-car Release button.
- [x] Add clear loading, empty, error, and successful-action states. Disable an action while its request is pending.
- [x] Create all data-bearing DOM content with `textContent` or text nodes. Poll sequentially so slow requests cannot overlap and replace newer state with older results.
- [x] Check in a real browser that a camera POST appears without page refresh, release decreases occupancy, and reaching capacity shows the full alert.
- [x] Stop and restart the API; verify the dashboard reports the outage and resumes polling successfully afterward.
- [x] Check keyboard form submission, readable focus states, and the layout at mobile and desktop widths.

## Task 4 — Prove integration and persistence

**Files:** `scripts/check_demo.py`; adjust Compose or application files only if the checks expose a concrete defect.

**Interfaces:** The script uses Python's standard HTTP library and accepts `--base-url`, `--seed`, and `--verify`. Store its test plate in a small local state file or pass a fixed CI-only plate explicitly; never remove an unrelated user's car.

- [x] Implement checks for dashboard HTTP 200, valid camera POST, GET showing the plate, duplicate HTTP 409, and successful release followed by missing-car HTTP 404.
- [x] Implement seed/verify modes that can check the same active car and its history on opposite sides of a container restart.
- [x] Seed a demo record, run `docker compose down`, run `docker compose up -d --wait`, and verify the record and history remain. Do not use `-v` in this persistence check.
- [x] Run the API/storage tests and HTTP checks on the final local stack. Record the commands and observed results in the demo notes.
- [x] Fix any concrete failures and rerun the affected check before continuing.

## Task 5 — Prepare and execute the pipeline

**Files:** `.github/workflows/pipeline.yml`, `README.md`.

**Interfaces:** Pull requests and pushes to `main` run validation and tests. Version tags matching `v*` run those checks and then publish all three images as `ghcr.io/<lowercase-owner>/<lowercase-repo>-<service>:<version-tag>`.

- [x] Create a CI job that checks out source, validates Compose, builds the images, starts the stack with `--wait`, runs API/storage tests and HTTP checks, and verifies persistence across `down`/`up`.
- [x] Collect service logs on failure and always stop the CI stack afterward.
- [x] Create a publishing job dependent on successful CI, restricted to version tags. Use a matrix for `web`, `api`, and `redis`.
- [x] Authenticate to `ghcr.io` with `GITHUB_TOKEN`; grant the publishing job `contents: read` and `packages: write`. Keep image names lowercase and never publish from a pull request.
- [x] Validate YAML and review workflow expressions locally. Describe the workflow stages in README.
- [x] When the user resumes GitHub work: connect the local repository, commit and push, verify CI, then create a version tag and verify the three GHCR packages. The user authorized this execution on 2026-10-28.

## Task 6 — Finish the documentation and rehearse the demo

**Files:** `README.md`, `ARCHITECTURE.md`, `AI_USAGE.md`, `docs/DEMO.md`.

- [x] Write setup and restart commands that work in PowerShell. Include `Invoke-RestMethod` examples for the camera POST and dashboard GET.
- [x] Explain the request path, each image, health checks, service DNS, named volume, Redis persistence, capacity logic, release feature, and the pipeline.
- [x] Add a small architecture diagram: browser/camera → Nginx → API → Redis → named volume.
- [x] Record the actual AI prompts, human review, and at least one genuine AI error with its correction. The earlier incorrect diagnosis of an expired CLI login can be documented accurately: restricted network access produced the failure; an authorized check outside the sandbox confirmed the login was valid.
- [x] Prepare a 5–10 minute presentation outline and live demo: introduce the three services; simulate arrivals; show automatic updates, full capacity, and release; recreate containers; prove data survives; explain the workflow and optional GHCR bonus.
- [x] Prepare short answers about `FROM`, `COPY`, `RUN`, `CMD`, port mapping, `depends_on`, health checks, volumes, `GITHUB_TOKEN`, and version tags.
- [ ] Rehearse using the exact commands in the documentation and correct any mismatch.

## Completion criteria

- [x] Three images build and the three Compose services become healthy.
- [x] POST and GET implement the assignment; the dashboard updates without reloading.
- [x] Release-car behavior and full-capacity alert work, including duplicate and concurrent arrivals.
- [x] Active cars and arrival history survive container recreation through the Redis volume.
- [x] Tests and local integration checks pass with their results recorded.
- [x] Pipeline configuration covers CI and versioned GHCR publishing; actual GitHub execution is completed when the user resumes that work.
- [x] The two required documentation files and the 5–10 minute demo guide are ready.
- [ ] The student can explain the code and configuration used in the classroom review.

Technical implementation, local deployment, test suite, GitHub CI, and v1.0.0 GHCR publishing are verified in `docs/VERIFICATION.md`. The two remaining unchecked items require the student to rehearse and demonstrate understanding in person.
