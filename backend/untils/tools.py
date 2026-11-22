import aiohttp, asyncio, logging, re
from datetime import datetime
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

SITE_URL = "https://www.ztoe.com.ua/unhooking-search.php"
SLOTS_PER_DAY = 48

_LABEL_RE = re.compile(r"^\s*([1-6])\.([12])\s*$")
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_WHITE = {"", "#ffffff", "#fff", "white", "none", "transparent"}

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


async def fetch_page() -> str | None:
    """Downloads the ZTOE schedule page once. Returns HTML or None."""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    timeout = aiohttp.ClientTimeout(total=30)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(SITE_URL, headers=headers) as resp:
                resp.raise_for_status()
                raw = await resp.read()
                encoding = resp.charset or "cp1251"
    except asyncio.TimeoutError:
        log.error("ztoe fetch: time out")
        return None
    except aiohttp.ClientError as e:
        log.error(f"ztoe fetch: client err: {e!r}")
        return None

    try:
        return raw.decode(encoding, errors="replace")
    except LookupError:
        return raw.decode("cp1251", errors="replace")


def _cell_color(td) -> str:
    style = td.get("style") or ""
    for part in style.split(";"):
        part = part.strip()
        if part.lower().startswith("background"):
            return part.split(":", 1)[1].strip().lower() if ":" in part else ""
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

    # Dates in the header (one per day block of 48 slots).
    dates: list[str] = []
    for tr in table.find_all("tr"):
        cells = _row_cells(tr)
        if any(_LABEL_RE.match(td.get_text(strip=True)) for td in cells):
            break
        for td in cells:
            m = _DATE_RE.search(td.get_text(strip=True))
            if m:
                dates.append(m.group(0))

    target_date = target_date or today_str()
    day_idx = dates.index(target_date) if target_date in dates else 0
    date = dates[day_idx] if dates else None

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
        start = day_idx * SLOTS_PER_DAY
        day_slots = slots[start:start + SLOTS_PER_DAY]
        if len(day_slots) != SLOTS_PER_DAY:
            log.error(f"ztoe parse: queue {code} has {len(slots)} slot cells, expected {SLOTS_PER_DAY}*n")
            continue

        queues[code] = [0 if _cell_color(td) in _WHITE else 1 for td in day_slots]

    if not queues:
        log.error("ztoe parse: no queues parsed")
        return None

    if date and date != target_date:
        log.warning(f"ztoe parse: page has schedule for {dates}, today is {target_date}")

    return {"date": date, "queues": queues}


async def get_schedule() -> dict | None:
    html = await fetch_page()
    if html is None:
        return None
    try:
        return parse_schedule(html)
    except Exception as e:
        log.error(f"ztoe parse error: {e!r}")
        return None
