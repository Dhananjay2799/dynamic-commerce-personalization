# Dynamic E-Commerce Personalization Engine

A full-stack, real-time e-commerce personalization system that learns from a shopper's current browsing behavior and re-ranks products during the active session.

The project combines a production-style Next.js storefront, FastAPI serving layer, PostgreSQL durable event storage, Redis online session state, and a classical machine-learning recommendation pipeline trained on real e-commerce behavior data.

The system is intentionally designed without an LLM recommendation dependency. Product ranking is driven by implicit behavioral feedback, temporal session intent, popularity priors, and latent product representations learned with Truncated SVD.

---

## Results at a Glance

### Recommendation Quality

Using a leakage-aware latest-item temporal holdout:

| Metric | Popularity Baseline | SVD | Improvement |
|---|---:|---:|---:|
| Recall@10 | 0.0840 | **0.1156** | **+37.6%** |
| NDCG@10 | 0.0463 | **0.0693** | **+49.6%** |
| MRR@10 | 0.0348 | **0.0551** | **+58.1%** |
| Coverage@10 | 0.00115 | **0.02560** | **22.2x** |

Evaluation used 9,971 eligible users with a latest-distinct-item holdout.

Full metrics are stored in:

```text
ml/results/svd-v1-metrics.json
```

### Online Serving Performance

Local benchmark:

```text
Model:              session-svd-v3
Strategy:           session_intent
Warm-up requests:   20
Measured requests:  500
Recommendations:    10 per request
```

| Measurement | Median | p95 | p99 | Maximum |
|---|---:|---:|---:|---:|
| Model inference | **1.705 ms** | **2.809 ms** | **4.198 ms** | 8.072 ms |
| Server total | **13.205 ms** | **21.653 ms** | **30.478 ms** | 38.393 ms |
| Client-observed HTTP | **23.448 ms** | **44.355 ms** | **51.572 ms** | 61.394 ms |

The benchmark was executed against the local FastAPI service on a Windows development machine.

These measurements are development-environment results, not production SLA claims.

The reproducible benchmark output is stored in:

```text
benchmark-results/recommendations-local.json
```

### Automated Validation

```text
56 automated tests passing

15  intent-engine tests
14  recommendation-model tests
17  telemetry/API contract tests
 5  category-context tests
 5  PostgreSQL + Redis integration tests
```

The integration suite exercises the real Docker-backed PostgreSQL and Redis services.

---

# What the System Does

A shopper opens the storefront and begins browsing.

The application records behavioral signals including:

```text
product impression
product click
product detail view
dwell time
scroll depth
search
add to cart
remove from cart
```

Those events are sent to FastAPI.

FastAPI persists the event to PostgreSQL and updates the shopper's short-lived online state in Redis.

The recommendation engine then converts recent behavioral signals into a weighted session-intent representation and combines that state with pretrained SVD product factors.

Recommendations are re-ranked during the same browsing session.

This creates a feedback loop:

```text
shopper behavior
      ↓
telemetry
      ↓
session intent
      ↓
recommendation ranking
      ↓
new shopper behavior
```

---

# Architecture

```mermaid
flowchart LR
    A["Next.js Storefront"] --> B["FastAPI API"]

    A -->|"Behavioral telemetry"| B

    B --> C["PostgreSQL"]
    B --> D["Redis Session State"]
    B --> E["In-Memory SVD Recommender"]

    D --> E
    E --> B
    B --> A

    F["E-Commerce Behavior CSV"] --> G["Polars Data Preparation"]

    G --> H["Processed Parquet Data"]

    H --> I["PostgreSQL Catalog Seeder"]
    I --> C

    H --> J["Offline SVD Training"]

    J --> K["Model Artifacts"]
    K --> E
```

The architecture deliberately separates the offline and online paths.

### Offline path

```text
behavior dataset
      ↓
Polars preprocessing
      ↓
Parquet
      ↓
implicit interaction matrix
      ↓
Truncated SVD
      ↓
product latent factors
      ↓
model artifacts
```

### Online path

