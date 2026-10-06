# Facebook Fake Engagement Detection — Design Specification

**Date:** 2026-10-06  
**Status:** Proposed for implementation planning  
**Initial scope:** One Facebook Page managed by the operator

## 1. Purpose

Build a local-first system that collects authorized Facebook Page data through the Meta Graph API and identifies suspicious engagement patterns. The system produces explainable risk assessments; it does not claim that an account is fake or that a specific percentage of reactions is fraudulent.

The first version supports a Page that the operator manages. Analysis of third-party Pages is outside the MVP because public data does not provide the same Page Insights or user-level evidence.

## 2. Success Criteria

The MVP is successful when it can:

1. Run end-to-end with deterministic mock Graph API data.
2. Connect to one managed Page when a valid Page access token is available.
3. Collect Page, post, and engagement snapshots without duplicates.
4. Detect synthetic engagement spikes and explain the contributing signals.
5. Display posts, time-series evidence, data coverage, and review actions in Streamlit.
6. Continue operating safely when optional API fields are unavailable.
7. Keep tokens and secrets out of source control and application logs.
8. Pass automated unit, contract, integration, and synthetic-attack tests.

## 3. Non-Goals

The MVP will not:

- Crawl the Facebook website or replay private browser GraphQL requests.
- Bypass Meta permissions, rate limits, App Review, or Business Verification.
- Provide a definitive fake-account label.
- Promise an exact number of fraudulent likes without account-level evidence and validated ground truth.
- Analyze arbitrary competitor Pages as if the operator were their administrator.
- Use a graph neural network or deep-learning model before suitable labels and graph data exist.
- Support multiple tenants, cloud deployment, or billing.

## 4. Guiding Principles

### 4.1 Behavior over identity

Meta's public description of inauthentic-behavior enforcement emphasizes deceptive behavior and coordination. The system therefore evaluates observable patterns rather than judging a person's identity or viewpoint.

### 4.2 Evidence over verdicts

Every alert includes the data coverage, confidence, contributing signals, and time-series evidence. User-facing labels use terms such as `normal`, `watch`, `suspicious`, and `highly suspicious` rather than `fake`.

### 4.3 Dynamic baselines over global thresholds

Expected engagement differs by Page, post type, publication hour, day of week, post age, audience size, and paid promotion. The system learns rolling baselines for comparable posts instead of applying one universal reaction threshold.

### 4.4 Progressive capability

The detector must work at post level when only aggregate metrics are available. Account coordination analysis is enabled only when the authorized API response contains stable interaction identities and timestamps.

## 5. Architecture

```text
Meta Graph API or Mock Provider
              |
              v
       Collection Service
              |
              v
       SQLite Repository
              |
       +------+-------+
       |              |
       v              v
Feature Pipeline   Data Health
       |
       v
Detection Pipeline
       |
       +--> Temporal anomaly detector
       +--> Engagement-quality detector
       +--> Comment similarity detector
       +--> Coordination graph detector (conditional)
       |
       v
Evidence Fusion + Confidence
       |
       v
Streamlit Dashboard + Review Queue
```

### 5.1 Modules

- `config`: validates environment variables and non-secret defaults.
- `providers.base`: defines the data-provider protocol.
- `providers.meta`: calls the Meta Graph API, follows pagination, and normalizes responses.
- `providers.mock`: returns deterministic fixtures for development and tests.
- `storage`: owns the SQLite schema, migrations, and idempotent writes.
- `collector`: orchestrates incremental collection and checkpoints.
- `features`: computes comparable-post, temporal, ratio, text, and data-quality features.
- `detectors.temporal`: detects abnormal growth and change points.
- `detectors.quality`: evaluates reaction/comment/share and downstream-quality mismatches.
- `detectors.comments`: measures repetition and semantic diversity when comment text is authorized.
- `detectors.coordination`: builds and analyzes an account-post-time multiplex graph when possible.
- `fusion`: combines available evidence and calculates confidence without assuming all signal families exist.
- `reviews`: records human decisions and analyst notes.
- `dashboard`: presents Page health, posts, evidence, coordination, and review views.
- `cli`: exposes collection, analysis, database initialization, and demo commands.

