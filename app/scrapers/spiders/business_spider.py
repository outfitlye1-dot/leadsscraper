from urllib.parse import urlparse

import scrapy
from bs4 import BeautifulSoup
from scrapy.http import HtmlResponse, Request

from app.scrapers.fetcher import PageFetcher
from app.scrapers.items import BusinessLeadItem
from app.scrapers.parser import extract_contacts_from_html, find_contact_links
from app.utils.scrape_sources import clean_search_title


class BusinessSpider(scrapy.Spider):
    """Scrapy spider: crawl business sites with Requests/Playwright fetch + BeautifulSoup parse."""

    name = "business"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "ERROR",
        "DOWNLOAD_DELAY": 0.25,
        "CONCURRENT_REQUESTS": 4,
    }

    def __init__(
        self,
        seed_urls: list[str] | None = None,
        seed_titles: dict[str, str] | None = None,
        location: str = "",
        limit: int = 20,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.seed_urls = seed_urls or []
        self.seed_titles = seed_titles or {}
        self.location = location
        self.limit = limit
        self.fetcher = PageFetcher()
        self._yielded = 0
        self._seen_hosts: set[str] = set()

    def start_requests(self):
        for url in self.seed_urls:
            if self._yielded >= self.limit:
                break
            html, final_url = self.fetcher.fetch(url)
            if not html:
                continue
            yield HtmlResponse(
                url=final_url,
                body=html.encode("utf-8", errors="ignore"),
                encoding="utf-8",
                request=Request(url=final_url, meta={"depth": 0, "seed_url": url}),
            )

    def parse(self, response: HtmlResponse):
        if self._yielded >= self.limit:
            return

        host = urlparse(response.url).netloc.lower()
        if host in self._seen_hosts:
            return
        self._seen_hosts.add(host)

        country = self._country_from_location()
        contacts = extract_contacts_from_html(response.text, response.url, country)

        soup = BeautifulSoup(response.text, "lxml")
        for link in find_contact_links(soup, response.url, max_links=1):
            html, final_url = self.fetcher.fetch(link)
            if not html:
                continue
            extra = extract_contacts_from_html(html, final_url, country)
            contacts = self._merge_contacts(contacts, extra)

        seed_title = self.seed_titles.get(response.meta.get("seed_url", response.url))
        company_name = seed_title or contacts.get("title") or clean_search_title(host)

        item = BusinessLeadItem(
            company_name=company_name,
            website=response.url,
            email=contacts.get("email"),
            phone=contacts.get("phone"),
            linkedin_url=contacts.get("linkedin_url"),
            instagram_url=contacts.get("instagram_url"),
            facebook_url=None,
            notes=contacts.get("description"),
            source="web_search",
        )
        self._yielded += 1
        yield item

    def _merge_contacts(self, base: dict, extra: dict) -> dict:
        merged = dict(base)
        for key in ("email", "phone", "linkedin_url", "instagram_url", "description"):
            if not merged.get(key) and extra.get(key):
                merged[key] = extra[key]
        return merged

    def _country_from_location(self) -> str | None:
        parts = [p.strip() for p in self.location.split(",") if p.strip()]
        return parts[-1] if parts else None
