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
- api: `GET /status` → 200 `{ingest:{last_run,status,detail}, train:{last_run,status,detail}}`
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
- V11: ∀ public function/method → type hints on params & return; hints ! specific (⊥ `object`/`Any` as public return unless documented)
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
- V37: Docker base image = `python:3.12-alpine`; CI jobs run inside `python:3.12-alpine` container; jupyter image ! Python 3.12; exception: Docker-build CI job runs on host runner (DinD)
- V38: release workflow ! use `GITHUB_TOKEN` only — ⊥ hardcoded PAT; ⊥ push to `main` without version bump commit
- V39: ∀ test file ! reference repo paths via `Path(__file__).parent...` (⊥ cwd-dependent bare paths)
- V40: ∀ third-party GitHub Action ! pinned to SHA or explicit version tag (⊥ `@master`, `@main`)
- V41: GitHub issue bodies = human prose; ⊥ § notation (V/T/B refs in body)
- V42: pre-commit hook tool versions ! match dev-group versions (single source of truth)
- V43: ∀ HTTP polling/healthcheck inside Alpine container ! use `python -c "urllib.request.urlopen(...)"` (⊥ `wget`, ⊥ `curl` — both implicit base-image deps); applies to Dockerfile, Compose, CI scripts
- V44: upsert helpers ! use dialect-level `INSERT … ON CONFLICT DO UPDATE` (⊥ SELECT-then-INSERT TOCTOU); applies to all `upsert_*` functions in `db.py`
- V45: ∀ external HTTP call ! set explicit `timeout=` (⊥ unbounded default); applies to `httpx.get`/`httpx.post` in scraper, enricher, and any future HTTP client code

