# PROJECT_CONTEXT.md — AI Lead Generation SaaS (Scraper)

> Last updated: July 2026  
> Purpose: Give any AI or developer full context to understand, debug, or extend this project.

---

## 1. What This Project Is

A **full-stack AI Lead Generation SaaS** for freelancers/agencies who:
1. Upload CV / build an **AI Brain** profile
2. **Scrape** local businesses (Google Maps, web crawl, Meta Ads)
3. Manage leads in an **Inbox** vs **Saved** workflow
4. Generate **short, human-touch outreach** (WhatsApp, Email, LinkedIn)
5. Run **campaigns** and track **message history**
6. **AI Email Outreach Agent** — connect Gmail, start agent, auto-verify leads, generate & send personalized emails + follow-ups

**Target users:** People selling web design, digital services, etc. to **local brick-and-mortar businesses** (restaurants, salons, clinics) — NOT other agencies.

**Primary language in UI/workflow:** English + Roman Urdu hints in Brain/Scraper/Email Outreach copy.

---

## 2. Tech Stack

| Layer | Stack |
|-------|--------|
| Backend | FastAPI, SQLAlchemy, SQLite (`leadgen.db`), Alembic |
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind |
| State | TanStack Query, Zustand (scraper jobs) |
| AI | Groq API (per-user API keys) |
| Scraping | Apify (Google Maps, Meta Ads), custom crawler (Playwright, Scrapy, BeautifulSoup) |
| Auth | JWT + email/password; OTP flow also exists |
| Email outreach | Gmail OAuth + SMTP; Groq for AI email generation; DB-backed job queue |
| Tests | pytest |

---

## 3. How to Run

```bash
# Backend (repo root)
pip install -r requirements.txt
cp .env.example .env   # set SECRET_KEY, Gmail OAuth vars (see §12)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# Frontend
cd frontend
cp .env.local.example .env.local   # BACKEND_INTERNAL_URL=http://127.0.0.1:8001
npm install && npm run dev
# → http://localhost:3000

# API docs (direct backend)
# → http://127.0.0.1:8001/docs

# Tests
pytest -v
```

**Important:** Frontend proxies `/api/*` → backend via `frontend/next.config.js` rewrites. Default backend URL is `http://127.0.0.1:8001` (`BACKEND_INTERNAL_URL` in `frontend/.env.local`). Browser always uses `http://localhost:3000/api/...`.

**API keys:** Groq + Apify are stored **per user** in Settings → API Keys (`user_api_keys` table), NOT in `.env`.

---

## 4. Repository Structure

```
scraper/
├── app/                          # FastAPI backend
│   ├── main.py                   # App entry, CORS, routers
│   ├── core/                     # config, security, JWT auth
│   ├── database/                 # SQLAlchemy engine, migrations helper
│   ├── models/                   # User, Lead, CV, Brain, Campaign, Message, etc.
│   ├── schemas/                  # Pydantic request/response models
│   ├── repositories/             # DB access layer
│   ├── services/               # Business logic
│   │   └── email_outreach/     # Agent, send, sync, worker, job queue
│   ├── routes/                   # API endpoints
│   ├── scrapers/                 # Crawler spiders, parsers
│   ├── scraper/                  # Scrape metrics, validators, exporters
│   └── utils/                    # prompts, contact_links, outreach_tone, datetime_utils, etc.
├── frontend/
│   ├── app/                      # Next.js pages
│   │   ├── (app)/                # Authenticated app shell
│   │   │   ├── dashboard/
│   │   │   ├── leads/            # Inbox
│   │   │   ├── leads/saved/      # Saved leads
│   │   │   ├── scraper/
│   │   │   ├── campaigns/
│   │   │   ├── messages/
│   │   │   ├── ai/               # AI message generator
│   │   │   ├── brain/            # AI Brain profile
│   │   │   ├── cv/
│   │   │   ├── analytics/
│   │   │   ├── email-outreach/   # AI Outreach Agent dashboard
│   │   │   └── settings/
│   │   └── login/
│   ├── components/               # UI components
│   ├── hooks/                    # React Query hooks (useLeads, useBrain, etc.)
│   └── lib/                      # api client, types, utils
├── tests/                        # pytest tests
├── alembic/                      # DB migrations
├── leadgen.db                    # SQLite database (local)
└── requirements.txt
```

---

## 5. Core User Workflow

```
CV Upload → AI Brain (profile + system prompt)
    ↓
Scraper (Maps / Internet / Meta Ads / All)
    ↓
Leads Inbox (unsaved leads, is_saved=false)
    ↓
"Remove no contact" → keeps phone leads, deletes email-only & no-contact
    ↓
User manually saves good leads → Saved page (is_saved=true)
    ↓
AI Generator / Campaigns → WhatsApp, Email, LinkedIn messages
    ↓
[OPTIONAL] Email Outreach Agent → Gmail connect → Start AI Agent
    → pilot email (immediate) → daily batch (delayed) → follow-ups (scheduled)
    ↓
Outreach via contact action buttons (wa.me, mailto, social links)
```

---

## 6. Database Models (Key)

### User
- email, password (bcrypt), role
- Has: leads, cv, brain, campaigns, messages, api_keys

### Lead (`app/models/lead.py`)
Important fields:
- `company_name`, `contact_name`, `phone`, `email`, `website`
- `linkedin_url`, `facebook_url`, `instagram_url`
- `city`, `country`, `category`, `industry`, `source`
- `status`: new | contacted | interested | follow_up | closed | lost
- `quality_score`, `quality_tier`, `whatsapp_ready`
- **`is_saved`**: `false` = Leads inbox, `true` = Saved page
- `saved_at`, `created_at`, `updated_at`

### Brain (`app/models/brain.py`)
One per user. Stores skills, services, tools, technologies, experience, projects, `professional_summary`, `custom_notes`, **`system_prompt`** (generated by Groq).

### CV
Parsed resume data + raw text from PDF/DOCX upload.

### Campaign + Message
Campaigns group outreach; messages store generated content per lead.

### UserApiKey
Per-user Groq and Apify tokens with rotation support.

### Email Outreach (`app/models/email_outreach.py`) — `[CURRENT]`
Key tables:
- `email_accounts` — Gmail OAuth / SMTP connections
- `email_outreach_settings` — automation, limits, agent state (`agent_running`, `agent_paused`, `agent_batch_delay_minutes`, working hours)
- `email_outreach_campaigns` — standing campaign **"AI Agent — Auto Outreach"**
- `outreach_emails` — generated emails (`status`, `follow_up_step`, `scheduled_at`, `body_text`)
- `outreach_jobs` — persistent job queue (`send_email`, `agent_cycle`, `sync_inbox`, etc.)
- `outreach_notifications`, `agent_activity_logs`, `email_conversations`, `ai_reply_drafts`

Email statuses: `pending_review` | `queued` | `sending` | `sent` | `delivered` | `replied` | `failed` | `verification_failed` | `cancelled`

**Note:** Follow-up emails show `queued` with a future `scheduled_at` — UI labels these as **scheduled**.

---

## 7. Critical Business Rules

### Lead inbox cleanup (`POST /api/leads/cleanup-no-contact`)
Logic in `app/services/lead_service.py`:

| Lead type | Action |
|-----------|--------|
| Has phone (≥10 digits) | **Keep** in Leads inbox |
| Email only (no phone) | **Delete** |
| No contact | **Delete** |
| Already Saved (`is_saved=true`) | **Untouched** |

- `_lead_has_phone()`: digits only, min 10
- `_lead_should_keep_in_inbox()`: phone required
- Auto-scraper uses `cleanup_non_phone_leads_by_ids()` — same phone-only keep rule

### Leads vs Saved
- **Inbox** = `GET /api/leads?saved=false` (default)
- **Saved** = `GET /api/leads?saved=true`
- Save = `POST /api/leads/bulk-save` or individual save
- Cleanup does **NOT** auto-move to Saved — user saves manually

### Outreach contact links (`app/utils/contact_links.py`)
`build_contact_links(lead)` returns:
- `whatsapp_url`, `email_url`, `linkedin_url`, `facebook_url`, `instagram_url`, `website_url`
- `needs_website_pitch`, `website_offer_whatsapp_url`, `website_offer_email_url`, `offer_message`

