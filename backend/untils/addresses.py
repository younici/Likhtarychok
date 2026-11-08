import asyncio
import bisect
import difflib
import json
import logging
import re
import time
from collections import Counter
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

import aiohttp
from bs4 import BeautifulSoup

from untils import redis_db as redis_un
from untils import tools
from untils.variebles import QUEUE_LABELS

log = logging.getLogger(__name__)

REDIS_ADDRESSES_KEY = "ztoe_addresses_cache"
CACHE_MAX_AGE_SECONDS = 12 * 3600  # 12 hours
BACKGROUND_RETRY_SECONDS = 300  # min pause between background load attempts

# ---------------------------------------------------------------------------
# Russian <-> Ukrainian Street & Settlement Synonyms Dictionary
# ---------------------------------------------------------------------------
RUSSIAN_REPLACEMENTS: List[Tuple[str, str]] = [
    # Multi-word phrases
    ("большая бердичевская", "велика бердичівська"),
    ("малая бердичевская", "мала бердичівська"),
    ("леси украинки", "лесі українки"),
    ("небесной сотни", "небесної сотні"),
    ("ивана кочерги", "івана кочерги"),
    ("князей острожских", "князів острозьких"),
    ("князей острожского", "князів острозьких"),
    ("ивана мазепы", "івана мазепи"),
    ("сергея параджанова", "сергія параджанова"),
    ("житний рынок", "житній ринок"),
    ("героев десантников", "героїв десантників"),
    ("героев чернобыля", "героїв чорнобиля"),
    ("героев крут", "героїв крут"),
    ("героев пожарных", "героїв пожежних"),
    ("героев майдана", "героїв майдану"),
    ("героев басараба", "героїв басараба"),
    ("святослава рихтера", "святослава ріхтера"),
    ("новоград-волынский", "звягель"),
    ("новоград волынский", "звягель"),
    ("новоград", "звягель"),
    ("володарск-волынский", "хорошів"),
    ("червоноармейск", "пулини"),
    ("1 мая", "1 травня"),
    # Settlements of Zhytomyr Oblast
    ("бердичев", "бердичів"),
    ("коростышев", "коростишів"),
    ("олевск", "олевськ"),
    ("радомышль", "радомишль"),
    ("барановка", "баранівка"),
    ("андрушевка", "андрушівка"),
    ("хорошев", "хорошів"),
    ("черняхов", "черняхів"),
    ("чуднов", "чуднів"),
    ("романов", "романів"),
    ("попельня", "попільня"),
    ("брусилов", "брусилів"),
    ("пулины", "пулини"),
    ("станишовка", "станишівка"),
    ("заречаны", "зарічани"),
    ("тетеревка", "тетерівка"),
    ("глубочица", "глибочиця"),
    ("олиевка", "оліївка"),
    ("новогуйвинское", "новогуйвинське"),
    ("озерное", "озерне"),
    ("ивановка", "іванівка"),
    ("сигуры", "сінгури"),
    ("сингуры", "сінгури"),
    ("пряжев", "пряжів"),
    ("вересы", "вереси"),
    ("левков", "левків"),
    ("каменка", "кам'янка"),
    ("солнечное", "сонячне"),
    # Street names
    ("киевская", "київська"),
    ("киевский", "київський"),
    ("бердичевская", "бердичівська"),
    ("бердичевский", "бердичівський"),
    ("чудновская", "чуднівська"),
    ("чудновский", "чуднівський"),
    ("покровская", "покровська"),
    ("покровский", "покровський"),
    ("победы", "перемоги"),
    ("мира", "миру"),
    ("независимости", "незалежності"),
    ("восточная", "східна"),
    ("восточный", "східний"),
    ("хлебная", "хлібна"),
    ("хлебный", "хлібний"),
    ("полевая", "польова"),
    ("полевой", "польовий"),
    ("промышленная", "промислова"),
    ("промышленный", "промисловий"),
    ("театральная", "театральна"),
    ("театральный", "театральний"),
    ("кафедральная", "кафедральна"),
    ("соборная", "соборна"),
    ("соборный", "соборний"),
    ("королева", "корольова"),
    ("грушевского", "грушевського"),
    ("шевченко", "шевченка"),
    ("острожских", "острозьких"),
    ("мазепы", "мазепи"),
    ("рихтера", "ріхтера"),
    ("космонавтов", "космонавтів"),
    ("циолковского", "ціолковського"),
    ("домбровского", "домбровського"),
    ("витрука", "вітрука"),
    ("селецкая", "селецька"),
    ("житомирская", "житомирська"),
    ("житомирский", "житомирський"),
    ("европейская", "європейська"),
    ("винницкая", "вінницька"),
    ("центральная", "центральна"),
    ("лесная", "лісова"),
    ("садовая", "садова"),
    ("школьная", "шкільна"),
    ("молодежная", "молодіжна"),
    ("вокзальная", "вокзальна"),
    ("набережная", "набережна"),
    ("гагарина", "гагаріна"),
    ("чкалова", "чкалова"),
    ("пушкина", "пушкіна"),
]