```text
browser interaction
      ↓
FastAPI telemetry endpoint
      ↓
PostgreSQL durable event
      +
Redis session state
      ↓
weighted session vector
      ↓
SVD candidate scoring
      ↓
product hydration
      ↓
personalized storefront
```

---

# Technology Stack

## Frontend

| Technology | Purpose |
|---|---|
| Next.js 16.3.3 | Application framework |
| React 19 | UI |
| TypeScript | Type safety |
| Tailwind CSS 4 | Styling |
| TanStack Query | Server-state management |
| Framer Motion | UI motion |
| Lucide React | Icons |

## Backend

| Technology | Purpose |
|---|---|
| FastAPI | HTTP API |
| Python | Backend and ML runtime |
| SQLAlchemy 2 | ORM / database access |
| asyncpg | Async PostgreSQL driver |
| Alembic | Schema migrations |
| Pydantic | API validation |
| Redis | Online session state |

## Data and Machine Learning

| Technology | Purpose |
|---|---|
| Polars | Large-scale CSV/Parquet processing |
| NumPy | Numerical computation |
| SciPy | Sparse matrices |
| scikit-learn | Truncated SVD |
| joblib | Model persistence |

## Infrastructure

| Technology | Purpose |
|---|---|
| PostgreSQL 17 | Catalog and durable telemetry |
| Redis 8 | Low-latency session state |
| Docker Compose | Local infrastructure |

---

# Dataset

The recommendation system uses the Kaggle dataset:

```text
E-Commerce Behavior Data from Multi-Category Store

Dataset identifier:
mkechinov/ecommerce-behavior-data-from-multi-category-store
```

The current experiment uses:

```text
2019-Oct.csv
```

The raw source contains behavioral and catalog-related fields including:

```text
event_time
event_type
product_id
category_id
category_code
brand
price
user_id
user_session
```

The original October CSV is approximately 5.67 GB.

For development and assessment reproducibility, the preparation pipeline uses a deterministic approximately 2% user sample.

### Processed Sample

```text
Events:              837,746
Users:                60,023
Sessions:            182,743
Observed products:    66,607
Catalog products:     23,435
Database categories:     525

Views:               804,301
Cart events:          18,719
Purchases:            14,726
```

Products require at least five sampled interactions to enter the serving catalog.

---

# Data Authenticity and Presentation Metadata

The behavioral dataset provides real:

```text
user behavior
session IDs
product IDs
category IDs
category hierarchy
brands
prices
timestamps
```

It does **not** provide a polished commerce catalog containing human-authored product titles, product descriptions, product photography, or inventory counts.

The project therefore keeps recommendation behavior grounded in the source data while generating deterministic display metadata where necessary.

Product names are generated from available brand/category information and the source product ID.

Example:

```text
Apple Headphone #4804056
```

Inventory is generated deterministically from the product ID solely to support storefront presentation.

Images are not fabricated from unrelated external product sources. The current UI instead uses minimalist product presentation and generated visual identity.

This distinction is intentional so that synthetic presentation metadata is never presented as part of the original behavioral dataset.

---

# Data Preparation

The preparation pipeline is implemented in:

```text
scripts/prepare_dataset.py
```

It performs deterministic user sampling and creates ML-ready Parquet files.

Default sampling configuration:

```text
sample_modulus       100
sample_buckets       2
min_product_events   5
```

This corresponds to an approximately 2% deterministic user sample.

Generated outputs:

```text
events.parquet
catalog.parquet
category_stats.parquet
```

---

# Recommendation Model

The offline recommender uses implicit-feedback Truncated SVD.

Behavioral signals are converted to interaction strengths:

```text
view       = 1
cart       = 3
purchase   = 5
```

Aggregated interaction strength is transformed with:

```text
log1p(strength)
```

and stored in a sparse user-product matrix.

The model is trained with:

```text
64 latent dimensions
randomized Truncated SVD
seed = 42
```

The resulting product factors are saved for low-latency online inference.

Artifacts include:

```text
ml/artifacts/product_ids.npy
ml/artifacts/item_factors.npy
ml/artifacts/item_embeddings.npy
ml/artifacts/popularity_scores.npy
ml/artifacts/svd_model.joblib
ml/artifacts/metrics.json
```

