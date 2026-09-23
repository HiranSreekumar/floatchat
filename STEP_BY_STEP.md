# FloatChat — Complete Step-by-Step Build & Deploy Guide

Stack: **Argovis** (real ARGO ocean data source) → **PostgreSQL** (data pipeline/storage)
→ **FastAPI** (backend, 2 Claude calls + deterministic SQL) → **React** (frontend).

Every file mentioned below is already written and included in `floatchat.zip`. This
guide walks through running it locally end-to-end, then deploying it as a real,
publicly reachable website. Nothing is skipped — follow it top to bottom.

---

## Part 0 — What you need before starting

| Requirement | Why | Get it |
|---|---|---|
| Python 3.11+ | Runs the FastAPI backend | https://www.python.org/downloads/ |
| Node.js 20+ and npm | Builds the React frontend | https://nodejs.org/ |
| PostgreSQL 14+ | Local database for the data pipeline | https://www.postgresql.org/download/ (or Docker, see Part 1B) |
| An Anthropic API key | Powers both Claude calls (NL→intent, results→explanation) | https://console.anthropic.com/ → **Settings → API Keys** |
| (Optional but recommended) Argovis API key | Higher rate limits when pulling real float data | https://argovis-keygen.colorado.edu/ (free, instant) |
| A GitHub account | To push your code for deployment | https://github.com |
| Git installed locally | To push to GitHub | https://git-scm.com/downloads |

You do **not** need a credit card or paid plan for anything in this guide — every
hosting step below uses a free tier.

---

## Part 1 — Get the project onto your machine

### 1A. Unzip and inspect

```bash
unzip floatchat.zip
cd floatchat
```

You should see:

```
floatchat/
  backend/
    app/               <- all Python source (see Part 2 for what each file does)
    requirements.txt
    .env.example
    Dockerfile
    render.yaml
  frontend/
    src/                <- all React source (see Part 3)
    index.html
    package.json
    .env.example
  docker-compose.yml
  README.md
  STEP_BY_STEP.md        <- this file
```

### 1B. Put this under Git (needed later for deployment)

```bash
git init
git add .
git commit -m "Initial FloatChat commit"
```

Create an empty repository on GitHub (github.com → New repository → don't
initialize with a README), then:

```bash
git remote add origin https://github.com/<your-username>/floatchat.git
git branch -M main
git push -u origin main
```

---

## Part 2 — Backend: understand and run it locally

### 2A. What each backend file does (nothing is a black box)

| File | Role |
|---|---|
| `app/config.py` | Loads all settings (API keys, DB URL) from environment variables |
| `app/db.py` | PostgreSQL schema (`profiles`, `measurements` tables) + connection helpers. **No LLM code here.** |
| `app/geo.py` | A gazetteer of ~25 Indian coastal reference points, used to ground Claude's geographic reasoning so it never invents coordinates for known places |
| `app/argovis_client.py` | Real HTTP client for `https://argovis-api.colorado.edu/profiles` — the actual Argovis ocean-data API |
| `app/demo_data.py` | Generates a realistic offline dataset (Arabian Sea vs. Bay of Bengal temperature/salinity structure, monsoon effects) so the app works even without a live Argovis pull |
| `app/ingest.py` | Command-line tool to pull **real** Argovis data into Postgres |
| `app/schemas.py` | Pydantic models — the exact shape of a "query intent" and API responses |
| `app/nl_parser.py` | **Claude call #1**: turns a question into a structured intent (location box, date range, variable). Never touches real data. |
| `app/sql_builder.py` | Deterministic, plain-Python: turns that intent into parameterized SQL and runs it. **No LLM here — same intent always produces the same SQL.** |
| `app/explainer.py` | **Claude call #2**: turns the real SQL results into a plain-English answer. Instructed to never state a number that isn't in the data. |
| `app/main.py` | FastAPI app — wires the 3 steps together behind `/api/chat` |

### 2B. Set up PostgreSQL locally

**Option A — Docker (easiest, recommended):**

```bash
docker compose up -d db
```

This starts Postgres in the background with database `floatchat`, user
`floatchat`, password `floatchat`, on port 5432 (matches `docker-compose.yml`).

**Option B — Postgres installed directly on your machine:**

```bash
# macOS (Homebrew)
brew install postgresql@16
brew services start postgresql@16
createdb floatchat

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
sudo -u postgres createdb floatchat
```

### 2C. Configure and install the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Open `.env` and fill it in:

```bash
ANTHROPIC_API_KEY=sk-ant-...your real key...
CLAUDE_MODEL=claude-sonnet-4-6

ARGOVIS_BASE_URL=https://argovis-api.colorado.edu
ARGOVIS_API_KEY=                # optional — leave blank to use Argovis unauthenticated (lower rate limit)

# If you used Docker Compose in 2B:
DATABASE_URL=postgresql://floatchat:floatchat@localhost:5432/floatchat
# If you used a local Postgres install with the postgres/postgres user instead:
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/floatchat

USE_LIVE_ARGOVIS=true
```

