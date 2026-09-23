# FloatChat — Conversational Interface for India's ARGO Ocean Data

Ask plain-English questions about subsurface ocean conditions ("What was the
salinity off Mumbai last monsoon season?") and get back real ARGO float
measurements — not an LLM's guess at what the ocean is probably like.

**For the full step-by-step setup and deployment walkthrough, see [STEP_BY_STEP.md](./STEP_BY_STEP.md).**

## Stack

- **Data source**: [Argovis API](https://argovis.colorado.edu) (real ARGO float profiles)
- **Data pipeline / storage**: PostgreSQL
- **Backend**: FastAPI (Python)
- **Frontend**: React (Vite)
- **LLM**: Claude — used twice per query (NL → structured intent, and results → explanation)

## How it works (and why it doesn't hallucinate data)

```
 User question
      |
      v
 [Claude call #1 — nl_parser.py]   Resolves the question into a structured,
      |                            typed intent: a lat/lon bounding box, a
      |                            date range, a variable (temp/salinity),
      |                            and a metric (profile/avg/min/max/count).
      |                            Claude NEVER sees or answers with real
      |                            ocean data here. If a location is too
      |                            ambiguous, it asks for clarification
      |                            instead of guessing.
      v
 [sql_builder.py — pure Python]    Deterministically turns that structured
      |                            intent into parameterized SQL and runs it
      |                            against PostgreSQL. No LLM involved. Same
      |                            intent -> same SQL -> same results, every
      |                            time. Shown to the user as a query trace.
      v
 [Claude call #2 — explainer.py]   Takes the ACTUAL rows/aggregates that came
      |                            back from Postgres and writes a grounded,
      |                            plain-English explanation. Instructed to
      |                            never state a number that isn't in the
      |                            provided data.
      v
 Natural-language answer + map + depth-profile chart + visible query trace
```

## Project layout

```
backend/
  app/
    main.py          FastAPI app — wires the 3-step pipeline together
    nl_parser.py      Claude call #1: question -> structured QueryIntent
    sql_builder.py    Deterministic intent -> SQL -> PostgreSQL execution
    explainer.py      Claude call #2: real results -> grounded explanation
    argovis_client.py Real HTTP client for the Argovis /profiles API
    ingest.py         CLI to pull real Argovis data into Postgres
    demo_data.py      Generates the offline realistic demo dataset
    geo.py            Gazetteer grounding geographic reasoning
    db.py             PostgreSQL schema (profiles, measurements)
    schemas.py        Pydantic models
    config.py         Env-based configuration
  requirements.txt
  Dockerfile
  render.yaml         Render blueprint (backend + managed Postgres)
  .env.example
frontend/
  src/
    App.jsx            Wires chat + map + chart together
    api.js              Backend API client
    components/
      ChatPanel.jsx      Chat UI + example questions
      QueryTrace.jsx     Collapsible parsed-intent + SQL panel
      MapView.jsx        Live float-location map (react-leaflet)
      DepthChart.jsx     Depth-vs-temperature chart (react-chartjs-2)
    index.css           Visual theme
  package.json
  .env.example
docker-compose.yml       One-command local Postgres + backend
STEP_BY_STEP.md          Full setup + deployment walkthrough
```

## Quick start

See **STEP_BY_STEP.md** for the complete walkthrough (local setup through live
deployment). Short version for local dev:

```bash
# Database
docker compose up -d db

# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY
python3 -c "from app.db import init_db; init_db()"
python3 -m app.demo_data
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Notes on scope: real vs. illustrative

- **Real**: the Argovis API client, the Postgres schema and SQL query
  builder, the FastAPI pipeline, both Claude prompts, and the full React
  frontend.
- **Illustrative fallback**: `demo_data.py` generates synthetic profiles
  shaped like real North Indian Ocean structure (warm mixed layer, sharp
  thermocline, Arabian Sea's high salinity vs. Bay of Bengal's river-driven
  freshening, monsoon mixed-layer shoaling) so the app is reliably demoable
  without a live Argovis pull. Every row from it is tagged `is_synthetic`,
  surfaced as a "Demo data" badge in the UI, and called out briefly in
  Claude's explanation.
- Argovis constrains `/profiles` queries to under ~1000 results per
  date-range/region combination — `ingest.py` chunks by region for this
  reason.
