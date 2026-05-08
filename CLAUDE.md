# DECISION RECORDS

Technical and process choices made in this project, organized by dev cycle.
Updated after every prompt that produces a new decision.


# ⟳ INNER LOOP
`spec › dev › build › test › commit`


## Spec

| Decision | Why | Rejected |
|----------|-----|---------|
| **cavekit** (`/ck:spec /ck:build /ck:check`) for spec-driven development | Keeps SPEC.md as the single source of truth across context resets; backprop automatically updates the spec on failures | ad-hoc prompting |
| **GitHub issue per feature** — spec content from SPEC.md becomes the issue description | Traceability: every feature has a tracked artifact before a line of code is written; issue links the spec to the PR and commit history | issues created retroactively |
| **PR per feature auto-closes its issue** via `Closes #N` in PR description | Keeps the issue tracker clean automatically; no manual housekeeping | manually closing issues |
| Issue body = human prose, no cavekit § syntax | Issue lives in GitHub UI for collaborators / reviewers; `§T`/`§V`/`§I` are SPEC.md addressing, opaque outside the repo | leaking spec notation into issue body |
| `Closes #N` belongs in PR description only | Issue closes on PR merge; putting `Closes` in the issue itself or in commit messages is meaningless self-reference | `Closes` in issue body or commit message |
| §T `issue` cell = markdown link `[#N](url)` | Cells become click-through in any markdown viewer; bare `#N` requires manual lookup | bare `#N` |


## Dev

| Decision | Why | Rejected |
|----------|-----|---------|
| **context7** (`npx ctx7@latest`) for fetching live library docs | Training data goes stale; context7 pulls current API docs at query time, preventing hallucinated signatures | relying on model training data for API details |
| **cavemem** for persistent memory across agent sessions | Prevents agents from re-explaining project context on every session; stores observations in local SQLite with full-text + vector search via MCP | re-prompting context manually each session |
| **caveman** for token compression | ~75% token reduction on prompts and stored specs without losing semantic fidelity; applied automatically via Claude Code hooks | uncompressed prompts |
| **Principal-level sub-agents** in `.claude/agents/` | Each agent runs in its own context window with role-specific tool restrictions; reviewer is read-only; prevents context pollution between tasks | monolithic single-agent sessions |
| Agents: 🛠️ code-writer · 🧪 test-writer · 🔍 code-reviewer · ☁️ cloud-reviewer | Role separation: writers have Edit/Write tools, reviewers are read-only; emoji prefix identifies which agent is speaking | single general-purpose agent |
| Review findings logged to `SPEC.md` §B BUGS via cavekit backprop | Findings survive context resets and link to invariants that prevent recurrence; SPEC.md is the single source of truth, no parallel file to drift | separate REVIEW.md, conversation-only output |
| Reviewers end report with a ready-to-paste code-writer prompt | Full convenience without autonomy; human checkpoint preserved before any fix is applied | reviewers auto-spawning code-writer |
| Python 3.12 | Latest stable, best type checking support, significant perf improvements over 3.11 | 3.11, 3.13 |
| `src/museums/` package, src/ layout | Prevents importing local dir instead of installed package during tests; PyPA endorsed standard | flat layout |
| `uv` for dependency management | 10–100× faster than pip; reproducible lock files; `[dependency-groups]` keeps dev deps out of the app image | pip, poetry |
| **httpx** for HTTP | Async-capable, consistent API for sync and async use | requests |
| **Pydantic / dataclasses** for structured data | Type-safe, validated, IDE-friendly; enforced by code-writer agent | plain dicts |
| No `print()` — logging only | Log level is runtime-configurable; no noise in library code | print statements |


## Build