# All replacements are compiled into ONE regex (longest phrases first) instead of
# running ~150 separate re.sub() calls for every string.
_RU_MAP: Dict[str, str] = {ru: ua for ru, ua in RUSSIAN_REPLACEMENTS}
_RU_PATTERN = re.compile(
    r"\b("
    + "|".join(re.escape(k) for k in sorted(_RU_MAP, key=len, reverse=True))
    + r")\b"
)

_ENDINGS_MAP: Dict[str, str] = {
    "ская": "ська",
    "ский": "ський",
    "цкая": "цька",
    "цкий": "цький",
    "овка": "івка",
}
_ENDINGS_PATTERN = re.compile(r"(ская|ский|цкая|цкий|овка)\b")

_APOSTROPHES_PATTERN = re.compile(r"[’`ʼ\"]")
_PUNCT_PATTERN = re.compile(r"[^\w\s\'-]")
_RU_LETTERS = str.maketrans({"ы": "и", "э": "е", "ъ": "", "ё": "ьо"})
_FOLD_TABLE = str.maketrans(
    {"і": "и", "ї": "и", "є": "е", "ґ": "г", "'": "", "`": "", "-": " "}
)

ABBREVIATIONS_PATTERN = re.compile(
    r"(?:^|\b)(вул|вулиця|ул|улица|пров|провулок|пер|переулок|пр-т|просп|проспект|майдан|пл|площа|площадь|тупик|проїзд|лінія|м|місто|г|город|с|село|смт|селище|с/рада|буд|будинок|д|дом|кв|рем)(?:\.|\b)",
    re.IGNORECASE,
)

HOUSE_PATTERN = re.compile(
    r"^\d+([а-яa-zіїєґ]|\/[0-9а-яa-zіїєґ-]+|-[0-9а-яa-zіїєґ]+)?$",
    re.IGNORECASE,
)
SINGLE_LETTER_SUFFIX_PATTERN = re.compile(r"^[а-яa-zіїєґ]$", re.IGNORECASE)
ORDINAL_PATTERN = re.compile(r"^\d+-(й|а|е|я|ій)$", re.IGNORECASE)
STREET_TYPE_PATTERN = re.compile(
    r"^(пров|провулок|пер|переулок|пр-т|просп|проспект|лінія|вул|вулиця|тупик|проїзд|травня|березня|грудня|жовтня|серпня|січня|лютого|квітня|червня|липня|вересня|листопада|річчя)\.?",
    re.IGNORECASE,
)
HOUSE_MARKER_PATTERN = re.compile(r"^(буд|будинок|д|дом|кв|№)\.?$", re.IGNORECASE)

LATIN_TO_CYR_HOUSE = str.maketrans(
    {
        "a": "а",
        "b": "б",
        "c": "в",
        "d": "г",
        "e": "е",
        "i": "і",
        "k": "к",
        "m": "м",
        "o": "о",
        "p": "р",
        "x": "х",
    }
)

HOUSE_SORT_RE = re.compile(r"^(\d+)(.*)$")
HOUSE_BASE_DIGITS_RE = re.compile(r"^(\d+)")
HOUSE_LETTER_HYPHEN_RE = re.compile(r"^(\d+)-([а-яіїєґ]+)$")

RESIDENTIAL_PREFIXES = ("вул", "пров", "просп", "майдан", "пл")


@lru_cache(maxsize=65536)
def canonical_house(house_str: str) -> str:
    """
    Normalizes a house number string for accurate comparison:
    - '63-А', '63 А', '63А', '63a' -> '63а'
    - '94/2' -> '94/2'
    - '-5' -> '5', '42-' -> '42'
    """
    if not house_str:
        return ""
    h = house_str.strip().lower().translate(LATIN_TO_CYR_HOUSE)
    h = h.replace(" ", "")
    h = h.strip("-.,")
    h = HOUSE_LETTER_HYPHEN_RE.sub(r"\1\2", h)
    return h


def _house_sort_key(h: str) -> Tuple[int, int, str]:
    s = h.strip().lstrip("-")
    if not s or s.lower() == "б/н" or s.lower().startswith("тп"):
        return (2, 999999, s.lower())
    m = HOUSE_SORT_RE.match(s)
    if m:
        return (0, int(m.group(1)), m.group(2).strip(" -").lower())
    return (1, 999999, s.lower())


@lru_cache(maxsize=65536)
def normalize_text(text: str) -> str:
    """
    Normalizes street / settlement text:
    1. Lowercase & unify apostrophes.
    2. Dictionary replacements for Russian street & settlement names.
    3. Adjective ending conversions (ская -> ська, etc.).
    4. Russian letters (ы->и, э->е, ъ->'', ё->ьо).
    5. Strip address type abbreviations (вул., м., с., селище, буд., etc.).
    6. Strip punctuation except internal hyphens / apostrophes.
    """
    if not text:
        return ""

    t = _APOSTROPHES_PATTERN.sub("'", text.lower())
    t = _RU_PATTERN.sub(lambda m: _RU_MAP[m.group(1)], t)
    t = _ENDINGS_PATTERN.sub(lambda m: _ENDINGS_MAP[m.group(1)], t)
    t = t.translate(_RU_LETTERS)
    t = ABBREVIATIONS_PATTERN.sub(" ", t)
    t = _PUNCT_PATTERN.sub(" ", t)
    return " ".join(t.split())