Binary model artifacts are intentionally excluded from Git because they can be regenerated from the preparation and training pipelines.

---

# Evaluation Methodology

The project does not evaluate recommendations by randomly splitting individual rows.

Instead, it uses a latest-distinct-item temporal holdout.

For each eligible user:

```text
earlier interactions
        ↓
training history

latest distinct product
        ↓
evaluation target
```

The held-out product is removed from that user's training history.

This reduces leakage from allowing the model to train on the same user-product pair later used as the evaluation target.

The evaluation compares:

```text
Popularity baseline

vs.

Truncated SVD
```

using:

```text
Recall@10
HitRate@10
NDCG@10
MRR@10
Coverage@10
```

The SVD model improves both ranking quality and catalog coverage over the popularity baseline.

---

# Online Session Personalization

Offline collaborative filtering captures historical structure between products.

The online serving layer adds current-session intent.

The serving policy is versioned as:

```text
session-svd-v3
```

The offline SVD metrics are stored under the training artifact version:

```text
svd-v1
```

These versions describe different layers:

```text
svd-v1
    offline latent-factor training/evaluation

session-svd-v3
    online session-aware serving strategy
```

---

# Session Intent Model

Behavioral events receive different strengths based on their meaning.

| Event | Base Intent Weight |
|---|---:|
| `view_item` | 1.0 |
| `product_click` | 1.5 |
| `add_to_cart` | 4.0 |
| `remove_from_cart` | -2.0 |
| `purchase` | 6.0 |
| `product_impression` | 0 |
| `search` | 0 |

Dwell time produces a dynamic positive signal capped at:

```text
2.5
```

Scroll depth contributes up to:

```text
1.5
```

Recent behavioral signals receive more influence using event-recency decay:

```text
0.92 ^ events_from_end
```

Zero-weight analytics events such as product impressions do not advance the behavioral recency clock.

That distinction prevents rendering activity from accidentally weakening genuine shopper intent.

---

# Example: Cart Intent

A clean session was manually and automatically verified with the following transition:

```text
initial intent       0.00

add_to_cart
      ↓
intent               4.00

remove_from_cart
      ↓
intent               1.68
```

Why does removing the item not return intent to zero?

The previous cart signal first receives recency decay:

```text
4.00 × 0.92 = 3.68
```

Then the removal contributes:

```text
-2.00
```

Result:

```text
3.68 - 2.00 = 1.68
```

Removing an item therefore reduces commercial intent without pretending that the shopper never expressed interest in it.

---

# Online SVD Scoring

For active product signals, the serving layer constructs a session representation from pretrained raw SVD item factors.

Conceptually:

```text
session_factor =
    Σ log1p(product_intent_weight)
      × item_factor
```

Candidate products are scored against that session factor.

Latent scores are normalized and blended with a small popularity prior:

```text
final_score =
    0.95 × latent_score
    +
    0.05 × popularity_score
```

This provides a small amount of popularity stabilization while allowing session intent to drive ranking.

Products already represented in the active positive-intent state are excluded from recommendation candidates.

---

# Cold Start

A session with no meaningful behavioral intent cannot yet construct a personalized latent vector.

The recommender therefore falls back to:

```text
popularity
```

As soon as meaningful product interaction arrives, serving switches to:

```text
session_intent
```

This gives the system deterministic cold-start behavior without inventing user preferences.

---

# Example Personalization Behavior

For a session with strong intent toward:

```text
Apple Headphone #4804056
```

the personalized model returned:

```text
1. Apple Headphone #4802036
2. Apple Headphone #4804572
```

before broader smartphone and electronics recommendations.

The original interacted product was excluded from the recommendation set.

This behavior is protected by automated regression tests.

---

# Telemetry Architecture

Supported event types include:

```text
product_impression
view_item
product_click
dwell_time
scroll_depth
add_to_cart
remove_from_cart
purchase
category_view
search
```

The storefront currently emits the events required for browsing, search, product engagement, and cart personalization.

