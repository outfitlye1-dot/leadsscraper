import json
import re
import time

from fastapi import HTTPException, status
from groq import APIError, AuthenticationError, Groq

from app.core.config import get_settings
from app.utils.api_key_utils import is_transient_api_error
from app.models.campaign import MessageType
from app.models.cv import CV
from app.models.lead import Lead
from app.utils.prompts import (
    CV_EXTRACTION_PROMPT,
    CV_SUMMARY_PROMPT,
    EMAIL_PROMPT,
    FOLLOW_UP_PROMPT,
    LINKEDIN_PROMPT,
    SEARCH_QUERY_OPTIMIZE_PROMPT,
    WHATSAPP_PROMPT,
    BRAIN_GENERATION_PROMPT,
    CV_SCRAPE_SUGGEST_PROMPT,
)
from app.utils.customer_language import language_rules_for_country
from app.utils.outreach_tone import (
    OUTREACH_MAX_CHARS,
    sanitize_paid_outreach_message,
    trim_outreach_message,
)
from app.utils.prompt_format import safe_prompt_format
from app.utils.query_optimizer import optimize_search_query_rules


class GroqService:
    def __init__(self, db=None, user_id: int | None = None):
        self.db = db
        self.user_id = user_id

    def _raw_chat(
        self,
        api_key: str,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        fast: bool = False,
    ) -> str:
        settings = get_settings()
        model = settings.GROQ_MODEL
        last_error: Exception | None = None
        attempts = 2 if fast else 3
        timeout = 18.0 if fast else 45.0
        client_retries = 0 if fast else 2

        for attempt in range(attempts):
            try:
                client = Groq(api_key=api_key, max_retries=client_retries, timeout=timeout)
                kwargs: dict = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }
                if max_tokens is not None:
                    kwargs["max_tokens"] = max_tokens
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except AuthenticationError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Invalid Groq API key. Add a valid key in Settings → API Keys.",
                )
            except APIError as exc:
                last_error = exc
                if (not fast) and is_transient_api_error(exc) and attempt < attempts - 1:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Groq API error: {exc}",
                )
            except Exception as exc:
                last_error = exc
                if (not fast) and is_transient_api_error(exc) and attempt < attempts - 1:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Groq API error: {exc}",
                ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq API error: {last_error}",
        )

    def _chat(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        fast: bool = False,
    ) -> str:
        if self.db is None or self.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Groq API key required. Add your own key in Settings → API Keys.",
            )

        from app.models.user_api_key import ApiProvider
        from app.services.api_key_rotation_service import ApiKeyRotationService

        return ApiKeyRotationService(self.db).execute_with_rotation(
            self.user_id,
            ApiProvider.groq,
            lambda api_key: self._raw_chat(
                api_key,
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                fast=fast,
            ),
        )

    def _strip_markdown_fence(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json|text)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def _parse_json(self, text: str) -> dict:
        text = self._strip_markdown_fence(text)
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(text)

    def _extract_system_prompt(self, text: str) -> str:
        text = self._strip_markdown_fence(text.strip())
        if not text:
            return ""

        try:
            parsed = self._parse_json(text)
            if isinstance(parsed, dict):
                prompt = (parsed.get("system_prompt") or "").strip()
                if prompt:
                    return prompt
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # Plain-text response (preferred for smaller models)
        lowered = text.lower()
        if lowered.startswith("you are") or len(text) >= 200:
            return text

        return ""

    def extract_cv_profile(self, raw_text: str) -> dict:
        prompt = CV_EXTRACTION_PROMPT.format(raw_text=raw_text[:15000])
        result = self._chat(prompt)
        parsed = self._parse_json(result)
        return {
            "name": parsed.get("name"),
            "skills": parsed.get("skills", []),
            "experience": parsed.get("experience", []),
            "education": parsed.get("education", []),
            "projects": parsed.get("projects", []),
            "services": parsed.get("services", []),
            "tools": parsed.get("tools", []),
            "technologies": parsed.get("technologies", []),
        }

    def generate_summaries(self, parsed_profile: dict) -> dict:
        prompt = safe_prompt_format(
            CV_SUMMARY_PROMPT,
            profile=json.dumps(parsed_profile, default=str),
        )
        result = self._chat(prompt)
        parsed = self._parse_json(result)
        return {
            "professional_summary": self._coerce_text_field(parsed.get("professional_summary")),
            "skills_summary": self._coerce_text_field(parsed.get("skills_summary")),
            "services_summary": self._coerce_text_field(parsed.get("services_summary")),
            "experience_summary": self._coerce_text_field(parsed.get("experience_summary")),
        }

    @staticmethod
    def _coerce_text_field(value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            for key in ("text", "summary", "content", "value", "description"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            return ""
        if isinstance(value, list):
            parts = [GroqService._coerce_text_field(item) for item in value]
            return " ".join(part for part in parts if part).strip()
        return str(value).strip()

    def _format_lead_info(self, lead: Lead) -> str:
        return json.dumps(
            {
                "company_name": lead.company_name,
                "contact_name": lead.contact_name,
                "phone": lead.phone,
                "email": lead.email,
                "website": lead.website,
                "linkedin_url": lead.linkedin_url,
                "instagram_url": lead.instagram_url,
                "address": lead.address,
                "postal_code": lead.postal_code,
                "city": lead.city,
                "country": lead.country,
                "category": lead.category,
                "industry": lead.industry,
                "notes": lead.notes,
            },
            indent=2,
        )

    def _format_cv_profile(self, cv: CV) -> str:
        return json.dumps(
            {
                "name": cv.name,
                "skills": cv.skills,
                "services": cv.services,
                "tools": cv.tools,
                "technologies": cv.technologies,
                "professional_summary": cv.professional_summary,
                "skills_summary": cv.skills_summary,
                "services_summary": cv.services_summary,
                "experience_summary": cv.experience_summary,
            },
            indent=2,
        )

    def generate_message(
        self, lead: Lead, cv: CV, message_type: MessageType
    ) -> tuple[str, str]:
        lead_info = self._format_lead_info(lead)
        cv_profile = self._format_cv_profile(cv)

        prompts = {
            MessageType.whatsapp: WHATSAPP_PROMPT,
            MessageType.email: EMAIL_PROMPT,
            MessageType.linkedin: LINKEDIN_PROMPT,
            MessageType.follow_up: FOLLOW_UP_PROMPT,
        }
        max_tokens_by_type = {
            MessageType.whatsapp: 100,
            MessageType.email: 280,
            MessageType.linkedin: 90,
            MessageType.follow_up: 100,
        }

        prompt = safe_prompt_format(
            prompts[message_type],
            lead_info=lead_info,
            cv_profile=cv_profile,
            language_rules=language_rules_for_country(
                lead.country,
                lead.city,
                channel="whatsapp" if message_type == MessageType.whatsapp else message_type.value,
            ),
        )
        result = self._chat(
            prompt,
            max_tokens=max_tokens_by_type[message_type],
            temperature=0.85,
        ).strip()

        if message_type == MessageType.email:
            email_data = self._parse_json(result)
            for key in ("subject", "body", "cta"):
                if key in email_data and isinstance(email_data[key], str):
                    email_data[key] = sanitize_paid_outreach_message(email_data[key])
            if isinstance(email_data.get("subject"), str):
                email_data["subject"] = trim_outreach_message(
                    email_data["subject"], OUTREACH_MAX_CHARS["email_subject"]
                )
            if isinstance(email_data.get("body"), str):
                email_data["body"] = trim_outreach_message(
                    email_data["body"], OUTREACH_MAX_CHARS["email_body"]
                )
            if isinstance(email_data.get("cta"), str):
                email_data["cta"] = trim_outreach_message(
                    email_data["cta"], OUTREACH_MAX_CHARS["email_cta"]
                )
            display_message = (
                f"Subject: {email_data.get('subject', '')}\n\n"
                f"{email_data.get('body', '')}\n\n"
                f"CTA: {email_data.get('cta', '')}"
            )
            stored_content = json.dumps(email_data)
            return display_message, stored_content

        result = sanitize_paid_outreach_message(result)
        max_key = {
            MessageType.whatsapp: "whatsapp",
            MessageType.linkedin: "linkedin",
            MessageType.follow_up: "follow_up",
        }[message_type]
        result = trim_outreach_message(result, OUTREACH_MAX_CHARS[max_key])

        return result, result

    def _has_groq_access(self) -> bool:
        if self.db is None or self.user_id is None:
            return False

        from app.models.user_api_key import ApiProvider
        from app.repositories.user_api_key_repository import UserApiKeyRepository

        return bool(
            UserApiKeyRepository(self.db).get_active_platform_keys(ApiProvider.groq)
        )

    def optimize_search_query(self, query: str, location: str | None = None) -> dict:
        query = query.strip()
        loc = (location or "").strip()
        if not query:
            return optimize_search_query_rules(query, loc or None)

        if not self._has_groq_access():
            return optimize_search_query_rules(query, loc or None)

        prompt = SEARCH_QUERY_OPTIMIZE_PROMPT.format(
            query=query,
            location=loc or "London, United Kingdom",
        )
        try:
            result = self._chat(prompt)
            parsed = self._parse_json(result)
            optimized = (parsed.get("optimized_query") or query).strip()
            suggestions = parsed.get("suggestions") or []
            if not isinstance(suggestions, list):
                suggestions = []
            suggestions = [str(s).strip() for s in suggestions if str(s).strip()]
            if optimized and optimized not in suggestions:
                suggestions.insert(0, optimized)
            result_dict = {
                "optimized_query": optimized or query,
                "suggestions": suggestions[:5] or [query],
                "tips": str(parsed.get("tips") or "AI improved the query"),
                "was_corrected": bool(parsed.get("was_corrected", optimized.lower() != query.lower())),
            }
            return self._ensure_location_in_result(result_dict, loc)
        except (HTTPException, json.JSONDecodeError, KeyError, TypeError, Exception):
            return optimize_search_query_rules(query, loc or None)

    @staticmethod
    def _ensure_location_in_result(result: dict, location: str) -> dict:
        if not location:
            return result
        loc_lower = location.lower()
        city = loc_lower.split(",")[0].strip()

        def with_loc(text: str) -> str:
            t = text.strip()
            low = t.lower()
            if city in low or loc_lower in low:
                return t
            return f"{t} {location}".strip()

        original = (result.get("optimized_query") or "").strip()
        result["optimized_query"] = with_loc(original)
        if result["optimized_query"].lower() != original.lower():
            result["was_corrected"] = True
        result["suggestions"] = [with_loc(s) for s in (result.get("suggestions") or [])]
        return result

    def generate_brain_prompt(self, profile: dict, custom_notes: str = "") -> str:
        prompt = safe_prompt_format(
            BRAIN_GENERATION_PROMPT,
            profile=json.dumps(profile, indent=2, default=str),
            custom_notes=custom_notes or "None",
        )
        try:
            result = self._chat(prompt, max_tokens=4096)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Groq brain generation failed: {exc}",
            ) from exc

        system_prompt = self._extract_system_prompt(result)
        if not system_prompt or len(system_prompt) < 100:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to generate brain prompt. Try again or add more profile details.",
            )
        return system_prompt

    def suggest_scrape_from_profile(
        self,
        profile: dict,
        scrape_source: str = "all",
        *,
        website_preference: str = "without_website",
    ) -> dict:
        if not self._has_groq_access():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Groq API key required. Add your key in Settings → API Keys.",
            )

        pref = (website_preference or "without_website").strip().lower()
        if pref not in {"without_website", "with_website", "all"}:
            pref = "without_website"

        prompt = safe_prompt_format(
            CV_SCRAPE_SUGGEST_PROMPT,
            profile=json.dumps(profile, indent=2, default=str),
            scrape_source=scrape_source,
            website_preference=pref,
        )
        try:
            result = self._chat(prompt)
            parsed = self._parse_json(result)
            return {
                "recommended_keyword": str(parsed.get("recommended_keyword") or "").strip(),
                "recommended_location": "",
                "recommended_search_query": str(
                    parsed.get("recommended_search_query") or ""
                ).strip(),
                "keyword_suggestions": [
                    str(s).strip() for s in (parsed.get("keyword_suggestions") or []) if str(s).strip()
                ][:6],
                "location_suggestions": [],
                "search_queries": [
                    str(s).strip() for s in (parsed.get("search_queries") or []) if str(s).strip()
                ][:6],
                "strategy_tips": str(parsed.get("strategy_tips") or "Brain-based local business targeting"),
                "profile_name": profile.get("name"),
                "has_profile": True,
            }
        except HTTPException:
            raise
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Brain scrape suggestions generate nahi ho sakin. Dubara try karein. ({exc})",
            ) from exc
