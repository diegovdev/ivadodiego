# SPEC

## §G GOAL
ingest top-visited museums + host-city populations → DB → fit linear regression visitors~population → expose via FastAPI + Jupyter notebook, all in Docker Compose.

## §C CONSTRAINTS
- Python 3.12; `src/museums/` layout; `uv` deps + lock
- libs locked: httpx, pydantic, FastAPI, Uvicorn, SQLAlchemy 2.0, scikit-learn, joblib, pandas
- data sources: Wikipedia MediaWiki REST API + `pandas.read_html()` for museums; Wikidata SPARQL for city populations
- DB: SQLite (MVP) → PostgreSQL (prod) via single `DATABASE_URL` switch; production RDS tier sizing per §T `infra` stage (T18)
- ML: sklearn `LinearRegression`, deterministic, persisted via `joblib`
- ⊥ `print()` in library code — `logging` only
- type hints ! everywhere
- structured data = Pydantic (API surface, validated) | `dataclasses` (internal value objects)
- tests = pytest; ∀ HTTP & DB mocked in unit (pytest-httpx, in-memory SQLite); real Wikipedia response stored as fixture
- Docker = multi-stage, base `python:3.12-alpine`, non-root uid 1000
- Compose = 2 services (`api`:8000, `jupyter`:8888), named volume `museums-data`, jupyter `depends_on` api healthy
- conventional commits enforced via `commitizen` + `pre-commit` hook; ruff lint+format
- versioning via `python-semantic-release` (auto bump, CHANGELOG, git tag, GitHub Release)
- API tests = Bruno in opencollection YAML format
- commits ! via GitButler — direct `git commit` blocked by hook

## §I INTERFACES
- api: `GET /health` → 200 `{status:"ok"}`
- api: `GET /museums` → 200 `[Museum]` (Pydantic)
- api: `GET /museums/{id}` → 200 `Museum` | 404
- api: `GET /cities` → 200 `[City]`
- api: `POST /predict` body `{population:int≥0}` → 200 `{predicted_visitors:int≥0}` | 400 if model absent
- api: `POST /ingest` → 202 `{status:"accepted"}`, triggers museum+city fetch+persist
- api: `POST /train` → 202 `{status:"accepted"}`, triggers regression fit+persist
- api: `GET /docs` → OpenAPI UI (FastAPI default)
- file: `models/regression.pkl` — joblib-serialized fitted `LinearRegression`
- file: SQLite DB on named vol `museums-data` (path = `${DATABASE_URL}`)
- file: `tests/fixtures/wikipedia_museums.html` — recorded real response
- env: `DATABASE_URL` (req), `MODEL_PATH` (default `models/regression.pkl`), `LOG_LEVEL` (default `INFO`)
- notebook: `notebooks/analysis.ipynb` — imports `museums` package, plots regression line + R²
- compose: `api` :8000, `jupyter` :8888, shared vol `museums-data`
- file: `tests/api/` — Bruno API tests (opencollection YAML)
- file: `.pre-commit-config.yaml` — commitizen + ruff hooks
- file: `.github/workflows/pr.yml` — preflight + ruff + pytest + SAST + Docker build + Trivy + Bruno
- file: `pyproject.toml` `[tool.semantic_release]` — versioning config
- file: `infra/` — Pulumi Python IaC project root
- file: `infra/environments/{preview,staging,prod}.yaml` — Pulumi stack configs
- file: `.github/workflows/nightly.yml` — nightly CI (live ingest, Locust, pip-audit, Trivy fresh)

