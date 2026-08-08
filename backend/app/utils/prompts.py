from app.utils.outreach_tone import FIRST_MESSAGE_OUTREACH_RULES, HUMAN_TOUCH_OUTREACH_RULES

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

WHATSAPP_PROMPT = """Write a short first WhatsApp message like a real person — not a sales bot.

{language_rules}

Rules:
- 2-3 short sentences max, under 180 characters
- Use the greeting from LANGUAGE rules (respect — even if no personal name is available)
- Introduce yourself (first name) + what you do for businesses like theirs
- Reference their business name or city once
- Soft CTA only (open to a quick chat?)
- NO price, NO package cost, NO numbers — pricing only later if they ask
""" + HUMAN_TOUCH_OUTREACH_RULES + FIRST_MESSAGE_OUTREACH_RULES + """

Lead Info:{lead_info}

Sender CV Profile:
{cv_profile}

Return ONLY the message text, no quotes or labels."""

EMAIL_PROMPT = """Write a short first cold email like a real person — not a sales letter.

{language_rules}

Rules:
- subject: under 45 characters, specific to their business (same language as body)
- body: 3-4 short lines max (under 90 words), conversational
- Use the greeting from LANGUAGE rules for respect (even without a personal name)
- cta: one soft line inviting a reply
- Introduce sender + one service you do for local businesses like theirs
- NO price, NO package cost, NO numbers in this first email
""" + HUMAN_TOUCH_OUTREACH_RULES + FIRST_MESSAGE_OUTREACH_RULES + """

Lead Info:{lead_info}

Sender CV Profile:
{cv_profile}

Return ONLY valid JSON with keys: subject, body, cta"""

LINKEDIN_PROMPT = """Write a brief LinkedIn connection note like a real professional — not a pitch deck.

{language_rules}

Rules:
- Under 200 characters
- Who you are + one soft question
- One relevant service only
- NO price or package numbers
""" + HUMAN_TOUCH_OUTREACH_RULES + FIRST_MESSAGE_OUTREACH_RULES + """

Lead Info:{lead_info}

Sender CV Profile:
{cv_profile}

Return ONLY the message text, no quotes or labels."""

FOLLOW_UP_PROMPT = """Write a short, friendly follow-up — like a real person checking in.

{language_rules}

Rules:
- 2 sentences max, under 180 characters
- Light reminder of your last message, not pushy
- One soft question to invite a reply
- Still NO price unless they already asked in the thread
""" + HUMAN_TOUCH_OUTREACH_RULES + FIRST_MESSAGE_OUTREACH_RULES + """

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

CV_SCRAPE_SUGGEST_PROMPT = """You are a lead-generation strategist. Read the AI Brain / CV profile carefully, then suggest Google Maps keywords for LOCAL businesses that would BUY this person's services.

Profile JSON (read ALL of it — name, services, skills, summary, experience, projects, custom_notes):
{profile}

Scrape mode: {scrape_source}
Website preference: {website_preference}
- without_website: prioritize small shops that often have NO real website (phone leads for WhatsApp outreach)
- with_website: prioritize businesses that typically HAVE a website (so we can also scrape emails/Gmail from their site)
- all: mix of both

TARGET TYPE (critical):
- ONLY local physical businesses: restaurant, cafe, salon, barber, dental clinic, gym, plumber, electrician, bakery, boutique, florist, auto repair, veterinary clinic, etc.
- NEVER target: web agencies, marketing agencies, software companies, SaaS, freelancers, or competitors like the user

How to use the CV/Brain:
- Infer what the person SELLS (web design, SEO, ads, branding, etc.) from services + summary + experience
- Suggest buyer niches that match that offer (e.g. web designer → restaurants, salons, clinics)
- Use custom_notes for niche hints — but NEVER invent cities/countries (user sets location)

Rules:
- Keywords: 1-3 words, Maps place categories (e.g. "beauty salon", "dental clinic")
- Search queries: business type + contact words (phone, email, whatsapp) — NO city/country
- If website_preference is with_website: strategy_tips should mention scraping emails from their sites
- If without_website: strategy_tips should mention phone/WhatsApp outreach to no-site businesses
- Give 4–6 distinct keyword options rooted in THIS profile (not generic filler)

Return ONLY valid JSON with keys:
- recommended_keyword (string)
- recommended_search_query (string, under 120 chars, NO location)
- keyword_suggestions (array of 4–6 local business type strings)
- search_queries (array of 5 strings, NO city/country)
- strategy_tips (string, 2–3 sentences: what the CV sells + which keywords to apply + why)
"""

BRAIN_GENERATION_PROMPT = """You are an expert AI prompt engineer. Create a comprehensive "AI Brain" system prompt for a sales/outreach assistant focused on LOCAL business lead generation.

This brain will power personalized WhatsApp, email, and LinkedIn messages to local brick-and-mortar business owners.

Professional profile data:
{profile}

Custom notes from user:
{custom_notes}

The ideal customer is a LOCAL business owner — restaurant, salon, clinic, shop, tradesperson, gym, etc. — NOT another agency or online-only company.

Generate a detailed system prompt that includes:
1. Persona and tone: warm human salesperson — contractions, short lines, never robotic or corporate
2. Sender identity (name, role, expertise)
3. Core services and value propositions for LOCAL businesses
4. Key skills and technologies to mention when relevant
5. Experience highlights to build credibility
6. FIRST MESSAGE RULES: always open with "Hi sir," for respect (even if only a phone number / no name); introduce who you are + what work you do; soft CTA; NEVER quote price/package/numbers in the first message
7. Channel style: WhatsApp 2-3 lines (~180 chars), LinkedIn under 200 chars, email body under 90 words
8. When the lead has no website or weak online presence, pitch a modern website / Google presence professionally (still no price in first message)
9. Always reference the lead's business name, city, and category — sound local and specific
10. Never pitch to marketing agencies, web agencies, or SaaS companies — only local physical businesses
11. PAID SERVICE ONLY: never offer free quotes, trials, audits, consultations, or discounts as hooks
12. PRICING / PACKAGE (use numbers from the profile when present, else USD 300–1000):
    - Quote HIGH / list price ONLY after the customer asks about price/cost/package
    - If they say "ok" → confirm and lock next step
    - If they say "less" / give a lower budget → auto-adjust to a smaller package/scope and counter toward mid, never below FLOOR
    - Close like a human: clear, kind, decisive — not pushy, not vague

Return ONLY the system prompt as plain text (400-900 words).Start with "You are..." — no JSON, no markdown fences, no labels or preamble.
"""
