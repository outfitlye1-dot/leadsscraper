# AI Lead Generation SaaS Backend

Production-ready FastAPI backend for an AI-powered Lead Generation SaaS platform.

## Features

- JWT authentication (register, login, protected routes)
- Lead CRUD with search, filters, pagination, and CSV export
- CV upload (PDF/DOCX) with AI-powered profile extraction via Groq
- Apify integration for Google Maps business lead scraping
- AI message generation (WhatsApp, Email, LinkedIn, Follow-up) via Groq
- Campaign management
- Message history tracking
- Dashboard analytics
- Swagger API documentation at `/docs`

## Tech Stack

- **FastAPI** — Web framework
- **SQLAlchemy** — ORM
- **SQLite** — Database (`leadgen.db`)
- **Alembic** — Migrations
- **Groq API** — AI provider
- **Apify API** — Web scraping
- **JWT** — Authentication

## Quick Start

### 1. Clone and setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your `SECRET_KEY` and other settings. Groq and Apify API keys are added per user in the app (**Settings → API Keys**), not in `.env`.

### 2. Run locally

```bash
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### 3. Run with Docker

```bash
docker-compose up --build
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing secret |
| `ALGORITHM` | JWT algorithm (default: HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry in minutes |
| `GROQ_MODEL` | Groq model name |
| `APIFY_ACTOR_ID` | Apify actor ID (default: Google Places scraper) |
| `DATABASE_URL` | Database connection string |

## Database Migrations

```bash
alembic upgrade head
```

Create a new migration after model changes:

```bash
alembic revision --autogenerate -m "description"
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login and get JWT |
| GET | `/api/auth/me` | Current user profile |
| POST | `/api/leads` | Create lead |
| GET | `/api/leads` | List leads (search/filter/paginate) |
| GET | `/api/leads/{id}` | Get lead |
| PUT | `/api/leads/{id}` | Update lead |
| DELETE | `/api/leads/{id}` | Delete lead |
| GET | `/api/leads/export` | Export leads to CSV |
| POST | `/api/cv/upload` | Upload CV |
| GET | `/api/cv/profile` | Get CV profile |
| GET | `/api/cv/raw` | Get raw CV text |
| POST | `/api/scraper/start` | Start Apify scraping |
| POST | `/api/ai/generate` | Generate AI message |
| POST | `/api/campaigns` | Create campaign |
| GET | `/api/campaigns` | List campaigns |
| PUT | `/api/campaigns/{id}` | Update campaign |
| DELETE | `/api/campaigns/{id}` | Delete campaign |
| GET | `/api/messages` | List messages |
| GET | `/api/messages/{id}` | Get message |
| GET | `/api/dashboard/stats` | Dashboard analytics |

## Apify Setup

1. Create an account at [apify.com](https://apify.com)
2. Get your API token from Settings → Integrations
3. Add your token in the app under **Settings → API Keys**
4. Default actor `compass/crawler-google-places` scrapes Google Maps businesses

## Testing

```bash
pytest -v
```

## Project Structure

```
app/
├── main.py              # FastAPI entry point
├── core/                # Config, security, auth
├── database/            # SQLAlchemy setup
├── models/              # Database models
├── schemas/             # Pydantic schemas
├── repositories/        # Data access layer
├── services/            # Business logic
├── routes/              # API endpoints
└── utils/               # Helpers
```

## License

MIT
