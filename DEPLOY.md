# Deploy: Vercel (frontend) + Railway (backend)

This project is set up so the **browser only talks to Vercel** (`/api`), and Vercel
**proxies** to Railway. That avoids most CORS / mixed-content issues.

## 1) Railway — backend

1. New Project → Deploy from GitHub (`outfitlye1-dot/leadsscraper`).
2. Add plugin: **PostgreSQL**.
3. Service settings:
   - Builder uses root `Dockerfile` (`railway.toml`).
   - Public networking: generate HTTPS domain.
4. Set variables (Variables tab):

| Variable | Value |
|----------|--------|
| `ENVIRONMENT` | `production` |
| `SECRET_KEY` | long random string |
| `DATABASE_URL` | *(auto from Postgres plugin)* |
| `FRONTEND_URL` | `https://YOUR-APP.vercel.app` |
| `CORS_ORIGINS` | `https://YOUR-APP.vercel.app` |
| `BACKEND_PUBLIC_URL` | `https://YOUR-RAILWAY.up.railway.app` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | strong admin login |
| `OTP_DEV_MODE` | `false` |
| `SMTP_*` | real SMTP (required for OTP email) |
| `WA_WEB_ENABLED` | `false` |
| `WEB_CONCURRENCY` | `1` |

5. Confirm health: `https://YOUR-RAILWAY.up.railway.app/health` → `{"status":"healthy",...}`

Copy remaining keys from `.env.production.example` as needed (Groq keys via Admin UI after login).

## 2) Vercel — frontend

1. Import the **same** GitHub repo.
2. **Critical:** Project → Settings → General → **Root Directory** = `frontend`  
   (If this is empty / `.`, Vercel deploys Python from `requirements.txt` and the site crashes.)
3. Framework Preset: **Next.js**
4. Environment variables:

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-RAILWAY.up.railway.app/api` |
| `BACKEND_INTERNAL_URL` | `https://YOUR-RAILWAY.up.railway.app` *(optional if using direct API URL above)* |

5. Redeploy. Build logs must show `next build`, **not** `Installing required dependencies from requirements.txt`.

## 3) After both are live

1. Update Railway `FRONTEND_URL` + `CORS_ORIGINS` to the final Vercel URL.
2. Google Cloud Console → OAuth client → Authorized redirect URIs:
   - `https://YOUR-APP.vercel.app/api/auth/google/callback`
   - `https://YOUR-APP.vercel.app/api/email-outreach/oauth/google/callback`
3. JazzCash / WhatsApp Cloud webhooks (if used) → `BACKEND_PUBLIC_URL` paths.
4. Log in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`, add Groq API keys in Admin.

## Important limitations (avoid production errors)

- **WhatsApp Web (Playwright CDP)** will not work on Railway the way it does on your PC. Keep `WA_WEB_ENABLED=false`. Use **WhatsApp Cloud API** for hosted messaging.
- Keep **`WEB_CONCURRENCY=1`**. Scraper / outreach jobs are in-process memory; multiple workers drop jobs.
- SQLite is for local only. Production **must** use Railway Postgres.
- Uploads/exports on the container disk are ephemeral unless you attach a volume — export soon or add S3 later.

## Troubleshoot: Vercel `FUNCTION_INVOCATION_FAILED` / 500

Usually one of these:

1. **Root Directory wrong** — Vercel project → Settings → General → Root Directory = `frontend` (not repo root).
2. **Backend URL missing** — set either:
   - `BACKEND_INTERNAL_URL=https://YOUR-RAILWAY.up.railway.app` + `NEXT_PUBLIC_API_URL=/api`, **or**
   - `NEXT_PUBLIC_API_URL=https://YOUR-RAILWAY.up.railway.app/api` (browser talks to Railway directly; simpler).
3. Never leave `BACKEND_INTERNAL_URL` as `localhost` / `127.0.0.1` on Vercel — that crashes serverless proxy.
4. Redeploy after pushing latest `main` (font + prod fixes).

Check logs: Vercel → Project → Deployments → latest → Functions / Runtime Logs.

```bash
# backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# frontend
cd frontend && npm run dev
```

`frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=/api
BACKEND_INTERNAL_URL=http://127.0.0.1:8001
```
