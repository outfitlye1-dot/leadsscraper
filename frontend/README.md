# LeadGen AI Frontend

Production-ready Next.js 14 frontend for the AI Lead Generation SaaS platform.

## Tech Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Axios + React Query
- Zustand (auth state)
- Recharts (analytics)
- React Hook Form + Zod
- Sonner (toasts)

## Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000

## Environment

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

Make sure the FastAPI backend is running on port 8000.

## Pages

| Route | Description |
|-------|-------------|
| `/login` | User login |
| `/register` | User registration |
| `/dashboard` | Overview stats |
| `/leads` | Lead management |
| `/scraper` | Apify lead scraping |
| `/ai` | AI message generator |
| `/cv` | CV upload & profile |
| `/campaigns` | Campaign management |
| `/analytics` | Charts & insights |

## Project Structure

```
app/           # Next.js App Router pages
components/    # UI components
hooks/         # React Query hooks
lib/           # API client, auth, utils
store/         # Zustand auth store
```