Each module has one clear responsibility and communicates through typed domain models rather than raw Graph API dictionaries.

## 6. Configuration and Secrets

Runtime configuration is loaded from environment variables. A local `.env` is supported for development and is excluded from Git.

Required for live collection:

```dotenv
META_PAGE_ID=
META_PAGE_ACCESS_TOKEN=
META_GRAPH_API_VERSION=
DATABASE_URL=sqlite:///data/fake_like_detector.db
```

Optional values such as `META_APP_ID` may be used for diagnostics. `META_APP_SECRET` is not required by the collector unless a future token-exchange workflow explicitly needs it. The system must never print, persist in ordinary logs, or return access tokens through the dashboard.

The repository contains `.env.example` with empty values and `.gitignore` entries for `.env`, local databases, caches, and generated reports.

## 7. Data Acquisition

### 7.1 Provider contract

The provider returns normalized Page, post, metric-snapshot, comment, and optional interaction records. It also reports field-level availability so the detector can distinguish `zero` from `not provided`.

### 7.2 Live collection behavior

The Meta provider:

- Uses only documented Graph API endpoints and approved permissions.
- Requests fields from configuration rather than assuming every API version supports them.
- Follows cursor pagination.
- Retries transient failures with bounded exponential backoff and jitter.
- Honors rate-limit responses and does not busy-loop.
- Writes a snapshot only after a valid response is normalized.
- Stores the raw response with secrets removed for reproducibility and schema debugging.
- Records the Graph API version and field-availability metadata with every collection run.

### 7.3 Collection cadence

The initial CLI supports manual runs. A local scheduler may later execute the same idempotent command. During the first 24 hours of a post, the recommended cadence is more frequent than for older posts, but the MVP keeps cadence configurable rather than embedding a policy in code.

## 8. Data Model

### 8.1 Core tables

`pages`

- provider page ID
- name
- category
- first and last observed timestamps

`posts`

- provider post ID
- page ID
- post type
- message fingerprint
- publication timestamp
- paid-promotion indicator when available
- first and last observed timestamps

`post_snapshots`

- post ID
- collected timestamp
- reactions total and breakdown when available
- comments total
- shares total
- reach, impressions, clicks, video views, and watch metrics when available
- follower count at collection time when available
- field-availability mask
- collection-run ID

`comments`

- Page-scoped or privacy-preserving actor identifier when authorized
- post ID
- comment timestamp when available
- text or text fingerprint according to data-minimization settings
- parent-comment identifier when available

`interaction_events`

- privacy-preserving actor identifier
- post ID
- interaction type
- event timestamp when available
- source quality and field-availability metadata

This table is optional and remains empty when the API provides only aggregate counts.

`risk_assessments`

- post ID
- assessment timestamp
- risk level
- uncalibrated anomaly score
- confidence
- data coverage
- detector-version identifier
- serialized evidence list

`analyst_reviews`

- assessment ID
- label: `normal`, `paid`, `viral`, `suspicious`, or `unknown`
- optional note
- reviewed timestamp

`collection_runs`

- start and finish timestamps
- provider and API version
- status
- request counts
- redacted error summary
- checkpoint

### 8.2 Idempotency

Provider identifiers and observation timestamps form unique keys. Re-running a collection window updates equivalent normalized records or performs no write; it never creates duplicate snapshots.

## 9. Detection Method

### 9.1 Data sufficiency gate

Before scoring, the pipeline calculates:

- number of comparable historical posts
- number and spacing of snapshots
- available signal families
- percentage of expected fields present

When evidence is insufficient, the result is `insufficient_data` rather than a high-risk score.

### 9.2 Comparable-post baseline

Historical posts are grouped by features that materially affect engagement:

- media type
- paid versus organic status when known
- publication hour bucket
- day-of-week bucket
- post age at observation
- audience-size range