## §V INVARIANTS
- V1: ∀ museum row → `name`, `city`, `country`, `visitors_annual` ≥ 0 present & non-null
- V2: ∀ city row → `name`, `country`, `population` ≥ 0 present & non-null
- V3: museum data sourced ! from Wikipedia MediaWiki REST API (no scraping)
- V4: city population sourced ! from Wikidata SPARQL endpoint
- V5: HTTP client = `httpx` (⊥ `requests`)
- V6: ∀ external HTTP call mocked in unit tests via `pytest-httpx`
- V7: DB writes ! inside transaction; rollback on error
- V8: `predict_visitors` output = `max(0, int(pred))` (⊥ negative)
- V9: model persistence ! via `joblib` to `MODEL_PATH`
- V10: ⊥ `print()` in `src/museums/`; `logging` only
- V11: ∀ public function/method → type hints on params & return
- V12: API responses ! Pydantic-validated models (no raw dicts)
- V13: Docker image runs as uid 1000 non-root
- V14: Compose `jupyter` ! start only after `api` healthcheck passes
- V15: SQLAlchemy session ! closed after each request (FastAPI dep injection)
- V16: `museums ingest` idempotent — re-run ⊥ duplicate rows (upsert by natural key)
- V17: regression fit ! requires ≥ 2 distinct samples; else raise `InsufficientDataError`
- V18: R² logged at INFO after every train
- V19: Wikipedia table parsed ! via `pandas.read_html` (no manual HTML walking)
- V20: city → Wikidata match = exact-string label match (known limitation, documented)
- V21: `museums-data` volume shared between `api` & `jupyter` services
- V22: `Closes #N` present in every PR description
- V23: dev deps ∉ production Docker image (multi-stage strip)
- V24: matrix CI runs Python 3.12 & 3.13
- V25: ∀ commit message ! conventional-commits format (commitizen-validated)
- V26: ⊥ direct `git commit` — GitButler hook only
- V27: ∀ PR pipeline ! preflight job <30s before heavy stages
- V28: PR CI ! run ruff + pytest + SAST + Docker build + Trivy + Bruno
- V29: Bruno collection ! in opencollection YAML format
- V30: Pulumi stack configs ! at `infra/environments/{env}.yaml` (specified via `--config-file`)
- V31: production tasks ! span ≥3 AZs with ≥2 instances
- V32: RDS staging auto-shutdown ! 8pm–7am UTC; ⊥ shutdown prod
- V33: Secrets Manager rotation cadence = 7 days; ⊥ password in env var or CW logs
- V34: CD to prod ! requires GitHub Environment manual approval
- V35: nightly CI ! enforce p95 + p99 + error-rate thresholds; threshold breach fails job
- V36: branches ! match pattern `main` | `staging` | `feature/*` | `hotfix/*`; ⊥ other prefixes
- V37: Docker base image = `python:3.12-alpine`; CI jobs run inside `python:3.12-alpine` container
- V38: release workflow ! use `GITHUB_TOKEN` only — ⊥ hardcoded PAT; ⊥ push to `main` without version bump commit