Frontend: `frontend/components/LeadContactActions.tsx` — compact buttons in leads table.

### AI message tone (`app/utils/prompts.py` + `outreach_tone.py`)
- **Short, human, casual-professional** — not corporate/salesy
- WhatsApp: ~180 chars, 2–3 sentences
- LinkedIn: ~200 chars
- Email: short subject + body under ~90 words
- **Paid service only** — never offer "free quote/audit/trial" (`sanitize_paid_outreach_message`)
- Post-generation trim via `trim_outreach_message()`
- Groq `temperature=0.85`, limited `max_tokens` per channel

### Website filter
`has_real_website()` rejects facebook.com, instagram.com, etc. as "real" websites.

### Scrape sources (`app/utils/scrape_sources.py`)
- `google_maps` — Apify Google Places
- `google_search` — web crawl + enrichment
- `meta_ads` — Facebook/Instagram advertisers via Apify
- `all` — combined

Main orchestrator: `app/services/all_in_one_scraper_service.py`

---

## 8. API Endpoints (Summary)

| Prefix | Purpose |
|--------|---------|
| `/api/auth` | register, login, OTP, `/me` |
| `/api/leads` | CRUD, list, export CSV/XLSX, bulk-save, bulk-delete, **cleanup-no-contact** |
| `/api/cv` | upload PDF/DOCX, get profile/raw |
| `/api/brain` | get/update brain, import CV, generate system prompt |
| `/api/scraper` | start job, status, daily scrape, demo (public), auto-scraper |
| `/api/ai` | generate message, optimize search query, suggest scrape from brain |
| `/api/campaigns` | CRUD + bulk message generation |
| `/api/messages` | message history |
| `/api/dashboard` | stats |
| `/api/user-api-keys` | Groq/Apify key management |
| `/api/email-outreach` | Gmail OAuth, settings, campaigns, agent start/stop, emails, notifications, dashboard |
| `/health` | health check |

Full list: `http://127.0.0.1:8001/docs`

---

## 9. Frontend Pages

| Route | File | Purpose |
|-------|------|---------|
| `/dashboard` | `dashboard/page.tsx` | Overview stats |
| `/leads` | `leads/page.tsx` | Inbox + "Remove no contact" button |
| `/leads/saved` | `leads/saved/page.tsx` | Saved leads |
| `/scraper` | `scraper/page.tsx` | Main scraper UI, tools list, job progress |
| `/campaigns` | `campaigns/page.tsx` | Campaign management |
| `/messages` | `messages/page.tsx` | Generated message history |
| `/ai` | `ai/page.tsx` | AI generator — **saved leads only** in dropdown |
| `/brain` | `brain/page.tsx` | CV profile + Generate Brain |
| `/cv` | `cv/page.tsx` | CV upload |
| `/analytics` | `analytics/page.tsx` | Charts |
| `/email-outreach` | `email-outreach/page.tsx` | **AI Outreach Agent** — Gmail, Start/Stop, sent messages, follow-ups |
| `/settings` | `settings/page.tsx` | Account + API keys |

**Key components:**
- `LeadContactActions.tsx` — outreach buttons
- `LeadDetailDrawer.tsx` — lead detail side panel
- `resizable-table.tsx` — leads table (full email visible, `break-all`)
- `LandingPage.tsx` — marketing landing with demo scrape
- `Sidebar.tsx` — navigation

**Key hooks:**
- `useLeads.ts` — includes `useCleanupLeadsWithoutContact()`
- `useBrain.ts`, `useCampaigns.ts`, `useMessages.ts`, `useAuth.ts`
- `useEmailOutreach.ts` — agent start/stop, dashboard, emails, settings, notifications

**API client:** `frontend/lib/api.ts` — axios with JWT from localStorage; base URL `/api` (proxied to backend)

---

## 10. AI / Prompts Architecture

| File | Role |
|------|------|
| `app/utils/prompts.py` | All Groq prompt templates |
| `app/services/groq_service.py` | Groq API calls, CV parse, message gen, brain gen |
| `app/utils/outreach_tone.py` | Paid-service rules, human-touch rules, trim/sanitize |
| `app/services/brain_service.py` | Brain CRUD + generate |
| `app/services/message_service.py` | `/api/ai/generate` handler |
| `app/services/cv_service.py` | CV upload + Groq extraction |

Message types: `whatsapp`, `email`, `linkedin`, `follow_up`

Brain `system_prompt` is used conceptually for outreach tone; per-message generation uses CV profile + lead info + channel-specific prompts.

---

## 11. Scraper Architecture

```
ScraperStartRequest
    → AllInOneScraperService.run()
        → ApifyService (Maps)
        → MetaAdsService (Meta Ads)
        → Web search + crawler (Playwright/BS4)
        → EnrichmentService (emails, socials from sites)
        → apply_quality_to_lead()
        → dedupe + website filter
        → bulk_create leads (inbox)
        → optional: Groq WhatsApp message generation
        → optional: cleanup_non_phone_leads_by_ids()
```

Job state: `app/services/scraper_job_store.py` + frontend `scraperJobStore` (Zustand)

---

## 12. Environment Variables (`.env`)

| Variable | Notes |
|----------|-------|
| `SECRET_KEY` | JWT signing (required) |
| `DATABASE_URL` | default `sqlite:///./leadgen.db` |
| `GROQ_MODEL` | default `llama-3.1-8b-instant` |
| `APIFY_ACTOR_ID` | Google Places scraper |
| `APIFY_META_ADS_ACTOR_ID` | Meta ads scraper |
| `SMTP_*` | Optional — email OTP; dev uses console OTP if SQLite + no SMTP |
| `OUTREACH_WORKER_ENABLED` | `true` — starts outreach job worker 3s after API boot |
| `GOOGLE_OAUTH_CLIENT_ID` / `SECRET` | Gmail connect for email outreach |
| `GOOGLE_OAUTH_REDIRECT_URI` | Must match Google Console — use `http://localhost:3000/api/email-outreach/oauth/google/callback` |

---

## 13. Recent Customizations (Important for AI)

1. **AI Email Outreach Agent** — autonomous SDR: Gmail → Start Agent → pilot email + daily batch + follow-ups (see §33)
2. **Pilot email on agent start** — first lead emailed immediately so user sees agent working; full batch after `agent_batch_delay_minutes` (default 10)
3. **Sent messages UI** — shows `to_email`, subject, full `body_text`; follow-ups labeled **scheduled** with date
4. **SQLite datetime fix** — `app/utils/datetime_utils.py` → `as_utc()`; job queue compares dates safely (was causing worker crashes + API 500s)
5. **Backend port 8001** — frontend `.env.local` + `next.config.js` default proxy target
6. **Single "Remove no contact" button** on Leads page — deletes non-phone inbox leads
7. **Phone-only keep rule** — email-only leads auto-deleted on cleanup
8. **No auto-save to Saved** on cleanup — manual save only
9. **AI page** shows **Saved leads only** in dropdown
10. **Full email** shown in table (no truncate)
11. **Facebook** added to outreach tools (`facebook_url` in contact_links)
12. **Shorter human-touch AI messages** — updated prompts + trim limits

---

## 14. Testing

```bash
pytest tests/test_leads.py          # lead CRUD, cleanup
pytest tests/test_contact_links.py  # outreach links
pytest tests/test_outreach_tone.py  # message sanitize/trim
pytest tests/test_ai.py             # AI generate (mocked Groq)
pytest tests/test_auto_scraper.py   # scrape cleanup
```

---

## 15. Common Pitfalls / Debug Tips

- **"8 kept" but nothing deleted** — frontend must use API `kept` not `saved`; refetch after cleanup
- **Groq errors** — user needs API key in Settings; check `ApiKeyRotationService`
- **Apify errors** — user needs Apify token in Settings
- **Leads not showing** — check `saved=false` vs `saved=true` filter
- **WhatsApp button missing** — phone must pass `is_whatsapp_ready()` + country
- **Backend reload stuck** — restart uvicorn manually on Windows (`port 8001`)
- **API 500 on login** — often SQLite lock or dead worker; check outreach worker logs; restart backend
- **`queued` email status** — initial email waiting to send OR follow-up scheduled for future date (check `follow_up_step` + `scheduled_at`)
- **Emails not sending** — enable **Auto-send** in Email Outreach settings; disable **Require review** OR approve pending emails
- **Working hours** — sends blocked outside `working_hours_start`–`end` (pilot emails bypass this)
- **Gmail OAuth redirect_uri_mismatch** — redirect URI must be frontend proxy URL on port 3000
- **CORS** — localhost:3000 allowed; ngrok regex in `main.py`