def fold_ukr(text: str) -> str:
    """Folds vowel variations (и/і/ї, е/є, г/ґ) and apostrophes for phonetic matching."""
    return text.translate(_FOLD_TABLE)


def parse_search_query(raw_query: str) -> Tuple[List[str], Optional[str]]:
    """
    Extracts normalized text tokens and optional house number from raw search query.
    Handles:
      - 'Київська 21' -> (['київська'], '21')
      - 'Київська 63-а' -> (['київська'], '63-а')
      - 'Київська 63 а' -> (['київська'], '63а')
      - 'м. Житомир, вул. Велика Бердичівська, 15/1' -> (['житомир', 'велика', 'бердичівська'], '15/1')
      - 'Бердичів Житомирська 131' -> (['бердичів', 'житомирська'], '131')
      - '1 пров. Калиновий 5' -> (['1', 'калиновий'], '5')
    """
    cleaned = raw_query.replace(",", " ").replace(";", " ")
    parts = cleaned.split()

    house_token: Optional[str] = None
    text_parts: List[str] = []

    i = 0
    while i < len(parts):
        token = parts[i]
        next_token = parts[i + 1] if i + 1 < len(parts) else ""

        # Explicit house marker: "буд. 15", "дом 21", "№ 14"
        if HOUSE_MARKER_PATTERN.match(token) and next_token:
            if (
                i + 2 < len(parts)
                and next_token.isdigit()
                and SINGLE_LETTER_SUFFIX_PATTERN.match(parts[i + 2])
            ):
                house_token = f"{next_token}{parts[i + 2]}"
                i += 3
            else:
                house_token = next_token
                i += 2
            continue

        if HOUSE_PATTERN.match(token):
            is_last_token = i == len(parts) - 1
            # Number that is part of the street name ("1 пров.", "1 Травня", "1-й пров.")
            if not is_last_token and (
                ORDINAL_PATTERN.match(token)
                or (STREET_TYPE_PATTERN.match(next_token) and token.isdigit())
            ):
                text_parts.append(token)
            else:
                # House written with a space before the letter: "63 А"
                if (
                    token.isdigit()
                    and next_token
                    and SINGLE_LETTER_SUFFIX_PATTERN.match(next_token)
                ):
                    house_token = f"{token}{next_token}"
                    i += 2
                    continue
                house_token = token
        else:
            text_parts.append(token)
        i += 1

    normalized_text = normalize_text(" ".join(text_parts))
    text_tokens = [tok for tok in normalized_text.split() if tok]

    return text_tokens, house_token


# ---------------------------------------------------------------------------
# In-Memory Index (Backed by Redis Cache & Live ZTOE Sync)
# ---------------------------------------------------------------------------
class IndexedRecord:
    __slots__ = (
        "raw",
        "rem",
        "city",
        "street",
        "queue_code",
        "norm_street",
        "street_words_f",
        "city_words_f",
        "street_set",
        "city_set",
        "houses_sorted",
        "houses_preview",
        "houses_canon_map",
        "houses_base_map",
        "is_zhytomyr_city",
        "is_major_city",
        "is_residential",
        "total_queues_for_street",
    )

    def __init__(self, item: Dict[str, Any], total_queues_for_street: int = 1):
        self.raw = item
        self.rem: str = item.get("rem", "").strip()
        self.city: str = item.get("city", "").strip()
        self.street: str = item.get("street", "").strip()
        self.queue_code: int = int(item.get("queue", 11))
        self.total_queues_for_street: int = total_queues_for_street

        self.norm_street = normalize_text(self.street)
        norm_city = normalize_text(self.city)

        self.street_words_f: Tuple[str, ...] = tuple(fold_ukr(self.norm_street).split())
        self.city_words_f: Tuple[str, ...] = tuple(fold_ukr(norm_city).split())
        self.street_set: FrozenSet[str] = frozenset(self.street_words_f)
        self.city_set: FrozenSet[str] = frozenset(self.city_words_f)

        unique_houses: Dict[str, None] = {}
        for h in item.get("houses", []):
            hs = h.strip()
            if hs:
                unique_houses[hs] = None

        sorted_houses = sorted(unique_houses.keys(), key=_house_sort_key)
        self.houses_sorted = sorted_houses

        real_houses = [h for h in sorted_houses if h.lower() != "б/н"]
        preview_source = real_houses if real_houses else sorted_houses
        self.houses_preview = ", ".join(preview_source[:14]) + (
            "…" if len(preview_source) > 14 else ""
        )

        canon_map: Dict[str, str] = {}
        base_map: Dict[str, str] = {}
        for h in real_houses:
            c = canonical_house(h)
            if c and c not in canon_map:
                canon_map[c] = h
            m_base = HOUSE_BASE_DIGITS_RE.match(c)
            if m_base:
                base_map.setdefault(m_base.group(1), h)

        self.houses_canon_map = canon_map
        self.houses_base_map = base_map
        self.is_zhytomyr_city = norm_city == "житомир"
        self.is_major_city = self.city.lower().startswith(("місто ", "м."))
        self.is_residential = self.street.lower().startswith(RESIDENTIAL_PREFIXES)