## §T TASKS
| id | status | stage | task | cites | issue | branch |
|---|---|---|---|---|---|---|
| T1 | x | scaffold | Commit hygiene: `.pre-commit-config.yaml` (commitizen + ruff), `pyproject.toml` `[tool.semantic_release]` config | V25,V26 | [#1](https://github.com/diegovdev/ivadodiego/issues/1) | feature/scaffold |
| T2 | x | scaffold | Bootstrap: `pyproject.toml` (uv, deps, dev-group), `src/museums/__init__.py`, module stubs (`scraper.py`, `enricher.py`, `db.py`, `regression.py`, `api.py`), `tests/conftest.py`, `notebooks/`, `models/`, ruff+ANN config, logging config | C | [#2](https://github.com/diegovdev/ivadodiego/issues/2) | feature/scaffold |
| T3 | x | scaffold | Docker: multi-stage `Dockerfile` (builder + `python:3.12-alpine`, uid 1000, apk build deps for compiled packages), `docker-compose.yml` (`api`:8000 + `jupyter`:8888, vol `museums-data`, healthcheck, depends_on) | V13,V14,V21,V23,V37,I.compose | [#3](https://github.com/diegovdev/ivadodiego/issues/3) | feature/scaffold |
| T4 | x | scaffold | API skeleton `src/museums/api.py`: FastAPI app, `GET /health`, `GET /docs`, route stubs returning empty Pydantic payloads — boots in container | V11,V12,I.api | [#4](https://github.com/diegovdev/ivadodiego/issues/4) | feature/scaffold |
| T5 | x | scaffold | Bruno API collection under `tests/api/` — opencollection YAML covering §I.api routes (hits skeleton, grows as routes flesh out) | V29,I.api | [#5](https://github.com/diegovdev/ivadodiego/issues/5) | feature/scaffold |
| T6 | x | scaffold | `.github/workflows/pr.yml` — preflight job <30s + matrix CI (ruff + pytest + SAST + Docker build + Trivy + Bruno); jobs run in `python:3.12-alpine` container | V24,V27,V28,V37 | [#6](https://github.com/diegovdev/ivadodiego/issues/6) | feature/scaffold |
| T7 | . | feature | Database `src/museums/db.py`: SQLAlchemy 2.0 models (`Museum`, `City`), engine + session factory from `DATABASE_URL`, upsert helpers, FastAPI session dependency | V1,V2,V7,V15,V16 | - | - |
| T8 | . | feature | Scraper `src/museums/scraper.py`: fetch Wikipedia "List_of_most_visited_museums" via REST API, parse via `pandas.read_html`, return `list[MuseumRecord]` (Pydantic); fixture `tests/fixtures/wikipedia_museums.html` | V1,V3,V5,V6,V19,I.api | - | - |
| T9 | . | feature | Enricher `src/museums/enricher.py`: query Wikidata SPARQL for city populations, return `list[CityRecord]`; exact-string label match | V2,V4,V5,V6,V20 | - | - |
| T10 | . | feature | Regression `src/museums/regression.py`: `train(session)`→fit+persist+log R²; `predict(population:int)→int`; `InsufficientDataError` | V8,V9,V17,V18 | - | - |
| T11 | . | feature | API impl: wire all routes (`GET /museums`, `/museums/{id}`, `/cities`, `POST /predict`, `POST /ingest`, `POST /train`) to DB + regression; load model at startup | V8,V11,V12,V15,I.api | - | - |
| T12 | . | feature | Wire `POST /ingest` → scraper+enricher→db; `POST /train` → regression.train(); background tasks via FastAPI BackgroundTasks | V16,I.api | - | - |
| T13 | . | feature | Notebook `notebooks/analysis.ipynb`: imports `museums`, calls regression, plots scatter + fit line + R² | I.notebook | - | - |
| T14 | . | test | Tests: unit suites per module with `pytest-httpx` + in-memory SQLite; fixture replay for scraper; matrix 3.12/3.13 | V6,V24 | - | - |
| T15 | . | infra | Pulumi Python project scaffold under `infra/` | V30 | - | - |
| T16 | . | infra | Stack configs `infra/environments/{preview,staging,prod}.yaml` (use `--config-file` flag) | T15,V30 | - | - |
| T17 | . | infra | ECS Fargate task definitions per env (preview = public IP no ALB; staging+prod behind ALB) | T15,T16 | - | - |
| T18 | . | infra | RDS provisioning per env (SQLite preview / Postgres t3.micro staging / Postgres t3.small multi-AZ prod) | T16 | - | - |
| T19 | . | infra | RDS Secrets Manager `manage_master_user_password` rotation; injected via ECS `secrets` field | T18,V33 | - | - |
| T20 | . | infra | RDS staging auto-shutdown via EventBridge + Lambda, 8pm–7am UTC | T18,V32 | - | - |
| T21 | . | infra | CloudWatch alarms: 5xx rate, p99 latency, ECS under-capacity, RDS CPU | T17,T18 | - | - |
| T22 | . | infra | HA: 3 AZs, ≥2 prod tasks | T17,V31 | - | - |
| T23 | . | delivery | CD workflow: `staging` auto-deploys staging; `main` merge requires GitHub Environment manual approval | T17,V34 | - | - |
| T26 | . | delivery | `.github/workflows/release.yml` — triggers on push to `main`; Alpine container; full history checkout; `semantic-release version` (bumps pyproject.toml + tag) + `semantic-release publish` (GitHub Release + CHANGELOG); uses `GITHUB_TOKEN` | V25,V37,V38,T6 | - | - |
| T24 | . | quality | Nightly CI: live Wikipedia ingest + pip-audit + Trivy fresh-image scan | T6 | - | - |
| T25 | . | quality | Locust stress thresholds enforced nightly: p95 + p99 + error rate | T24,V35 | - | - |

## §B BUGS
| id | date | cause | fix |
|---|---|---|---|
