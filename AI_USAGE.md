# AI usage and corrections

## Scope of assistance

OpenAI Codex helped read the Hebrew assignment, plan the application, write the source/configuration/tests/docs, run Docker locally, inspect the UI, and prepare GitHub CI and GHCR publishing. AI-generated code must be reviewed and understood by the students before the classroom code review. Automated test results are not a claim that a human has reviewed or learned every line.

## Actual prompts and clarifications

1. User asked AI to read the DevOps assignment and prepare a shared GitHub project with “3 images,” one Docker Compose file, and a pipeline.
2. User clarified that the images are Docker container images, selected `DevOps-Project` as a private repository, and said they would add the teammate later.
3. User asked to create a project plan in the local folder and defer GitHub work.
4. User then authorized following the plan, testing it, deploying a fully working app on the local machine, fully documenting the project, and pushing everything to GitHub.

The plan selected Python/Flask, a five-space lot, the release-car feature, and a full-capacity alert as implementation defaults. The assignment allowed any backend language and required a personal feature.

## Genuine error 1 — GitHub login diagnosis

The AI initially interpreted `gh auth status` reporting an invalid token as an expired login and asked the user to authenticate again. The restricted network sandbox prevented a reliable check. The user said they had logged in; a subsequent authorized check outside the sandbox confirmed the account was already authenticated.

Correction: distinguish network/sandbox failures from credential failures, and verify outside the restricted environment when the operation is authorized. No token was added to the repository.

## Genuine error 2 — Unicode normalization

The initial API trimmed and uppercased a plate before checking its ASCII pattern. Python uppercasing turns `ß12` into `SS12` and `ı12` into `I12`, so those non-ASCII inputs were incorrectly admitted with HTTP 201.

Detection: added those two inputs to `test_invalid_inputs_do_not_touch_storage`; both failed because the expected status was 400. The test also showed that admission storage had been called.

Correction: trim first, reject a value unless `isascii()` is true, then uppercase and validate the pattern. The same regression cases passed afterward. This check is applied to both admissions and release URLs.

## Genuine error 3 — Redis retries exceeded the proxy timeout

The initial Redis client set two-second socket timeouts but inherited redis-py's automatic retries. A real test with Redis stopped produced an Nginx HTML 504 instead of the promised Flask JSON 503. The independent reviewer identified the same cause; the mocked outage test had missed the client's retry delay.

Correction: added `test_explicit_bounded_redis_retry`, observed it fail, then configured `Retry(NoBackoff(), 0)`. The real Redis outage test subsequently returned HTTP 503 with the expected JSON error. Normal dashboard polling performs later recovery attempts. The review also corrected an unescaped hyphen in the HTML validation pattern for modern browser Unicode Sets semantics.

## Validation and learning checklist

- Read `api/app.py` to explain validation, status codes, the factory, and Redis errors.
- Read `api/storage.py` to explain the atomic Lua script and why two workers cannot overfill the lot.
- Read the three Dockerfiles and `compose.yaml` to explain build versus runtime, service names, health checks, loopback ports, and the volume.
- Read `web/app.js` to explain fetch, polling, DOM updates, and failure recovery.
- Read `pipeline.yml` to explain CI, a version tag, `GITHUB_TOKEN`, and package permissions.
- Rehearse `docs/DEMO.md` and add any further genuine corrections made during student review.