| Decision | Why | Rejected |
|----------|-----|---------|
| **Thin API handlers + dedicated module for domain logic** — route handlers only dispatch (call module functions, return Pydantic response). All orchestration, DB queries, and ML logic live in specialized modules (`pipeline`, `db`, `regression`). | Couples API layer to domain when logic is inline; harder to test in isolation without the full HTTP stack. | logic inline in route handlers |
| FastAPI + Uvicorn | Auto OpenAPI docs at /docs, Pydantic-validated settings; sync endpoints run in threadpool automatically | Flask, Django |
| SQLAlchemy 2.0 ORM, SQLite (MVP) → PostgreSQL (prod) | SQLite = zero infrastructure for ~30 rows MVP; dialect switch is one-line change to DATABASE_URL | raw SQL, other ORMs |
| Wikipedia MediaWiki REST API + pandas.read_html() for museum data | Returns rendered HTML; pandas parses without custom HTML wrangling; no API key needed | HTML scraping, third-party wrappers |
| Wikidata SPARQL for city populations | Structured data backbone Wikipedia uses internally; free, no API key; exact-string city match (known limitation) | external population APIs, static datasets |
| scikit-learn LinearRegression | Deterministic, auditable, no hidden hyperparameters; R² communicates quality to non-technical readers | custom implementation, statsmodels |
| Clamp predicted visitors to `max(0, int(pred))` | Negative visitor counts are nonsensical; linear regression can extrapolate below zero | unclamped predictions |
| joblib for model persistence (`models/regression.pkl`) | Standard sklearn companion; fast serialization | pickle directly |


## Test

| Decision | Why | Rejected |
|----------|-----|---------|
| pytest only | Fixture-first design; parametrize for data-driven cases | unittest |
| Mock all HTTP + DB in unit tests (pytest-httpx, in-memory SQLite) | Tests must be fast and deterministic; no live Wikipedia/Wikidata calls in CI | integration-first testing |
| Record real Wikipedia response as fixture file for scraper tests | Replay-based tests are deterministic and document the real API shape | mocking from scratch |
| Matrix builds: Python 3.12 + 3.13 | Catches compatibility regressions before upgrading | single version only |
| ruff pinned to `==0.15.12` in dev-group, pre-commit rev, and CI install; same version in all three (V42) | Different versions produce different formatting output — CI `ruff format --check` fails if local ruff version differs; 0.15.12 is the project baseline | mixing versions, unpinned |
| Bruno API tests in opencollection YAML format | Diffs are readable in PR reviews; standard YAML tooling applies | .bru format |
| Bruno collection manifest = `opencollection.yml` (not `bruno.json`) | `bruno.json` is the legacy `.bru` format manifest; opencollection format requires `opencollection.yml` with `opencollection: 1.0.0` header | `bruno.json` |
| Bruno request files use `.yml` extension (not `.yaml`) | Bruno desktop only loads `.yml` files; `.yaml` silently ignored | `.yaml` extension |
| Bruno request files numbered `NN-name.yml` (e.g. `01-get-health.yml`) | Explicit `seq:` field + numeric prefix both control run order; prefix makes ordering visible in directory listings | arbitrary names |
| Bruno environments file format: `name:` + `variables: [{name, value}]` | opencollection env schema uses list-of-objects; flat `vars:` dict is wrong format and causes Bruno to ignore the file | `vars: {key: value}` dict |


## Commit

| Decision | Why | Rejected |
|----------|-----|---------|
| **GitButler** for branch management (stacked branches per feature) | Stacked branches map 1:1 to features and their GitHub issues; GitButler manages the branch graph; direct git commits blocked by hook | plain git branches |
| Conventional commits enforced via commitizen + pre-commit hook | Enables automated semantic versioning; readable git history | manual commit message discipline |
| python-semantic-release for versioning | Python-native (in pyproject.toml); automates version bump, CHANGELOG, git tag, GitHub Release from conventional commits | Release Please, manual tagging |


# ↻ OUTER LOOP
`PR › build › test › deliver › deploy`


## PR

| Decision | Why | Rejected |
|----------|-----|---------|
| One PR per feature, stacked on GitButler branch | Each feature maps to one issue → one branch → one PR; stacking allows dependent features to be reviewed independently | feature branches off main |
| PR description includes `Closes #N` | Issue auto-closes on merge; zero housekeeping | manually closing issues post-merge |
| Preflight job first in every pipeline (< 30s) | Fails fast on broken lockfile, YAML syntax errors, broken Compose config; saves 5–10 min of CI per bad push | running full CI before basic checks |


## Build

