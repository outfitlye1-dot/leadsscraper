export const SCRAPER_STAGE_LABELS: Record<string, string> = {
  pending: "Waiting",
  init: "Starting",
  google_maps: "Google Maps",
  web_search: "Internet",
  meta_ads: "Meta Ads",
  parallel: "Parallel scrape",
  merge: "Merging results",
  filter: "Filtering",
  enrich: "Enriching contacts",
  save: "Saving leads",
  whatsapp: "AI WhatsApp messages",
  done: "Complete",
  error: "Error",
};

export function scraperStageLabel(stage: string): string {
  return SCRAPER_STAGE_LABELS[stage] ?? stage.replace(/_/g, " ");
}
