export type LeadStatus =
  | "new"
  | "contacted"
  | "interested"
  | "follow_up"
  | "closed"
  | "lost";

export type LeadOutreachEmailStatus = "none" | "awaiting_reply" | "replied";

export type MessageType = "whatsapp" | "email" | "linkedin" | "follow_up";

export type CampaignStatus = "draft" | "active" | "paused" | "completed";

export interface User {
  id: number;
  name: string;
  email: string;
  avatar_url?: string | null;
  role: string;
  api_access?: boolean;
  plan?: "free" | "paid";
  daily_token_limit?: number;
  tokens_used_today?: number;
  tokens_remaining?: number | null;
  own_api_keys_enabled?: boolean;
  own_api_keys_requested?: boolean;
  paid_plan_requested?: boolean;
  created_at: string;
  updated_at: string;
}

export interface UsageQuota {
  plan: string;
  daily_token_limit: number;
  tokens_used_today: number;
  tokens_remaining: number;
  tokens_reset_on: string;
  api_access: boolean;
  own_api_keys_enabled: boolean;
  own_api_keys_requested: boolean;
  paid_plan_requested?: boolean;
  is_unlimited: boolean;
  paid_plan_tokens: number;
}

export interface PlanOption {
  id: string;
  name: string;
  price_usd: number;
  daily_tokens: number;
  features: string[];
  is_current: boolean;
}

export interface PlansCatalog {
  current_plan: string;
  paid_plan_requested: boolean;
  checkout_url?: string | null;
  contact_email?: string | null;
  price_pkr?: number | null;
  payment_methods?: PaymentMethod[];
  plans: PlanOption[];
}

export interface PaymentMethod {
  id: string;
  name: string;
  description: string;
  currency: string;
  amount: number;
}

