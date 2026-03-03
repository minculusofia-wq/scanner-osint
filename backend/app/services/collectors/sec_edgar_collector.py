import logging
import re
from datetime import datetime, timedelta

import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# SEC EDGAR full-text search API
EDGAR_API_URL = "https://efts.sec.gov/LATEST/search-index"

# Filing types that signal market-moving events
FILING_QUERIES = [
    {"q": '"8-K"', "label": "8-K", "desc": "Material events"},
    {"q": '"Form 4" insider', "label": "Form 4", "desc": "Insider trading"},
]

# User-Agent required by SEC (they block requests without it)
HEADERS = {
    "User-Agent": "ScannerOSINT research@scanner-osint.local",
    "Accept": "application/json",
}


class SECEdgarCollector(BaseCollector):
    """Collects SEC EDGAR filings (8-K material events, Form 4 insider trades)."""

    SOURCE_NAME = "sec_edgar"

    async def collect(self, config: dict) -> list[dict]:
        items = []
        today = datetime.utcnow()
        yesterday = today - timedelta(days=1)

        date_from = yesterday.strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=20, headers=HEADERS) as client:
            # Use EDGAR FULL-TEXT SEARCH API
            for query_info in FILING_QUERIES:
                try:
                    params = {
                        "q": query_info["q"],
                        "dateRange": "custom",
                        "startdt": date_from,
                        "enddt": date_to,
                        "forms": query_info["label"],
                    }

                    resp = await client.get(EDGAR_API_URL, params=params)

                    if resp.status_code != 200:
                        logger.warning(f"SEC EDGAR {query_info['label']}: HTTP {resp.status_code}")
                        continue

                    data = resp.json()
                    hits = data.get("hits", {}).get("hits", [])

                    for hit in hits[:15]:
                        source = hit.get("_source", {})
                        filing_type = source.get("file_type", query_info["label"])
                        company = source.get("display_names", ["Unknown"])[0] if source.get("display_names") else "Unknown"
                        filed_date = source.get("file_date", "")
                        title_text = f"SEC {filing_type}: {company}"
                        summary = source.get("display_description", "") or f"{filing_type} filing by {company}"

                        # Build URL to SEC filing
                        file_num = source.get("file_num", "")
                        accession = source.get("accession_no", "")
                        filing_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&filenum={file_num}" if file_num else "https://www.sec.gov/cgi-bin/browse-edgar"

                        # Relevance: 8-K > Form 4
                        relevance = 0.85 if "8-K" in filing_type else 0.7

                        published = None
                        if filed_date:
                            try:
                                published = datetime.strptime(filed_date, "%Y-%m-%d")
                            except ValueError:
                                pass

                        items.append(self._make_item(
                            title=title_text,
                            summary=summary[:500],
                            url=filing_url,
                            category="financial",
                            tags=["sec", "filing", filing_type.lower(), company[:50]],
                            raw_relevance=relevance,
                            published_at=published,
                            source_id=accession or f"sec-{company}-{filed_date}",
                        ))

                except Exception as e:
                    logger.error(f"SEC EDGAR {query_info['label']} error: {e}")

            # Also try the RSS feed as backup
            try:
                rss_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=20&search_text=&action=getcurrent&output=atom"
                resp = await client.get(rss_url)
                if resp.status_code == 200:
                    # Parse Atom feed manually (simple extraction)
                    text = resp.text
                    entries = text.split("<entry>")[1:] if "<entry>" in text else []
                    for entry in entries[:10]:
                        title_match = _extract_tag(entry, "title")
                        link_match = _extract_tag(entry, "link", attr="href")
                        summary_match = _extract_tag(entry, "summary")
                        updated_match = _extract_tag(entry, "updated")

                        if title_match:
                            published = None
                            if updated_match:
                                try:
                                    published = datetime.fromisoformat(updated_match.replace("Z", "+00:00")).replace(tzinfo=None)
                                except (ValueError, TypeError):
                                    pass

                            items.append(self._make_item(
                                title=f"SEC Filing: {title_match[:200]}",
                                summary=(summary_match or "")[:500],
                                url=link_match or "https://www.sec.gov/cgi-bin/browse-edgar",
                                category="financial",
                                tags=["sec", "filing", "8-K"],
                                raw_relevance=0.8,
                                published_at=published,
                                source_id=f"sec-rss-{title_match[:50]}",
                            ))
            except Exception as e:
                logger.debug(f"SEC EDGAR RSS fallback error: {e}")

        logger.info(f"SEC EDGAR: collected {len(items)} items")
        return items


def _extract_tag(text: str, tag: str, attr: str = "") -> str:
    """Simple XML tag content extractor."""
    if attr:
        match = re.search(f'<{tag}[^>]*{attr}="([^"]*)"', text)
        return match.group(1) if match else ""
    match = re.search(f'<{tag}[^>]*>(.*?)</{tag}>', text, re.DOTALL)
    return match.group(1).strip() if match else ""
