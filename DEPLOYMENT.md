# Deploying AppPulse Analytics: Netlify (frontend) + Render (backend)

This app splits cleanly across the two platforms: **Render** hosts the
FastAPI backend + Postgres (it needs a persistent process for the
WebSocket connection and background polling, which a static/serverless
host can't do), and **Netlify** hosts the Next.js frontend.

## Prerequisites

- Push this repo to GitHub (or GitLab/Bitbucket) - both platforms deploy
  from a connected repo.
- Accounts on [render.com](https://render.com) and [netlify.com](https://netlify.com).

## 1. Deploy the backend to Render

**Easiest path - Blueprint:**

1. In the Render dashboard: **New +** → **Blueprint**.
2. Point it at your repo. Render reads `render.yaml` at the repo root and
   provisions the web service + Postgres database automatically.
3. Wait for the first deploy to finish, then copy the service's URL (looks
   like `https://apppulse-backend-xxxx.onrender.com`).
4. Go to the `apppulse-backend` service → **Environment**, and update
   `CORS_ORIGINS` to your Netlify URL once you have it (step 2 below) -
   you'll come back to this.

**Manual path**, if you'd rather not use the Blueprint:

1. **New +** → **PostgreSQL** → create a database, note its "Internal
   Database URL".
2. **New +** → **Web Service** → connect your repo → set:
   - **Root Directory**: `backend`
   - **Runtime**: Docker (it'll pick up `backend/Dockerfile`)
   - **Health Check Path**: `/api/health`
3. Add environment variables: `DATABASE_URL` (the Postgres URL from step
   1), `REFRESH_INTERVAL_SECONDS=900`, `CORS_ORIGINS=http://localhost:3000`
   (temporary), `SECRET_KEY` (any random string).

**A cost/behavior tradeoff worth knowing before you pick a plan:** Render's
free web service tier spins down after about 15 minutes without an
incoming request, and takes 30-60 seconds to cold-start on the next one.
Since this app's background polling runs *inside* the same process, a
spin-down also pauses ingestion until something wakes the service back up.
Free is fine to try things out; for genuinely continuous polling, use at
least the Starter plan (~$7/mo at time of writing - confirm current
pricing on Render's site, it changes). If you want polling to survive even
if nobody's actively using the dashboard, uncomment the `worker` service
block in `render.yaml`, set `ENABLE_EMBEDDED_SCHEDULER=false` on the web
service, and deploy both - that's a second paid service, so weigh whether
you need it. Render's free Postgres also auto-expires roughly 30 days
after creation; move to a paid database tier before then if you want to
keep the data.

## 2. Deploy the frontend to Netlify

1. In the Netlify dashboard: **Add new site** → **Import an existing
   project** → connect your repo.
2. Netlify should auto-detect the `netlify.toml` at the repo root, which
   points the build at the `frontend/` subdirectory. If it asks you to
   confirm build settings: **Base directory**: `frontend`, **Build
   command**: `npm run build`, **Publish directory**: `.next`.
3. Before the first deploy, go to **Site settings** → **Environment
   variables** and add:
   ```
   NEXT_PUBLIC_API_BASE_URL = https://apppulse-backend-xxxx.onrender.com
   ```
   (your actual Render URL from step 1 - no trailing slash). This must be
   set *before* building, since `NEXT_PUBLIC_*` values are baked into the
   JS bundle at build time, not read at runtime.
4. Deploy. Netlify gives you a URL like `https://your-site.netlify.app`.

## 3. Close the loop: update CORS on the backend

Go back to the Render backend's **Environment** tab and set:
```
CORS_ORIGINS=https://your-site.netlify.app
```
(a bare URL is fine - no brackets or quotes needed; comma-separate if you
have more than one origin, e.g. a staging site too). Save - Render
redeploys automatically. Without this, the browser will block API
requests from your Netlify site with a CORS error.

## How the pieces talk to each other

- The Next.js frontend calls the FastAPI backend directly over HTTPS for
  all REST endpoints (`NEXT_PUBLIC_API_BASE_URL`).
- The live-updates WebSocket (`lib/useLiveUpdates.ts`) connects **directly
  from the browser to the Render backend** (`wss://your-backend.onrender.com/ws`),
  not through Netlify. This matters because Netlify's own infrastructure
  doesn't proxy persistent WebSocket connections - but that's irrelevant
  here since the browser talks to Render directly, bypassing Netlify
  entirely for that connection.
- Render's Postgres is only reachable from the backend service, never from
  the frontend.

## Verifying it worked

1. Open your Netlify URL. You should see the dashboard shell (KPI cards at
   zero, empty watchlist).
2. Open the Render backend's `/docs` URL (`https://your-backend.onrender.com/docs`)
   to confirm the API is up.
3. Add an app from the "Track an app" page. If it hangs or errors, open
   the browser console - a CORS error here almost always means step 3
   above (updating `CORS_ORIGINS`) hasn't happened yet or hasn't
   redeployed.
4. Check the "Live" indicator top-right of the dashboard - it should flip
   from "Reconnecting…" to "Live" once the WebSocket connects.

## Local development is unaffected

`docker-compose up --build` still runs everything locally exactly as
before - none of the above changes local dev, only what ships to
production.
