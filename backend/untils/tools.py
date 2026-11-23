import aiohttp
import asyncio
import logging
import os
import re
import time
from datetime import datetime
from urllib.parse import quote
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

SITE_URL = "https://www.ztoe.com.ua/unhooking-search.php"
SITE_URL_HTTP = "http://www.ztoe.com.ua/unhooking-search.php"
SLOTS_PER_DAY = 48

_LABEL_RE = re.compile(r"^\s*([1-6])\.([12])\s*$")
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_WHITE = {
    "",
    "#ffffff",
    "#fff",
    "white",
    "none",
    "transparent",
    "rgb(255, 255, 255)",
    "rgb(255,255,255)",
}

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Sticky source selection: when direct access to ztoe.com.ua is blocked/timed out
# from the server's datacenter IP, stay on the working fallback source and only
# re-probe direct access periodically.
DIRECT_RETRY_INTERVAL = 1800  # 30 minutes
_preferred_source: str | None = None
_last_direct_probe: float = 0.0

try:
    from zoneinfo import ZoneInfo
    _KYIV_TZ = ZoneInfo("Europe/Kyiv")
except Exception:  # tzdata may be missing on some hosts
    _KYIV_TZ = None


def today_str() -> str:
    """Current date in Kyiv as dd.mm.yyyy (format used on the ZTOE page)."""
    now = datetime.now(_KYIV_TZ) if _KYIV_TZ else datetime.now()
    return now.strftime("%d.%m.%Y")


def queue_to_index(n: int) -> int:
    """Переводит 11 -> 1, 12 -> 2, 21 -> 3 и т.д."""
    x = n // 10
    y = n % 10
    return (x - 1) * 2 + y


def index_to_queue(idx: int) -> int:
    y = 2 if idx % 2 == 0 else 1
    x = (idx - 1) // 2 + 1
    return x * 10 + y


def bias_from_index(idx: int) -> int:
    return 2 if idx % 2 == 0 else 3