## §T TASKS
Status: `.` open, `~` wip, `x` fixed.
| id | status | stage | task | cites | issue | branch |
|---|---|---|---|---|---|---|
| T1 | x | scaffold | Commit hygiene: `.pre-commit-config.yaml` (commitizen + ruff), `pyproject.toml` `[tool.semantic_release]` config | V25,V26 | [#1](https://github.com/diegovdev/ivadodiego/issues/1) | feature/scaffold |
| T2 | x | scaffold | Bootstrap: `pyproject.toml` (uv, deps, dev-group), `src/museums/__init__.py`, module stubs (`scraper.py`, `enricher.py`, `db.py`, `regression.py`, `api.py`), `tests/conftest.py`, `notebooks/`, `models/`, ruff+ANN config, logging config | C | [#2](https://github.com/diegovdev/ivadodiego/issues/2) | feature/scaffold |
| T3 | x | scaffold | Docker: multi-stage `Dockerfile` (builder + `python:3.12-alpine`, uid 1000, apk build deps for compiled packages), `docker-compose.yml` (`api`:8000 + `jupyter`:8888, vol `museums-data`, healthcheck, depends_on) | V13,V14,V21,V23,V37,I.compose | [#3](https://github.com/diegovdev/ivadodiego/issues/3) | feature/scaffold |
| T4 | x | scaffold | API skeleton `src/museums/api.py`: FastAPI app, `GET /health`, `GET /docs`, route stubs returning empty Pydantic payloads — boots in container | V11,V12,I.api | [#4](https://github.com/diegovdev/ivadodiego/issues/4) | feature/scaffold |
| T5 | x | scaffold | Bruno API collection under `tests/api/` — opencollection YAML covering §I.api routes (hits skeleton, grows as routes flesh out) | V29,I.api | [#5](https://github.com/diegovdev/ivadodiego/issues/5) | feature/scaffold |
| T6 | x | scaffold | `.github/workflows/pr.yml` — preflight job <30s + matrix CI (ruff + pytest + SAST + Docker build + Trivy + Bruno); jobs run in `python:3.12-alpine` container | V24,V27,V28,V37 | [#6](https://github.com/diegovdev/ivadodiego/issues/6) | feature/scaffold |
| T7 | x | feature | Database `src/museums/db.py`: SQLAlchemy 2.0 models (`Museum`, `City`), engine + session factory from `DATABASE_URL`, upsert helpers, FastAPI session dependency | V1,V2,V7,V15,V16,V44 | [#8](https://github.com/diegovdev/ivadodiego/issues/8) | feature/db-7 |
| T8 | x | feature | Scraper `src/museums/scraper.py`: fetch Wikipedia "List_of_most_visited_museums" via REST API, parse via `pandas.read_html`, return `list[MuseumRecord]` (Pydantic); fixture `tests/fixtures/wikipedia_museums.html` | V1,V3,V5,V6,V19,V45,I.api | [#9](https://github.com/diegovdev/ivadodiego/issues/9) | feature/scraper-8 |
| T9 | x | feature | Enricher `src/museums/enricher.py`: query Wikidata SPARQL for city populations, return `list[CityRecord]`; exact-string label match | V2,V4,V5,V6,V20 | [#10](https://github.com/diegovdev/ivadodiego/issues/10) | feature/enricher-9 |
| T10 | x | feature | Regression `src/museums/regression.py`: `train(session)`→fit+persist+log R²; `predict(population:int)→int`; `InsufficientDataError` | V8,V9,V17,V18 | [#11](https://github.com/diegovdev/ivadodiego/issues/11) | feature/regression-10 |
| T11 | x | feature | API impl: wire all routes (`GET /museums`, `/museums/{id}`, `/cities`, `POST /predict`, `POST /ingest`, `POST /train`) to DB + regression; load model at startup | V8,V11,V12,V15,I.api | [#12](https://github.com/diegovdev/ivadodiego/issues/12) | feature/api-impl-12 |
| T12 | x | feature | Wire `POST /ingest` → scraper+enricher→db; `POST /train` → regression.train(); background tasks via FastAPI BackgroundTasks | V16,I.api | [#14](https://github.com/diegovdev/ivadodiego/issues/14) | feature/ingest-12 |
| T13 | x | feature | Notebook `notebooks/analysis.ipynb`: imports `museums`, calls regression, plots scatter + fit line + R² | I.notebook | [#15](https://github.com/diegovdev/ivadodiego/issues/15) | feature/notebook-13 |
| T14 | x | test | Tests: unit suites per module with `pytest-httpx` + in-memory SQLite; fixture replay for scraper; matrix 3.12/3.13 | V6,V24 | - | - |
| T15 | x | infra | Pulumi Python project scaffold under `infra/` | V30 | - | - |
| T16 | x | infra | Stack configs `infra/environments/{preview,staging,prod}.yaml` (use `--config-file` flag) | T15,V30 | - | - |
| T17 | x | infra | ECS Fargate task definitions per env (preview = public IP no ALB; staging+prod behind ALB) | T15,T16 | - | - |
| T18 | x | infra | RDS provisioning per env (SQLite preview / Postgres t3.micro staging / Postgres t3.small multi-AZ prod) | T16 | - | - |
| T19 | x | infra | RDS Secrets Manager `manage_master_user_password` rotation; injected via ECS `secrets` field | T18,V33 | - | - |
| T20 | x | infra | RDS staging auto-shutdown via EventBridge + Lambda, 8pm–7am UTC | T18,V32 | - | - |
| T21 | x | infra | CloudWatch alarms: 5xx rate, p99 latency, ECS under-capacity, RDS CPU | T17,T18 | - | - |
| T22 | x | infra | HA: 3 AZs, ≥2 prod tasks | T17,V31 | - | - |
| T23 | x | delivery | CD workflow: `staging` auto-deploys staging; `main` merge requires GitHub Environment manual approval | T17,V34 | - | - |
| T26 | . | delivery | `.github/workflows/release.yml` — triggers on push to `main`; Alpine container; full history checkout; `semantic-release version` (bumps pyproject.toml + tag) + `semantic-release publish` (GitHub Release + CHANGELOG); uses `GITHUB_TOKEN` | V25,V37,V38,T6 | - | - |
| T24 | x | quality | Nightly CI: live Wikipedia ingest + pip-audit + Trivy fresh-image scan | T6 | - | - |
| T25 | x | quality | Locust stress thresholds enforced nightly: p95 + p99 + error rate | T24,V35 | - | - |

## §B BUGS
Status: `.` open, `~` wip, `x` fixed.

| id | status | date | task | severity | description | cause | fix |
|---|---|---|---|---|---|---|---|
| B1 | x | 2026-05-06 | T3,T5,T6 | high | 3 test files use bare `Path("...")` → cwd-dependent FileNotFoundError | tests assume pytest cwd = repo root | `Path(__file__).parent...` repo-relative; +V39 |
| B2 | x | 2026-05-06 | T3 | high | jupyter image `python-3.11`; §C requires 3.12 | wrong image tag in compose | bump to `python-3.12`; amend V37 |
| B3 | x | 2026-05-06 | T6 | high | `trivy-action@master` floating ref (supply-chain) | third-party action unpinned | pin to `trivy-action@v0.36.0`; +V40 |
| B4 | x | 2026-05-06 | T2 | medium | `db.py:6` returns `object`; `regression.py:10` `session: object` | vacuous hints satisfy V11 letter, not spirit | use `Engine`/`Session`; amend V11 |
| B5 | x | 2026-05-06 | T6 | medium | preflight `timeout-minutes: 5`; V27 says <30s | cold pip install ~60-90s dominates | `actions/cache@v4` on `/root/.cache/pip` keyed to `uv.lock` hash; V27 stands |
| B6 | x | 2026-05-06 | T6 | medium | build job `runs-on: ubuntu-latest`, not Alpine container | DinD requires host runner | amended V37: Docker-build job uses host runner; all other CI jobs use alpine container |
| B7 | x | 2026-05-06 | T6 | medium | issue #6 body contains `Invariants: V24,V27,V28,V37` | § notation leaked into human prose | rewrote #6 body to human prose; +V41 |
| B8 | x | 2026-05-06 | T1,T2 | low | ruff pinned in pre-commit, unpinned in dev-group → drift | no version-sync policy | `ruff==0.6.9` in dev-group + CI; matches pre-commit rev; +V42 |
| B9 | x | 2026-05-06 | T1 | low | `[tool.semantic_release]` v7 schema; PSR unpinned can pull v8 | unpinned PSR + v7 schema | pinned `python-semantic-release>=7,<8` in dev-group |
| B10 | x | 2026-05-06 | T3 | low | `uv sync` may install editable; runtime venv → `/build/src` | no `--no-editable` in builder | added `--no-editable` to Dockerfile `uv sync --no-dev` |
| B11 | x | 2026-05-06 | T3 | low | healthcheck `wget -qO-` relies on busybox wget in Alpine | implicit base-image dep | switch to `python -c "urllib.request.urlopen(...)"` |
| B12 | x | 2026-05-06 | T6 | low | `pr.yml:113` api-test step polls `/health` via `wget` in Alpine container — same busybox anti-pattern as B11 | B11 fix scoped to Compose only; CI script missed | replaced with `until python -c "urllib.request.urlopen(...)"` poll; +V43 |
| B13 | x | 2026-05-07 | T7 | low | `get_engine` calls `Base.metadata.create_all(engine)` — DDL side effect in factory function; not in T7 spec | scope creep: schema creation coupled to engine instantiation | move `create_all` to `init_db`; remove from `get_engine` |
| B14 | x | 2026-05-07 | T7 | — | reviewer claimed `get_session` commits on HTTPException (V7 violation) | FALSE POSITIVE: FastAPI yield-dep injection throws exception into generator; `except Exception` catches HTTPException → rollback fires correctly | no fix needed; recorded for precedent |
| B15 | . | 2026-05-07 | T7 | low | `upsert_museum`/`upsert_city` use SELECT-then-INSERT — TOCTOU race under concurrent ingest | no dialect-level atomic upsert | defer to PostgreSQL migration: SQLite serialises writes so no real race at MVP; dialect-specific `insert().on_conflict_do_update()` belongs in prod migration, not MVP db.py |
| B16 | x | 2026-05-07 | T7 | — | reviewer flagged `SessionDep` unused in `api.py` endpoints | NOT A BUG: T4 created stubs; T11 wires SessionDep into routes | no fix needed; T11 scope |
| B17 | x | 2026-05-07 | T8 | medium | `scraper.py:24` `httpx.get` has no `timeout=` — indefinite hang on slow Wikipedia | unbounded default timeout | add `timeout=10.0` to `httpx.get` call; +V45; also check T9 enricher when implemented |
| B18 | x | 2026-05-07 | T9 | medium | `_parse_results` signature `data: dict[str, object]` — V11 bans `object` in hints (same class as B4) | vacuous type on SPARQL response dict | narrow type or use `Any` (private fn, acceptable); cites V11 |
| B19 | x | 2026-05-07 | T9 | medium | `country` defaults to `""` when `countryLabel` absent — empty string is semantically null | `.get("countryLabel", {}).get("value", "")` fallback bypasses V2 | skip binding + log warning when country empty; add test for missing-country path |
| B20 | x | 2026-05-07 | T9 | low | Python-side dedup guard `if name not in found or population > found[name].population` is dead code — SPARQL already does `MAX(?pop) GROUP BY` | defensive code for impossible state = scope creep | remove guard; simple assignment sufficient |
| B21 | x | 2026-05-07 | T10 | low | `load_model()` not in T10 spec (T10 = `train` + `predict` + `InsufficientDataError`) | premature implementation of T11 "load model at startup" | resolved by T11: lifespan calls `load_model()` at startup |
| B22 | x | 2026-05-07 | T10 | medium | `predict()` raises bare `RuntimeError` when model absent — §I says `POST /predict` → 400 if model absent; API layer must catch specific exception | generic `RuntimeError` is fragile boundary; any other RuntimeError also triggers 400 | add `ModelNotLoadedError(RuntimeError)` alongside `InsufficientDataError`; T11 API layer catches by type |
| B23 | x | 2026-05-08 | T11 | low | `PredictResponse.predicted_visitors` lacks `Field(ge=0)` — §I says `predicted_visitors:int≥0` but OpenAPI schema shows bare `int` | Pydantic model omits constraint that §I declares | add `predicted_visitors: int = Field(ge=0)` to match §I |
| B24 | x | 2026-05-08 | T11 | low | `test_api_skeleton.py:31` `override_get_session` yields bare session — no commit/rollback/close lifecycle, bypasses V7 transaction wrapper | test fixture shortcuts V7 pattern | replicate try/commit/except rollback/finally close from `get_session`; will bite when T12/T14 add write-path tests |
| B25 | x | 2026-05-08 | T12 | medium | `pipeline.py:68-87` `run_train()` has no `session.rollback()` in either except branch — V7 requires rollback on error | `run_ingest` has rollback (line 59) but `run_train` omits it | add `session.rollback()` before status update in both except branches |
| B26 | x | 2026-05-08 | T12 | medium | `pipeline.py:26,34` `last_ingest_status()`/`last_train_status()` return bare `dict` — V11 bans unspecific return types; `db.py:140` `get_training_rows() -> list[Any]` same class | bare dict/Any returns (same class as B4/B18) | type as `dict[str, datetime \| str \| None]`; `get_training_rows` as `list[Row[tuple[int, int]]]` |
| B27 | x | 2026-05-08 | T12 | low | `GET /status` + `PipelineStatus` + `StatusReport` not in §I — undocumented EXTRA API surface | T12 added status endpoint without amending §I | amend §I to document `GET /status` route |
| B28 | x | 2026-05-08 | T13 | — | reviewer flagged `print()` in notebook as V10 violation | FALSE POSITIVE: V10 scoped to `src/museums/`; `print()` in Jupyter notebook is normal interactive output | no fix needed |
| B29 | x | 2026-05-08 | T13 | medium | `analysis.ipynb` accesses `regression._model.score(X, visitors)` — private attribute of regression module | no public `score()`/`r2()` API in regression.py; notebook couples to internal `_model` | add public helper or compute R² via `sklearn.metrics.r2_score` + `regression.predict` in notebook |
| B30 | x | 2026-05-08 | T13 | — | reviewer flagged `Path(__file__).parent.parent` in test_notebook.py as V39 violation | FALSE POSITIVE: V39 requires `Path(__file__).parent...` pattern — test uses exactly that (⊥ bare paths) | no fix needed |
| B31 | . | 2026-05-08 | T14 | low | `test_pipeline.py:131` `tmp_path: pytest.TempPathFactory` — wrong type annotation; `tmp_path` fixture returns `pathlib.Path`, not `TempPathFactory` | copy-paste error; pytest resolves by name so no runtime failure, but hint is misleading | change to `tmp_path: Path` + import `pathlib.Path` |