class _AddressIndex:
    """
    Immutable snapshot of the address index. A new snapshot is built off the event
    loop and swapped in with a single reference assignment, so readers never see
    a half-built index.
    """

    __slots__ = (
        "version",
        "records",
        "street_postings",
        "city_postings",
        "street_vocab",
        "city_vocab",
        "by_rem",
        "by_city",
        "default_ids",
        "locations",
        "updated_at",
        "source",
    )

    def __init__(self) -> None:
        self.version: int = 0
        self.records: List[IndexedRecord] = []
        self.street_postings: Dict[str, Set[int]] = {}
        self.city_postings: Dict[str, Set[int]] = {}
        self.street_vocab: List[str] = []
        self.city_vocab: List[str] = []
        self.by_rem: Dict[str, Set[int]] = {}
        self.by_city: Dict[str, Set[int]] = {}
        self.default_ids: List[int] = []
        self.locations: Dict[str, Any] = {
            "rems": [],
            "cities_by_rem": {},
            "total_rems": 0,
            "total_cities": 0,
        }
        self.updated_at: Optional[str] = None
        self.source: str = "empty"


_INDEX: _AddressIndex = _AddressIndex()
_VERSION_COUNTER = 0
_SYNC_LOCK: Optional[asyncio.Lock] = None
_BG_TASK: Optional["asyncio.Task[None]"] = None
_LAST_BG_ATTEMPT: float = 0.0


def _get_sync_lock() -> asyncio.Lock:
    global _SYNC_LOCK
    if _SYNC_LOCK is None:
        _SYNC_LOCK = asyncio.Lock()
    return _SYNC_LOCK


def _city_sort_key(city_name: str) -> Tuple[int, str]:
    c_low = city_name.lower()
    if c_low == "місто житомир":
        return (0, c_low)
    if c_low.startswith(("місто ", "м.")):
        return (1, normalize_text(city_name))
    if c_low.startswith(("селище ", "смт")):
        return (2, normalize_text(city_name))
    return (3, normalize_text(city_name))


def _rem_sort_key(rem_name: str) -> Tuple[int, str]:
    if rem_name == "Житомирський":
        return (0, rem_name)
    return (1, rem_name)


def _build_index(
    items: List[Dict[str, Any]], updated_at: Optional[str], source: str
) -> _AddressIndex:
    """CPU-heavy part: builds a full index snapshot. Safe to run in a worker thread."""
    idx = _AddressIndex()
    idx.updated_at = updated_at
    idx.source = source

    street_key = lambda it: (  # noqa: E731
        it.get("rem", "").strip(),
        it.get("city", "").strip(),
        it.get("street", "").strip(),
    )
    street_queue_counts = Counter(street_key(it) for it in items)

    records = [
        IndexedRecord(it, total_queues_for_street=street_queue_counts[street_key(it)])
        for it in items
    ]
    idx.records = records

    cities_by_rem_sets: Dict[str, Set[str]] = {}
    zhytomyr_ids: List[int] = []
    other_ids: List[int] = []

    for rid, rec in enumerate(records):
        for w in rec.street_set:
            idx.street_postings.setdefault(w, set()).add(rid)
        for w in rec.city_set:
            idx.city_postings.setdefault(w, set()).add(rid)

        if rec.rem:
            idx.by_rem.setdefault(rec.rem.lower(), set()).add(rid)
        if rec.city:
            idx.by_city.setdefault(rec.city.lower(), set()).add(rid)
        if rec.rem and rec.city:
            cities_by_rem_sets.setdefault(rec.rem, set()).add(rec.city)

        (zhytomyr_ids if rec.is_zhytomyr_city else other_ids).append(rid)

    idx.street_vocab = sorted(idx.street_postings)
    idx.city_vocab = sorted(idx.city_postings)
    idx.default_ids = zhytomyr_ids + other_ids

    rems_sorted = sorted(cities_by_rem_sets, key=_rem_sort_key)
    cities_by_rem = {
        rem: sorted(cities_by_rem_sets[rem], key=_city_sort_key) for rem in rems_sorted
    }
    idx.locations = {
        "rems": rems_sorted,
        "cities_by_rem": cities_by_rem,
        "total_rems": len(rems_sorted),
        "total_cities": sum(len(v) for v in cities_by_rem.values()),
    }
    return idx