---

## 16. Key File Index (Quick Reference)

| Concern | File |
|---------|------|
| Lead cleanup logic | `app/services/lead_service.py` |
| Lead API routes | `app/routes/leads.py` |
| Leads inbox UI | `frontend/app/(app)/leads/page.tsx` |
| Outreach buttons | `frontend/components/LeadContactActions.tsx` |
| AI prompts | `app/utils/prompts.py` |
| Message generation | `app/services/groq_service.py` |
| Scraper UI | `frontend/app/(app)/scraper/page.tsx` |
| Scraper engine | `app/services/all_in_one_scraper_service.py` |
| Brain UI | `frontend/app/(app)/brain/page.tsx` |
| Types (frontend) | `frontend/lib/types.ts` |
| Config | `app/core/config.py` |
| AI Outreach Agent | `app/services/email_outreach/agent.py` |
| Outreach worker + queue | `app/services/email_outreach/worker.py`, `job_queue.py` |
| Email send + limits | `app/services/email_outreach/send.py` |
| Outreach API routes | `app/routes/email_outreach.py` |
| Outreach frontend | `frontend/app/(app)/email-outreach/page.tsx` |
| Outreach hooks | `frontend/hooks/useEmailOutreach.ts` |
| Datetime helper (SQLite) | `app/utils/datetime_utils.py` |

---

## 17. Product Vision (For AI Assistants)

When suggesting features or copy:
- Target **local small businesses without websites**
- Outreach should feel **human, short, not spammy**
- **Paid services only** — no free hooks
- Prefer **phone/WhatsApp** as primary contact channel
- User workflow is: **Scrape → Filter/cleanup → Save best → Outreach**
- Do not break `is_saved` inbox/saved separation

---

## 18. Production Architecture

> **Legend:** `[CURRENT]` = implemented today · `[REQUIRED]` = must be built before production scale

### 18.1 Deployment topology

```
[CURRENT — local / single-container]
Browser → Next.js (port 3000) → FastAPI (port 8001) → SQLite (leadgen.db)
                                              ↓
                                    uploads/ + exports/ (local disk)
                                    outreach worker (daemon thread, DB job queue)

[REQUIRED — production]
Browser → CDN (static) → Next.js (Vercel or container)
                      → API Gateway / reverse proxy (TLS termination)
                      → FastAPI (N replicas, stateless)
                      → PostgreSQL (managed)
                      → Redis (job queue + rate limits + sessions)
                      → Object storage (S3/R2: CV uploads, exports)
                      → Worker processes (scraper + AI jobs)
```

### 18.2 Component responsibilities

| Component | Dev (`[CURRENT]`) | Production (`[REQUIRED]`) |
|-----------|-------------------|---------------------------|
| Frontend | `npm run dev` on 3000 | `next build` + `next start` or Vercel deploy; `NEXT_PUBLIC_API_URL` points to API domain |
| API | `uvicorn --reload` | Gunicorn + Uvicorn workers; no `--reload`; health at `/health` |
| Database | SQLite file in repo root | PostgreSQL 15+; connection pool via SQLAlchemy; `DATABASE_URL` in secrets manager |
| File storage | `./uploads`, `./exports` | S3-compatible bucket; signed URLs for download; virus scan on upload |
| Background jobs | `threading.Thread` daemon jobs | Celery/RQ/Arq workers backed by Redis; job persistence survives API restart |
| Secrets | `.env` file | Platform secrets (Railway/Fly/AWS/GCP); never commit `.env` |

### 18.3 Docker (`[CURRENT]`)

- `Dockerfile` — Python 3.12-slim, runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- `docker-compose.yml` — API only; mounts `leadgen.db`, `uploads/`, `exports/`

**Production Docker rules:**
- Add separate `frontend` service or deploy frontend independently
- Do **not** mount SQLite in production — use PostgreSQL service
- Add `worker` service for scraper/AI queue consumers
- Add `redis` service for queue + cache
- Set `restart: unless-stopped` on all services
- Use multi-stage builds; pin dependency versions

### 18.4 CI/CD (`[REQUIRED]` — not in repo yet)

Minimum pipeline (GitHub Actions recommended):

```yaml
# On PR + main push:
1. lint-backend    → ruff/black (if adopted) + mypy optional
2. test-backend    → pytest -v --cov=app
3. lint-frontend   → npm run lint
4. build-frontend  → npm run build
5. docker-build    → build API image, scan for CVEs
6. deploy-staging  → auto on main merge
7. deploy-prod     → manual approval gate
```

**Deploy checklist per release:**
- Run `alembic upgrade head` before traffic switch
- Smoke test: `/health`, login, scrape job start, lead list
- Rollback: previous container image + DB migration downgrade plan

### 18.5 Environment matrix

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| `DATABASE_URL` | `sqlite:///./leadgen.db` | PostgreSQL (staging) | PostgreSQL (prod, HA) |
| `SECRET_KEY` | dev placeholder | unique 64+ char random | unique 64+ char random |
| `OTP_DEV_MODE` | auto if no SMTP | `false` | `false` |
| `CORS_ORIGINS` | localhost | staging domain | prod domain only |
| Groq/Apify keys | per-user in DB | per-user in DB | per-user in DB + platform fallback keys optional |
| Logging | stdout | JSON structured | JSON + log aggregator |
| HTTPS | optional (ngrok) | required | required |

---

## 19. Security Requirements

### 19.1 JWT security

