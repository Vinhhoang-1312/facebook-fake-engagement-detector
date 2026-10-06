# Facebook Fake Engagement MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python application that collects authorized Facebook Page engagement data, stores snapshots, detects explainable anomalies, and presents them in a Streamlit review dashboard.

**Architecture:** A provider interface separates deterministic mock data from the live Meta Graph API. Both providers feed an idempotent SQLite repository; focused feature and detector modules create evidence that a fusion service turns into risk levels and confidence. A Typer CLI drives collection and analysis, while Streamlit reads stable dashboard view models.

**Tech Stack:** Python 3.11, Pydantic 2, pydantic-settings, HTTPX, SQLAlchemy 2, Alembic, Typer, NumPy, pandas, Plotly, Streamlit, pytest, pytest-cov, respx, Ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-10-06-facebook-fake-engagement-detection-design.md`

## Global Constraints

- MVP supports exactly one managed Facebook Page.
- Use only documented Meta Graph API endpoints and authorized permissions; do not crawl Facebook HTML or browser GraphQL calls.
- Python version floor is 3.11.
- Store runtime secrets only in environment variables or a local ignored `.env`.
- Never log or display access tokens, App Secrets, cookies, or authorization headers.
- A missing API field is `None`/unavailable, never numeric zero.
- Risk scores represent anomaly, not fraud probability or fake-account percentage.
- Strong risk labels require sufficient baseline data; otherwise return `insufficient_data`.
- Account-level coordination is not implemented in this MVP, but the schema preserves optional interaction events for a future plan.
- Every alert includes evidence, confidence, and data coverage.
- Tests must not use real credentials or personal data.

## Review Focus

- A metric that is absent versus explicitly zero must remain distinguishable through ingestion, storage, features, and dashboard rendering; pinned in Tasks 2 and 7.
- Duplicate and out-of-order snapshots must not create duplicate rows or negative growth evidence; pinned in Tasks 2 and 3.
- Tokens embedded in request failures must be redacted from exceptions, logs, and persisted collection errors; pinned in Task 8.
- Pagination followed by a transient rate limit must retry the same cursor once and then continue without duplicate writes; pinned in Task 8.
- Paid or legitimately viral fixtures and immature baselines must not receive strong suspicious labels; pinned in Tasks 5 and 6.

---

## File Structure

```text
pyproject.toml                         packaging, dependencies, tool configuration
.env.example                          documented environment variables without values
.gitignore                            secrets, databases, caches, reports
README.md                             setup, commands, safety language
alembic.ini                           database migration configuration
migrations/env.py                     SQLAlchemy/Alembic integration
migrations/versions/0001_initial.py  initial schema
src/fake_like_detector/
  __init__.py
  config.py                           validated configuration
  domain.py                           provider-neutral immutable domain models
  security.py                         secret redaction
  providers/base.py                   provider protocol and provider errors
  providers/mock.py                   deterministic offline provider
  providers/meta.py                   documented Graph API client
  storage/db.py                       engine/session creation
  storage/models.py                   SQLAlchemy persistence models
  storage/repository.py               idempotent persistence and queries
  collection.py                       collection orchestration and checkpoints
  features/baseline.py                comparable-post grouping and robust baselines
  features/temporal.py                deltas, rates, bursts, out-of-order handling
  features/quality.py                 ratio and downstream-quality features
  detection/types.py                  evidence and assessment models
  detection/temporal.py               temporal detector
  detection/quality.py                engagement-quality detector
  detection/fusion.py                 evidence fusion, confidence, risk level
  detection/service.py                end-to-end post assessment
  dashboard/queries.py                stable dashboard view models
  dashboard/app.py                    Streamlit UI
  cli.py                              init-db, collect, analyze, demo commands