`purchase` remains part of the event contract for a future checkout flow.

A real payment implementation is intentionally outside the scope of this personalization assessment.

---

# PostgreSQL vs Redis Responsibilities

The system intentionally gives PostgreSQL and Redis different responsibilities.

## PostgreSQL

PostgreSQL is the durable system of record.

It stores:

```text
products
categories
interaction events
```

Telemetry is committed to PostgreSQL before online personalization state is considered successful.

## Redis

Redis maintains short-lived online session behavior.

It is optimized for:

```text
low-latency event retrieval
session intent reconstruction
real-time re-ranking
```

The API degrades differently depending on which dependency fails.

### PostgreSQL failure

```text
event cannot be durably stored
        ↓
request rejected
        ↓
HTTP 503
```

### Redis failure

```text
event successfully stored in PostgreSQL
        ↓
online state update fails
        ↓
event remains accepted
        ↓
online_state_updated = false
```

This prevents a transient personalization-cache failure from destroying durable behavioral data.

The behavior is covered by automated tests.

---

# Product Impression Design

Recommendation and catalog product cards use visibility-based impression tracking.

An impression fires when a product is sufficiently visible for a minimum period instead of firing immediately when React renders the component.

Impressions are:

```text
stored as telemetry
zero-weight for personalization
excluded from behavioral recency decay
```

This prevents the recommendation engine from learning from its own rendering activity.

For a production system, analytics-only events and online feature-state events would typically use separate Redis structures so very large numbers of impressions cannot crowd behavioral events out of a bounded session history.

---

# Search

The product API supports server-side search.

Example:

```text
GET /api/v1/products?search=apple
```

Search telemetry records the query and surface but does not directly create product intent.

A shopper must interact with a search result before that product becomes part of the product-intent representation.

This prevents a text query alone from being treated as equivalent to product engagement.

---

# API

## Health

```text
GET /health
```

Reports:

```text
API
PostgreSQL
Redis
```

health.

## Products

```text
GET /api/v1/products
GET /api/v1/products/{product_id}
```

Product listing supports filtering and search.

## Categories

```text
GET /api/v1/categories
```

## Telemetry

```text
POST /api/v1/events
```

Example payload:

```json
{
  "session_id": "browser-session-id",
  "event_type": "add_to_cart",
  "product_id": 4804056,
  "category_id": 2053013554658804075,
  "metadata": {
    "surface": "storefront"
  }
}
```

Successful response includes:

```json
{
  "accepted": true,
  "persisted": true,
  "online_state_updated": true
}
```

## Session Intent

```text
GET /api/v1/sessions/{session_id}/intent
```

Returns the current active product signals used by the online recommender.

## Recommendations

```text
GET /api/v1/recommendations?session_id={session_id}&limit=10
```

Response metadata includes:

```text
strategy
model_version
inference_ms
total_ms
```

---


# Category-Aware Session Context

Product interactions and category browsing are modeled as separate but complementary online signals.

Selecting a top-level category emits a `category_view` event with the active `category_l1` value in telemetry metadata.

The `session-svd-v3` serving policy reads the latest explicit category context from Redis-backed session events.

Category context does not alter product-intent weights and does not advance the product-intent recency clock.

Instead, the active category constrains the recommendation candidate pool. The pretrained SVD factors and current session-intent vector still determine ranking order inside that category.

Selecting `All` emits a clearing `category_view` event with `category = null` and `cleared = true`. This removes the category constraint and restores the global session-aware candidate pool.

Live end-to-end validation confirmed:

```text
category_view persisted to PostgreSQL
category_view updated Redis session state
category switching changed recommendation ranking
returned recommendations matched the selected category
serving remained in session_intent mode
clearing category context restored the original SVD ranking
```

---

# Storefront

The frontend is designed as a polished commerce experience rather than a dashboard placed in front of a recommendation API.

It includes:

```text
responsive product discovery
top-level category filtering
server-side search
paginated catalog browsing
personalized recommendation rail
product detail drawer
session-local cart
live bag count
behavioral telemetry
intent-driven re-ranking
product loading skeletons
recommendation loading skeletons
catalog empty state
recommendation empty state
catalog error + retry state
recommendation error + retry state
responsive desktop and mobile layouts
```

