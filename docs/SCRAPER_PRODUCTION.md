# Production Scraper Upgrade

This document describes the production-grade scraping layer added under `app/scraper/` and how it integrates with the existing FastAPI lead pipeline.

## Root causes fixed (bad / missing data)

| Issue | Cause | Fix |
|-------|--------|-----|
| Missing address / owner | Parser only extracted email/phone/social | JSON-LD + schema.org address, `founder`, `contactPoint` parsing |
| No Facebook links | Not extracted from HTML | `extract_facebook_urls()` + parser wiring |
| City/country always from search | Page metadata ignored | `addressLocality` / `addressCountry` from structured data |
| Duplicates across sources | Dedup by website host only | Multi-key dedup: email + phone + website |
| JS sites empty | 8s timeout, no retry, static UA | Retries, rotating UA, Playwright `networkidle` + per-context stealth |
| Thin success telemetry | No persisted metrics | `ScrapeMetrics` returned in scraper job result |

## Architecture

```
app/scraper/
  api/           # Dashboard formatting for API responses
  logging/       # Structured scrape logs (FETCH_OK, LEAD_REJECT, …)
  metrics.py     # Thread-safe telemetry
  storage/       # CSV + Excel exporters
  utils/         # UA rotation, retries, delays, dedup
  validators/    # Email, phone, website, quality scoring
```

Existing crawl code remains in `app/scrapers/` and is upgraded in place (`fetcher.py`, `playwright_pool.py`, `parser.py`, `crawler_core.py`).

## Features

### 1. Retries & anti-blocking
- `PageFetcher`: up to `SCRAPER_FETCH_RETRIES` (default 3) with exponential backoff
- Random delays between requests (`SCRAPER_DELAY_MIN_MS` / `SCRAPER_DELAY_MAX_MS`)
- Rotating user agents on every HTTP request
- Playwright: isolated browser contexts, stealth launch args, `networkidle` wait with DOM fallback

### 2. Dynamic content
- Playwright waits for `networkidle` then additional random delay before `page.content()`
- Requests fallback when static HTML is sufficient

### 3. Pagination
- Bing search paginates up to `SCRAPER_BING_PAGES` (default 3) via `first=` offset

### 4. Deduplication
`dedupe_leads_production()` merges on:
- Normalized website host
- Lowercased email
- Normalized phone (E.164 when possible)

### 5. Validation
- `validators/email_validator.py` — format + MX (via existing `is_valid_email`)
- `validators/phone_validator.py` — libphonenumber mobile checks
- `validators/website_validator.py` — real business URL check

### 6. Quality scoring
Each lead gets `quality_score` (0–100) and `quality_tier`:
- **high** — company + verified contact + strong field coverage
- **medium** — company + contact or website
- **low** — minimal record

Stored on `leads.quality_score`, `leads.quality_tier`, `leads.whatsapp_ready`.

### 7. Exports
- CSV: existing `/api/leads/export`
- Excel: `/api/leads/export?format=xlsx`
- SQLite: unchanged (`leadgen.db`)

### 8. Scrape dashboard metrics
`ScraperStartResponse.scrape_metrics` includes:
- `total_pages_scanned`, `total_leads_found`, `valid_emails_found`
- `success_rate`, `failed_requests`
- Quality breakdown (`high_quality`, `medium_quality`, `low_quality`)

Poll via `GET /api/scraper/jobs/{job_id}` when using background scraper.

### 9. Logging
Logger `scraper.production` emits:
- `FETCH_OK` / `FETCH_FAIL`
- `LEAD_OK` / `LEAD_REJECT`

## Configuration (`.env` / `config.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `SCRAPER_TIMEOUT` | 12.0 | HTTP/Playwright timeout (seconds) |
| `SCRAPER_FETCH_RETRIES` | 3 | Max fetch attempts |
| `SCRAPER_DELAY_MIN_MS` | 200 | Min random delay |
| `SCRAPER_DELAY_MAX_MS` | 900 | Max random delay |
| `SCRAPER_WORKERS` | 8 | Parallel crawl threads |
| `SCRAPER_BING_PAGES` | 3 | Bing pagination depth |
| `SCRAPER_ENABLE_PLAYWRIGHT` | true | JS fallback |

## Running tests

```bash
pytest tests/test_scraper_production.py -v
pytest tests/ -v
```

## Dependencies added

- `openpyxl` — Excel export

Existing: `playwright`, `phonenumbers`, `extruct`, `trafilatura`.

## Playwright browsers

If Playwright fetches fail locally:

```bash
playwright install chromium
```