def _swap_index(idx: _AddressIndex) -> None:
    global _INDEX, _VERSION_COUNTER
    _VERSION_COUNTER += 1
    idx.version = _VERSION_COUNTER
    _INDEX = idx
    _search_cached.cache_clear()
    _fuzzy_vocab_matches.cache_clear()
    log.info(
        "Addresses index updated: %d items across %d REMs and %d settlements (source: %s, updated_at: %s)",
        len(idx.records),
        idx.locations["total_rems"],
        idx.locations["total_cities"],
        idx.source,
        idx.updated_at,
    )


def _set_indexed_addresses(
    items: List[Dict[str, Any]], updated_at: Optional[str], source: str
) -> None:
    """Synchronously builds and activates a new index (use via asyncio.to_thread in async code)."""
    _swap_index(_build_index(items, updated_at, source))


async def _set_indexed_addresses_async(
    items: List[Dict[str, Any]], updated_at: Optional[str], source: str
) -> None:
    """Builds the index in a worker thread so the event loop is never blocked."""
    idx = await asyncio.to_thread(_build_index, items, updated_at, source)
    _swap_index(idx)


def get_meta() -> Dict[str, Any]:
    """Returns metadata about the currently loaded address index."""
    idx = _INDEX
    return {
        "total_indexed": len(idx.records),
        "total_rems": idx.locations.get("total_rems", 0),
        "total_cities": idx.locations.get("total_cities", 0),
        "updated_at": idx.updated_at,
        "source": idx.source,
    }


def get_locations() -> Dict[str, Any]:
    """Returns all REMs and settlements grouped by REM for Zhytomyr Oblast."""
    return _INDEX.locations


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
def _match_house_in_record(
    rec: IndexedRecord, ht_canon: str, ht_base: str
) -> Tuple[int, Optional[str]]:
    """
    Returns (tier, matched_house_display):
      tier 2 = exact canonical match ('21' == '21', '63а' == '63-А')
      tier 1 = variant/base match ('15' -> '15/1' or '15-А', never '150'; '15а' -> '15')
      tier 0 = no match
    """
    if not ht_canon:
        return 0, None

    if ht_canon in rec.houses_canon_map:
        return 2, rec.houses_canon_map[ht_canon]

    if ht_base:
        if ht_canon == ht_base:
            if ht_base in rec.houses_base_map:
                return 1, rec.houses_base_map[ht_base]
        else:
            if ht_base in rec.houses_canon_map:
                return 1, rec.houses_canon_map[ht_base]
            if ht_base in rec.houses_base_map:
                return 1, rec.houses_base_map[ht_base]

    return 0, None


def _format_result(record: IndexedRecord, matched_house: Optional[str]) -> Dict[str, Any]:
    item = record.raw
    queue_code = record.queue_code
    queue_label = item.get(
        "queue_label",
        QUEUE_LABELS.get(queue_code, f"{queue_code // 10}.{queue_code % 10}"),
    )
    return {
        "id": item.get("id"),
        "rem": record.rem,
        "city": record.city,
        "street": record.street,
        "houses": record.houses_sorted,
        "houses_preview": record.houses_preview,
        "matched_house": matched_house,
        "queue": str(queue_code),
        "queue_label": str(queue_label),
        "total_queues_for_street": record.total_queues_for_street,
        "note": item.get("note", "побутові споживачі"),
        "display": f"{record.city}, {record.street}",
    }


def _prefix_words(vocab: List[str], prefix: str) -> List[str]:
    """All vocabulary words starting with prefix (binary search on a sorted list)."""
    out: List[str] = []
    i = bisect.bisect_left(vocab, prefix)
    n = len(vocab)
    while i < n and vocab[i].startswith(prefix):
        out.append(vocab[i])
        i += 1
    return out


@lru_cache(maxsize=2048)
def _fuzzy_vocab_matches(
    version: int, tok_f: str
) -> Tuple[FrozenSet[str], FrozenSet[str]]:
    """Typo-tolerant matches computed ONCE per token over the unique vocabulary."""
    idx = _INDEX
    street = frozenset(difflib.get_close_matches(tok_f, idx.street_vocab, n=25, cutoff=0.76))
    city = frozenset(difflib.get_close_matches(tok_f, idx.city_vocab, n=25, cutoff=0.78))
    return street, city


def _filter_ids(idx: _AddressIndex, rem: str, city: str) -> Optional[Set[int]]:
    ids: Optional[Set[int]] = None
    if rem:
        ids = idx.by_rem.get(rem.lower(), set())
    if city:
        city_ids = idx.by_city.get(city.lower(), set())
        ids = city_ids if ids is None else (ids & city_ids)
    return ids