Robust median and median absolute deviation (MAD) are the initial estimators. The implementation must allow baseline strategies to be replaced without changing collectors or dashboard code.

### 9.3 Temporal anomaly detector

The detector derives deltas and rates from successive snapshots and evaluates:

- burst magnitude relative to comparable posts
- acceleration and abrupt change points
- unusually regular interaction intervals
- growth that stops immediately after a burst
- follower growth followed by rapid loss

The first implementation uses robust statistics and explicit change-point features. It does not claim a learned probability.

### 9.4 Engagement-quality detector

The detector measures context-normalized relationships such as:

- reactions to comments
- reactions to shares
- engagement to reach or impressions
- engagement to clicks, follows, video views, or watch time when available
- conversion quality before and after a burst

Missing denominators disable the affected feature instead of substituting zero.

### 9.5 Comment detector

When comment text is authorized, the detector measures:

- exact duplicate ratio
- normalized near-duplicate ratio
- semantic-cluster concentration
- lexical diversity
- generic-comment concentration
- mismatch between comments and post content

The MVP implements deterministic text normalization and similarity first. Embeddings are an optional extension behind an interface and must not be required for offline tests.

### 9.6 Coordination graph detector

This detector is conditional on account-level interactions. It creates a temporal multiplex network with separate layers for:

- synchronized interactions
- repeated co-engagement across posts
- similar or duplicated comments
- repeated amplification of the same content

Edges use time-aware decay and normalization so highly active accounts do not automatically appear coordinated. Leiden or Louvain community detection is sufficient for the first graph-enabled version. A graph neural network is deferred until labelled, representative data exists.

### 9.7 Evidence fusion

The MVP does not hard-code a permanent global formula such as `35/25/20/10/10`. It:

1. Normalizes available detector outputs onto a common anomaly scale.
2. Combines only signal families with sufficient coverage.
3. Reduces confidence when evidence families are missing or disagree.
4. Emits an ordered list of evidence and counter-evidence.
5. Maps the anomaly score to a risk level without presenting it as a fraud percentage.

Initial fusion parameters are configurable and versioned. After enough analyst reviews exist, a supervised calibration model such as logistic regression or gradient-boosted trees may learn fusion weights. Calibration must be evaluated before its output is called a probability.

## 10. Dashboard

### 10.1 Overview

- collection status and last successful run
- posts observed
- alerts by level
- data-coverage summary
- Page baseline maturity

### 10.2 Posts

- sortable list of posts
- risk level and confidence
- data coverage
- paid/organic/unknown status
- top evidence

### 10.3 Post detail

- cumulative and delta engagement charts
- comparable-post baseline band
- detected change points and bursts
- evidence and counter-evidence
- current analyst review

### 10.4 Coordination

Shown only when interaction-event data is available. It displays communities, strong edges, repeated synchronized actions, and the evidence behind each cluster. It does not label a cluster as malicious without review.

### 10.5 Data health

- configured provider mode: mock or live
- API version
- available and missing fields
- token validity status without revealing the token
- rate-limit and retry summary
- database and baseline health

### 10.6 Review queue

The operator can label alerts as `normal`, `paid`, `viral`, `suspicious`, or `unknown` and add notes. Reviews are never sent to Meta automatically.

## 11. Error Handling

- Invalid or expired token: stop live collection, retain existing data, and provide a safe remediation message.
- Permission denied: identify the missing field or endpoint without printing credentials.
- Rate limit: back off with jitter and checkpoint progress.
- Network failure: leave the current collection run failed or partial; do not write zero-valued snapshots.
- API field removal: mark the field unavailable and continue when core identifiers remain valid.
- Pagination interruption: checkpoint the cursor and resume safely.
- Duplicate payload: rely on unique constraints and idempotent upserts.
- Database error: roll back the affected transaction and keep the raw redacted response for diagnosis.
- Insufficient baseline: withhold strong risk labels.
- Detector error: isolate the failing detector and produce a lower-confidence assessment from remaining evidence.

## 12. Privacy, Security, and Responsible Use

