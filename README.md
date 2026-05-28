# Private Credit Risk Watch v2

![Private Credit Risk Watch dashboard](docker/screen.png)

A real-time Python monitoring project for private-credit stress with a live web dashboard, WebSockets, PostgreSQL/TimescaleDB persistence, Redis pub/sub, token-protected replay controls, and alert sinks.

This version is designed to watch what actually matters instead of flattering the operator with vanity charts.

## What it does

- streams live risk states to a web dashboard
- stores snapshots in PostgreSQL / TimescaleDB-compatible schema
- distributes updates through Redis pub/sub
- supports token-protected historical replay mode
- sends alert events to console, Slack, WhatsApp Cloud API, or SMTP email
- marks structural danger zones directly on diagrams
- keeps the scoring model opinionated around liquidity mismatch and contagion

## Architecture

```mermaid
flowchart LR
    A[Fund disclosures / SEC filings] --> N[Normalization layer]
    B[Spread proxies / secondary discounts] --> N
    C[Analyst overrides / manual events] --> N
    D[News ingestion adapters] --> N
    N --> S[Scoring engine]
    S --> DB[(PostgreSQL / TimescaleDB)]
    S --> R[(Redis pub/sub)]
    R --> W[WebSocket broadcaster]
    W --> UI[FastAPI dashboard]
    S --> AL[Alert manager]
    AL --> E1[Slack]
    AL --> E2[WhatsApp]
    AL --> E3[SMTP email]
```

## Where danger lies

```mermaid
flowchart TD
    A[Redemptions rise] --> B[Gate / cap pressure]
    B --> C[Confidence damage]
    C --> D[Secondary discounts widen]
    D --> E[More redemption requests]
    E --> B
    F[Software / tech borrower weakness] --> G[Defaults / markdowns]
    G --> C
    H[Peer manager outflows] --> C
```

## Dashboard diagrams

The UI includes three visual layers:

1. **Danger diagram**  
   Marks the reflexive loop where confidence, discounts, and sector weakness feed one another.

2. **Radar chart**  
   Shows the five main failure surfaces:
   - liquidity mismatch
   - contagion
   - sector damage
   - market stress
   - oversight heat

3. **Trigger ladder**  
   Marks each threshold where normal stress becomes structural danger.

## Project layout

```text
private_credit_risk_watch_v2/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── scoring.py
│   ├── engine.py
│   ├── datasource.py
│   ├── routers/
│   │   └── api.py
│   ├── services/
│   │   ├── alerts.py
│   │   ├── auth.py
│   │   ├── database.py
│   │   └── pubsub.py
│   ├── static/
│   │   └── dashboard.js
│   └── templates/
│       └── index.html
├── docker/
│   └── init.sql
├── tests/
│   ├── test_api.py
│   └── test_scoring.py
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Run locally without Docker

### 1. Create environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start supporting services

You need PostgreSQL and Redis if you want the full stack. For quick local development you can stay on SQLite by leaving defaults in place.

### 3. Launch app

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Run full stack with Docker

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8000
```

Auth token for replay mode defaults to:

```text
dev-token
```

Inside Docker it is set in `docker-compose.yml` as:

```text
changeme-super-long-token
```

## Replay mode

Replay mode is token-protected. Paste your bearer token into the dashboard and press **Start replay**.

It replays stored snapshots from the database at accelerated speed so you can see how the system behaves under historical stress instead of staring at a frozen dashboard like a tourist.

## Replace the mock feed

The weak point is obvious and intentional: `app/datasource.py` is still mocked.

That is where you plug in:

- SEC filing parsers
- fund factsheet scrapers
- BDC discount feeds
- spread and financing proxies
- curated news event ingestion
- internal analyst overrides

## Why this is built this way

Because the real problem is not drawing charts. The real problem is catching the moment when an illiquid book is being sold as a liquid experience and the marginal seller has decided the story is over.


## WhatsApp setup

The WhatsApp sink uses Meta's WhatsApp Cloud API, not Twilio.

Set:

```env
PCRW_WHATSAPP_ACCESS_TOKEN=...
PCRW_WHATSAPP_PHONE_NUMBER_ID=...
PCRW_WHATSAPP_TO_NUMBER=49123...
```

Use the recipient number in international format without a leading `+` when following WhatsApp Cloud API conventions.
