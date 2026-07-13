from app.utils.outreach_tone import HUMAN_TOUCH_OUTREACH_RULES, PAID_SERVICE_OUTREACH_RULES

CV_EXTRACTION_PROMPT = """Extract structured information from the following CV/resume text.
Return ONLY valid JSON with these keys:
- name (string)
- skills (array of strings)
- experience (array of objects with title, company, duration, description)
- education (array of objects with degree, institution, year)
- projects (array of objects with name, description)
- services (array of strings - professional services offered)
- tools (array of strings)
- technologies (array of strings)

CV Text:
{raw_text}
"""

CV_SUMMARY_PROMPT = """Based on this parsed CV profile, generate professional summaries.
Return ONLY valid JSON with these keys:- professional_summary (2-3 sentence overview)
- skills_summary (concise paragraph about key skills)
- services_summary (concise paragraph about services offered)
- experience_summary (concise paragraph about experience)

Parsed Profile:
{profile}
"""

WHATSAPP_PROMPT = """Write a short WhatsApp message like a real person would send — not a marketing blast.

Rules:
- 2-3 short sentences max, under 180 characters total
- Mention sender first name + one relevant service only
- Reference the lead's business name or city once
- Soft CTA: ask if they're open to chat or want details
""" + HUMAN_TOUCH_OUTREACH_RULES + PAID_SERVICE_OUTREACH_RULES + """

Lead Info:{lead_info}

Sender CV Profile:
{cv_profile}

Return ONLY the message text, no quotes or labels."""

EMAIL_PROMPT = """Write a short, human cold email — not a long sales letter.

Rules:
- subject: under 45 characters, specific to their business
- body: 3-4 short lines max (under 90 words), conversational tone
- cta: one short line inviting a reply
- Mention sender name + one service; reference lead business naturally
""" + HUMAN_TOUCH_OUTREACH_RULES + PAID_SERVICE_OUTREACH_RULES + """

Lead Info:{lead_info}

Sender CV Profile:
{cv_profile}

Return ONLY valid JSON with keys: subject, body, cta"""

LINKEDIN_PROMPT = """Write a brief LinkedIn connection note like a real professional — not a pitch deck.

Rules:
- Under 200 characters
- One sentence why you're connecting + one soft question
- Mention one relevant service only
""" + HUMAN_TOUCH_OUTREACH_RULES + PAID_SERVICE_OUTREACH_RULES + """

Lead Info:{lead_info}

Sender CV Profile:
{cv_profile}

Return ONLY the message text, no quotes or labels."""

FOLLOW_UP_PROMPT = """Write a short, friendly follow-up — like a real person checking in.

Rules:
- 2 sentences max, under 180 characters
- Light reminder of your last message, not pushy
- One soft question to invite a reply
""" + HUMAN_TOUCH_OUTREACH_RULES + PAID_SERVICE_OUTREACH_RULES + """

Lead Info:{lead_info}

Sender CV Profile:
{cv_profile}

Return ONLY the message text, no quotes or labels."""

SEARCH_QUERY_OPTIMIZE_PROMPT = """You help optimize internet lead-generation search queries.

The user wants to find business leads (companies with contact info) via web search.

User query:
{query}

Target location (add to query if missing — prefer this over any default):
{location}

Fix spelling, grammar, and structure. Ensure the query includes:
- business/niche type
- city and country from the target location above (if location is empty, use London, United Kingdom)
- words like contact, email, or phone for better lead results

Return ONLY valid JSON with keys:
- optimized_query (string, single best query under 120 chars)
- suggestions (array of 3-4 alternative query strings)
- tips (short string explaining what you fixed, in plain English)
- was_corrected (boolean, true if you changed the query meaningfully)
"""

CV_SCRAPE_SUGGEST_PROMPT = """You are a lead-generation strategist for LOCAL business outreach. Based on this AI Brain profile, suggest scraping targets: real local brick-and-mortar businesses who would BUY this person's services.

Profile JSON (from AI Brain — use custom_notes, services, skills, professional_summary):
{profile}

Scrape mode: {scrape_source}
- google_maps: suggest business-type keywords only (user enters city/location manually in the scraper form)
- google_search: suggest full internet search query templates with contact keywords (no city names)
- all: suggest all of the above

TARGET TYPE (critical):
- ONLY local physical businesses: restaurant, cafe, salon, barber, dental clinic, gym, plumber, electrician, bakery, boutique, florist, auto repair, veterinary clinic, real estate office, law firm (local), etc.
- These are Google Maps "places" with a street address in a city
- NEVER target: web agencies, marketing agencies, software companies, SaaS, freelancers, e-commerce brands, or other service providers like the user

Rules:
- Target businesses that would BUY this person's services (not competitors doing the same thing)
- PRIORITY: local small businesses that likely have NO real website yet
- Keywords must be 1-3 words, Google Maps place categories (e.g. "restaurant", "beauty salon", "dental clinic") — NOT "web agency" or "marketing agency"
- If profile offers websites/digital/SEO, target restaurants, salons, clinics, trades, retail shops
- Read custom_notes for niche and intent — but DO NOT output cities, countries, or locations (user sets location themselves)
- Search queries: business type + contact keywords only (phone, email, whatsapp) — NO city or country names
- strategy_tips: explain which LOCAL business types to target and why (2-3 sentences)

Return ONLY valid JSON with keys:
- recommended_keyword (string, a local business type e.g. "restaurant")
- recommended_search_query (string, under 120 chars, business type + contact keywords, NO location)
- keyword_suggestions (array of 4 local business type strings for Google Maps)
- search_queries (array of 5 strings for internet search, NO city/country names)
- strategy_tips (string)
"""

BRAIN_GENERATION_PROMPT = """You are an expert AI prompt engineer. Create a comprehensive "AI Brain" system prompt for a sales/outreach assistant focused on LOCAL business lead generation.

This brain will power personalized WhatsApp, email, and LinkedIn messages to local brick-and-mortar business owners.

Professional profile data:
{profile}

Custom notes from user:
{custom_notes}

The ideal customer is a LOCAL business owner — restaurant, salon, clinic, shop, tradesperson, gym, etc. — NOT another agency or online-only company.

Generate a detailed system prompt that includes:
1. Persona and tone (professional, friendly, not spammy)
2. Sender identity (name, role, expertise)
3. Core services and value propositions for LOCAL businesses
4. Key skills and technologies to mention when relevant
5. Experience highlights to build credibility
6. Rules for outreach: SHORT messages with human touch — WhatsApp 2-3 lines (~180 chars), LinkedIn under 200 chars, email body under 90 words; sound like a real person, not a sales bot
7. How to adapt messages per channel (WhatsApp casual, email brief, LinkedIn one-liner)
8. When the lead has no website or weak online presence, pitch a modern website / Google presence professionally
9. Always reference the lead's business name, city, and category (e.g. salon, restaurant) — sound local and specific
10. Never pitch to marketing agencies, web agencies, or SaaS companies — only local physical businesses
11. PAID SERVICE ONLY: never offer free quotes, trials, audits, consultations, or discounts — all outreach must reflect paid professional packages from $300 to $1,000 USD depending on scope, and invite discussion of requirements and pricing

Return ONLY the system prompt as plain text (400-900 words).Start with "You are..." — no JSON, no markdown fences, no labels or preamble.
"""