- Use the minimum Meta permissions and fields required.
- Do not scrape Facebook HTML or private browser endpoints.
- Treat account identifiers as personal data; store Page-scoped identifiers only when authorized and necessary.
- Support hashing or pseudonymization at ingestion.
- Configure retention for raw comments and interaction events.
- Never expose access tokens, App Secrets, cookies, or authorization headers.
- Redact secrets from exceptions and raw-response fixtures.
- Do not publish accusations about individual accounts based on the detector.
- Require human review before an alert is used for external reporting or enforcement.

## 13. Testing Strategy

### 13.1 Unit tests

- configuration validation
- snapshot delta calculation
- robust baseline and MAD behavior
- missing-field handling
- temporal features and change-point evidence
- ratio features with zero and missing denominators
- text normalization and duplicate detection
- fusion, confidence, and risk-level mapping

### 13.2 Contract tests

Versioned JSON fixtures represent successful, paginated, permission-denied, rate-limited, missing-field, and malformed Graph API responses. Fixtures contain no real tokens or personal data.

### 13.3 Integration tests

- mock provider to SQLite to detector
- repeated collection is idempotent
- partial detector failure lowers confidence without losing all results
- dashboard repository queries return stable view models

### 13.4 Synthetic attacks

Generate controlled scenarios:

- organic growth
- legitimate viral post
- paid campaign
- sudden like burst
- slow stealthy inflation
- repeated duplicate comments
- synchronized account clusters
- missing-data and field-removal cases

Tests verify that attack evidence increases while legitimate viral and paid cases remain distinguishable through context and review metadata.

### 13.5 Evaluation

Until validated ground truth exists, report:

- precision at the top-k alerts after human review
- false-positive rate on reviewed normal, paid, and viral posts
- data coverage
- score stability across repeated runs
- alert stability across detector versions
- reviewer agreement

Recall and fraud percentages must not be reported without a defensible labelled population.

## 14. Delivery Phases

### Phase 1: Offline vertical slice

- project skeleton and configuration
- SQLite schema and migrations
- mock provider and fixtures
- collector and idempotent writes
- robust baseline and temporal/quality detectors
- evidence fusion
- CLI and Streamlit dashboard
- automated tests

### Phase 2: Authorized Meta integration

- live Meta provider
- pagination, retries, rate limits, and checkpoints
- field-availability audit against the managed Page
- token and permission diagnostics
- live-data validation without changing detection semantics

### Phase 3: Comment and coordination analysis

- comment-text features when authorized
- optional interaction-event ingestion
- temporal multiplex graph and community detection
- coordination evidence view

### Phase 4: Learning and calibration

- analyst review dataset
- supervised fusion experiment
- calibration and drift evaluation
- versioned promotion only when it outperforms the transparent baseline

Cloud deployment, multi-tenant OAuth, webhook infrastructure, and competitor-Page analysis require separate specifications.

## 15. Research Basis

The design reflects these established directions:

- Facebook CopyCatch: lockstep Page-Like detection using graph structure and edge timing.
- Facebook like-farm research: temporal, demographic, social, lexical, and non-lexical signals; limitations of simple graph co-clustering against stealthy farms.
- Unsupervised coordination networks: shared behavioral traces and account-similarity graphs.
- Temporal multiplex coordination: multiple behavioral layers with time-aware collaboration and decay.
- Commercial trust-and-safety practice: multi-signal analysis, network structure, engagement spikes, repeated content, geographic concentration, and explainable analyst evidence.

The project borrows the multi-signal and graph concepts but makes no claim of matching Meta's internal visibility or commercial proprietary datasets.

## 16. Key Decisions

1. Start with a managed Page and official Graph API data.
2. Build an offline mock-data vertical slice before depending on live credentials.
3. Use dynamic robust baselines instead of permanent fixed weights.
4. Separate post-level anomaly detection from account-level coordination detection.
5. Enable graph analysis only when authorized event identities exist.
6. Keep all assessments explainable and subject to human review.
7. Defer machine learning until review labels and representative data exist.