### 2D. Create the database schema and load data

```bash
# Still inside backend/, with venv activated and .env filled in:
python3 -c "from app.db import init_db; init_db()"
```

Now load data — pick ONE:

```bash
# Fastest: realistic offline demo dataset (no network call needed)
python3 -m app.demo_data

# OR real live data for one coastal region:
python3 -m app.ingest --region mumbai --start 2023-06-01 --end 2023-09-30

# OR real live data for every reference region, falling back to demo data
# if Argovis is unreachable:
python3 -m app.ingest --all-regions --start 2023-06-01 --end 2023-09-30 --fallback-demo
```

### 2E. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

Verify it's alive:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","profiles":888,"measurements":15096}
```

Verify the full pipeline (this is the step that calls Claude twice):

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What was the salinity off Mumbai last monsoon season?"}'
```

You should get back JSON containing `intent`, `sql`, `results`, and a plain-English
`explanation`. If you get a `502` with an authentication error, double check
`ANTHROPIC_API_KEY` in `.env`.

Leave this running — the frontend needs it.

---

## Part 3 — Frontend: understand and run it locally

### 3A. What each frontend file does

| File | Role |
|---|---|
| `src/api.js` | Fetch wrapper — talks to the backend's `/api/health` and `/api/chat` |
| `src/components/ChatPanel.jsx` | Chat message list, example-question buttons, input box |
| `src/components/QueryTrace.jsx` | The collapsible "show me the SQL" transparency panel |
| `src/components/MapView.jsx` | Live float-location map (react-leaflet) |
| `src/components/DepthChart.jsx` | Depth-vs-temperature chart (react-chartjs-2) |
| `src/App.jsx` | Wires chat + map + chart together, tracks selected float |
| `src/index.css` | The whole visual theme (dark oceanographic palette) |

### 3B. Install and configure

```bash
cd ../frontend      # from the backend/ directory, or `cd frontend` from project root
npm install
cp .env.example .env
```

`.env` should contain:

```
VITE_BACKEND_URL=http://localhost:8000
```

### 3C. Run it

```bash
npm run dev
```

Open the URL it prints (usually `http://localhost:5173`). You should see the
FloatChat UI, with the header showing "888 profiles loaded" (or however many
you ingested) once it reaches the backend. Try one of the example question
buttons.

### 3D. Confirm a production build works too (you'll need this for deployment)

```bash
npm run build
```

This outputs static files into `frontend/dist/`. If this command errors,
deployment will fail too — fix it here first.

---

## Part 4 — Deploy it as a real, public website

We'll deploy the **database + backend on Render** (free tier, handles Python +
Postgres well) and the **frontend on Vercel** (free tier, built for exactly
this kind of static React app). Both connect straight to your GitHub repo, so
every `git push` can redeploy automatically.

### 4A. Deploy the database + backend on Render

1. Go to https://render.com and sign up / log in (GitHub login is easiest).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub account if prompted, then select your `floatchat` repo.
4. Render will detect `backend/render.yaml` automatically and show you a plan:
   one **PostgreSQL database** (`floatchat-db`) and one **web service**
   (`floatchat-backend`). Click **Apply**.
5. Render will start building. While it builds, go to the `floatchat-backend`
   service → **Environment** tab and add the two secret values the blueprint
   left blank:
   - `ANTHROPIC_API_KEY` = your real Anthropic key
   - `ARGOVIS_API_KEY` = your Argovis key (or leave empty)
6. Wait for the deploy to finish (the dashboard shows build logs live). When
   it says **Live**, copy the service's URL — it looks like
   `https://floatchat-backend.onrender.com`.
7. Verify it:
   ```bash
   curl https://floatchat-backend.onrender.com/api/health
   ```
   You'll see `{"status":"ok","profiles":0,"measurements":0}` — the database
   is empty because it's a fresh Postgres instance.
8. Load data into the **production** database. Easiest way: use Render's
   **Shell** tab on the `floatchat-backend` service (it gives you a terminal
   inside the running container) and run:
   ```bash
   python3 -m app.demo_data
   # or for real data:
   python3 -m app.ingest --all-regions --start 2023-06-01 --end 2023-09-30 --fallback-demo
   ```
   Re-check `/api/health` — it should now show real counts.

> **Free-tier note:** Render's free web services spin down after 15 minutes of
> inactivity and take ~30-60 seconds to wake back up on the next request.
> That's fine for a demo; if you need it always-on, upgrade that one service
> to a paid instance type later (no code changes needed).

### 4B. Lock down CORS to your real frontend domain