def _build_sources() -> list[dict]:
    ts = int(time.time())
    base_headers = {
        "User-Agent": _BROWSER_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    jina_headers = {
        "User-Agent": _BROWSER_UA,
        "X-Return-Format": "html",
        "X-No-Cache": "true",
    }
    jina_key = os.getenv("JINA_API_KEY", "").strip()
    if jina_key:
        jina_headers["Authorization"] = f"Bearer {jina_key}"

    sources: list[dict] = [
        {
            "name": "direct_https",
            "url": SITE_URL,
            "headers": base_headers,
            "encoding": None,
            "ssl": False,
            "connect_timeout": 5,
            "total_timeout": 10,
            "is_direct": True,
        },
        {
            "name": "direct_http",
            "url": SITE_URL_HTTP,
            "headers": base_headers,
            "encoding": None,
            "ssl": False,
            "connect_timeout": 4,
            "total_timeout": 8,
            "is_direct": True,
        },
    ]

    custom_proxy = os.getenv("ZTOE_PROXY_URL", "").strip()
    if custom_proxy:
        target = f"{SITE_URL}?t={ts}"
        if "{url}" in custom_proxy:
            proxy_url = custom_proxy.replace("{url}", quote(target, safe=""))
        else:
            proxy_url = f"{custom_proxy.rstrip('/')}/{target}"
        sources.append(
            {
                "name": "custom_proxy",
                "url": proxy_url,
                "headers": base_headers,
                "encoding": None,
                "ssl": True,
                "connect_timeout": 6,
                "total_timeout": 15,
                "is_direct": False,
            }
        )

    sources.extend(
        [
            {
                "name": "jina_https",
                "url": f"https://r.jina.ai/{SITE_URL}?t={ts}",
                "headers": jina_headers,
                "encoding": "utf-8",
                "ssl": True,
                "connect_timeout": 6,
                "total_timeout": 15,
                "is_direct": False,
            },
            {
                "name": "jina_http",
                "url": f"https://r.jina.ai/{SITE_URL_HTTP}?t={ts}",
                "headers": jina_headers,
                "encoding": "utf-8",
                "ssl": True,
                "connect_timeout": 6,
                "total_timeout": 15,
                "is_direct": False,
            },
        ]
    )

    return sources


def _ordered_sources() -> list[dict]:
    sources = _build_sources()
    if not _preferred_source:
        return sources

    now = time.monotonic()
    # Periodically re-probe direct sources in case connectivity recovered.
    if now - _last_direct_probe >= DIRECT_RETRY_INTERVAL:
        return sources

    preferred = [s for s in sources if s["name"] == _preferred_source]
    others = [s for s in sources if s["name"] != _preferred_source]
    return preferred + others


async def _fetch_source(source: dict) -> str | None:
    timeout = aiohttp.ClientTimeout(
        total=source["total_timeout"],
        connect=source["connect_timeout"],
        sock_connect=source["connect_timeout"],
    )
    connector = aiohttp.TCPConnector(ssl=source["ssl"])

    try:
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(source["url"], headers=source["headers"]) as resp:
                resp.raise_for_status()
                raw = await resp.read()
                encoding = source["encoding"] or resp.charset or "cp1251"
    except asyncio.TimeoutError:
        log.warning("ztoe fetch [%s]: timeout", source["name"])
        return None
    except aiohttp.ClientError as e:
        log.warning("ztoe fetch [%s]: client err: %r", source["name"], e)
        return None
    except Exception as e:
        log.warning("ztoe fetch [%s]: unexpected err: %r", source["name"], e)
        return None

    try:
        return raw.decode(encoding, errors="replace")
    except LookupError:
        return raw.decode("cp1251", errors="replace")


async def fetch_page() -> str | None:
    """Downloads the ZTOE schedule page (direct with proxy fallbacks). Returns HTML or None."""
    for source in _ordered_sources():
        html = await _fetch_source(source)
        if html:
            return html
    return None


def _cell_color(td) -> str:
    style = td.get("style") or ""
    for part in style.split(";"):
        part = part.strip()
        if part.lower().startswith("background"):
            if ":" not in part:
                return ""
            val = part.split(":", 1)[1].strip().lower()
            val = val.split("!")[0].strip()
            return val
    return ""


def _is_slot_cell(td) -> bool:
    # Slot cells always carry a background colour; spacer cells (width:3pt) don't.
    return "background" in (td.get("style") or "").lower()


def _row_cells(tr):
    return tr.find_all("td", recursive=False) or tr.find_all("td")


def _find_schedule_table(soup):
    """The innermost table that has rows labelled with subqueues (1.1 ... 6.2)."""
    def labelled_rows(table):
        count = 0
        for tr in table.find_all("tr"):
            if any(_LABEL_RE.match(td.get_text(strip=True)) for td in _row_cells(tr)):
                count += 1
        return count

    candidates = [t for t in soup.find_all("table") if labelled_rows(t) >= 12]
    for table in candidates:
        if not any(labelled_rows(inner) >= 12 for inner in table.find_all("table")):
            return table
    return candidates[0] if candidates else None


def parse_schedule(html: str, target_date: str | None = None) -> dict | None:
    """
    Parses the ZTOE page into
        {"date": "dd.mm.yyyy" | None, "queues": {11: [0/1 * 48], ..., 62: [...]}}
    Returns None when the schedule table can't be recognised.
    """
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    table = _find_schedule_table(soup)
    if table is None:
        log.error("ztoe parse: schedule table not found")
        return None

    # Dates in the header (one per day block of 48 or 24 slots).
    dates: list[str] = []
    header_colspans: list[int] = []
    for tr in table.find_all("tr"):
        cells = _row_cells(tr)
        if any(_LABEL_RE.match(td.get_text(strip=True)) for td in cells):
            break
        for td in cells:
            m = _DATE_RE.search(td.get_text(strip=True))
            if m:
                dates.append(m.group(0))
                try:
                    header_colspans.append(int(td.get("colspan") or 0))
                except (TypeError, ValueError):
                    header_colspans.append(0)

    target_date = target_date or today_str()
    day_idx = dates.index(target_date) if target_date in dates else 0
    date = dates[day_idx] if dates else None
    num_days = max(1, len(dates))

    queues: dict[int, list[int]] = {}
    for tr in table.find_all("tr"):
        cells = _row_cells(tr)
        label_pos = None
        code = None
        for i, td in enumerate(cells):
            m = _LABEL_RE.match(td.get_text(strip=True))
            if m:
                label_pos = i
                code = int(m.group(1)) * 10 + int(m.group(2))
        if label_pos is None:
            continue

        slots = [td for td in cells[label_pos + 1:] if _is_slot_cell(td)]

        # Determine slots per day: normally 48 (half-hour), fallback to 24 (hourly).
        per_day = SLOTS_PER_DAY
        if len(slots) == 24 * num_days or (
            day_idx < len(header_colspans) and header_colspans[day_idx] == 24 and len(slots) >= 24
        ):
            per_day = 24

        start = day_idx * per_day
        day_slots = slots[start:start + per_day]
        if len(day_slots) != per_day:
            log.error(
                "ztoe parse: queue %s has %s slot cells, expected %s*n",
                code,
                len(slots),
                per_day,
            )
            continue

        parsed_row = [0 if _cell_color(td) in _WHITE else 1 for td in day_slots]
        if per_day == 24:
            parsed_row = [v for v in parsed_row for _ in range(2)]

        queues[code] = parsed_row

    if not queues:
        log.error("ztoe parse: no queues parsed")
        return None

    if date and date != target_date:
        log.warning("ztoe parse: page has schedule for %s, today is %s", dates, target_date)

    return {"date": date, "queues": queues}


async def get_schedule() -> dict | None:
    """Fetches and parses the ZTOE schedule using direct access with automatic fallbacks."""
    global _preferred_source, _last_direct_probe

    for source in _ordered_sources():
        if source["is_direct"]:
            _last_direct_probe = time.monotonic()

        html = await _fetch_source(source)
        if not html:
            continue

        try:
            parsed = await asyncio.to_thread(parse_schedule, html)
        except Exception as e:
            log.error("ztoe parse error [%s]: %r", source["name"], e)
            parsed = None

        if parsed and parsed.get("queues"):
            if _preferred_source != source["name"]:
                log.info(
                    "ztoe schedule loaded via [%s] (date=%s, queues=%d)",
                    source["name"],
                    parsed.get("date"),
                    len(parsed["queues"]),
                )
            _preferred_source = source["name"]
            return parsed

        log.warning("ztoe fetch [%s]: response did not contain a valid schedule table", source["name"])

    log.error("ztoe fetch: all schedule sources failed")
    return None
