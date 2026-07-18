# AppPulse Analytics

A working app-store intelligence dashboard: it tracks apps you add from the
Apple App Store and Google Play, polls public data sources on a schedule,
and shows download **estimates** with an honest confidence score — never a
fake-precise number presented as fact.

**Deploying this?** See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for step-by-step
Netlify (frontend) + Render (backend) instructions.

## A note on the frontend's Next.js version

The frontend runs Next.js 16.2.7 / React 19.2.0. This isn't an arbitrary
choice: Next.js coordinated a security release in May 2026 covering 13
CVEs (denial-of-service, SSRF, middleware/auth bypass) in the React Server
Components stack, and **the 13.x/14.x release lines have no patch** -
upgrading to 15.5.18+ or 16.2.6+ is the only fix. If you fork this and see
a dependency bot flag `next`, check whether a newer patch has shipped
before downgrading.

## What's real here

- **Apple App Store** (primary): metadata, ratings, review counts, price,
  version via Apple's official free iTunes Lookup API
  (`backend/app/scrapers/apple.py`). Apple's official top-charts RSS feed
  is also wired up for future ranking features.
- **Google Play** (primary): metadata, ratings, review counts, and install
  *buckets* (e.g. "1,000,000+") via the actively-maintained
  [`google-play-scraper`](https://pypi.org/project/google-play-scraper/)
  library, with a second, independent raw-HTML reader as a built-in
  fallback if the library itself fails (`backend/app/scrapers/google_play.py`).
- **AppBrain** (fallback / enrichment): an independent third party
  (appbrain.com) that crawls Google Play and computes its own rank and
  rating figures - not derived from the same page read as the primary
  source. Used both to fill gaps when the primary source fails and to
  cross-check rank as a second opinion (`backend/app/scrapers/appbrain.py`).
- **Wikipedia** (fallback / enrichment): uses Wikipedia's free, official,
  keyless API to find an app's article and text-mine any company-reported
  download/install milestone it cites (e.g. "over 500 million downloads"),
  with the exact source sentence and URL attached
  (`backend/app/scrapers/wikipedia_source.py`).
- **Orchestrator** (`backend/app/scrapers/orchestrator.py`): the single
  place that calls the primary store source, then always attempts the
  independent fallback/enrichment sources regardless of whether the
  primary succeeded. If the primary source is completely down, the app
  still gets real data from AppBrain and/or Wikipedia rather than nothing.
  Every field returned is tagged with which provider produced it - the
  API and UI never present a number without saying where it came from.
- **Estimation engine** (`backend/app/estimation.py`): combines install-bucket
  deltas, review velocity, and (when available) AppBrain's independent rank
  and Wikipedia's milestone figure into a bounded daily-download estimate
  with a confidence percentage and plain-English notes on how each number
  was derived. No source here claims to know exact downloads - because
  none exists publicly for arbitrary apps. If every source fails for a
  cycle, the API returns `null` fields and a logged error - it never
  fabricates a placeholder number.
- **Live refresh**: an in-process APScheduler job polls every tracked app on
  an interval (default 15 min — see "On refresh frequency and rate limits"
  below) and broadcasts updates to connected browsers over WebSockets.
- **Full working API** (FastAPI + Postgres): add/list/update/delete apps,
  force a refresh, fetch history, dashboard KPIs, alerts, milestones.
- **Dashboard UI** (Next.js + TypeScript + Tailwind): KPI cards, live
  watchlist table, per-app profile page with rating history chart, a
  "confidence ring" showing how sure the estimate is, source badges
  showing exactly which providers produced the current data, a reported-
  milestones panel linking back to Wikipedia, an add-app flow, and an
  alerts feed. Installable as a PWA with offline app-shell caching.

### Adding another free source

The orchestrator is intentionally the only place that knows about the
provider list. To add a new one (e.g. SimilarWeb's public app pages, a
different Android crawler, a specific country's press-release aggregator):

1. Add a new file under `backend/app/scrapers/` with a `fetch_...(...)`
   function that returns a plain dict and raises on failure (never returns
   fabricated data on error).
2. Call it from `fetch_all_sources()` in `orchestrator.py`, wrapped in its
   own `try/except` so a failure there can't take down the others.
3. Tag whatever it contributes with its name in `result.sources`.

### On refresh frequency and rate limits

Google's and AppBrain's servers will rate-limit or block an IP that scrapes
too aggressively, and Apple's and Wikipedia's public endpoints are generous
but not unlimited. "Real-time" here means **polling on a short, respectful
interval** (default every 15 minutes, configurable via
`REFRESH_INTERVAL_SECONDS`), not a live feed — because no such feed exists
publicly for any of these sources. The dashboard's WebSocket layer pushes
updates to the browser the moment each poll cycle finishes, so the UI
itself feels real-time even though the underlying data updates in cycles.

## What's intentionally deferred

This spec described an enterprise product on the scale of Sensor Tower or
AppFigures — full RBAC, billing, Kubernetes, SOC2 audit trails, 10+ alert
channels, keyword-rank tracking, competitor comparison, ML forecasting, etc.
Building all of that as inert scaffolding would produce a lot of code that
doesn't run correctly and isn't worth much. Instead this is a real, tested
vertical slice, structured so the rest can be added incrementally:

- **Auth/RBAC**: not implemented. Add JWT + role checks as FastAPI
  dependencies once you have real users.
- **Billing (Stripe/PayPal)**: not implemented.
- **Celery/RabbitMQ**: the scheduler uses in-process APScheduler instead,
  which is simpler to run locally. `scheduler.py` is written so the actual
  polling logic (`refresh_one_app_sync`) can be lifted into a Celery task
  with minimal changes.
- **Kubernetes manifests, CI/CD**: not included; Docker Compose covers local
  dev and a simple single-host deploy.
- **Keyword tracking, competitor comparison, country-by-country maps,
  reports (PDF/Excel/PowerPoint export)**: not implemented yet. The data
  model (`models.py`) has room to extend into these.
- **Multi-channel alerts (email/SMS/Slack/Discord)**: alerts are currently
  stored and shown in-app only.

## Running it

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

- Backend: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:3000

To add your first app, use the "Track an app" page. You'll need:
- **Apple**: the numeric ID from the App Store URL, e.g.
  `apps.apple.com/us/app/name/id284882215` → `284882215`
- **Google Play**: the package name from the Play Store URL, e.g.
  `play.google.com/store/apps/details?id=com.spotify.music` → `com.spotify.music`

## Project layout

```
backend/
  app/
    scrapers/
      apple.py             # primary source - iTunes Lookup API
      google_play.py       # primary source - google-play-scraper lib + HTML fallback
      appbrain.py          # fallback/enrichment - independent third-party rank+rating
      wikipedia_source.py  # fallback/enrichment - self-reported download milestones
      orchestrator.py      # combines all of the above, tags every field with its source
    estimation.py          # download estimation engine, confidence scoring
    scheduler.py           # background polling job
    models.py, schemas.py, database.py, config.py
    routers/                # apps.py, dashboard.py
    main.py                 # FastAPI app + WebSocket endpoint
frontend/
  app/                      # Next.js App Router pages
  components/               # Sidebar, KpiCard, AppTable, ConfidenceRing,
                             # SourceBadges, etc.
  lib/                       # typed API client, WebSocket hook
docker-compose.yml
```

## Notes on accuracy

Every estimate returned by the API includes `confidence_pct` and `notes`
explaining which signals produced it, and every snapshot includes a
`sources` list naming exactly which provider(s) contributed its fields.
Treat the *range* (`low_bound` / `high_bound`) as more trustworthy than the
point estimate. When an app has too little history, or every source fails
for a cycle, the API returns `null` rather than guessing - this is
deliberate, not a bug.
