export type WebsiteFilterPref = "without_website" | "with_website" | "all";

export type ScrapePrefs = {
  website_filter: WebsiteFilterPref;
  enrich_emails: boolean;
};

const STORAGE_KEY = "leadgen-scrape-prefs";

const VALID: WebsiteFilterPref[] = ["without_website", "with_website", "all"];

export function readScrapePrefs(): ScrapePrefs | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ScrapePrefs>;
    const wf = parsed.website_filter;
    if (!wf || !VALID.includes(wf)) return null;
    return {
      website_filter: wf,
      enrich_emails: Boolean(parsed.enrich_emails) && wf !== "without_website",
    };
  } catch {
    return null;
  }
}

export function writeScrapePrefs(prefs: ScrapePrefs) {
  if (typeof window === "undefined") return;
  const website_filter = VALID.includes(prefs.website_filter)
    ? prefs.website_filter
    : "without_website";
  const enrich_emails =
    website_filter !== "without_website" && Boolean(prefs.enrich_emails);
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ website_filter, enrich_emails })
  );
}