def _search_impl(
    idx: _AddressIndex, query: str, limit: int, rem: str, city: str
) -> List[Dict[str, Any]]:
    records = idx.records
    allowed = _filter_ids(idx, rem, city)

    # ── Empty query: browse selected settlement / REM, or default list ──
    if not query:
        if allowed is not None:
            recs = sorted(
                (records[i] for i in allowed),
                key=lambda r: (
                    _city_sort_key(r.city),
                    0 if r.is_residential else 1,
                    r.norm_street,
                    r.queue_code,
                ),
            )
            return [_format_result(r, None) for r in recs[:limit]]
        return [_format_result(records[i], None) for i in idx.default_ids[:limit]]

    text_tokens, house_token = parse_search_query(query)
    ht_canon = canonical_house(house_token) if house_token else ""
    m_base = HOUSE_BASE_DIGITS_RE.match(ht_canon) if ht_canon else None
    ht_base = m_base.group(1) if m_base else ""

    # Fold tokens the same way record words were folded (hyphen -> space, і -> и ...)
    tokens_f: List[str] = list(
        dict.fromkeys(w for t in text_tokens for w in fold_ukr(t).split())
    )
    num_tokens = len(tokens_f)

    # ── Candidate generation through the inverted index ──
    token_info: List[Tuple[str, FrozenSet[str], FrozenSet[str]]] = []
    if num_tokens > 0:
        hit_counts: Counter = Counter()
        for tok_f in tokens_f:
            ids: Set[int] = set()
            s_words = _prefix_words(idx.street_vocab, tok_f)
            if len(tok_f) >= 3:
                c_words = _prefix_words(idx.city_vocab, tok_f)
            else:
                c_words = [tok_f] if tok_f in idx.city_postings else []

            for w in s_words:
                ids |= idx.street_postings[w]
            for w in c_words:
                ids |= idx.city_postings[w]

            fz_s: FrozenSet[str] = frozenset()
            fz_c: FrozenSet[str] = frozenset()
            if len(tok_f) >= 4:
                # Similar word forms / typos ("київська" ~ "київське", "перемги" ~ "перемоги")
                fz_s, fz_c = _fuzzy_vocab_matches(idx.version, tok_f)
                for w in fz_s:
                    ids |= idx.street_postings[w]
                for w in fz_c:
                    ids |= idx.city_postings[w]

            token_info.append((tok_f, fz_s, fz_c))
            hit_counts.update(ids)

        required = num_tokens if num_tokens <= 2 else num_tokens - 1
        candidate_ids = [rid for rid, c in hit_counts.items() if c >= required]
        if allowed is not None:
            candidate_ids = [rid for rid in candidate_ids if rid in allowed]
    else:
        # Query contains only a house number
        candidate_ids = list(allowed) if allowed is not None else range(len(records))

    # ── Scoring of the (small) candidate set ──
    raw_candidates: List[Tuple[float, int, Optional[str], IndexedRecord]] = []

    for rid in candidate_ids:
        rec = records[rid]
        base_score = 0.0

        if num_tokens > 0:
            s_exact = s_pref = c_exact = c_pref = fuzzy = unmatched = 0
            for tok_f, fz_s, fz_c in token_info:
                if tok_f in rec.street_set:
                    s_exact += 1
                elif tok_f in rec.city_set:
                    c_exact += 1
                elif any(w.startswith(tok_f) for w in rec.street_words_f):
                    s_pref += 1
                elif len(tok_f) >= 3 and any(w.startswith(tok_f) for w in rec.city_words_f):
                    c_pref += 1
                elif (fz_s and not fz_s.isdisjoint(rec.street_set)) or (
                    fz_c and not fz_c.isdisjoint(rec.city_set)
                ):
                    fuzzy += 1
                else:
                    unmatched += 1

            if unmatched > 0:
                if num_tokens <= 2 or unmatched > 1:
                    continue
                base_score -= 40.0

            base_score += s_exact * 95.0 + s_pref * 70.0 + fuzzy * 35.0
            base_score += c_exact * 85.0 + c_pref * 55.0

            street_hit = (s_exact + s_pref) > 0
            city_hit = (c_exact + c_pref) > 0

            # Both settlement AND street matched ("Бердичів Житомирська")
            if city_hit and street_hit:
                base_score += 110.0

            if street_hit:
                first_word = rec.street_words_f[0] if rec.street_words_f else ""
                if first_word in tokens_f:
                    base_score += 35.0
                elif any(first_word.startswith(t) for t in tokens_f):
                    base_score += 20.0
                base_score -= min(len(rec.street_words_f), 5) * 2.0
            else:
                # Only the settlement matched ("Станишівка"): prefer real residential streets
                if rec.is_residential:
                    base_score += 15.0 + min(len(rec.houses_canon_map), 25) * 0.4
                else:
                    base_score -= 20.0

            if not city and not city_hit:
                if rec.is_zhytomyr_city:
                    base_score += 28.0
                elif rec.is_major_city:
                    base_score += 12.0

        house_tier = 0
        matched_house: Optional[str] = None
        if ht_canon:
            house_tier, matched_house = _match_house_in_record(rec, ht_canon, ht_base)
            if num_tokens == 0 and house_tier == 0:
                continue
            if house_tier == 2:
                base_score += 250.0
            elif house_tier == 1:
                base_score += 140.0

        if base_score > 0:
            raw_candidates.append((base_score, house_tier, matched_house, rec))

    # Multi-queue disambiguation: if some queue of the same street contains the house,
    # drop the other queues of that street that don't.
    if ht_canon and raw_candidates:
        best_tier: Dict[Tuple[str, str, str], int] = {}
        for _, h_tier, _, rec in raw_candidates:
            key = (rec.rem, rec.city, rec.street)
            if h_tier > best_tier.get(key, 0):
                best_tier[key] = h_tier
        raw_candidates = [
            c
            for c in raw_candidates
            if not (
                best_tier.get((c[3].rem, c[3].city, c[3].street), 0) > 0
                and c[1] < best_tier[(c[3].rem, c[3].city, c[3].street)]
            )
        ]

    raw_candidates.sort(
        key=lambda c: (
            c[0],
            c[1],
            1 if c[3].is_zhytomyr_city else (0.5 if c[3].is_major_city else 0),
            -c[3].queue_code,
        ),
        reverse=True,
    )

    return [_format_result(rec, mh) for _, _, mh, rec in raw_candidates[:limit]]