**`[CURRENT]`**
- Access token only (no refresh token) — `app/core/security.py`
- Algorithm: HS256; expiry: `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60)
- Payload: `sub` = user email; validated in `get_current_user`
- Frontend stores token in `localStorage` via `frontend/lib/api.ts`

**`[REQUIRED]`**
- Rotate `SECRET_KEY` with dual-key verification window during rotation
- Shorten access token TTL to 15–30 min in production
- Implement refresh token strategy (see §19.2)
- Move token storage to `httpOnly` secure cookies (mitigate XSS)
- Add `jti` claim + token revocation list in Redis for logout-all-devices
- Reject tokens if user password changed after `iat`

### 19.2 Refresh token strategy (`[REQUIRED]`)

```
Login → access_token (15 min) + refresh_token (30 days, httpOnly cookie)
Refresh endpoint → rotate refresh token (one-time use), issue new access token
Logout → revoke refresh token family in Redis
```

Rules:
- Store refresh token hash only (never plaintext)
- Bind refresh token to `user_id` + device fingerprint optional
- Max 5 active refresh sessions per user

### 19.3 Password security

**`[CURRENT]`**
- bcrypt hashing via `get_password_hash()` / `verify_password()`
- Register + login + forgot-password OTP flow exists

**`[REQUIRED]`**
- Enforce min 10 chars, block common passwords (zxcvbn or HIBP API)
- Rate-limit login attempts: 5 failures / 15 min per IP + per email
- Password reset tokens single-use, 15 min expiry
- Never log passwords, OTP codes, or API keys

### 19.4 API key encryption (`[CURRENT]` gap)

**`[CURRENT]`**
- `user_api_keys.api_key` stored as **plaintext** `String(500)` in SQLite
- Rotation via `ApiKeyRotationService` — marks keys `exhausted` on quota errors

**`[REQUIRED]`**
- Encrypt at rest: AES-256-GCM with `ENCRYPTION_KEY` from secrets manager
- Decrypt only in service layer at call time; never return full key in API responses (mask: `gsk_...xxxx`)
- Audit log every key create/delete/rotate
- Separate encryption key per environment

### 19.5 User data isolation

**`[CURRENT]`**
- All repositories filter by `user_id` from JWT (`get_current_user`)
- `Lead`, `Campaign`, `Message`, `Brain`, `CV`, `UserApiKey` all have `user_id` FK with `CASCADE` delete
- Scraper jobs scoped: `scraper_job_store.get(job_id, user_id)` rejects cross-user access

**Rules for all new endpoints:**
- Never accept `user_id` from request body for data access — always use `current_user.id`
- Admin routes must explicitly check `current_user.role == UserRole.admin`
- Integration tests must assert user A cannot read user B's leads (IDOR tests)

### 19.6 File upload security

**`[CURRENT]`**
- CV upload: PDF/DOCX; `MAX_UPLOAD_SIZE_MB` = 10
- Files saved to `uploads/` directory

**`[REQUIRED]`**
- Validate MIME type + magic bytes (not just extension)
- Generate random filenames (no user-supplied paths)
- Scan uploads with ClamAV or cloud AV
- Serve files via signed URLs, not direct filesystem paths
- Per-user upload quota (e.g. 5 CV versions, 50 MB total)

### 19.7 Rate limiting

**`[CURRENT]`**
- Demo scrape: `app/utils/demo_rate_limit.py` — 5 requests/hour/IP (in-memory)
- Apify/Groq quota handled via key rotation, not platform rate limits

**`[REQUIRED]`**
- Redis-backed rate limits per endpoint:
  - Auth login: 10/min/IP
  - `/api/scraper/start`: 5/hour/user (free), higher on Pro
  - `/api/ai/generate`: 30/hour/user (free), 500/hour (Pro)
  - `/api/scraper/demo`: keep IP limit, move to Redis for multi-instance
- Return `429` with `Retry-After` header

### 19.8 CORS production rules

**`[CURRENT]`**
- `CORS_ORIGINS` defaults to localhost 3000/3001
- `allow_origin_regex` permits ngrok domains for dev tunnels
- `allow_credentials=True`

**Production rules:**
- Set `CORS_ORIGINS` to exact production frontend origin(s) only — **remove `*` behavior**
- Remove or restrict ngrok regex in production builds
- Do not use `allow_credentials=True` with wildcard origins
- API should not be callable from arbitrary browser origins

---

## 20. Multi-Tenant SaaS Rules

### 20.1 Tenant model

- **Tenant = User account** (`users.id`)
- One user owns: leads, CV, brain (1:1), campaigns, messages, API keys, daily scrape runs
- No organization/team tenant yet — all isolation is `user_id` scoped

### 20.2 `user_id` isolation (mandatory)

Every DB query for tenant data MUST include:

```python
.filter(Model.user_id == current_user.id)
```

Repositories enforcing this: `LeadRepository`, `CampaignRepository`, `MessageRepository`, `CVRepository`, `BrainRepository`, `UserApiKeyRepository`.

**Never:**
- Return leads by `lead_id` alone without `user_id` check
- Share scraper job results across users
- Use global caches keyed without `user_id`

### 20.3 Permission rules

| Role | `UserRole.user` | `UserRole.admin` |
|------|-----------------|------------------|
| Own leads/CV/brain | ✅ | ✅ |
| Other users' data | ❌ | ✅ (admin panel only) |
| Platform API key override | ❌ | ✅ optional |
| User management | ❌ | ✅ |
| Scraper demo (no auth) | public, rate-limited | same |

**`[CURRENT]`** — `UserRole` enum exists; admin routes not fully implemented.

**`[REQUIRED]`** — Admin router prefix `/api/admin/*` with role guard dependency.

### 20.4 Data access policies

- **Soft delete:** not implemented — deletes are hard delete with `CASCADE`
- **Export:** user can export only own leads (`GET /api/leads/export`)
- **GDPR delete account:** `[REQUIRED]` — endpoint to purge user + all related rows + uploaded files
- **Data retention:** `[REQUIRED]` — define inbox lead TTL (e.g. 90 days unsaved auto-purge optional)

### 20.5 Cross-tenant scraping

- Apify/Groq calls use **the requesting user's API keys** — platform does not share one Apify account across users in production billing model
- Demo scrape (`/api/scraper/demo`) does not persist leads — no tenant data created

---

## 21. Background Processing Architecture

### 21.1 Scraper job queue (`[CURRENT]`)

```
POST /api/scraper/start
  → scraper_job_store.create(user_id)
  → threading.Thread(target=_run_job, daemon=True)
  → AllInOneScraperService.run() with on_progress callback
  → scraper_job_store.complete() | .fail()
```

- Job state: in-memory `ScraperJobStore` (`app/services/scraper_job_store.py`)
- Statuses: `pending` | `running` | `completed` | `failed`
- Modes: `single` | `auto` (loop every 15s until cancel)
- Frontend polls `GET /api/scraper/jobs/{job_id}` via Zustand store

**Limitations (fix in production):**
- Jobs lost on API restart
- No horizontal scaling (in-memory, single process)
- Daemon threads die with process

### 21.2 Outreach worker (`[CURRENT]`)

Persistent DB-backed queue for email outreach — survives API restarts (jobs in `outreach_jobs` table).

```
app/main.py lifespan → threading.Timer(3s) → outreach_worker.start()
    ↓
OutreachJobQueue.claim_next()  # uses as_utc() for scheduled_at
    ↓
Job types: send_email | agent_cycle | sync_inbox | process_lead | process_campaign | schedule_followups
```

Key files: `app/services/email_outreach/worker.py`, `job_queue.py`, `agent.py`, `send.py`

Worker polls every `OUTREACH_WORKER_POLL_SECONDS` (default 15s); processes claimed jobs in separate DB sessions.

**Agent cycle flow:**
1. `POST /api/email-outreach/agent/start` → sets `agent_running=true`
2. **Pilot email** — immediately generates + queues send for first available lead (`pilot=True`, bypasses review + working hours)
3. **Daily batch** — scheduled after `agent_batch_delay_minutes` (default 10) for today's unsaved/saved leads
4. Re-schedules `agent_cycle` every 2 min while agent running
5. On lead save (when agent running) → hooks `on_leads_saved` → schedules batch

### 21.3 General worker system (`[REQUIRED]` for scraper scale)

```
API enqueues → Redis queue: scrape_jobs, ai_jobs, email_jobs
Worker pool  → consumes jobs, updates job status in Redis + DB
```

Job record schema (persist to DB):

```python
{
  "job_id": "uuid",
  "user_id": int,
  "type": "scrape_single | scrape_auto | ai_generate | campaign_bulk",
  "status": "queued | running | completed | failed | cancelled",
  "progress": 0-100,
  "payload": {...},
  "result": {...},
  "error": str | null,
  "attempts": int,
  "created_at", "updated_at"
}
```

### 21.4 Retry handling

**`[CURRENT]`**
- Groq API: 3 retries with backoff in `_raw_chat()` for transient errors
- Apify/Groq key rotation on quota errors via `ApiKeyRotationService`
- HTTP fetch retries: `SCRAPER_FETCH_RETRIES` = 2

**`[REQUIRED]`**
- Queue jobs: max 3 attempts, exponential backoff (30s, 2m, 10m)
- Dead-letter queue for jobs failing all attempts
- Idempotent job handlers (re-run safe for same `job_id`)

### 21.5 Failed jobs

**`[CURRENT]`**
- `scraper_job_store.fail(job_id, error)` — status `failed`, error string exposed to frontend
- User sees error in scraper UI banner

**`[REQUIRED]`**
- Persist failed jobs to `scrape_job_runs` table (user-visible history)
- Notify user on failure (see §28)
- Admin dashboard for failure rate by source (Maps/Meta/Web)

### 21.6 Long-running AI tasks

| Task | Duration | Current execution |
|------|----------|-------------------|
| CV extraction | 5–30s | synchronous in upload request |
| Brain generation | 10–60s | synchronous in `/api/brain/generate` |
| Single AI message | 2–10s | synchronous in `/api/ai/generate` |
| Campaign bulk generate | N × message time | synchronous loop in campaign service |

**`[REQUIRED]`**
- Move brain generation + campaign bulk + auto-scraper to worker queue
- Return `job_id` immediately; client polls or uses SSE/WebSocket for progress
- Timeout: 120s per AI call; 30 min per scrape job

---

## 22. Scraper Reliability Rules

### 22.1 Duplicate prevention (`[CURRENT]`)

**Within scrape batch** — `app/scraper/utils/dedup.py` → `dedupe_leads_production()`:
- Keys: `web:{host}`, `email:{email}`, `phone:{phone}`, `name:{company}`
- Merges duplicates via `merge_lead_records()`

**Against existing DB** — `app/utils/lead_dedup.py` → `filter_new_leads()`:
- Builds index from user's existing leads
- Skips if any key intersects; tracks `skipped` count in scrape response

### 22.2 Retry strategy

| Layer | Retries | Backoff |
|-------|---------|---------|
| HTTP page fetch | `SCRAPER_FETCH_RETRIES` (2) | internal crawler delay |
| Groq chat | 3 | 1.2s × attempt |
| Apify actor | via Apify client | key rotation on quota |
| Playwright render | timeout `SCRAPER_PLAYWRIGHT_TIMEOUT` 14s | fail page, continue batch |

**Rule:** A single bad URL must not fail the entire scrape job — catch, log, continue.

### 22.3 Proxy support (`[REQUIRED]`)

**`[CURRENT]`** — no proxy configuration.

**Production:**
- Add `SCRAPER_PROXY_URL` (rotating residential proxy for web crawl)
- Apify handles its own proxy for Maps/Meta actors
- Respect `SCRAPER_DELAY_MIN_MS` / `SCRAPER_DELAY_MAX_MS` (60–280ms) — increase under proxy

### 22.4 Rate limits

**`[CURRENT]`** config (`app/core/config.py`):
- `SCRAPER_WORKERS` = 12 (thread pool)
- `SCRAPER_DELAY_MIN_MS` / `MAX_MS` = 60–280
- `SCRAPER_BING_PAGES` = 4
- Demo: 5 req/hour/IP

**Rules:**
- Never remove delays — prevents IP blocks
- Cap concurrent Playwright contexts (memory intensive)
- Daily scrape: once per user per day (`DailyScrapeRun` model)

### 22.5 Failed actor handling

**Apify Maps/Meta actor failure:**
- Catch exception in `ApifyService` / `MetaAdsService`
- If one source fails in `all` mode, continue with other sources; partial results OK
- Surface source-level errors in scrape response `message` field

**Empty results:**
- Do not create placeholder leads
- Return `leads_saved=0` with actionable tips (check keyword, location, API key)

### 22.6 Scraping logs (`[REQUIRED]`)

**`[CURRENT]`** — Python `logging` in services; no structured scrape audit table.

**Production log per job:**
```json
{
  "job_id": "...",
  "user_id": 1,
  "source": "google_maps",
  "keyword": "restaurant",
  "location": "Lahore, Pakistan",
  "raw_found": 120,
  "after_dedupe": 85,
  "after_filter": 40,
  "saved": 32,
  "skipped_duplicates": 48,
  "errors": ["apify timeout on page 3"],
  "duration_ms": 45000
}
```

Store in `scrape_job_logs` table; expose summary in Scraper UI history.

---

## 23. AI Sales Intelligence Engine

### 23.1 Previous limitations (`[SUPERSEDED]`)

Before this upgrade, the scraper was primarily a **data collector**:

- Basic `quality_score` from contact completeness only (`app/scraper/validators/quality.py`)
- Duplicate detection by phone/email/website/name keys only (no fuzzy name/address)
- No website opportunity analysis (HTTPS, mobile, forms, booking, SEO)
- Google Maps data limited to name/phone/website — no reviews, hours, profile score
- No buying-intent or HOT/WARM/COLD tiers for sales prioritization
- Social URLs stored but not analyzed for activity
- Meta ads mapped to leads without `is_running_ads`, ad counts, or landing-page scoring
- Contact fields not verified (format, MX, disposable email, WhatsApp readiness)
- No niche-specific pain points or recommended offers
- Crawler visited fewer paths; no structured intelligence pipeline

### 23.2 Intelligence pipeline (`[CURRENT]`)

Implemented in `app/services/intelligence/pipeline.py` → `LeadIntelligencePipeline`.

Runs automatically inside `LeadService.save_scraped_leads()` before DB insert:

```
Scrape Sources
    ↓
Data Cleaning (existing validators)
    ↓
Duplicate Detection (advanced_dedup + existing keys)
    ↓
Contact Verification
    ↓
Website Audit
    ↓
Social Intelligence
    ↓
Niche Intelligence
    ↓
Buying Intent Scoring
    ↓
AI Qualification (rule-based; Groq helper available)
    ↓
Quality Score (legacy apply_quality_to_lead)
    ↓
Save Lead
```

Returns `intelligence_stats` on scrape responses (`ScraperStartResponse.intelligence_stats`):

| Stat | Meaning |
|------|---------|
| `total_scraped` | Leads entering pipeline |
| `duplicates_removed` | Removed vs existing DB leads |
| `invalid_contacts` | No verified phone or email |
| `no_phone_leads` | Missing phone |
| `qualified_leads` | `ai_qualification == qualified` |
| `hot_leads` / `warm_leads` / `cold_leads` | Intent tier counts |
| `avg_opportunity_score` | Mean `website_opportunity_score` |
| `avg_buying_intent` | Mean `buying_intent_score` |

### 23.3 Website Opportunity Audit (`[CURRENT]`)

Service: `app/services/intelligence/website_audit_service.py`

Detects: no website, social-only/fake site, missing HTTPS, poor mobile viewport, slow load, missing contact form, booking, pricing/services pages, old-site indicators, broken fetch, poor SEO metadata.

Lead fields:

| Field | Type |
|-------|------|
| `website_quality_score` | 0–100 (higher = better site) |
| `website_opportunity_score` | 0–100 (higher = better sales opportunity) |
| `website_problems` | JSON array of human-readable issues |

### 23.4 Google Maps enrichment (`[CURRENT]`)

Service: `app/services/intelligence/maps_enrichment.py`  
Hook: `app/services/apify_service.py` → `enrich_maps_lead()` on Apify Maps items.

| Field | Source |
|-------|--------|
| `reviews_count` | Total reviews |
| `rating` | Average rating |
| `business_hours` | Opening hours text |
| `google_profile_score` | Profile completeness heuristic |
| `photos_count` | Photo count when available |

### 23.5 Buying intent scoring (`[CURRENT]`)

Service: `app/services/intelligence/buying_intent_service.py`

| Signal | Points |
|--------|--------|
| No website | +30 |
| Active social media | +20 |
| Running ads | +20 |
| High reviews | +15 |
| Recently opened | +10 |
| Poor website | +10 |
| Agency/consultant | −30 |
| Duplicate risk | −20 |
| Closed business | −20 |

Fields: `buying_intent_score` (0–100), `intent_tier` (`hot` ≥70, `warm` ≥40, else `cold`).

### 23.6 Social media intelligence (`[CURRENT]`)

Service: `app/services/intelligence/social_intelligence_service.py`

Analyzes Facebook/Instagram presence (exists, activity heuristics).  
Fields: `social_activity_score`, `social_links_verified`.

### 23.7 Meta ads intelligence (`[CURRENT]`)

Service: `app/services/intelligence/meta_enrichment.py`  
Hook: `app/utils/scrape_sources.py` → `map_meta_ad_to_lead()`.

Fields: `is_running_ads`, `ads_count`, `ad_platform`, `landing_page`, `ad_activity_score`.

### 23.8 Contact verification (`[CURRENT]`)

Service: `app/services/intelligence/contact_verification_service.py`

Phone: normalize, country detect, format validate, WhatsApp readiness.  
Email: format, domain, MX record, disposable detection.

Fields: `phone_verified`, `email_verified`, `whatsapp_ready` (also set by legacy quality scorer).

### 23.9 AI lead qualification (`[CURRENT]`)

Service: `app/services/intelligence/lead_qualification_service.py`

Rule-based qualification in pipeline (`qualify_lead_rules`). Optional Groq path: `qualify_lead_with_ai`.

Fields: `ai_qualification`, `recommended_offer`, `qualification_reason`.

### 23.10 Advanced duplicate detection (`[CURRENT]`)

Services: `app/services/intelligence/advanced_dedup.py`, `app/utils/lead_dedup.py`

Matches: phone, website host, fuzzy business name, fuzzy address (in addition to legacy email/name keys).

### 23.11 Niche intelligence (`[CURRENT]`)

Service: `app/services/intelligence/niche_intelligence.py`

Niches: `restaurant`, `salon`, `clinic`, `gym`, `hotel`, `real_estate`.

Each defines pain points, opportunity signals, recommended service.  
Fields: `niche_key`, `recommended_service`, `intelligence_meta` (JSON).

### 23.12 Improved crawler (`[CURRENT]`)

`app/scrapers/parser.py` — extended `CONTACT_PATH_HINTS` (menu, booking, pricing, about, services, contact).  
`app/scrapers/crawler_core.py` — increased link crawl depth for intelligence extraction.

### 23.13 Legacy quality scoring (`[CURRENT]` — preserved)

`app/scraper/validators/quality.py` → `score_lead_quality()` still runs at end of pipeline.

| Signal | Points |
|--------|--------|
| `company_name` present | +15 |
| `source == meta_ads` | +10 |
| Real website | +15 |
| Valid email | +25 |
| Phone present | +15 |
| WhatsApp-ready phone | +15 |
| Address / city / country / contact name | +5 each |
| Social URLs | +3 each |
| **Cap** | 100 |

Tiers: **high** (≥70 + contact + name), **medium** (≥40 + contact or site), **low** (else).

### 23.14 API endpoints (`[CURRENT]`)

| Method | Path | Response schema |
|--------|------|-----------------|
| `GET` | `/api/leads/{id}/intelligence` | `LeadIntelligenceResponse` |
| `GET` | `/api/leads/{id}/website-audit` | `LeadWebsiteAuditResponse` |
| `GET` | `/api/leads/{id}/qualification` | `LeadQualificationResponse` |

Extended `LeadResponse` includes all intelligence fields for list/detail views.

### 23.15 Database migration (`[CURRENT]`)

Alembic: `alembic/versions/002_lead_intelligence.py`  
SQLite bootstrap: `app/database/migrate.py` → `ensure_lead_columns()` on startup.

### 23.16 Tests (`[CURRENT]`)

- `tests/test_intelligence.py` — website audit, buying intent
- `tests/test_intelligence_dedup.py` — niche, contact verify, fuzzy dedup
- `tests/test_leads.py` — existing lead API + cleanup (unchanged behavior)

### 23.17 Recommended inbox sort (`[REQUIRED]` UI)

1. `intent_tier` (hot → warm → cold)
2. `buying_intent_score DESC`
3. `website_opportunity_score DESC`
4. `whatsapp_ready DESC`
5. `created_at DESC`

### 23.18 Future enhancements (`[NOT IMPLEMENTED]`)

- Playwright-based mobile/responsive audit in production pipeline
- Groq qualification enabled by default when API key present
- Re-run intelligence on existing leads (batch enrich endpoint)
- `opportunity_score` as unified sort column in Leads UI

---

## 24. AI Cost Management

### 24.1 Token tracking (`[CURRENT]` gap)

**`[CURRENT]`**
- `user_api_keys.usage_count` incremented on successful Groq/Apify calls
- `last_used_at`, `last_error` tracked per key
- No per-request token counts stored

**`[REQUIRED]`**
- Log per call: `user_id`, `operation` (cv_extract | message_gen | brain_gen | scrape_suggest), `model`, `prompt_tokens`, `completion_tokens`, `estimated_cost_usd`
- Table: `ai_usage_logs`
- Aggregate daily/monthly per user for billing enforcement

### 24.2 Usage limits (plan-based — see §25)

| Operation | Free (proposed) | Pro (proposed) |
|-----------|-----------------|----------------|
| AI messages / day | 20 | 500 |
| Brain regenerations / day | 3 | unlimited |
| CV uploads | 3 total | unlimited |
| Scrape leads / day | 100 (daily scrape) | 2000 |
| Auto-scraper | disabled | enabled |

Enforce in service layer before calling Groq:

```python
if usage_today(user_id, "ai_message") >= plan.limit:
    raise HTTPException(429, "Daily AI limit reached. Upgrade to Pro.")
```

### 24.3 Per-user AI credits (`[REQUIRED]`)

- `users.ai_credits_balance` — integer, decremented per AI operation
- Free plan: 50 credits/month (1 credit = 1 message gen)
- Pro plan: 2000 credits/month + top-up packs
- Brain generation: 5 credits; CV parse: 3 credits; message: 1 credit

### 24.4 API cost monitoring (`[REQUIRED]`)

- Dashboard (admin): daily Groq spend estimate, Apify compute units per user
- Alert if platform-wide Groq spend > budget threshold
- Per-user anomaly detection: >200 messages/hour → flag/spam review

### 24.5 Model fallback strategy

**`[CURRENT]`**
- Single model: `GROQ_MODEL` = `llama-3.1-8b-instant`

**`[REQUIRED]` fallback chain:**
1. `llama-3.1-8b-instant` (default — fast, cheap)
2. `llama-3.3-70b-versatile` (brain generation, complex CV only)
3. On 503/rate limit → retry with backoff → next key in rotation
4. On all keys exhausted → queue job for later; never infinite retry
5. Template-based fallback message if AI fully unavailable (static WhatsApp template with merge fields)

---

## 25. Billing & Subscription Architecture

> **Status:** `[NOT IMPLEMENTED]` — architecture spec for production SaaS

### 25.1 Plans

| Feature | Free | Pro ($29/mo proposed) |
|---------|------|-------------------------|
| Leads in inbox | 500 max | 10,000 |
| Saved leads | 100 | unlimited |
| Daily scrape | 1×/day, 100 leads | unlimited manual + auto-scraper |
| AI messages | 20/day | 500/day |
| Campaigns | 1 active | unlimited |
| API keys | BYOK (Groq + Apify) | BYOK + optional platform credits |
| Export | CSV | CSV + XLSX |
| Support | community | email |

### 25.2 Subscription states

```
trialing → active → past_due → cancelled → expired
                 ↘ paused
```

- `past_due`: 3-day grace, read-only access, no new scrapes
- `cancelled`: access until period end
- `expired`: data retained 30 days, then archive

### 25.3 Data model (`[REQUIRED]`)

```python
# subscriptions table
user_id, plan_id, status, stripe_subscription_id,
current_period_start, current_period_end, cancel_at_period_end

# plans table
name, stripe_price_id, limits_json  # stores numeric limits from §24.2

# usage_records table
user_id, metric, count, period_start  # for metered billing
```

### 25.4 Payment integration structure

- **Provider:** Stripe (Checkout + Customer Portal + Webhooks)
- Webhook events: `checkout.session.completed`, `invoice.paid`, `customer.subscription.updated`, `customer.subscription.deleted`
- Webhook handler: `app/routes/billing.py` → update `subscriptions` table
- Frontend: `/settings/billing` — plan picker, manage subscription link

### 25.5 Credit system

- **AI credits** (§24.3) bundled with Pro plan monthly
- **Top-up:** Stripe one-time payment → add credits to `ai_credits_balance`
- **Scrape credits:** optional — 1 credit per 10 leads saved (if moving away from pure BYOK Apify model)

---

## 26. Analytics Specification

### 26.1 Dashboard metrics (`[CURRENT]`)

`GET /api/dashboard/stats` returns:
- `total_leads`, counts by status (new, contacted, interested, follow_up, closed, lost)
- `campaign_count`, `messages_generated`

### 26.2 Metrics to add (`[REQUIRED]`)

**Leads funnel:**
- inbox count vs saved count
- cleanup deleted count (phone-only rule impact)
- conversion: inbox → saved rate
- conversion: saved → contacted rate

**Scraper analytics:**
- leads per source (google_maps, google_search, meta_ads)
- avg quality_score by source
- duplicate skip rate
- scrape job success/failure rate
- avg job duration

**Campaign analytics:**
- messages sent per campaign (when send tracking added)
- reply rate (manual user input or webhook future)
- best performing message type (whatsapp vs email vs linkedin)

**AI performance:**
- avg message length by channel
- generation latency p50/p95
- Groq error rate
- tokens used per user per day

### 26.3 Frontend analytics page (`[CURRENT]`)

`frontend/app/(app)/analytics/page.tsx` — extend with Recharts using above metrics.

### 26.4 Event tracking (`[REQUIRED]`)

```python
# analytics_events table
user_id, event_name, properties_json, created_at

# Key events:
scrape_started, scrape_completed, lead_saved, lead_deleted,
cleanup_run, message_generated, campaign_created, outreach_clicked
```

---

## 27. Notification System

### 27.1 In-app notifications

**`[CURRENT]` for email outreach** — `outreach_notifications` table + `GET /api/email-outreach/notifications`; shown on Email Outreach page.

**`[REQUIRED]` for scraper/campaigns** — global bell icon, WebSocket push.

Types (outreach): `agent_started`, `email_sent`, `lead_processed`, `reply_received`, etc.

### 27.2 Email notifications

**`[CURRENT]`** — SMTP configured for OTP only (`app/services/otp_service.py`).

**Extend for:**
- Scrape job completed (summary: X leads saved)
- Scrape job failed (error + retry link)
- Weekly digest: new leads, outreach reminders
- Billing: payment failed, subscription expiring

Use queue (`email_jobs`) — never send SMTP inline in request handler.

### 27.3 Scraper completion alerts

Trigger on `scraper_job_store.complete()` and `.fail()`:
```python
notify_user(user_id, type="scrape_complete", data={
  "leads_saved": result.leads_saved,
  "job_id": job_id,
  "duration": "...",
})
```

### 27.4 Campaign alerts

- Campaign bulk message generation complete
- `[FUTURE]` Campaign send complete (when WhatsApp API integration added)

---

## 28. Compliance & Outreach Safety

### 28.1 Spam prevention (`[CURRENT]` + rules)

**`[CURRENT]`**
- `sanitize_paid_outreach_message()` — removes "free" hooks
- `HUMAN_TOUCH_OUTREACH_RULES` in prompts — no spam wording
- Message length caps enforced post-generation
- Demo scrape rate limited

**`[REQUIRED]` rules:**
- Max 50 AI messages per hour per user (hard cap)
- Max 20 outreach clicks tracked per hour (wa.me opens) — warn user
- Flag identical messages sent to >10 leads (template spam detection)
- Require user to confirm bulk campaign send with recipient count

### 28.2 Message limits by channel

| Channel | Limit | Enforcement |
|---------|-------|-------------|
| WhatsApp (manual) | user sends via own WA | UI warning: max 50 new contacts/day |
| Email | 100/day free, 500/day pro | future SMTP send integration |
| LinkedIn | 20 connection notes/day | UI reminder only |

### 28.3 Opt-out handling (`[REQUIRED]`)

- Add lead field: `opted_out: bool`, `opted_out_at`, `opt_out_reason`
- Block message generation for opted-out leads
- Add `lost` status + notes as manual opt-out today
- Email: include opt-out line in template when platform sending enabled

### 28.4 WhatsApp compliance

- This app generates messages + `wa.me` links — **user sends manually** (no WhatsApp Business API yet)
- UI disclaimer: user must comply with WhatsApp Business Policy and local laws
- Never auto-send WhatsApp messages without explicit user action per message
- Do not scrape personal WhatsApp numbers from non-business sources

### 28.5 Email compliance (`[REQUIRED]` for future sending)

- CAN-SPAM / GDPR: physical address in footer, unsubscribe link
- Only email leads with publicly listed business emails from scrape
- Validate email with `is_valid_email()` before outreach (already done)
- Log consent basis: "legitimate interest — B2B cold outreach to business contact"

### 28.6 Data scraping compliance

- Scrape only publicly available business information
- Respect `robots.txt` in web crawl mode
- Apify actors used per their ToS
- Do not scrape EU personal data without GDPR review for production EU launch

---

## 29. Backup & Recovery

### 29.1 Database backups

**`[CURRENT]`** — SQLite file `leadgen.db`; no automated backup.

**Production (PostgreSQL):**
- Automated daily snapshots (managed DB: RDS/Supabase/Neon)
- Point-in-time recovery enabled (7–30 days)
- Pre-migration manual snapshot before every `alembic upgrade`
- Test restore monthly

### 29.2 File backups

- `uploads/` (CV files) → replicate to S3 with versioning
- `exports/` → ephemeral; regenerate on demand; optional 7-day retention

### 29.3 Restore process

1. Stop API + workers
2. Restore DB snapshot to staging first; verify row counts
3. Restore file bucket version if needed
4. Run `alembic current` — must match expected revision
5. Smoke test login + lead list + scrape
6. Switch DNS/traffic

**RTO target:** 4 hours · **RPO target:** 24 hours (daily backup)

### 29.4 Disaster recovery

- Multi-AZ database in production
- API stateless — redeploy from container image anywhere
- Document runbook in `docs/runbooks/disaster-recovery.md` `[REQUIRED]`
- Keep secrets in vault — not in backups

---

## 30. Monitoring & Logging

### 30.1 Application logs (`[CURRENT]`)

- Python `logging` module in services
- Uvicorn access logs to stdout
- OTP dev mode logs codes to console

**`[REQUIRED]`**
- Structured JSON logs: `timestamp, level, request_id, user_id, path, duration_ms, message`
- Middleware: assign `X-Request-ID` per request; propagate to worker jobs
- Log levels: INFO for business events, WARNING for retries, ERROR for failures

### 30.2 Error tracking (`[REQUIRED]`)

- Integrate Sentry (backend + frontend)
- Capture: unhandled exceptions, Groq 502s, Apify actor failures, 500 rate
- Alert on error rate > 5% over 5 min

### 30.3 Performance monitoring (`[REQUIRED]`)

- APM: scrape job duration, AI generation latency, DB query time
- `/health` extended: DB connectivity, Redis ping, disk space
- Uptime monitor on `/health` every 60s (Better Uptime / Pingdom)

### 30.4 Audit logs (`[REQUIRED]`)

Immutable log for security-sensitive actions:

```
user_id, action, resource_type, resource_id, ip, user_agent, created_at
```

Actions: login, logout, api_key_created, api_key_deleted, lead_export, bulk_delete, account_delete, plan_change

Store in `audit_logs` table; admin read-only access; 1-year retention.

---

## 31. Testing Strategy

### 31.1 Backend tests (`[CURRENT]` — 36 test files)

```bash
pytest -v                    # full suite
pytest tests/test_leads.py   # lead CRUD + cleanup rules
pytest tests/test_auth.py    # JWT auth
pytest tests/test_otp_auth.py
pytest tests/test_ai.py      # AI endpoints (mocked Groq)
pytest tests/test_auto_scraper.py
pytest tests/test_lead_dedup.py
pytest tests/test_scraper_job_store.py
pytest tests/test_user_api_keys.py
```

**Coverage priorities:**
- `lead_service.py` — phone-only cleanup, save, bulk ops
- `contact_links.py`, `outreach_tone.py` — message safety
- `quality.py` — scoring tiers
- `api_key_rotation_service.py` — quota failover

### 31.2 Frontend tests (`[REQUIRED]`)

Not in repo yet. Add:
- Vitest + React Testing Library
- Test: `LeadContactActions` renders correct buttons per `contact_links`
- Test: leads page cleanup button calls correct API + shows toast
- Test: auth guard redirects unauthenticated users

### 31.3 Integration tests (`[REQUIRED]`)

- Full flow: register → upload CV → start scrape (mocked Apify) → leads appear → cleanup → save → generate message
- IDOR: user A token cannot access user B lead by ID
- Scraper job lifecycle: start → poll → complete

### 31.4 Security tests (`[REQUIRED]`)

- JWT expired / tampered token → 401
- SQL injection on search `q` param → no leak
- File upload: reject `.exe` renamed as `.pdf`
- Rate limit: 6th demo scrape in 1 hour → 429
- CORS: reject unknown origin in production config

### 31.5 Load tests (`[REQUIRED]`)

Tool: k6 or Locust

Scenarios:
- 50 concurrent users listing leads (paginated)
- 10 concurrent scrape job starts (should queue, not crash)
- 100 AI generate requests/min with mocked Groq

**SLO targets:**
- API p95 latency < 500ms (non-scrape endpoints)
- Scrape job enqueue < 200ms
- 99.9% uptime

### 31.6 CI command (`[REQUIRED]`)

```bash
# Minimum pre-merge
pytest -v --tb=short
cd frontend && npm run lint && npm run build
```

---

## 32. Future Roadmap

### 32.1 CRM integrations
- Export/sync leads to HubSpot, Pipedrive, Google Sheets
- Webhook on `lead_saved` event for Zapier/Make
- Two-way status sync (contacted → CRM deal stage)

### 32.2 Team accounts
- Organization model: `organizations`, `organization_members` (owner, member, viewer)
- Shared lead pool with assignee per lead
- Team billing (one Stripe subscription, seat-based)

### 32.3 Advanced AI agents
- **`[CURRENT]`** AI Email Outreach Agent — Gmail, auto-generate, send, follow-up scheduling, inbox sync, reply drafts
- Autonomous follow-up sequences with scheduled dates (user can disable via `auto_follow_up`)
- AI lead qualification agent: auto-score + auto-save P1 leads `[REQUIRED]`
- Voice note → WhatsApp message generator `[NOT IMPLEMENTED]`
- Multi-language outreach (Urdu/English auto-detect from lead country) `[NOT IMPLEMENTED]`

### 32.4 Automated follow-ups
- **`[CURRENT]`** Email follow-ups — steps with `delay_days`; status `queued` until `scheduled_at`; agent cycle enqueues send when due
- Schedule follow-up messages in campaign (uses `MessageType.follow_up`)
- Pause on reply detection (manual mark as `interested`)
- Drip campaigns with daily send limits

### 32.5 Marketplace features
- Template marketplace: proven outreach templates by industry (restaurant, salon, clinic)
- Scrape recipe marketplace: share keyword + location + source presets
- Verified freelancer directory (optional monetization)

### 32.6 Engineering priorities (ordered)

1. PostgreSQL + persistent job queue (blocks scale)
2. API key encryption + refresh tokens (blocks security audit)
3. Stripe billing + usage limits (blocks monetization)
4. Notification system (blocks user retention)
5. Team accounts + CRM webhooks (blocks B2B expansion)

---

## 33. AI Email Outreach Agent (`[CURRENT]`)

### 33.1 User flow

```
Settings → Connect Gmail (OAuth)
    ↓
Email Outreach page → configure automation settings
    ↓
Click "Start AI Agent"
    ↓
Pilot email sent immediately (first lead with email)
    ↓
Daily batch scheduled (default 10 min delay) for today's leads
    ↓
Follow-ups auto-scheduled after initial send (if auto_follow_up enabled)
    ↓
Agent cycles every 2 min while running (sync inbox, due follow-ups, new leads)
```

### 33.2 Key API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/email-outreach/oauth/google/start` | Begin Gmail OAuth |
| `GET` | `/api/email-outreach/oauth/google/callback` | OAuth callback (via frontend proxy) |
| `GET` | `/api/email-outreach/settings` | Automation settings |
| `PATCH` | `/api/email-outreach/settings` | Update limits, review, auto-send, working hours |
| `POST` | `/api/email-outreach/agent/start` | Start agent; returns `pilot_email` object |
| `POST` | `/api/email-outreach/agent/stop` | Stop agent |
| `POST` | `/api/email-outreach/agent/pause` | Pause agent |
| `POST` | `/api/email-outreach/agent/resume` | Resume agent |
| `GET` | `/api/email-outreach/agent/status` | Agent state + limits remaining |
| `GET` | `/api/email-outreach/agent/activity` | Activity log feed |
| `GET` | `/api/email-outreach/dashboard` | Rich stats for UI |
| `GET` | `/api/email-outreach/emails` | List outreach emails (includes `body_text`) |
| `GET` | `/api/email-outreach/notifications` | In-app notifications |
| `GET` | `/api/email-outreach/timeline/{lead_id}` | Per-lead email timeline |

### 33.3 Agent settings (`email_outreach_settings`)

| Setting | Default | Notes |
|---------|---------|-------|
| `automation_enabled` | false | Must be on for sends |
| `auto_send_enabled` | false | If false + require_review, emails stay `pending_review` |
| `require_review` | true | Pilot emails bypass this |
| `auto_follow_up` | true | Schedules follow-up emails after initial send |
| `daily_send_limit` | 50 | Enforced in `send.py` |
| `hourly_send_limit` | 10 | Enforced in `send.py` |
| `working_hours_start` / `end` | 9 / 18 | Sends blocked outside hours (pilot bypasses) |
| `agent_batch_delay_minutes` | 10 | Delay before daily batch on agent start |
| `agent_running` / `agent_paused` | false | Agent state flags |

### 33.4 Email status meanings

| Status | Meaning |
|--------|---------|
| `pending_review` | AI generated; waiting for user approval |
| `queued` | Ready to send OR follow-up waiting for `scheduled_at` |
| `sending` | Transport in progress |
| `sent` | Successfully sent via Gmail |
| `failed` | Send error (see `error_message`) |
| `verification_failed` | Email failed MX/format verification |

**UI tip:** Follow-ups with future `scheduled_at` display badge **scheduled** + date, not just "queued".

### 33.5 Pilot email (`agent.start`)

On `start_agent()`:
1. Finds first lead: today's unprocessed → else any saved lead with email
2. Calls `process_single_lead(..., pilot=True)` synchronously
3. Returns `pilot_email: { to_email, subject, body_text, status }` in API response
4. Enqueues `send_email` job with `pilot: true` (high priority, bypasses working hours + review)

### 33.6 Job queue (`outreach_jobs`)

| Job type | Purpose |
|----------|---------|
| `send_email` | Send one outreach email or reply draft |
| `agent_cycle` | Run full agent loop for user |
| `sync_inbox` | Fetch Gmail inbox for replies |
| `process_lead` | Generate email for one lead |
| `process_campaign` | Batch campaign processing |
| `schedule_followups` | Create follow-up email rows |

Idempotency via `idempotency_key`; duplicate key cleared on job complete. Use `as_utc()` when comparing `scheduled_at` from SQLite.

### 33.7 Key files

| Concern | File |
|---------|------|
| Agent logic | `app/services/email_outreach/agent.py` |
| Worker loop | `app/services/email_outreach/worker.py` |
| Job queue | `app/services/email_outreach/job_queue.py` |
| Send + rate limits | `app/services/email_outreach/send.py` |
| AI email generation | `app/services/email_outreach/generation.py` |
| Inbox sync | `app/services/email_outreach/sync.py` |
| Gmail OAuth | `app/services/email_outreach/oauth.py` |
| API routes | `app/routes/email_outreach.py` |
| Schemas | `app/schemas/email_outreach.py` |
| DB models | `app/models/email_outreach.py` |
| Lead save hook | `app/services/lead_service.py` → `on_leads_saved` |
| Startup migration | `app/database/migrate.py` → `ensure_outreach_settings_columns()` |
| Frontend page | `frontend/app/(app)/email-outreach/page.tsx` |
| Frontend hooks | `frontend/hooks/useEmailOutreach.ts` |
| Types | `frontend/lib/types.ts` |
| Datetime helper | `app/utils/datetime_utils.py` |

### 33.8 Standing campaign

Auto-created campaign: **"AI Agent — Auto Outreach"** (`STANDING_CAMPAIGN_NAME` in `agent.py`). Stored in `settings.standing_campaign_id`.

### 33.9 Debug checklist

1. Gmail connected? `GET /api/email-outreach/agent/status` → `gmail_connected`
2. `automation_enabled` + `auto_send_enabled` on? Or approve `pending_review` emails
3. Daily/hourly limit hit? Check dashboard `emails_remaining_today`
4. Outside working hours? Status stays `queued` with error in job (except pilot)
5. Worker running? `OUTREACH_WORKER_ENABLED=true` in `.env`
6. Stuck jobs? Query `outreach_jobs` where `status='failed'` or `error_message` set
7. API 500? Check backend terminal for datetime comparison errors — ensure `as_utc()` used

---

## Document conventions for AI coding agents

- **`[CURRENT]`** — behavior in codebase today; do not break without explicit request
- **`[REQUIRED]`** — production gap; safe to implement when task says "productionize"
- **`[NOT IMPLEMENTED]`** — spec only; no code exists yet
- When editing leads logic, always preserve §7 phone-only cleanup rules and `is_saved` inbox/saved split
- When editing AI messages, always preserve §7 paid-service + human-touch rules in `outreach_tone.py` and `prompts.py`
- When comparing datetimes from SQLite, use `app/utils/datetime_utils.as_utc()` — DB returns naive UTC
- When editing outreach worker/job queue, preserve idempotency key cleanup on job complete (see `job_queue.py`)
- Prefer minimal diffs; match existing repository → service → route layering
