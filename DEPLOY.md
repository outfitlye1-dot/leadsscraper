# Deploy guide (simple)

```
GitHub repo
├── frontend/   →  Vercel   (website)
└── backend/    →  Railway  (API + database)
```

---

## 1) Railway = backend

1. New project → Deploy from GitHub `leadsscraper`
2. **Settings → Root Directory** = `backend`  ← important
3. Add **PostgreSQL** plugin
4. Variables (example):

```
ENVIRONMENT=production
SECRET_KEY=long-random-secret
FRONTEND_URL=https://YOUR-APP.vercel.app
CORS_ORIGINS=https://YOUR-APP.vercel.app
BACKEND_PUBLIC_URL=https://YOUR-API.up.railway.app
WA_WEB_ENABLED=false
OTP_DEV_MODE=false
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=StrongPassword123!
```

`DATABASE_URL` usually comes from the Postgres plugin automatically.

5. Check: `https://YOUR-API.up.railway.app/health`

Dockerfile is already in `backend/`.

---

## 2) Vercel = frontend

1. Import same GitHub repo
2. **Settings → General → Root Directory** = `frontend`  ← important  
   (If empty, Vercel wrongly builds Python and crashes)
3. Framework: **Next.js**
4. Environment variables:

```
NEXT_PUBLIC_API_URL=https://YOUR-API.up.railway.app/api
```

5. Deploy. Build log must show `next build`, not `requirements.txt`.

---

## 3) After both live

1. Put real Vercel URL into Railway `FRONTEND_URL` + `CORS_ORIGINS`
2. Google OAuth redirect URIs (if used):
   - `https://YOUR-APP.vercel.app/api/auth/google/callback`
3. Login with admin email/password → add Groq keys in Admin

---

## Troubleshoot Vercel 500

| Problem | Fix |
|---------|-----|
| Build installs `requirements.txt` | Root Directory must be `frontend` |
| `FUNCTION_INVOCATION_FAILED` | Set `NEXT_PUBLIC_API_URL` to Railway `/api` URL |
| API not found | Railway health URL must work first |

---

## Local (unchanged idea)

```bash
# terminal 1
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# terminal 2
cd frontend
npm run dev
```
