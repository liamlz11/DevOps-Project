# Classroom demo and code review guide

Aim for 7–8 minutes, with room for questions. Keep Docker Desktop running and a PowerShell window open in the project root. Open http://localhost:8080 in a browser. Read the verification record before the lesson.

## 0–1 minutes — Explain the system

“Our camera sends a recognized license plate as an HTTP POST. Nginx serves the guard's dashboard and forwards API requests to Flask. Redis stores active cars and the arrival log. Docker Compose builds and runs all three services.” Show the architecture diagram in `ARCHITECTURE.md` and `docker compose ps`.

## 1–3 minutes — Show arrivals and the personal feature

Use the camera simulator form to register a plate. Point out that the parked count, bay markers, table, and arrival log change without reloading the page. Send another arrival from PowerShell to prove the camera does not need the dashboard form:

```powershell
Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/api/entries' `
  -ContentType 'application/json' -Body '{"plate":"555-66-777"}'
Invoke-RestMethod 'http://localhost:8080/api/parking' | ConvertTo-Json -Depth 5
```

Register enough distinct cars to fill five spaces. Show the full-capacity alert and rejection of a sixth plate. Click Release for one car; the count decreases, the gate opens, and its arrival remains in history. Explain that the bay drawings represent occupied/free capacity, not individually assigned parking positions.

## 3–5 minutes — Prove persistence live

Leave at least one parked car visible. Note its plate and timestamp. Run exactly:

```powershell
docker compose down
docker compose up -d --wait
```

Return to the dashboard and confirm the same car and timestamp remain. Explain that containers were removed and recreated, while the `gatehouse_redis-data` named volume was retained. Show `redis/redis.conf`: append-only persistence writes below `/data`, where the volume is mounted. Do not use `down -v` for this demo.

If time allows, show the repeatable verification approach on a lot with a free space:

```powershell
python scripts/check_demo.py --seed
docker compose down
docker compose up -d --wait
python scripts/check_demo.py --verify
python scripts/check_demo.py --cleanup
```

## 5–7 minutes — Show CI and the bonus

Open GitHub Actions in the private repository. Show a successful test run and a version-tag run that publishes three images to GHCR. Explain the stages: validate, build, start, test, recreate, verify, publish. `GITHUB_TOKEN` is automatically provided by Actions; package publishing has `packages: write`. Tags name the exact release version.

## 7–8 minutes — AI use and review questions

Show the genuine Unicode validation error in `AI_USAGE.md`, the regression test, and the corrected validation order. Be prepared to explain these points in your own words:

| Question | Answer to understand |
| --- | --- |
| Why three images? | Each service packages a separate responsibility and its own configuration. Redis is based on the official image with our config. |
| What does `FROM` do? | Chooses the base filesystem and runtime for an image. |
| `RUN` versus `CMD`? | `RUN` executes during image build; `CMD` defines the default container process at runtime. |
| Why `COPY requirements.txt` before the source? | Docker can reuse the dependency-install layer when only source changes. |
| Why Gunicorn? | It runs the Flask WSGI application as the container process with two workers. |
| Why `api:5000` and `redis`? | Compose service names resolve through Docker's internal DNS. |
| Does `EXPOSE` publish a port? | No. Compose `ports` publishes the Nginx port; API/Redis stay internal. |
| Why health checks and `depends_on`? | Startup waits for working dependencies, rather than only created containers. |
| What is the volume for? | It preserves Redis files across container recreation. |
| Does AOF guarantee zero loss? | No. `everysec` can lose approximately the latest second on abrupt power/host failure. |
| What stops a race for the last space? | Redis executes the admission Lua script atomically. |
| Why does history remain after release? | Active occupancy and recent arrivals are different Redis collections. |
| Why a version tag? | It triggers publishing and provides a versioned image reference. |
| What if Redis/API stops? | Errors are reported, stale data is labeled, and polling recovers when service returns. |

## Before the lesson

Run `docker compose up --build -d --wait` and the test commands from README. Release unneeded demo cars through the UI so there is room for arrivals. Confirm the intended plate examples are not already active. Keep a successful GitHub run ready to show. A human still needs to rehearse the explanation; automated checks cannot do that part for the student.