@lru_cache(maxsize=1024)
def _search_cached(
    version: int, query: str, limit: int, rem: str, city: str
) -> Tuple[Dict[str, Any], ...]:
    return tuple(_search_impl(_INDEX, query, limit, rem, city))


def search_addresses(
    query: str = "",
    limit: int = 15,
    rem: str = "",
    city: str = "",
) -> List[Dict[str, Any]]:
    """
    Smart address search across all REMs and settlements of Zhytomyr Oblast.
    Uses an inverted word index + LRU result cache. Pure CPU work: call it through
    `asyncio.to_thread` (or `search_addresses_async`) from async code.
    """
    return list(
        _search_cached(
            _INDEX.version,
            (query or "").strip(),
            int(limit),
            (rem or "").strip(),
            (city or "").strip(),
        )
    )


async def search_addresses_async(
    query: str = "", limit: int = 15, rem: str = "", city: str = ""
) -> List[Dict[str, Any]]:
    """Non-blocking wrapper for FastAPI endpoints."""
    return await asyncio.to_thread(search_addresses, query, limit, rem, city)


# ---------------------------------------------------------------------------
# Redis Cache + Live Scraping from ztoe.com.ua
# ---------------------------------------------------------------------------
def _is_cache_expired(updated_at: Optional[str]) -> bool:
    """Checks whether the cached updated_at timestamp is missing or older than 12 hours."""
    if not updated_at:
        return True
    try:
        dt = datetime.fromisoformat(updated_at)
    except ValueError:
        try:
            dt = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return True
    return (datetime.now() - dt).total_seconds() >= CACHE_MAX_AGE_SECONDS


def _decode_redis_payload(raw: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    data = json.loads(raw)
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list) and items:
            return items, data.get("updated_at")
    return None, None