| Decision | Why | Rejected |
|----------|-----|---------|
| Multi-stage Dockerfile (builder + python:3.12-alpine, non-root uid 1000) | Keeps dev deps out of production image; non-root reduces attack surface; Alpine ~50MB vs ~130MB slim | single-stage build, python:3.12-slim |
| Alpine (`python:3.12-alpine`) for Docker + CI containers | Smallest attack surface; forces minimal deps; prod image matches CI container; consistent environment | python:3.12-slim (larger), ubuntu-latest CI container (mismatches prod) |
| Poe the Poet for dev scripts | All scripts in pyproject.toml alongside deps and tool config; `uv run poe <task>` works inside uv venv; no separate file needed | Makefile (external file), hatch scripts (conflicts with uv venv management) |
| Two Compose services: `api` (port 8000) + `jupyter` (port 8888) | Different restart policies and health-check paths; jupyter depends_on api healthy | single container |
| Named volume `museums-data` shared between services | DB and model files persist across restarts; both services read the same data | bind mounts |


## Test

| Decision | Why | Rejected |
|----------|-----|---------|
| PR CI: lint + format (ruff) + unit tests + SAST + Docker build + Trivy + Bruno | Developer feedback loop; fast and cheap; no real Wikipedia calls | slower integration-only CI |
| Nightly CI: full Wikipedia ingest + pip-audit + Trivy on fresh images | Catches external changes (new CVE, Wikipedia table change) that don't trigger on commits | on-demand only |
| Locust stress tests run nightly, gated on p95 + p99 + error-rate thresholds | Catches latency regressions external to PR-time CI; threshold breach fails the nightly job and pages oncall | bundled into nightly without explicit gating, manual perf testing |
| Stress test thresholds: p95 + p99 latency + error rate | p95 = widespread degradation; p99 = tail latency spikes; both needed | p50 only |


## Deliver

| Decision | Why | Rejected |
|----------|-----|---------|
| CD: push to `staging` branch auto-deploys to staging env; merge to `main` requires manual GitHub Environment approval for prod | Dedicated staging branch gives a persistent UAT surface; approval gate prevents accidental prod deploys | auto-deploy to prod, staging served off main |
| `release.yml` workflow separate from `pr.yml` | PR CI validates; release CI publishes — single responsibility; release only runs on `main` merge, not every PR | combining release step into pr.yml |
| Three environments: preview / staging / prod (no separate UAT) | Staging serves UAT; separate UAT would double RDS costs for identical infrastructure | four-environment model |
| Preview deploys: ECS Fargate task with public IP, no ALB | ALBs are expensive (~$0.008/hr/LCU) for a temporary per-PR env | ALB per PR |


## Deploy

| Decision | Why | Rejected |
|----------|-----|---------|
| **Pulumi Python** for IaC | Real Python in infra code; same mental model as app code; first-class ECS + RDS support | Terraform HCL, CDKTF (deprecated Dec 2025) |
| Stack configs in `infra/environments/{env}.yaml` | No "Pulumi" prefix per user preference; specified via `--config-file` flag | default Pulumi.stackname.yaml convention |
| 3 AZs, 2 minimum prod tasks for HA | 2 tasks across 3 AZs = HA if one AZ fails without 3× task cost | single-AZ |
| RDS: SQLite (preview) → db.t3.micro (staging) → db.t3.small multi-AZ (prod) | Right-sized per environment; multi-AZ only where it matters | uniform sizing across envs |
| RDS auto-shutdown on staging via EventBridge + Lambda (8pm–7am UTC) | ~46% cost saving; not applied to prod (always-on) | always-on staging |
| RDS password rotation via AWS Secrets Manager `manage_master_user_password` | AWS rotates every 7 days; password injected via ECS `secrets` field (never in CloudWatch logs) | manual rotation, env vars |
| CloudWatch alarms: 5xx rate + p99 latency + ECS under-capacity + RDS CPU | Covers the four most common failure modes | ad-hoc monitoring |
| Git flow: `main` + `staging` + `feature/*` + `hotfix/*` | staging branch = persistent UAT surface auto-deployed to staging env; feature/* branch off main, merge to staging for testing, then to main for prod; hotfix/* branch off main | Gitflow with develop + release/*, trunk-based without staging |