For technical review, append:

```text
?debug=true
```

to the storefront route.

The Intent Inspector exposes the active recommendation strategy, model version, current product signals, and model inference timing.

---

# Repository Structure

```text
dynamic-commerce-personalization/
│
├── apps/
│   └── web/
│       ├── public/
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── lib/
│       │   └── types/
│       └── package.json
│
├── services/
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── core/
│       │   ├── db/
│       │   ├── models/
│       │   ├── recommendations/
│       │   ├── schemas/
│       │   └── telemetry/
│       ├── migrations/
│       ├── tests/
│       ├── alembic.ini
│       ├── pytest.ini
│       └── requirements.txt
│
├── ml/
│   ├── artifacts/
│   ├── results/
│   ├── src/
│   │   └── train_recommender.py
│   └── requirements.txt
│
├── scripts/
│   ├── prepare_dataset.py
│   └── benchmark_recommendations.py
│
├── benchmark-results/
│   └── recommendations-local.json
│
├── data/
├── .env.example
├── docker-compose.yml
└── README.md
```

---

# Local Setup

The following walkthrough uses Windows PowerShell.

## 1. Clone the repository

```powershell
git clone <repository>
cd dynamic-commerce-personalization
```

## 2. Create the Python environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
pip install -r .\services\api\requirements.txt
```

Install ML dependencies:

```powershell
pip install -r .\ml\requirements.txt
```

Install the test runner:

```powershell
pip install pytest
```

## 3. Configure environment variables

Copy the backend template:

```powershell
Copy-Item .\.env.example .\.env -Force
```

Default development configuration:

```dotenv
APP_NAME=Dynamic Commerce Personalization API
ENVIRONMENT=development

DATABASE_URL=postgresql+asyncpg://personalization:personalization_dev@localhost:5432/personalization
REDIS_URL=redis://localhost:6379/0

FRONTEND_URL=http://localhost:3000
```

## 4. Install frontend dependencies

```powershell
cd .\apps\web
npm ci
Copy-Item .\.env.example .\.env -Force
cd ..\..
```

Frontend configuration:

```dotenv
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## 5. Start PostgreSQL and Redis

```powershell
docker compose up -d
```

Verify:

```powershell
docker compose ps
```

The Compose stack starts:

```text
personalization-postgres
personalization-redis
```

with persistent Docker volumes and health checks.

## 6. Obtain the dataset

Create a local raw-data directory:

```powershell
New-Item .\data\raw -ItemType Directory -Force
```

The dataset identifier is:

```text
mkechinov/ecommerce-behavior-data-from-multi-category-store
```

The project uses:

```text
2019-Oct.csv
```

Place that CSV at:

```text
data/raw/2019-Oct.csv
```

The data directory is excluded from Git.

## 7. Prepare the deterministic sample

From the repository root:

```powershell
python .\scripts\prepare_dataset.py `
  --input .\data\raw\2019-Oct.csv `
  --output-dir .\data\processed `
  --sample-modulus 100 `
  --sample-buckets 2 `
  --min-product-events 5
```

Expected generated files:

```text
data/processed/events.parquet
data/processed/catalog.parquet
data/processed/category_stats.parquet
```

## 8. Apply database migrations

```powershell
cd .\services\api
```

Run:

```powershell
alembic upgrade head
```

Verify:

```powershell
alembic current
```

The current migration head for this repository is:

```text
437db3ada2e3
```

## 9. Seed the serving catalog

Still inside:

```text
services/api
```

run:

```powershell
python -m app.db.seed_catalog `
  --catalog ..\..\data\processed\catalog.parquet `
  --category-stats ..\..\data\processed\category_stats.parquet `
  --replace
```

The loader:

```text
reads processed Parquet data
builds category metadata
builds deterministic storefront metadata
upserts categories
upserts products
```

Return to the project root:

```powershell
cd ..\..
```

## 10. Train the recommendation model