async def _load_from_redis() -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Reads cached addresses payload from Redis if available."""
    redis_client = redis_un.get_redis_client()
    if not redis_client:
        return None, None
    try:
        raw = await redis_client.get(REDIS_ADDRESSES_KEY)
        if not raw:
            return None, None
        # Parsing several MB of JSON is CPU work -> worker thread
        return await asyncio.to_thread(_decode_redis_payload, raw)
    except Exception as exc:
        log.warning("Failed to load addresses cache from Redis: %s", exc)
    return None, None


async def _save_to_redis(records: List[Dict[str, Any]], updated_at: str) -> bool:
    """Persists parsed addresses and timestamp into Redis."""
    redis_client = redis_un.get_redis_client()
    if not redis_client:
        return False
    try:
        payload = await asyncio.to_thread(
            json.dumps,
            {"updated_at": updated_at, "source": "ztoe_live", "items": records},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        await redis_client.set(REDIS_ADDRESSES_KEY, payload)
        log.info("Saved %d addresses to Redis (updated_at: %s)", len(records), updated_at)
        return True
    except Exception as exc:
        log.warning("Failed to save addresses to Redis: %s", exc)
        return False


def _parse_ztoe_html(
    html: str, pidcherga_id: int
) -> List[Tuple[str, str, str, int, List[str]]]:
    """CPU-heavy BeautifulSoup parsing of one ZTOE page. Runs in a worker thread."""
    soup = BeautifulSoup(html, "html.parser")
    target_table = None
    for tbl in soup.find_all("table"):
        if tbl.find("table"):
            continue
        first_tr = tbl.find("tr")
        if first_tr and "Населений пункт" in first_tr.get_text():
            target_table = tbl
            break

    if not target_table:
        log.warning("No innermost address table found for pidcherga %s", pidcherga_id)
        return []

    parsed_rows: List[Tuple[str, str, str, int, List[str]]] = []
    for row in target_table.find_all("tr")[1:]:
        tds = row.find_all("td")
        if len(tds) < 6:
            continue

        rem = tds[0].get_text(strip=True)
        city = tds[1].get_text(strip=True)
        street = tds[2].get_text(strip=True)
        houses_raw = tds[3].get_text(strip=True)
        cherga_str = tds[4].get_text(strip=True)
        pidcherga_str = tds[5].get_text(strip=True)

        if "РЕМ" in rem or "Населений пункт" in city:
            continue

        if cherga_str.isdigit() and pidcherga_str.isdigit():
            queue_code = int(cherga_str) * 10 + int(pidcherga_str)
        else:
            queue_code = tools.index_to_queue(pidcherga_id)

        raw_houses = [h.strip() for h in re.split(r"[,;]+", houses_raw) if h.strip()]
        parsed_rows.append((rem, city, street, queue_code, raw_houses))

    return parsed_rows


async def sync_addresses_from_ztoe() -> bool:
    """
    Downloads addresses from https://www.ztoe.com.ua/unhooking-search.php?pidcherga_id={1..12}.
    If ZTOE is available, rebuilds the in-memory index and saves to Redis.
    If ZTOE is unavailable, leaves the existing Redis cache and in-memory index untouched.
    """
    lock = _get_sync_lock()
    if lock.locked():
        async with lock:
            return bool(_INDEX.records)

    async with lock:
        log.info("Starting full oblast addresses synchronization from ztoe.com.ua...")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
        }
        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(ssl=False)
        sem = asyncio.Semaphore(4)

        async def fetch_pidcherga(
            session: aiohttp.ClientSession, pidcherga_id: int
        ) -> List[Tuple[str, str, str, int, List[str]]]:
            url = f"https://www.ztoe.com.ua/unhooking-search.php?pidcherga_id={pidcherga_id}"
            async with sem:
                try:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status != 200:
                            log.warning("ZTOE responded with status %s for %s", resp.status, url)
                            return []
                        raw_bytes = await resp.read()
                except Exception as req_err:
                    log.warning("Error fetching ZTOE pidcherga %s: %s", pidcherga_id, req_err)
                    return []

            html = raw_bytes.decode("cp1251", errors="ignore")
            try:
                return await asyncio.to_thread(_parse_ztoe_html, html, pidcherga_id)
            except Exception as parse_err:
                log.warning("Error parsing ZTOE pidcherga %s: %s", pidcherga_id, parse_err)
                return []

        grouped: Dict[Tuple[str, str, str, int], Dict[str, None]] = {}
        try:
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                results = await asyncio.gather(
                    *(fetch_pidcherga(session, pid) for pid in range(1, 13))
                )
            for pid_rows in results:
                for rem, city, street, queue_code, raw_houses in pid_rows:
                    bucket = grouped.setdefault((rem, city, street, queue_code), {})
                    for h in raw_houses:
                        bucket[h] = None
        except Exception as exc:
            log.warning("sync_addresses_from_ztoe encountered an unexpected error: %s", exc)

        if len(grouped) < 100:
            log.warning(
                "ZTOE website unavailable or returned incomplete data (%d records). "
                "Keeping existing Redis cache untouched.",
                len(grouped),
            )
            return False

        records: List[Dict[str, Any]] = [
            {
                "id": i,
                "rem": rem,
                "city": city,
                "street": street,
                "houses": list(houses.keys()),
                "queue": queue_code,
                "queue_label": QUEUE_LABELS.get(
                    queue_code, f"{queue_code // 10}.{queue_code % 10}"
                ),
            }
            for i, ((rem, city, street, queue_code), houses) in enumerate(grouped.items(), start=1)
        ]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await _set_indexed_addresses_async(records, updated_at=now_str, source="ztoe_live")
        await _save_to_redis(records, now_str)
        return True


async def ensure_addresses_loaded() -> None:
    """
    Startup & on-demand loader:
    1. Checks Redis for cached addresses ('ztoe_addresses_cache').
    2. If found: loads them into memory immediately; if older than 12h, fetches fresh
       data from ztoe.com.ua (if the site is down, the Redis cache stays in use).
    3. If not found: parses ztoe.com.ua right away and saves the result to Redis.
    """
    items, updated_at = await _load_from_redis()

    if items:
        await _set_indexed_addresses_async(items, updated_at=updated_at, source="redis_cache")
        if _is_cache_expired(updated_at):
            log.info(
                "Redis address cache is outdated (updated_at=%s). Fetching fresh data from ZTOE...",
                updated_at,
            )
            await sync_addresses_from_ztoe()
        else:
            log.info(
                "Loaded fresh address cache from Redis (%d records, updated_at=%s)",
                len(items),
                updated_at,
            )
    else:
        log.info("No addresses found in Redis cache. Parsing ztoe.com.ua immediately...")
        await sync_addresses_from_ztoe()


def trigger_background_load() -> None:
    """
    Fire-and-forget loading when the index is empty. Never blocks a request and
    is rate-limited, so a ZTOE outage can't cause a sync storm.
    """
    global _BG_TASK, _LAST_BG_ATTEMPT
    if _BG_TASK is not None and not _BG_TASK.done():
        return
    now = time.monotonic()
    if _LAST_BG_ATTEMPT and now - _LAST_BG_ATTEMPT < BACKGROUND_RETRY_SECONDS:
        return
    _LAST_BG_ATTEMPT = now
    _BG_TASK = asyncio.create_task(ensure_addresses_loaded())