tests/
  fixtures/meta/*.json                redacted API fixtures
  test_config.py
  test_repository.py
  test_collection.py
  test_baseline.py
  test_temporal_features.py
  test_quality_features.py
  test_detectors.py
  test_fusion.py
  test_dashboard_queries.py
  test_meta_provider.py
  test_cli_integration.py
```

## Task 1: Project Foundation and Safe Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `src/fake_like_detector/__init__.py`
- Create: `src/fake_like_detector/config.py`
- Create: `src/fake_like_detector/security.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: none.
- Produces: `Settings(provider: Literal["mock", "meta"], database_url: str, meta_page_id: str | None, meta_page_access_token: SecretStr | None, meta_graph_api_version: str | None)`; `Settings.validate_live() -> None`; `redact_secrets(text: str, secrets: Iterable[str]) -> str`.

- [ ] **Step 1: Initialize source control**

Run `git init` in the project root and verify `git status --short` succeeds.

- [ ] **Step 2: Write failing configuration and redaction tests**

Add tests named `test_mock_settings_need_no_token`, `test_meta_settings_require_page_id_token_and_version`, and `test_redaction_removes_bearer_query_and_raw_token`. Assert that Meta validation names missing variables without echoing values.

- [ ] **Step 3: Verify the tests fail**

Run: `python -m pytest tests/test_config.py -v`  
Expected: FAIL because `fake_like_detector.config` and `security` do not exist.

- [ ] **Step 4: Add packaging and minimal implementations**

Configure the `src` layout, Python 3.11 floor, runtime/test dependencies, Ruff, mypy, pytest, and a project-wide coverage floor of 85%. Implement the exact interfaces above with Pydantic settings and conservative redaction for bearer headers, `access_token` query parameters, and known raw secrets.

- [ ] **Step 5: Install the editable development package**

Run: `python -m pip install -e ".[dev]"`  
Expected: installation exits 0 and `python -c "import fake_like_detector"` exits 0.

- [ ] **Step 6: Add secret-safe repository defaults and setup documentation**

Ignore `.env`, `*.db`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `__pycache__`, coverage files, and generated reports. Document mock-mode setup first; list live variables without values.

- [ ] **Step 7: Verify foundation quality**

Run: `python -m pytest tests/test_config.py -v && python -m ruff check . && python -m mypy src`  
Expected: all commands exit 0.

- [ ] **Step 8: Commit**

Run: `git add pyproject.toml .gitignore .env.example README.md src tests/test_config.py && git commit -m "chore: establish safe project foundation"`.

## Task 2: Domain Models and Idempotent SQLite Repository

**Files:**
- Create: `src/fake_like_detector/domain.py`
- Create: `src/fake_like_detector/storage/db.py`
- Create: `src/fake_like_detector/storage/models.py`
- Create: `src/fake_like_detector/storage/repository.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_initial.py`
- Test: `tests/test_repository.py`

**Interfaces:**
- Consumes: `Settings.database_url` from Task 1.
- Produces: immutable `PageRecord`, `PostRecord`, `MetricSnapshot`, `CommentRecord`, `InteractionEvent`, `CollectionRun`, `RiskAssessment`, and `AnalystReview`; `create_engine_and_session(database_url: str) -> tuple[Engine, sessionmaker[Session]]`; `Repository.upsert_page(page: PageRecord) -> None`; `Repository.upsert_post(post: PostRecord) -> None`; `Repository.add_snapshot(snapshot: MetricSnapshot) -> bool`; `Repository.snapshots_for_post(post_id: str) -> list[MetricSnapshot]`; `Repository.save_collection_run(run: CollectionRun) -> None`; `Repository.save_assessment(assessment: RiskAssessment) -> None`; `Repository.save_review(review: AnalystReview) -> None`.

- [ ] **Step 1: Write failing repository tests**

Cover round-tripping a snapshot with `reactions=0` and `shares=None`, rejecting a second identical `(post_id, collected_at)` snapshot, accepting an older unique snapshot, preserving field-availability metadata, and rolling back a failed transaction.

- [ ] **Step 2: Verify the tests fail**

Run: `python -m pytest tests/test_repository.py -v`  
Expected: FAIL because domain and storage modules do not exist.

- [ ] **Step 3: Implement provider-neutral domain models**

Use timezone-aware UTC datetimes, optional metrics, frozen Pydantic models, and explicit availability sets. Interaction identities are optional privacy-preserving strings.

- [ ] **Step 4: Implement schema, migration, and repository**

Create tables from spec sections 8.1–8.2. Enforce unique snapshot and review keys in the database. Repository methods accept/return domain types and own transaction boundaries.

- [ ] **Step 5: Verify storage behavior**

Run: `python -m alembic upgrade head && python -m pytest tests/test_repository.py -v`  
Expected: migration succeeds and all tests pass.

- [ ] **Step 6: Commit**

Run: `git add src/fake_like_detector/domain.py src/fake_like_detector/storage alembic.ini migrations tests/test_repository.py && git commit -m "feat: add engagement snapshot repository"`.

## Task 3: Mock Provider and Collection Orchestration

**Files:**
- Create: `src/fake_like_detector/providers/base.py`
- Create: `src/fake_like_detector/providers/mock.py`
- Create: `src/fake_like_detector/collection.py`
- Create: `tests/fixtures/mock/organic.json`
- Create: `tests/fixtures/mock/burst.json`
- Test: `tests/test_collection.py`

**Interfaces:**
- Consumes: domain records and `Repository` from Task 2.
- Produces: `PageDataProvider.fetch_page(page_id: str) -> PageRecord`; `PageDataProvider.iter_posts(page_id: str, since: datetime | None) -> Iterator[PostRecord]`; `PageDataProvider.fetch_snapshot(post_id: str, collected_at: datetime) -> MetricSnapshot`; `collect_page(provider: PageDataProvider, repository: Repository, page_id: str, collected_at: datetime) -> CollectionSummary`.

- [ ] **Step 1: Write failing collection tests**

Test deterministic fixture collection, repeated-run idempotency, out-of-order fixture ingestion, provider failure producing a failed collection run without zero snapshots, and collection summary counts.

- [ ] **Step 2: Verify the tests fail**

Run: `python -m pytest tests/test_collection.py -v`  
Expected: FAIL because provider and collector modules do not exist.

- [ ] **Step 3: Implement provider protocol and typed provider errors**

Define `ProviderAuthenticationError`, `ProviderPermissionError`, `ProviderRateLimitError(retry_after_seconds: float | None)`, `ProviderTransientError`, and `ProviderSchemaError` without embedding credentials.

- [ ] **Step 4: Implement deterministic mock provider**

Load versioned JSON fixtures, normalize them into domain records, and make timestamps injectable so tests never depend on wall-clock time.

- [ ] **Step 5: Implement idempotent collection orchestration**

Create one collection-run record per attempt, persist valid records transactionally, and never synthesize zero metrics after a provider failure.

- [ ] **Step 6: Verify collection behavior**

Run: `python -m pytest tests/test_collection.py tests/test_repository.py -v`  
Expected: all tests pass.

- [ ] **Step 7: Commit**

Run: `git add src/fake_like_detector/providers src/fake_like_detector/collection.py tests/fixtures/mock tests/test_collection.py && git commit -m "feat: collect deterministic engagement snapshots"`.

## Task 4: Comparable Baselines and Feature Pipeline

**Files:**
- Create: `src/fake_like_detector/features/baseline.py`
- Create: `src/fake_like_detector/features/temporal.py`
- Create: `src/fake_like_detector/features/quality.py`
- Test: `tests/test_baseline.py`
- Test: `tests/test_temporal_features.py`
- Test: `tests/test_quality_features.py`

**Interfaces:**
- Consumes: `PostRecord` and ordered `MetricSnapshot` values from Task 2.
- Produces: `ComparableKey(media_type: str, paid_status: str, hour_bucket: int, weekday: int, audience_bucket: str)`; `RobustBaseline(count: int, median: float, mad: float)`; `build_baseline(values: Sequence[float], minimum_count: int = 8) -> RobustBaseline | None`; `compute_temporal_features(snapshots: Sequence[MetricSnapshot], baseline: RobustBaseline | None) -> TemporalFeatures`; `compute_quality_features(snapshot: MetricSnapshot) -> QualityFeatures`.

- [ ] **Step 1: Write failing feature tests**

Assert MAD behavior with a large outlier, `None` baseline below eight comparable values, chronological sorting of out-of-order snapshots, no negative growth evidence after counter corrections, burst-rate calculation, `None` ratios for missing denominators, and valid zero-valued ratios for explicit zeros.

- [ ] **Step 2: Verify the tests fail**

Run: `python -m pytest tests/test_baseline.py tests/test_temporal_features.py tests/test_quality_features.py -v`  
Expected: FAIL because feature modules do not exist.

- [ ] **Step 3: Implement robust baseline functions**

Use NumPy median and MAD with deterministic audience buckets and the exact minimum count of eight.

- [ ] **Step 4: Implement temporal and quality features**

Sort snapshots by UTC time, flag counter corrections separately, calculate deltas/rates only over positive elapsed durations, and preserve unavailable features as `None`.

- [ ] **Step 5: Verify the feature pipeline**

Run: `python -m pytest tests/test_baseline.py tests/test_temporal_features.py tests/test_quality_features.py -v`  
Expected: all tests pass.

- [ ] **Step 6: Commit**

Run: `git add src/fake_like_detector/features tests/test_baseline.py tests/test_temporal_features.py tests/test_quality_features.py && git commit -m "feat: compute robust engagement features"`.

## Task 5: Explainable Detectors and Data-Sufficiency Gates

**Files:**
- Create: `src/fake_like_detector/detection/types.py`
- Create: `src/fake_like_detector/detection/temporal.py`
- Create: `src/fake_like_detector/detection/quality.py`
- Test: `tests/test_detectors.py`

**Interfaces:**
- Consumes: `TemporalFeatures`, `QualityFeatures`, and baseline maturity from Task 4.
- Produces: `Evidence(code: str, severity: float, message: str, observed: float | None, expected: float | None, coverage: float)`; `DetectorResult(name: str, anomaly: float, coverage: float, evidence: tuple[Evidence, ...], counter_evidence: tuple[Evidence, ...])`; `TemporalDetector.evaluate(features: TemporalFeatures) -> DetectorResult`; `QualityDetector.evaluate(features: QualityFeatures) -> DetectorResult`; `check_data_sufficiency(comparable_count: int, snapshot_count: int, coverage: float) -> SufficiencyResult`.

- [ ] **Step 1: Write failing detector tests**

Cover organic, burst, slow-inflation, counter-correction, missing-metric, paid-campaign, legitimate-viral, and fewer-than-eight-comparable-post scenarios. Assert that immature baselines return insufficient data and that paid/viral context produces counter-evidence instead of an automatic strong alert.

- [ ] **Step 2: Verify the tests fail**

Run: `python -m pytest tests/test_detectors.py -v`  
Expected: FAIL because detector modules do not exist.

- [ ] **Step 3: Implement sufficiency and temporal detector**

Keep anomaly values on `[0.0, 1.0]`; emit stable evidence codes for burst magnitude, acceleration, abrupt stop, counter correction, and missing history.

- [ ] **Step 4: Implement quality detector**

Evaluate only available ratios, normalize against comparable baselines when present, and emit counter-evidence for healthy downstream conversion or declared paid promotion.

- [ ] **Step 5: Verify detector behavior**

Run: `python -m pytest tests/test_detectors.py -v`  
Expected: all tests pass.

- [ ] **Step 6: Commit**

Run: `git add src/fake_like_detector/detection tests/test_detectors.py && git commit -m "feat: add explainable anomaly detectors"`.

## Task 6: Evidence Fusion and End-to-End Assessment

**Files:**
- Create: `src/fake_like_detector/detection/fusion.py`
- Create: `src/fake_like_detector/detection/service.py`
- Test: `tests/test_fusion.py`

**Interfaces:**
- Consumes: `DetectorResult` values from Task 5 and repository snapshots from Task 2.
- Produces: `fuse_results(results: Sequence[DetectorResult], sufficiency: SufficiencyResult, detector_version: str) -> RiskAssessment`; `AssessmentService.assess_post(post_id: str, assessed_at: datetime) -> RiskAssessment`.

- [ ] **Step 1: Write failing fusion tests**

Assert: unavailable detectors are excluded rather than treated as zero; disagreement lowers confidence; all-low-coverage input returns `insufficient_data`; burst plus quality mismatch reaches at least `suspicious`; paid/viral fixtures remain below `suspicious`; evidence is sorted by contribution; repeated identical inputs produce byte-stable serialized evidence.

- [ ] **Step 2: Verify the tests fail**

Run: `python -m pytest tests/test_fusion.py -v`  
Expected: FAIL because fusion and service modules do not exist.

- [ ] **Step 3: Implement configurable evidence fusion**

Use versioned configuration, coverage-normalized weighted averaging, disagreement penalty, and confidence derived from coverage, sufficiency, and agreement. Keep risk labels `normal`, `watch`, `suspicious`, `highly_suspicious`, and `insufficient_data`.

- [ ] **Step 4: Implement assessment orchestration**

Load post context and snapshots, build comparable baselines, compute features, run detectors, fuse results, persist the assessment, and return the persisted domain model.

- [ ] **Step 5: Verify end-to-end assessment**

Run: `python -m pytest tests/test_fusion.py tests/test_detectors.py -v`  
Expected: all tests pass.

- [ ] **Step 6: Commit**

Run: `git add src/fake_like_detector/detection tests/test_fusion.py && git commit -m "feat: fuse evidence into explainable assessments"`.

## Task 7: Dashboard Queries, Review Queue, and Streamlit UI

**Files:**
- Create: `src/fake_like_detector/dashboard/queries.py`
- Create: `src/fake_like_detector/dashboard/app.py`
- Test: `tests/test_dashboard_queries.py`

**Interfaces:**
- Consumes: repository records and assessments from Tasks 2 and 6.
- Produces: `DashboardRepository.overview() -> OverviewView`; `DashboardRepository.posts() -> list[PostSummaryView]`; `DashboardRepository.post_detail(post_id: str) -> PostDetailView`; `DashboardRepository.data_health() -> DataHealthView`; `DashboardRepository.save_review(assessment_id: int, label: ReviewLabel, note: str | None, reviewed_at: datetime) -> None`; Streamlit entry point `main() -> None`.

- [ ] **Step 1: Write failing dashboard-query tests**

Assert deterministic ordering, explicit display of unavailable metrics as `Not available`, explicit zero as `0`, evidence/counter-evidence visibility, data-health field coverage, and review persistence without any network request.

- [ ] **Step 2: Verify the tests fail**

Run: `python -m pytest tests/test_dashboard_queries.py -v`  
Expected: FAIL because dashboard modules do not exist.

- [ ] **Step 3: Implement typed dashboard queries**

Keep Streamlit out of repository/query tests. Return view models that contain display-safe values and no secrets.

- [ ] **Step 4: Implement Streamlit pages**

Build Overview, Posts, Post Detail, Data Health, and Review Queue. Show the Coordination page only as a disabled explanation that account-level data is unavailable in the MVP; do not render fake graph results.

- [ ] **Step 5: Verify dashboard code**

Run: `python -m pytest tests/test_dashboard_queries.py -v && python -m streamlit run src/fake_like_detector/dashboard/app.py --server.headless true`  
Expected: tests pass and Streamlit starts without a traceback; terminate the local process after the health check.

- [ ] **Step 6: Commit**

Run: `git add src/fake_like_detector/dashboard tests/test_dashboard_queries.py && git commit -m "feat: add engagement review dashboard"`.

## Task 8: Live Meta Graph API Provider

**Files:**
- Create: `src/fake_like_detector/providers/meta.py`
- Create: `tests/fixtures/meta/page.json`
- Create: `tests/fixtures/meta/posts_page_1.json`
- Create: `tests/fixtures/meta/posts_page_2.json`
- Create: `tests/fixtures/meta/snapshot_missing_fields.json`
- Create: `tests/fixtures/meta/error_permission.json`
- Create: `tests/fixtures/meta/error_rate_limit.json`
- Test: `tests/test_meta_provider.py`

**Interfaces:**
- Consumes: `PageDataProvider` and provider errors from Task 3, `Settings` and redaction from Task 1.
- Produces: `MetaGraphProvider(client: httpx.Client, page_id: str, access_token: SecretStr, api_version: str, max_retries: int = 3)` implementing the provider contract; `MetaGraphProvider.audit_fields() -> FieldAvailabilityReport`.

- [ ] **Step 1: Write failing HTTP contract tests**

Use respx fixtures to assert correct versioned URLs, bearer authorization, two-page cursor pagination, field normalization, missing-versus-zero preservation, permission-error mapping, retry/backoff on transient rate limits, and token redaction from raised errors.

- [ ] **Step 2: Add the pagination-plus-rate-limit regression test**

Return page 1, rate-limit the first request to page 2, then return page 2. Assert one retry of the same cursor, no skipped post, no duplicate post, and no token in captured logs.

- [ ] **Step 3: Verify the tests fail**

Run: `python -m pytest tests/test_meta_provider.py -v`  
Expected: FAIL because `MetaGraphProvider` does not exist.

- [ ] **Step 4: Implement the Meta provider**

Use documented endpoints selected after the field audit, bearer authorization, bounded exponential backoff with injectable sleep, cursor pagination, strict normalization, and safe typed errors. Do not silently fall back to scraping or browser calls.

- [ ] **Step 5: Implement field availability audit**

Probe the configured Page with the same documented client, report accessible/missing/denied fields, and redact secrets from all diagnostics.

- [ ] **Step 6: Verify provider contracts**

Run: `python -m pytest tests/test_meta_provider.py -v`  
Expected: all tests pass without network access.

- [ ] **Step 7: Commit**

Run: `git add src/fake_like_detector/providers/meta.py tests/fixtures/meta tests/test_meta_provider.py && git commit -m "feat: integrate authorized Meta Graph API data"`.

## Task 9: CLI, Vertical-Slice Verification, and Operator Documentation

**Files:**
- Create: `src/fake_like_detector/cli.py`
- Modify: `README.md`
- Test: `tests/test_cli_integration.py`

**Interfaces:**
- Consumes: settings, providers, repository, collection service, assessment service, and dashboard entry point from prior tasks.
- Produces commands: `init-db`; `audit-fields`; `collect --at ISO_DATETIME`; `analyze`; `demo`; `serve`.

- [ ] **Step 1: Write failing CLI integration tests**

Use Typer's test runner and a temporary SQLite database. Assert `demo` initializes schema, collects fixtures twice without duplicates, produces organic and burst assessments, and never prints a token. Assert live commands fail safely when Meta variables are incomplete.

- [ ] **Step 2: Verify the tests fail**

Run: `python -m pytest tests/test_cli_integration.py -v`  
Expected: FAIL because CLI commands do not exist.

- [ ] **Step 3: Implement CLI commands**

Resolve provider selection from `Settings`, reuse the same services as tests/dashboard, return non-zero exit codes for safe configuration/provider failures, and keep command output secret-free.

- [ ] **Step 4: Complete operator documentation**

Document Python setup, mock demo, live field audit, collection, analysis, Streamlit startup, token rotation, known limits, responsible-use language, and the distinction between anomaly risk and fake-account percentage.

- [ ] **Step 5: Run the complete test and quality suite**

Run: `python -m pytest --cov=src/fake_like_detector --cov-report=term-missing && python -m ruff check . && python -m mypy src`  
Expected: all tests pass with at least 85% total coverage, no lint/type errors, and no uncovered critical path in configuration, storage, collection, features, detection, Meta normalization, or CLI orchestration.

- [ ] **Step 6: Run the offline acceptance flow**

Run: `python -m fake_like_detector.cli demo` followed by `python -m fake_like_detector.cli analyze`.  
Expected: a populated local database, an organic result below `suspicious`, a synthetic burst at or above `suspicious`, evidence and confidence printed, and no secrets in output.

- [ ] **Step 7: Run the live field audit only when credentials are present**

Run: `python -m fake_like_detector.cli audit-fields`.  
Expected: accessible, unavailable, and denied fields are listed without revealing the token. If Page access is not yet available, record this verification as pending rather than weakening tests or inserting fake credentials.

- [ ] **Step 8: Commit**

Run: `git add src/fake_like_detector/cli.py README.md tests/test_cli_integration.py && git commit -m "feat: deliver fake engagement MVP workflow"`.

## Final Verification

- [ ] Run `git status --short` and confirm only intentional artifacts remain.
- [ ] Run the full test, coverage, lint, and type-check commands from Task 9.
- [ ] Start Streamlit and verify Overview, Posts, Post Detail, Data Health, and Review Queue with mock data.
- [ ] Search tracked files for credential-like values with `rg -n "access_token=|Bearer |META_PAGE_ACCESS_TOKEN=.+|META_APP_SECRET=.+" .` and confirm only examples/tests with redacted placeholders are present.
- [ ] Compare delivered files and behavior against every Success Criterion and Non-Goal in the spec.
- [ ] Perform a whole-branch code review before handing off.