export interface PurchaseProPlanResult {
  action: "redirect" | "request" | "already_active" | "jazzcash_form";
  checkout_url?: string | null;
  post_url?: string | null;
  fields?: Record<string, string> | null;
  txn_ref_no?: string | null;
  amount_pkr?: number | null;
  message: string;
  usage?: UsageQuota | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface LeadContactLinks {
  whatsapp_url: string | null;
  email_url: string | null;
  linkedin_url: string | null;
  facebook_url: string | null;
  instagram_url: string | null;
  website_url: string | null;
  needs_website_pitch: boolean;
  website_offer_whatsapp_url: string | null;
  website_offer_email_url: string | null;
  offer_message: string | null;
}

export interface Lead {
  id: number;
  company_name: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  linkedin_url: string | null;
  facebook_url: string | null;
  instagram_url: string | null;
  address: string | null;
  postal_code: string | null;
  category: string | null;
  city: string | null;
  country: string | null;
  industry: string | null;
  notes: string | null;
  source: string | null;
  status: LeadStatus;
  quality_score: number | null;
  quality_tier: string | null;
  whatsapp_ready: boolean | null;
  phone_verified: boolean | null;
  email_verified: boolean | null;
  website_quality_score: number | null;
  website_opportunity_score: number | null;
  website_problems: string[] | null;
  reviews_count: number | null;
  rating: number | null;
  business_hours: string | null;
  google_profile_score: number | null;
  photos_count: number | null;
  buying_intent_score: number | null;
  intent_tier: string | null;
  social_activity_score: number | null;
  social_links_verified: boolean | null;
  is_running_ads: boolean | null;
  ads_count: number | null;
  ad_platform: string | null;
  landing_page: string | null;
  ad_activity_score: number | null;
  ai_qualification: string | null;
  recommended_offer: string | null;
  qualification_reason: string | null;
  niche_key: string | null;
  recommended_service: string | null;
  is_saved: boolean;
  saved_at: string | null;
  contact_links: LeadContactLinks | null;
  outreach_email_status?: LeadOutreachEmailStatus;
  created_at: string;
  updated_at: string;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface DashboardStats {
  total_leads: number;
  new_leads: number;
  contacted_leads: number;
  interested_leads: number;
  follow_up_leads: number;
  closed_leads: number;
  lost_leads: number;
  campaign_count: number;
  messages_generated: number;
}

export interface Campaign {
  id: number;
  name: string;
  message_type: MessageType;
  status: CampaignStatus;
  message_count?: number;
  eligible_leads?: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignRunResultItem {
  lead_id: number;
  company_name: string;
  success: boolean;
  message_preview?: string | null;
  whatsapp_url?: string | null;
  error?: string | null;
}

export interface CampaignRunResponse {
  campaign_id: number;
  campaign_status: CampaignStatus;
  processed: number;
  generated: number;
  skipped: number;
  failed: number;
  results: CampaignRunResultItem[];
}

export interface Message {
  id: number;
  lead_id: number | null;
  campaign_id: number | null;
  message_type: MessageType;
  message_content: string;
  created_at: string;
}

export interface MessageListResponse {
  items: Message[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface MessageBulkDeleteResponse {
  deleted: number;
  message: string;
}

export interface CVProfile {
  id: number;
  original_filename: string;
  file_type: string;
  name: string | null;
  skills: string[] | null;
  experience: Record<string, string>[] | null;
  education: Record<string, string>[] | null;
  projects: Record<string, string>[] | null;
  services: string[] | null;
  tools: string[] | null;
  technologies: string[] | null;
  professional_summary: string | null;
  skills_summary: string | null;
  services_summary: string | null;
  experience_summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface WhatsAppLeadPreview {
  lead_id: number;
  company_name: string;
  phone: string;
  message: string;
  whatsapp_url: string;
}

export interface ScrapeMetricsResponse {
  total_pages_scanned: number;
  total_leads_found: number;
  valid_emails_found: number;
  success_rate: number;
  failed_requests: number;
  pages_discovered: number;
  pages_fetched: number;
  pages_failed: number;
  leads_parsed: number;
  leads_rejected: number;
  leads_saved: number;
  valid_emails: number;
  valid_phones: number;
  whatsapp_ready: number;
  high_quality: number;
  medium_quality: number;
  low_quality: number;
  validation_errors?: string[];
  failed_urls?: string[];
  pages_crawled?: number;
  requests_per_minute?: number;
  retry_count?: number;
  browser_renders?: number;
  js_render_used?: number;
  images_downloaded?: number;
  active_workers?: number;
  queue_size?: number;
  bot_blocks?: number;
  proxy_switches?: number;
  strategy_http?: number;
  strategy_playwright?: number;
  strategy_api?: number;
}

export interface ScraperResponse {
  success: boolean;
  count: number;
  message?: string;
  leads_discovered?: number;
  filtered_unverified?: number;
  filtered_website?: number;
  skipped_duplicates?: number;
  emails_found?: number;
  whatsapp_numbers_found?: number;
  linkedin_found?: number;
  with_website?: number;
  without_website?: number;
  google_maps_count?: number;
  google_search_count?: number;
  meta_ads_count?: number;
  messages_generated?: number;
  whatsapp_previews?: WhatsAppLeadPreview[];
  scrape_metrics?: ScrapeMetricsResponse | null;
  intelligence_stats?: {
    total_scraped?: number;
    duplicates_removed?: number;
    hot_leads?: number;
    warm_leads?: number;
    cold_leads?: number;
    avg_opportunity_score?: number;
    avg_buying_intent?: number;
  } | null;
}

export interface ScraperJobStartResponse {
  job_id: string;
}

export type ScraperJobStatus = "pending" | "running" | "paused" | "completed" | "failed" | "cancelled";
export type ScraperJobMode = "single" | "auto";

export interface ScraperLogEntry {
  seq: number;
  ts: string;
  level: string;
  stage: string;
  text: string;
}

export interface ScraperAgentStatus {
  id: string;
  label?: string;
  keyword?: string;
  city?: string;
  status?: "waiting" | "queued" | "running" | "done" | "failed" | "idle";
  message?: string;
  kept?: number;
  scraped?: number;
}

export interface ScraperJobStatusResponse {
  job_id: string;
  status: ScraperJobStatus;
  mode?: ScraperJobMode;
  progress: number;
  stage: string;
  message: string;
  result?: ScraperResponse | null;
  error?: string | null;
  iteration?: number;
  auto_kept_total?: number;
  auto_deleted_total?: number;
  auto_scraped_total?: number;
  cancel_requested?: boolean;
  pause_requested?: boolean;
  live_metrics?: ScrapeMetricsResponse | null;
  failed_urls?: string[];
  logs?: ScraperLogEntry[];
  agents?: ScraperAgentStatus[];
}

export interface SearchQueryOptimizeResponse {
  optimized_query: string;
  suggestions: string[];
  tips: string;
  was_corrected: boolean;
}

export interface ScrapeSuggestResponse {
  recommended_keyword: string;
  recommended_location: string;
  recommended_search_query: string;
  keyword_suggestions: string[];
  location_suggestions: string[];
  search_queries: string[];
  strategy_tips: string;
  profile_name: string | null;
  has_profile: boolean;
  user_location?: string;
}

export interface DailyScrapeStatusResponse {
  can_run: boolean;
  leads_target: number;
  run_date: string;
  last_run_date: string | null;
  last_job_id: string | null;
  preview_search_query: string;
  profile_name: string | null;
  has_profile: boolean;
}

export interface DailyScrapeStartResponse {
  job_id: string;
  leads_target: number;
  search_query: string;
  message: string;
}

export interface BackgroundScrapeStatusResponse {
  active: boolean;
  running: boolean;
  total_saved: number;
  iteration: number;
  last_query: string;
  progress: number;
  stage: string;
  message: string;
  logs: ScraperLogEntry[];
}

export interface LeadDatabaseSummaryItem {
  id: number;
  company_name: string;
  phone: string | null;
  city: string | null;
  country: string | null;
  created_at: string;
  keyword: string | null;
  location: string | null;
}

export interface LeadDatabaseStatsResponse {
  database_name: string;
  database_type: string;
  database_size_bytes: number | null;
  total_leads: number;
  inbox_leads: number;
  saved_leads: number;
  background_leads: number;
  manual_leads: number;
  with_phone: number;
  without_website: number;
  background_active: boolean;
  background_running: boolean;
  background_total_saved: number;
  background_iteration: number;
  background_last_query: string;
  recent_background: LeadDatabaseSummaryItem[];
}

export interface GenerateMessageResponse {
  message: string;
}

export interface BrainProfile {
  id: number;
  name: string | null;
  skills: string[] | null;
  experience: Record<string, string>[] | null;
  education: Record<string, string>[] | null;
  projects: Record<string, string>[] | null;
  services: string[] | null;
  tools: string[] | null;
  technologies: string[] | null;
  professional_summary: string | null;
  custom_notes: string | null;
  system_prompt: string | null;
  pricing_currency?: string | null;
  pricing_high?: number | null;
  pricing_floor?: number | null;
  created_at: string;
  updated_at: string;
}

export interface BrainGenerateResponse {
  system_prompt: string;
  message: string;
}

export type ApiProvider = "apify" | "groq";
export type ApiKeyStatus = "active" | "exhausted" | "disabled";

export interface UserApiKey {
  id: number;
  provider: ApiProvider;
  label: string;
  masked_key: string;
  priority: number;
  status: ApiKeyStatus;
  usage_count: number;
  last_error: string | null;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserApiKeyBulkCreateResponse {
  created: number;
  keys: UserApiKey[];
}

// Email Outreach Automation
export interface EmailAccount {
  id: number;
  provider: string;
  email_address: string;
  display_name: string | null;
  smtp_host: string | null;
  smtp_port: number | null;
  imap_host: string | null;
  imap_port: number | null;
  use_tls: boolean;
  status: string;
  is_default: boolean;
  daily_sent_count: number;
  last_sync_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailOutreachSettings {
  automation_enabled: boolean;
  auto_send_enabled: boolean;
  require_review: boolean;
  daily_send_limit: number;
  hourly_send_limit: number;
  rate_limit_per_minute: number;
  auto_reply_enabled: boolean;
  auto_reply_simple_only: boolean;
  include_unsubscribe: boolean;
  default_email_account_id: number | null;
  agent_running: boolean;
  agent_paused: boolean;
  auto_follow_up: boolean;
  working_hours_start: number;
  working_hours_end: number;
  weekends_enabled: boolean;
  standing_campaign_id: number | null;
  last_agent_run_at: string | null;
  ai_emails_generated: number;
  ai_replies_generated: number;
  agent_batch_delay_minutes: number;
}

export interface FollowUpStep {
  id?: number;
  step_number: number;
  delay_days: number;
  subject_override?: string | null;
  is_active: boolean;
}

export interface EmailOutreachCampaign {
  id: number;
  name: string;
  campaign_id: number | null;
  email_account_id: number | null;
  status: string;
  automation_enabled: boolean;
  require_review: boolean | null;
  follow_up_enabled: boolean;
  lead_filter_saved_only: boolean;
  lead_ids: number[] | null;
  stats: Record<string, number> | null;
  follow_up_steps: FollowUpStep[];
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OutreachEmail {
  id: number;
  outreach_campaign_id: number;
  lead_id: number;
  follow_up_step: number;
  to_email: string;
  subject: string;
  body_text: string;
  status: string;
  verification_status: string | null;
  verification_details: Record<string, unknown> | null;
  scheduled_at: string | null;
  sent_at: string | null;
  opened_at: string | null;
  replied_at: string | null;
  error_message: string | null;
  ai_generated: boolean;
  is_follow_up: boolean;
  created_at: string;
}

export interface EmailOutreachDashboard {
  connected_accounts: number;
  active_campaigns: number;
  emails_sent: number;
  emails_delivered: number;
  open_rate: number;
  reply_rate: number;
  bounce_rate: number;
  follow_up_queue: number;
  pending_ai_drafts: number;
  automation_enabled: boolean;
  pending_jobs: number;
  emails_sent_today: number;
  emails_sent_this_week: number;
  emails_sent_this_month: number;
  pending_emails: number;
  failed_emails: number;
  queued_emails: number;
  replies_received: number;
  positive_replies: number;
  interested_leads: number;
  meetings_requested: number;
  follow_ups_scheduled: number;
  follow_ups_completed: number;
  no_response_leads: number;
  completed_campaigns: number;
  running_campaigns: number;
  paused_campaigns: number;
  ai_emails_generated: number;
  ai_replies_generated: number;
  ai_tokens_used: number;
  estimated_ai_cost: number;
  gmail_connected: boolean;
  gmail_email: string | null;
  daily_sending_limit: number;
  emails_remaining_today: number;
  sync_status: string;
  last_sync_time: string | null;
  agent_running: boolean;
  agent_paused: boolean;
  last_agent_run_at: string | null;
  within_working_hours: boolean;
  success_rate: number;
  conversion_rate: number;
  recent_activity: Array<{
    id: number;
    type: string;
    message: string;
    level: string;
    lead_id: number | null;
    created_at: string;
  }>;
  recent_replies: Array<{
    conversation_id: number;
    lead_id: number;
    intent: string | null;
    summary: string | null;
    last_message_at: string | null;
  }>;
  upcoming_followups: Array<{
    id: number;
    lead_id: number;
    subject: string;
    scheduled_at: string | null;
    follow_up_step: number;
  }>;
  running_jobs: number;
}

export interface AgentStatus {
  agent_running: boolean;
  agent_paused: boolean;
  automation_enabled: boolean;
  gmail_connected: boolean;
  gmail_email: string | null;
  daily_limit: number;
  emails_sent_today: number;
  emails_remaining_today: number;
  last_sync_at: string | null;
  last_agent_run_at: string | null;
  standing_campaign_id: number | null;
  within_working_hours: boolean;
  batch_delay_minutes: number;
}

export interface PilotEmail {
  lead_id: number;
  company_name: string | null;
  to_email: string;
  subject: string;
  body_text: string;
  status: string;
}

export interface AgentStartResponse {
  status: string;
  message: string;
  campaign_id?: number;
  batch_scheduled_at?: string;
  pilot_email?: PilotEmail | null;
}

export interface ManualLeadOutreachResponse {
  message: string;
  subject: string;
  to_email: string;
  status: string;
  lead_id: number;
  company_name: string | null;
}

export interface OutreachNotification {
  id: number;
  notification_type: string;
  title: string;
  message: string;
  lead_id: number | null;
  is_read: boolean;
  created_at: string;
}

export interface AiReplyDraft {
  id: number;
  conversation_id: number;
  detected_intent: string;
  summary: string;
  draft_subject: string;
  draft_body: string;
  status: string;
  created_at: string;
}

export interface EmailConversation {
  id: number;
  lead_id: number;
  outreach_campaign_id: number | null;
  subject: string;
  status: string;
  reply_intent: string | null;
  reply_summary: string | null;
  follow_ups_stopped: boolean;
  last_message_at: string | null;
  created_at: string;
}

export interface ChatThread {
  lead_id: number;
  conversation_id: number | null;
  lead_name: string;
  lead_email: string;
  subject: string;
  status: string;
  reply_intent: string | null;
  reply_summary: string | null;
  last_message_at: string | null;
  last_preview: string | null;
  has_reply: boolean;
  message_count?: number;
  unread_count?: number;
  is_manual_chat?: boolean;
  is_online?: boolean;
  last_seen_at?: string | null;
}

export interface ChatMessage {
  id: string;
  direction: "outbound" | "inbound" | string;
  from_email: string;
  to_email: string;
  subject: string;
  body_text: string;
  sent_at: string | null;
  status: string | null;
  source: string;
  outreach_email_id: number | null;
  /** WhatsApp-style: sent | delivered | read */
  delivery_status?: "sent" | "delivered" | "read" | string | null;
}

export interface ChatThreadDetail {
  lead_id: number;
  conversation_id: number | null;
  lead_name: string;
  lead_email: string;
  subject: string;
  status: string;
  messages: ChatMessage[];
  is_online?: boolean;
  last_seen_at?: string | null;
}

export interface SupportMessage {
  id: number;
  direction: "outbound" | "inbound";
  body_text: string;
  sent_at: string;
  sender_name: string;
  sender_role: string;
  sender_user_id: number;
}

export interface SupportThread {
  user_id: number;
  user_name: string;
  user_email: string;
  user_avatar_url?: string | null;
  last_message_at: string | null;
  last_preview: string | null;
  unread_count: number;
}

export interface SupportThreadDetail {
  user_id: number;
  user_name: string;
  user_email: string;
  user_avatar_url?: string | null;
  messages: SupportMessage[];
  unread_count: number;
}

export interface AdminDashboard {
  total_users: number;
  admin_users: number;
  regular_users: number;
  total_leads: number;
  total_campaigns: number;
  total_messages: number;
  total_api_keys: number;
  total_outreach_emails: number;
  total_outreach_campaigns: number;
  active_scraper_jobs: number;
  outreach_worker_enabled: boolean;
}

export interface AdminUserListItem extends User {
  lead_count: number;
  campaign_count: number;
}

export interface AdminUserList {
  items: AdminUserListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminUserStats {
  leads: number;
  campaigns: number;
  messages: number;
  api_keys: number;
  outreach_emails: number;
  email_accounts: number;
}

export interface AdminUserDetail extends User {
  stats: AdminUserStats;
}

export interface AdminLeadListItem {
  id: number;
  user_id: number;
  user_email: string | null;
  company_name: string | null;
  email: string | null;
  phone: string | null;
  city: string | null;
  country: string | null;
  status: string;
  is_saved: boolean;
  created_at: string;
}

export interface AdminLeadList {
  items: AdminLeadListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminScraperJob {
  job_id: string;
  user_id: number;
  user_email: string | null;
  status: string;
  mode: string;
  progress: number;
  stage: string;
  message: string;
  created_at: string;
  updated_at: string;
}

export interface AdminScraperJobList {
  items: AdminScraperJob[];
}

export interface AdminOutreachSummary {
  total_accounts: number;
  connected_accounts: number;
  agents_running: number;
  emails_sent: number;
  emails_queued: number;
  replies_received: number;
  pending_jobs: number;
}

export interface AdminSystemInfo {
  status: string;
  app_name: string;
  app_version: string;
  database_url: string;
  database_type: string;
  database_size_mb: number | null;
  outreach_worker_enabled: boolean;
  outreach_worker_running: boolean;
  outreach_worker_poll_seconds: number;
  outreach_sync_interval_seconds: number;
  smtp_configured: boolean;
  google_oauth_configured: boolean;
  microsoft_oauth_configured: boolean;
  scraper_workers: number;
  scraper_fast_mode: boolean;
  scraper_playwright_enabled: boolean;
  scraper_timeout: number;
  groq_model: string;
  otp_dev_mode: boolean;
  frontend_url: string;
  default_secret_key: boolean;
  upload_dir: string;
  export_dir: string;
  total_users: number;
  total_leads: number;
  total_messages: number;
  total_api_keys: number;
  active_scraper_jobs: number;
  outreach_agents_running: number;
  outreach_pending_jobs: number;
  checked_at: string;
}

export interface WhatsAppChatContact {
  lead_id: number;
  company_name?: string | null;
  contact_name?: string | null;
  phone: string;
  city?: string | null;
  country?: string | null;
  last_message?: string | null;
  last_message_at?: string | null;
  message_count: number;
}

export interface WhatsAppChatMessage {
  id: number;
  lead_id: number;
  direction: "inbound" | "outbound" | string;
  body: string;
  created_at: string;
}

export interface WhatsAppChatThread {
  lead_id: number;
  company_name?: string | null;
  contact_name?: string | null;
  phone: string;
  city?: string | null;
  country?: string | null;
  memory_summary?: string | null;
  last_price_quoted?: number | null;
  customer_budget?: number | null;
  deal_status?: string | null;
  messages: WhatsAppChatMessage[];
}

export interface WhatsAppChatReplyResponse {
  customer: WhatsAppChatMessage;
  reply: WhatsAppChatMessage;
}

export interface WhatsAppChatOpenerResponse {
  reply: WhatsAppChatMessage;
}

export interface WhatsAppWebStatus {
  enabled: boolean;
  headless: boolean;
  profile_dir: string;
  browser_started: boolean;
  logged_in: boolean;
  worker_running: boolean;
  auto_reply: boolean;
  ignore_groups: boolean;
  owner_user_id?: number | null;
  owner_email?: string | null;
  cdp_mode?: boolean;
  cdp_configured?: boolean;
  cdp_alive?: boolean;
  cloud_api_untouched: boolean;
  message?: string | null;
  daily_outreach_enabled?: boolean;
  daily_outreach_limit?: number;
  daily_outreach_sent_count?: number;
  daily_outreach_remaining?: number;
  daily_outreach_interval_minutes?: number;
  daily_outreach_seconds_until_next?: number;
}

export interface WhatsAppWebStartResult {
  ok: boolean;
  logged_in: boolean;
  worker_running: boolean;
  qr_data_url?: string | null;
  message?: string | null;
  owner_email?: string | null;
}

export interface WhatsAppWebQrResult {
  logged_in: boolean;
  qr_data_url?: string | null;
  message?: string | null;
}

export interface WhatsAppWebSettings {
  auto_reply: boolean;
  ignore_phones: string[];
  ignore_groups: boolean;
  human_takeover_phones: string[];
  owner_user_id?: number | null;
  owner_email?: string | null;
  daily_outreach_enabled?: boolean;
  daily_outreach_limit?: number;
  daily_outreach_sent_date?: string | null;
  daily_outreach_sent_count?: number;
  daily_outreach_interval_minutes?: number;
}

export interface WhatsAppWebJob {
  id: number;
  chat_title: string;
  phone_hint?: string | null;
  body: string;
  status: string;
  ai_replied: boolean;
  reply_body?: string | null;
  error_message?: string | null;
  lead_id?: number | null;
  created_at?: string | null;
}