```powershell
python .\ml\src\train_recommender.py `
  --events .\data\processed\events.parquet `
  --catalog .\data\processed\catalog.parquet `
  --artifacts-dir .\ml\artifacts `
  --components 64 `
  --top-k 10 `
  --max-eval-users 10000 `
  --batch-size 256 `
  --seed 42
```

This regenerates the model artifacts required by the FastAPI recommender.

## 11. Start FastAPI

Open a PowerShell terminal:

```powershell
cd .\services\api
```

Run:

```powershell
python -m uvicorn app.main:app `
  --host 127.0.0.1 `
  --port 8000
```

The API should now be available on port:

```text
8000
```

Verify from another terminal:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
```

Expected status:

```text
healthy
```

with PostgreSQL and Redis also healthy.

## 12. Start the storefront

Open another terminal:

```powershell
cd .\apps\web
npm run dev
```

Open the storefront on port:

```text
3000
```

For the engineering/debug view, add:

```text
?debug=true
```

to the page route.

---

# Testing

## Fast unit and API contract suite

From:

```text
services/api
```

run:

```powershell
python -m pytest .\tests -m "not integration" -v
```

Current validated result:

```text
51 passed
5 deselected
```

## Real infrastructure integration tests

PostgreSQL and Redis must be running:

```powershell
docker compose up -d
```

Then from:

```text
services/api
```

run:

```powershell
python -m pytest `
  -m integration `
  .\tests\test_runtime_integration.py `
  -v
```

Current validated result:

```text
5 passed
```

## Full backend suite

```powershell
python -m pytest .\tests -v
```

Current validated result:

```text
56 passed
```

The test suite covers:

```text
event validation
telemetry response contracts
PostgreSQL failure behavior
Redis degradation behavior
intent weights
recency behavior
zero-weight impression handling
dwell-time bounds
scroll-depth bounds
category-context selection and replacement
category-context clearing
category-constrained candidate ranking
cold-start ranking
personalized ranking
candidate uniqueness
score ordering
catalog-valid IDs
seen-product exclusion
deterministic recommendation output
real PostgreSQL writes
real Redis state
real add/remove intent behavior
real recommendation serving
```

---

# Frontend Validation

From:

```text
apps/web
```

run:

```powershell
npm run lint
```

Then:

```powershell
npm run build
```

Both should complete before submitting or deploying the assessment.

---

# Performance Benchmark

Start FastAPI without development reload mode:

```powershell
cd .\services\api

python -m uvicorn app.main:app `
  --host 127.0.0.1 `
  --port 8000
```

From the repository root in a second terminal:

```powershell
python .\scripts\benchmark_recommendations.py `
  --warmups 20 `
  --iterations 500 `
  --limit 10
