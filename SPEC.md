# SPEC

## §G GOAL
ingest top-visited museums + host-city populations → DB → fit linear regression visitors~population → expose via FastAPI + Jupyter notebook, all in Docker Compose.

## §C CONSTRAINTS
- Python 3.12; `src/museums/` layout; `uv` deps + lock
- libs locked: httpx, pydantic, FastAPI, Uvicorn, SQLAlchemy 2.0, scikit-learn, joblib, pandas
- data sources: Wikipedia MediaWiki REST API + `pandas.read_html()` for museums; Wikidata SPARQL for city populations
- DB: SQLite (MVP) → PostgreSQL (prod) via single `DATABASE_URL` switch; production RDS tier sizing per T-INFRA
- ML: sklearn `LinearRegression`, deterministic, persisted via `joblib`
- ⊥ `print()` in library code — `logging` only
- type hints ! everywhere
- structured data = Pydantic (API surface, validated) | `dataclasses` (internal value objects)
- tests = pytest; ∀ HTTP & DB mocked in unit (pytest-httpx, in-memory SQLite); real Wikipedia response stored as fixture
- Docker = multi-stage, base `python:3.12-slim`, non-root uid 1000
- Compose = 2 services (`api`:8000, `jupyter`:8888), named volume `museums-data`, jupyter `depends_on` api healthy
- conventional commits enforced via `commitizen` + `pre-commit` hook; ruff lint+format
- versioning via `python-semantic-release` (auto bump, CHANGELOG, git tag, GitHub Release)
- API tests = Bruno in opencollection YAML format
- commits ! via GitButler — direct `git commit` blocked by hook

## §I INTERFACES
- cli: `museums ingest` → fetch + persist museums & city populations into DB; idempotent
- cli: `museums train` → fit regression on DB rows, write `models/regression.pkl`, log R²
- api: `GET /health` → 200 `{status:"ok"}`
- api: `GET /museums` → 200 `[Museum]` (Pydantic)
- api: `GET /museums/{id}` → 200 `Museum` | 404
- api: `GET /cities` → 200 `[City]`
- api: `POST /predict` body `{population:int≥0}` → 200 `{predicted_visitors:int≥0}` | 400 if model absent
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

## §T TASKS
| id | status | task | cites |
|---|---|---|---|
| T1 | . | Commit hygiene: `.pre-commit-config.yaml` (commitizen + ruff), `pyproject.toml` `[tool.semantic_release]` config | V25,V26 |
| T2 | . | Bootstrap: `pyproject.toml` (uv, deps, dev-group), `src/museums/__init__.py`, module stubs (`scraper.py`, `enricher.py`, `db.py`, `regression.py`, `api.py`, `cli.py`), `tests/conftest.py`, `notebooks/`, `models/`, ruff config, logging config | C |
| T3 | . | Docker: multi-stage `Dockerfile` (builder + `python:3.12-slim`, uid 1000), `docker-compose.yml` (`api`:8000 + `jupyter`:8888, vol `museums-data`, healthcheck, depends_on) | V13,V14,V21,V23,I.compose |
| T4 | . | API skeleton `src/museums/api.py`: FastAPI app, `GET /health`, `GET /docs`, route stubs returning empty Pydantic payloads — boots in container | V11,V12,I.api |
| T5 | . | Bruno API collection under `tests/api/` — opencollection YAML covering §I.api routes (hits skeleton, grows as routes flesh out) | V29,I.api |
| T6 | . | `.github/workflows/pr.yml` — preflight job <30s + matrix CI (ruff + pytest + SAST + Docker build + Trivy + Bruno) | V24,V27,V28 |
| T7 | . | Database `src/museums/db.py`: SQLAlchemy 2.0 models (`Museum`, `City`), engine + session factory from `DATABASE_URL`, upsert helpers, FastAPI session dependency | V1,V2,V7,V15,V16 |
| T8 | . | Scraper `src/museums/scraper.py`: fetch Wikipedia "List_of_most_visited_museums" via REST API, parse via `pandas.read_html`, return `list[MuseumRecord]` (Pydantic); fixture `tests/fixtures/wikipedia_museums.html` | V1,V3,V5,V6,V19,I.cli |
| T9 | . | Enricher `src/museums/enricher.py`: query Wikidata SPARQL for city populations, return `list[CityRecord]`; exact-string label match | V2,V4,V5,V6,V20 |
| T10 | . | Regression `src/museums/regression.py`: `train(session)`→fit+persist+log R²; `predict(population:int)→int`; `InsufficientDataError` | V8,V9,V17,V18 |
| T11 | . | API impl: wire skeleton routes (`GET /museums`, `/museums/{id}`, `/cities`, `POST /predict`) to DB + regression; load model at startup | V8,V11,V12,V15,I.api |
| T12 | . | CLI `src/museums/cli.py`: `museums ingest`, `museums train` subcommands wiring T8+T9→T7 and T10 | V16,I.cli |
| T13 | . | Notebook `notebooks/analysis.ipynb`: imports `museums`, calls regression, plots scatter + fit line + R² | I.notebook |
| T14 | . | Tests: unit suites per module with `pytest-httpx` + in-memory SQLite; fixture replay for scraper; matrix 3.12/3.13 | V6,V24 |
| T-INFRA | . | SCOPE MARKER — items below live in DECISIONS.md OUTER LOOP, ⊥ implement under this SPEC.md, separate infra spec required:<br>• Pulumi Python IaC<br>• `infra/environments/{env}.yaml` stack configs<br>• ECS Fargate (preview = task w/ public IP, no ALB; staging + prod behind ALB)<br>• HA: 3 AZs, ≥2 prod tasks (one AZ failure tolerated, no 3× task cost)<br>• RDS tier per env (preview SQLite / staging PostgreSQL t3.micro / prod PostgreSQL t3.small multi-AZ)<br>• RDS staging auto-shutdown (EventBridge + Lambda, 8pm–7am UTC, ~46% cost saving)<br>• Secrets Manager password rotation<br>• CloudWatch alarms (5xx, p99, ECS under-capacity, RDS CPU)<br>• staging-branch CD + GitHub Environment approval for prod<br>• nightly CI (live ingest, Locust, pip-audit, Trivy fresh-image)<br>• stress thresholds (p95, p99, error rate)<br>• Git flow `main`/`staging`/`feature/*`/`hotfix/*` | - |

## §B BUGS
| id | date | cause | fix |
|---|---|---|---|