Right now `backend/app/main.py` allows requests from any origin
(`allow_origins=["*"]`), which is fine for local testing but shouldn't stay
that way in production. Once you know your Vercel URL (next step gives it to
you), come back and update it:

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-app-name.vercel.app"],  # <- your real frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Commit and push this change — Render will auto-redeploy.

### 4C. Deploy the frontend on Vercel

1. Go to https://vercel.com and sign up / log in with GitHub.
2. Click **Add New...** → **Project**, and import your `floatchat` repo.
3. Vercel will ask for the project settings:
   - **Root Directory**: click "Edit" and set it to `frontend`
   - **Framework Preset**: Vercel auto-detects "Vite" — leave it
   - **Build Command**: `npm run build` (default, leave it)
   - **Output Directory**: `dist` (default, leave it)
4. Before deploying, expand **Environment Variables** and add:
   - `VITE_BACKEND_URL` = `https://floatchat-backend.onrender.com` (your
     Render URL from step 4A.6 — no trailing slash)
5. Click **Deploy**. Vercel builds and gives you a live URL like
   `https://floatchat-yourname.vercel.app`.
6. Open it. The header should show your Render backend's profile count. Ask
   it a question.

### 4D. Finish locking down CORS

Now that you have the real Vercel URL, go back and do Part 4B for real if you
skipped it — put your actual `https://floatchat-yourname.vercel.app` into
`allow_origins` in `backend/app/main.py`, commit, push. Render redeploys
automatically on every push to `main`.

### 4E. (Optional) Put a custom domain on it

**On Vercel (frontend):** Project → **Settings** → **Domains** → add your
domain (e.g. `floatchat.yourdomain.com`) → Vercel shows you a CNAME record →
add that record at your domain registrar (Namecheap, GoDaddy, Google
Domains, etc.) → wait a few minutes for DNS to propagate.

**On Render (backend, optional — most people leave the API on its
`onrender.com` URL):** Service → **Settings** → **Custom Domain** → same idea,
add the CNAME Render gives you at your registrar.

If you add a custom domain to the frontend, remember to also add it to
`allow_origins` in `main.py` (Part 4B) alongside the `.vercel.app` one, since
both will be live.

---

## Part 5 — Verify the live site end-to-end

Open your live frontend URL and check, in order:

1. **Header** shows "N profiles loaded" (not "unreachable") — confirms
   frontend ↔ backend ↔ Postgres are all connected.
2. **Ask an example question** (e.g. "SST off Mumbai, last monsoon") —
   confirms both Claude calls work in production (your `ANTHROPIC_API_KEY`
   is correctly set on Render).
3. **Map** populates with float markers — confirms `profile_locations` is
   flowing through.
4. **Depth chart** draws a line — confirms `depth_profiles` is flowing
   through. Click a marker on the map to swap the chart to that single float.
5. **Query trace** (the collapsible panel under the answer) shows a resolved
   location/time and real SQL — confirms the transparency layer works.
6. Ask something ambiguous like "temperature near the thing off the coast" —
   confirms Claude correctly asks for clarification instead of guessing.

If any step fails, check, in order: browser console (frontend errors), Render
service logs (backend errors), and that both `ANTHROPIC_API_KEY` and
`DATABASE_URL` are set correctly in Render's environment tab.

---

## Part 6 — Keeping the data fresh

The database is a point-in-time snapshot from whenever you last ran
`app.ingest` or `app.demo_data`. For a real deployment you'll want new float
profiles coming in regularly:

- Simplest: re-run `python3 -m app.ingest --all-regions --start <date> --end
  <date> --fallback-demo` from Render's Shell tab periodically.
- Better: set up a scheduled job. Render has a **Cron Jobs** service type —
  add one pointing at the same repo/`backend` root dir with the ingest
  command above as its command, on whatever schedule you like (e.g. daily).

---

## Troubleshooting quick reference

| Symptom | Likely cause | Fix |
|---|---|---|
| Frontend header says "unreachable" | Wrong `VITE_BACKEND_URL`, or CORS blocking the request | Check the env var in Vercel; check `allow_origins` in `main.py` includes your frontend's exact URL |
| `/api/chat` returns 502 with an authentication error | Bad/missing `ANTHROPIC_API_KEY` | Re-check the value in Render's Environment tab, redeploy |
| `/api/health` shows 0 profiles | Data was never loaded into that environment's database | Run `app.demo_data` or `app.ingest` in that environment (local shell or Render Shell) |
| Argovis ingestion fails with HTTP 400 | Query matched >1000 profiles | Narrow `--start`/`--end` or use `--region` instead of `--all-regions` for a bigger area |
| `npm run build` fails | A dependency issue or JSX syntax error | Read the error output — it names the exact file/line; rerun `npm install` if it's a missing-package error |
| Render free service is slow to respond the first time | Free tier spins down after inactivity | Normal — it wakes up in under a minute; upgrade the plan if you need always-on |