```

The benchmark:

```text
creates a fresh session
writes an add_to_cart event
verifies session_intent mode
measures the first request in the measured benchmark sequence
executes 20 warm-up requests
executes 500 measured requests
calculates median, p95, and p99 latency
writes a JSON result
```

Output:

```text
benchmark-results/recommendations-local.json
```

---

# Engineering Decisions

## Why SVD instead of an LLM recommender?

This project is fundamentally an implicit-feedback ranking problem.

The useful information is:

```text
which products users interacted with
how strongly they interacted
which products co-occur in behavior
what the current session is signaling
```

A latent-factor model is therefore:

```text
deterministic
fast
inexpensive
measurable
easy to evaluate offline
appropriate for in-memory serving
```

An LLM would add cost and latency without solving the core collaborative-filtering problem more directly.

LLMs could be complementary in a production system for semantic search, query understanding, explanation generation, or catalog enrichment, but they are not required for this ranking path.

## Why Redis?

Session personalization is latency-sensitive and ephemeral.

Redis provides a better fit than repeatedly reconstructing active session state from the durable event table.

PostgreSQL remains authoritative; Redis is the online feature-state layer.

## Why PostgreSQL?

Products, categories, and telemetry require durable, queryable relational storage.

PostgreSQL also gives the project clear transaction semantics for event persistence.

## Why Polars?

The source CSV is multi-gigabyte.

Polars provides efficient columnar data processing and Parquet generation without introducing distributed-processing infrastructure that is unnecessary for this assessment-sized sample.

## Why not Kafka?

Kafka would make sense in a larger production architecture where:

```text
multiple downstream consumers
stream processing
feature pipelines
analytics
fraud systems
experimentation
real-time model updates
```

all consume the same behavioral stream.

For this assessment, introducing Kafka would add operational complexity without improving the core end-to-end demonstration.

The current telemetry service therefore writes directly to PostgreSQL and Redis.

A production evolution could place an event broker between ingestion and downstream consumers.

## Why not Kubernetes?

The local system contains:

```text
one frontend
one API
PostgreSQL
Redis
```

Docker Compose is sufficient for reproducible local infrastructure.

Kubernetes would be appropriate when the system needs independent scaling, multi-instance deployments, service discovery, rolling releases, autoscaling, and production orchestration.

Adding Kubernetes only for technology-name coverage would not improve this assessment.

---

# Current Scope Boundaries

This project focuses on personalization rather than implementing every component of a complete commerce business.

Intentionally excluded:

```text
real payment processing
user authentication
shipping
tax calculation
order fulfillment
production distributed event streaming
online model retraining
A/B experimentation infrastructure
```

The cart is session-local and exists primarily to produce meaningful commercial-intent signals.

The `purchase` event is already represented in the telemetry schema so the recommendation system can integrate with a future checkout/order service.

---

# Production Evolution

A production version could evolve toward:

```text
browser / mobile clients
        ↓
API gateway
        ↓
telemetry ingestion
        ↓
event broker
        ↓
stream processing
        ↓
online feature store
        ↓
recommendation service
        ↓
experimentation layer
```

Potential extensions include:

```text
Kafka or Redpanda event streaming
dedicated online feature store
candidate-generation service
two-stage retrieval and ranking
ANN/vector retrieval
real-time feature aggregation
model registry
scheduled retraining
A/B testing
observability
rate limiting
multi-region serving
Kubernetes deployment
cloud object storage
CI/CD
```

These are deliberately documented as production extensions rather than presented as technologies already implemented in the repository.

---

# Reviewer Walkthrough

A fast technical review can follow this sequence.

### 1. Open the storefront

Verify:

```text
responsive product catalog
recommendation rail
search
product detail interactions
cart
```

### 2. Enable the Intent Inspector

Use:

```text
?debug=true
```

### 3. Open a product

Observe:

```text
product_click
view_item
scroll_depth
dwell_time
```

signals.

### 4. Add a product to the cart

Observe the active product-intent weight increase.

For an isolated cart event:

```text
add_to_cart → 4.0
```

### 5. Remove the product

Observe the intent decrease.

Validated isolated example:

```text
4.0 → 1.68
```

### 6. Watch recommendations change

The strategy should report:

```text
session_intent
```

and recommendations should respond to current-session behavior.

### 7. Switch category context

Select a top-level category such as ppliances.

The recommendation strategy should remain session_intent, while returned recommendations adapt to products in the active category.

### 8. Clear category context

Select All.

The storefront emits a category-context clearing event and the recommendation service returns to the global session-aware candidate pool.

### 9. Review ML evidence

Inspect:

```text
ml/results/svd-v1-metrics.json
```

### 10. Review serving benchmark

Inspect:

```text
benchmark-results/recommendations-local.json
```

### 11. Run automated tests

```powershell
cd .\services\api
python -m pytest .\tests -v
```

Expected:

```text
56 passed
```

---

# Key Takeaways

This project demonstrates more than a recommendation algorithm in a notebook.

It connects:

```text
large behavioral data processing
implicit-feedback machine learning
leakage-aware evaluation
real-time session features
low-latency model inference
durable telemetry
online state management
async API engineering
responsive frontend development
automated regression testing
real infrastructure integration testing
performance benchmarking
```

into one working personalization system.

The core engineering goal is to show how an offline recommendation model becomes an online product experience with measurable quality, latency, state management, and failure semantics.
