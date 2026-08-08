# LeadGen AI

Simple monorepo — **two folders only** for deploy:

```
leadsscraper/
├── frontend/     ← Next.js  → deploy on Vercel  (Root Directory = frontend)
└── backend/      ← FastAPI  → deploy on Railway (Root Directory = backend)
```

## Local run

### Backend (API :8001)

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

API docs: http://127.0.0.1:8001/docs

### Frontend (UI :3000)

```bash
cd frontend
npm install
# create .env.local:
#   NEXT_PUBLIC_API_URL=/api
#   BACKEND_INTERNAL_URL=http://127.0.0.1:8001
npm run dev
```

App: http://localhost:3000

## Production

| Service | Platform | Root Directory |
|---------|----------|----------------|
| UI | **Vercel** | `frontend` |
| API | **Railway** | `backend` |

Full steps: see [DEPLOY.md](./DEPLOY.md)
