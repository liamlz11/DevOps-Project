# Gatehouse Parking Control

A working three-container parking application for the Full Stack DevOps assignment. A simulated IoT camera sends license plates to a Python API. The guard's Nginx dashboard fetches live parking data every two seconds. Redis stores active cars and arrival history on a persistent Docker volume.

The personal features are **Release car** and **a full-capacity alert**. The default five-space lot makes both easy to show in class.

## Start on Windows

Prerequisites: Docker Desktop running with Linux containers and Docker Compose v2 or newer. Python on Windows is optional; it is used only for the host-side verification script. Application dependencies run inside Docker.

Open PowerShell in this project folder:

```powershell
docker compose config --quiet
docker compose up --build -d --wait
docker compose ps
Start-Process 'http://localhost:8080'
```

Open **http://localhost:8080**. Register a plate in the camera simulator, observe the parked count and arrival log, and click Release to free a space. Add five cars to see the full-lot state; a sixth arrival is rejected with HTTP 409.

The dashboard uses Google Fonts when internet access is available and a local system-font fallback when offline. Application requests stay on localhost. The UI initially has honest empty states; it does not fabricate parking records.

## Configuration

Copy `.env.example` to `.env` only if you want to change the defaults:

```powershell
Copy-Item .env.example .env
```

| Variable | Default | Meaning |
| --- | --- | --- |
| `APP_PORT` | `8080` | Dashboard port on the local machine |
| `PARKING_CAPACITY` | `5` | Positive integer maximum number of active cars |

After editing `.env`, run `docker compose up -d --wait`. API and Redis have no host ports. The dashboard is bound to `127.0.0.1` for a local classroom deployment.

## Services and project files

| Service | Image source | Responsibility |
| --- | --- | --- |
| `web` | `web/Dockerfile`, Nginx 1.28 Alpine | HTML/CSS/JS and `/api/` reverse proxy |
| `api` | `api/Dockerfile`, Python 3.12 slim | Flask routes, validation, Gunicorn workers |
| `redis` | `redis/Dockerfile`, Redis 7.4 Alpine | Atomic admission, active cars, arrival log, persistence |

`compose.yaml` builds all three images, defines health checks, starts services in dependency order, and mounts `redis-data` at `/data`. `api/storage.py` contains Redis logic. `api/tests/` contains API and real Redis tests. `scripts/check_demo.py` checks the deployed HTTP interface and persistence. Details are in [ARCHITECTURE.md](ARCHITECTURE.md).

## API examples in PowerShell

```powershell
# The camera reports a plate. Success: HTTP 201.
Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/api/entries' `
  -ContentType 'application/json' -Body '{"plate":"123-45-678"}'

# The dashboard reads active cars, arrival history, count, capacity, and full flag.
Invoke-RestMethod 'http://localhost:8080/api/parking' | ConvertTo-Json -Depth 5

# The guard releases a parked car. Success: HTTP 204, no response body.
Invoke-RestMethod -Method Delete -Uri 'http://localhost:8080/api/vehicles/123-45-678'

# Checks both API and Redis readiness.
Invoke-RestMethod 'http://localhost:8080/api/health'
```

Plates are trimmed and uppercased; they must contain 3–12 ASCII letters, digits, or hyphens. Invalid JSON/input returns HTTP 400. Duplicate cars and a full lot return 409 with `code` equal to `duplicate` or `full`. Releasing an absent car returns 404. Redis failures return a JSON error with 503. See the full contract in [ARCHITECTURE.md](ARCHITECTURE.md).

## Persistence demo

After adding a car, run:

```powershell
docker compose down
docker compose up -d --wait
```

The car and its history remain. The volume is named `gatehouse_redis-data`. Ordinary `down` does not remove it. **`docker compose down -v` deletes the project's persisted parking data** and is not part of the classroom persistence demo. Append-only writes are synced every second; an abrupt host or power failure can lose roughly the latest second of writes. A volume is persistence, not a backup.

## Run the tests

```powershell
docker compose exec -T api python -m unittest discover -s tests -v
python scripts/check_demo.py

# Automated persistence check; run these consecutively.
python scripts/check_demo.py --seed
docker compose down
docker compose up -d --wait
python scripts/check_demo.py --verify
python scripts/check_demo.py --cleanup
```

The eleven unittest cases cover normalization, malformed input, conflicts, release, Redis failure, a bounded retry policy, atomic concurrent admission, history retention, and ordering. Storage tests use unique Redis prefixes and delete only their own keys. The HTTP smoke script creates and releases its own temporary car; it requires at least one free space. `--seed` writes a local `.demo-state.json`, `--verify` compares the full record after recreation, and `--cleanup` releases that same car and removes the state file. History is retained. Run the persistence sequence without other arrivals that could evict its record from the latest 20 history entries.

## GitHub Actions and the GHCR bonus

The private repository is [liamlz11/DevOps-Project](https://github.com/liamlz11/DevOps-Project). The workflow is `.github/workflows/pipeline.yml`.

1. Pushes to `main`, pull requests, and manual runs validate Compose, build three images, start the stack, run all tests, and prove data survives container recreation.
2. Failed runs print service logs. Cleanup runs whether the tests pass or fail.
3. A version tag such as `v1.0.0` runs the checks first, then builds and publishes all three images to GHCR. A normal branch push does not publish.
4. Publishing uses the automatic `GITHUB_TOKEN` with `packages: write`; no personal access token or repository secret is needed.

Versioned image names:

```text
ghcr.io/liamlz11/devops-project-web:v1.0.0
ghcr.io/liamlz11/devops-project-api:v1.0.0
ghcr.io/liamlz11/devops-project-redis:v1.0.0
```

To publish a later version after committing and testing:

```powershell
git tag v1.0.1
git push origin v1.0.1
```

New GHCR packages default to private. Reading a private package outside Actions requires GitHub package access. Local Compose builds from source and does not require GHCR login.

## Operations and troubleshooting

```powershell
docker compose ps                       # health and published ports
docker compose logs --tail 50            # recent logs across services
docker compose logs -f api               # follow API requests
docker compose restart api              # restart one service
docker compose down                     # stop; retain volume
docker compose up --build -d --wait      # rebuild and deploy source changes
```

- If Docker reports a missing pipe or cannot reach the engine, start Docker Desktop and wait until the engine is running. If Codex's restricted shell reports permission/network errors, verify in normal PowerShell before treating the login or engine as broken.
- If port 8080 is occupied, set another `APP_PORT` in `.env` and open that port.
- If the dashboard says Reconnecting, check `docker compose ps` and API/Redis logs. Polling recovers automatically; Nginx resolves the API service again after container recreation.
- A full lot requires releasing a car before another arrival. Repeated camera messages for an active plate intentionally return a conflict and do not add history.

## Classroom materials

- [מדריך הכנה בעברית](docs/STUDY_GUIDE_HE.md): סדר לימוד, הסברים, תרגילים ובדיקת הבנה לקראת ההצגה.
- [Demo and code review guide](docs/DEMO.md): a 5–10 minute presentation, exact commands, and questions to rehearse.
- [Architecture](ARCHITECTURE.md): request flow, data model, Docker and workflow decisions, and limits.
- [AI usage](AI_USAGE.md): prompts and genuine errors/corrections.
- [Verification record](docs/VERIFICATION.md): observed test and deployment evidence.
- [Implementation plan](docs/superpowers/plans/2026-10-28-parking-project.md): the original task checklist.

The student should rehearse and be able to explain each source file before the teacher's live review. This app simulates a camera HTTP request; it does not perform image recognition or connect to physical camera hardware.
