import logging
import re
from datetime import datetime

import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# Public Telegram channels with OSINT-relevant content
# These are accessed via the public preview page (no API key needed)
TELEGRAM_CHANNELS = [
    {
        "channel": "intel_slava",
        "name": "Intel Slava Z",
        "category": "conflict",
        "region": "europe",
        "desc": "Ukraine/Russia conflict updates",
    },
    {
        "channel": "nexabortnaya",
        "name": "Nexta Live",
        "category": "geopolitical",
        "region": "europe",
        "desc": "Eastern Europe breaking news",
    },
    {
        "channel": "CIG_telegram",
        "name": "CIG",
        "category": "geopolitical",
        "region": "global",
        "desc": "Conflict Intelligence Group",
    },
    {
        "channel": "ryaboruss",
        "name": "Rybar",
        "category": "conflict",
        "region": "europe",
        "desc": "Military analysis and maps",
    },
    {
        "channel": "bbaboron",
        "name": "BB",
        "category": "conflict",
        "region": "middle_east",
        "desc": "Middle East conflict updates",
    },
]

# Keywords that boost relevance
HIGH_PRIORITY_KEYWORDS = [
    "breaking", "urgent", "missile", "strike", "attack",
    "explosion", "nuclear", "offensive", "retreat", "advance",
    "ceasefire", "negotiations", "surrender", "casualties",
    "drone", "air defense", "escalation", "mobilization",
]


class TelegramCollector(BaseCollector):
    """Scrapes public Telegram channel preview pages for OSINT intelligence."""

    SOURCE_NAME = "telegram"

    async def collect(self, config: dict) -> list[dict]:
        items = []

        async with httpx.AsyncClient(
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
        ) as client:
            for chan in TELEGRAM_CHANNELS:
                try:
                    # Telegram public preview page
                    url = f"https://t.me/s/{chan['channel']}"
                    resp = await client.get(url)

                    if resp.status_code != 200:
                        logger.warning(f"Telegram {chan['channel']}: HTTP {resp.status_code}")
                        continue

                    html = resp.text

                    # Extract messages from the public preview page
                    messages = _parse_telegram_messages(html)

                    for msg in messages[:10]:  # Latest 10 messages
                        text = msg.get("text", "").strip()
                        if not text or len(text) < 20:
                            continue

                        views = msg.get("views", 0)
                        msg_time = msg.get("datetime")

                        # Truncate long messages
                        title_text = text[:150]
                        if len(text) > 150:
                            title_text += "..."

                        summary = text[:500]

                        # Calculate relevance
                        relevance = 0.5
                        text_lower = text.lower()

                        for kw in HIGH_PRIORITY_KEYWORDS:
                            if kw in text_lower:
                                relevance = max(relevance, 0.85)
                                break

                        # Views boost
                        if views > 100000:
                            relevance = min(1.0, relevance + 0.15)
                        elif views > 50000:
                            relevance = min(1.0, relevance + 0.1)
                        elif views > 10000:
                            relevance = min(1.0, relevance + 0.05)

                        published = None
                        if msg_time:
                            try:
                                published = datetime.fromisoformat(msg_time.replace("Z", "+00:00")).replace(tzinfo=None)
                            except (ValueError, TypeError):
                                pass

                        msg_id = msg.get("id", "")
                        msg_url = f"https://t.me/{chan['channel']}/{msg_id}" if msg_id else url

                        items.append(self._make_item(
                            title=f"[{chan['name']}] {title_text}",
                            summary=summary,
                            url=msg_url,
                            category=chan["category"],
                            region=chan["region"],
                            tags=["telegram", chan["channel"], "osint"],
                            raw_relevance=relevance,
                            published_at=published,
                            source_id=f"tg-{chan['channel']}-{msg_id or text[:30]}",
                        ))

                except Exception as e:
                    logger.error(f"Telegram {chan['channel']} error: {e}")

        logger.info(f"Telegram: collected {len(items)} items")
        return items


def _parse_telegram_messages(html: str) -> list[dict]:
    """Parse Telegram public preview page HTML to extract messages."""
    messages = []

    # Find message widget blocks (each message is wrapped in tgme_widget_message)
    # Use the data-post attribute to split messages reliably
    msg_blocks = re.findall(
        r'<div class="tgme_widget_message "[^>]*data-post="[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        html,
        re.DOTALL,
    )

    if not msg_blocks:
        # Fallback: find message text divs directly
        text_blocks = re.findall(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            html,
            re.DOTALL,
        )

        for block in text_blocks:
            text = _strip_html(block)
            if text:
                messages.append({"text": text, "views": 0, "id": "", "datetime": None})
        return messages

    for block in msg_blocks:
        msg = {}

        # Extract message ID
        id_match = re.search(r'data-post="[^/]*/(\d+)"', block)
        if id_match:
            msg["id"] = id_match.group(1)
        else:
            msg["id"] = ""

        # Extract text
        text_match = re.search(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            block,
            re.DOTALL,
        )
        if text_match:
            msg["text"] = _strip_html(text_match.group(1))
        else:
            msg["text"] = ""

        # Extract views
        views_match = re.search(r'<span class="tgme_widget_message_views">([^<]+)</span>', block)
        if views_match:
            views_str = views_match.group(1).strip()
            msg["views"] = _parse_views(views_str)
        else:
            msg["views"] = 0

        # Extract datetime
        time_match = re.search(r'<time[^>]*datetime="([^"]+)"', block)
        if time_match:
            msg["datetime"] = time_match.group(1)
        else:
            msg["datetime"] = None

        if msg.get("text"):
            messages.append(msg)

    return messages


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    clean = re.sub(r'<br\s*/?>', '\n', text)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def _parse_views(views_str: str) -> int:
    """Parse view count strings like '1.2K', '45.3K', '1.1M'."""
    views_str = views_str.strip().upper()
    try:
        if 'M' in views_str:
            return int(float(views_str.replace('M', '')) * 1_000_000)
        elif 'K' in views_str:
            return int(float(views_str.replace('K', '')) * 1_000)
        else:
            return int(views_str)
    except (ValueError, TypeError):
        return 0
