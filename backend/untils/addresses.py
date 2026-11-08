import asyncio
import difflib
import json
import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

from untils import redis_db as redis_un
from untils import tools
from untils.variebles import QUEUE_LABELS

log = logging.getLogger(__name__)

REDIS_ADDRESSES_KEY = "ztoe_addresses_cache"
CACHE_MAX_AGE_SECONDS = 12 * 3600  # 12 hours

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

ENDINGS_SUB: List[Tuple[str, str]] = [
    (r"ская\b", "ська"),
    (r"ский\b", "ський"),
    (r"цкая\b", "цька"),
    (r"цкий\b", "цький"),
    (r"овка\b", "івка"),
]

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
    h = re.sub(r"^(\d+)-([а-яіїєґ]+)$", r"\1\2", h)
    return h


def _house_sort_key(h: str) -> Tuple[int, int, str]:
    s = h.strip().lstrip("-")
    if not s or s.lower() == "б/н" or s.lower().startswith("тп"):
        return (2, 999999, s.lower())
    m = HOUSE_SORT_RE.match(s)
    if m:
        return (0, int(m.group(1)), m.group(2).strip(" -").lower())
    return (1, 999999, s.lower())


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

    t = text.lower()
    t = re.sub(r"[’`ʼ\"]", "'", t)

    for ru, ua in RUSSIAN_REPLACEMENTS:
        pattern = r"\b" + re.escape(ru) + r"\b"
        t = re.sub(pattern, ua, t)

    for pat, rep in ENDINGS_SUB:
        t = re.sub(pat, rep, t)

    trans = str.maketrans({"ы": "и", "э": "е", "ъ": "", "ё": "ьо"})
    t = t.translate(trans)

    t = ABBREVIATIONS_PATTERN.sub(" ", t)
    t = re.sub(r"[^\w\s\'-]", " ", t)
    return " ".join(t.split())


def fold_ukr(text: str) -> str:
    """Folds vowel variations (и/і/ї, е/є, г/ґ) and apostrophes for phonetic matching."""
    return (
        text.replace("і", "и")
        .replace("ї", "и")
        .replace("є", "е")
        .replace("ґ", "г")
        .replace("'", "")
        .replace("`", "")
        .replace("-", " ")
    )


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
            # Check if this number is part of the street name (e.g. "1 пров.", "1 Травня", "1-й пров.")
            if not is_last_token and (
                ORDINAL_PATTERN.match(token)
                or (STREET_TYPE_PATTERN.match(next_token) and token.isdigit())
            ):
                text_parts.append(token)
            else:
                # Check if user wrote house with space before letter: "63 А"
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
        "norm_rem",
        "norm_street",
        "norm_city",
        "street_folded",
        "city_folded",
        "street_words",
        "street_folded_words",
        "city_words",
        "city_folded_words",
        "houses_sorted",
        "houses_preview",
        "houses_canon_map",
        "houses_base_map",
        "is_zhytomyr_city",
        "is_major_city",
        "total_queues_for_street",
    )

    def __init__(self, item: Dict[str, Any], total_queues_for_street: int = 1):
        self.raw = item
        self.rem: str = item.get("rem", "").strip()
        self.city: str = item.get("city", "").strip()
        self.street: str = item.get("street", "").strip()
        self.queue_code: int = int(item.get("queue", 11))
        self.total_queues_for_street: int = total_queues_for_street

        self.norm_rem = normalize_text(self.rem)
        self.norm_street = normalize_text(self.street)
        self.norm_city = normalize_text(self.city)

        self.street_folded = fold_ukr(self.norm_street)
        self.city_folded = fold_ukr(self.norm_city)

        self.street_words = self.norm_street.split()
        self.street_folded_words = self.street_folded.split()
        self.city_words = self.norm_city.split()
        self.city_folded_words = self.city_folded.split()

        raw_houses: List[str] = item.get("houses", [])
        unique_houses: Dict[str, None] = {}
        for h in raw_houses:
            hs = h.strip()
            if hs:
                unique_houses[hs] = None

        sorted_houses = sorted(unique_houses.keys(), key=_house_sort_key)
        self.houses_sorted = sorted_houses

        real_houses = [h for h in sorted_houses if h.lower() != "б/н"]
        preview_source = real_houses if real_houses else sorted_houses
        preview_slice = preview_source[:14]
        self.houses_preview = ", ".join(preview_slice) + (
            "…" if len(preview_source) > 14 else ""
        )

        canon_map: Dict[str, str] = {}
        base_map: Dict[str, str] = {}
        for h in sorted_houses:
            if h.lower() == "б/н":
                continue
            c = canonical_house(h)
            if c and c not in canon_map:
                canon_map[c] = h
            m_base = HOUSE_BASE_DIGITS_RE.match(c)
            if m_base:
                b_num = m_base.group(1)
                if b_num not in base_map:
                    base_map[b_num] = h

        self.houses_canon_map = canon_map
        self.houses_base_map = base_map
        self.is_zhytomyr_city = self.norm_city == "житомир"
        self.is_major_city = self.city.lower().startswith(("місто ", "м."))


_INDEXED_RECORDS: List[IndexedRecord] = []
_LOCATIONS_CACHE: Dict[str, Any] = {
    "rems": [],
    "cities_by_rem": {},
    "total_rems": 0,
    "total_cities": 0,
}
_UPDATED_AT: Optional[str] = None
_SOURCE: str = "empty"
_SYNC_LOCK: Optional[asyncio.Lock] = None


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


def _set_indexed_addresses(
    items: List[Dict[str, Any]], updated_at: Optional[str], source: str
) -> None:
    global _INDEXED_RECORDS, _LOCATIONS_CACHE, _UPDATED_AT, _SOURCE

    street_queue_counts = Counter(
        (
            item.get("rem", "").strip(),
            item.get("city", "").strip(),
            item.get("street", "").strip(),
        )
        for item in items
    )

    _INDEXED_RECORDS = [
        IndexedRecord(
            item,
            total_queues_for_street=street_queue_counts[
                (
                    item.get("rem", "").strip(),
                    item.get("city", "").strip(),
                    item.get("street", "").strip(),
                )
            ],
        )
        for item in items
    ]
    _UPDATED_AT = updated_at
    _SOURCE = source

    cities_by_rem_sets: Dict[str, set] = {}
    for rec in _INDEXED_RECORDS:
        if rec.rem and rec.city:
            cities_by_rem_sets.setdefault(rec.rem, set()).add(rec.city)

    rems_sorted = sorted(cities_by_rem_sets.keys(), key=_rem_sort_key)
    cities_by_rem = {
        rem: sorted(cities_by_rem_sets[rem], key=_city_sort_key)
        for rem in rems_sorted
    }
    total_cities = sum(len(v) for v in cities_by_rem.values())

    _LOCATIONS_CACHE = {
        "rems": rems_sorted,
        "cities_by_rem": cities_by_rem,
        "total_rems": len(rems_sorted),
        "total_cities": total_cities,
    }

    log.info(
        "Addresses index updated: %d items across %d REMs and %d settlements (source: %s, updated_at: %s)",
        len(_INDEXED_RECORDS),
        len(rems_sorted),
        total_cities,
        source,
        updated_at,
    )


def get_meta() -> Dict[str, Any]:
    """Returns metadata about the currently loaded address index."""
    return {
        "total_indexed": len(_INDEXED_RECORDS),
        "total_rems": _LOCATIONS_CACHE.get("total_rems", 0),
        "total_cities": _LOCATIONS_CACHE.get("total_cities", 0),
        "updated_at": _UPDATED_AT,
        "source": _SOURCE,
    }


def get_locations() -> Dict[str, Any]:
    """Returns all REMs and settlements grouped by REM for Zhytomyr Oblast."""
    return _LOCATIONS_CACHE


def _match_house_in_record(
    rec: IndexedRecord, ht_canon: str, ht_base: str
) -> Tuple[int, Optional[str]]:
    """
    Matches canonical house token against a record's houses.
    Returns (tier, matched_house_display):
      tier 2 = exact canonical house match (e.g. '21' == '21', '63а' == '63-А')
      tier 1 = variant/base match (e.g. query '15' matches '15/1' or '15-А', NEVER '150';
               or query '15а' matches base '15')
      tier 0 = no match
    """
    if not ht_canon:
        return 0, None

    if ht_canon in rec.houses_canon_map:
        return 2, rec.houses_canon_map[ht_canon]

    if ht_base and ht_canon == ht_base:
        if ht_base in rec.houses_base_map:
            return 1, rec.houses_base_map[ht_base]

    if ht_base and ht_canon != ht_base:
        if ht_base in rec.houses_canon_map:
            return 1, rec.houses_canon_map[ht_base]
        if ht_base in rec.houses_base_map:
            return 1, rec.houses_base_map[ht_base]

    return 0, None


def _format_result(
    record: IndexedRecord, matched_house: Optional[str]
) -> Dict[str, Any]:
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


def search_addresses(
    query: str = "",
    limit: int = 15,
    rem: str = "",
    city: str = "",
) -> List[Dict[str, Any]]:
    """
    Smart address search across all REMs and settlements of Zhytomyr Oblast.
    """
    clean_query = (query or "").strip()
    rem_filter = (rem or "").strip()
    city_filter = (city or "").strip()

    norm_rem_filter = normalize_text(rem_filter) if rem_filter else ""
    norm_city_filter = normalize_text(city_filter) if city_filter else ""

    pool: List[IndexedRecord] = []
    for rec in _INDEXED_RECORDS:
        if rem_filter:
            if rec.rem.lower() != rem_filter.lower() and rec.norm_rem != norm_rem_filter:
                continue
        if city_filter:
            if (
                rec.city.lower() != city_filter.lower()
                and rec.norm_city != norm_city_filter
            ):
                continue
        pool.append(rec)

    if not clean_query:
        if city_filter or rem_filter:
            sorted_pool = sorted(
                pool,
                key=lambda r: (
                    _city_sort_key(r.city),
                    0
                    if r.street.lower().startswith(
                        ("вул", "пров", "просп", "майдан", "пл")
                    )
                    else 1,
                    r.norm_street,
                    r.queue_code,
                ),
            )
            return [_format_result(rec, None) for rec in sorted_pool[:limit]]

        top = [
            _format_result(rec, None) for rec in pool if rec.is_zhytomyr_city
        ][:limit]
        if len(top) < limit:
            remaining = [
                _format_result(rec, None) for rec in pool if not rec.is_zhytomyr_city
            ][: (limit - len(top))]
            top.extend(remaining)
        return top

    text_tokens, house_token = parse_search_query(clean_query)
    ht_canon = canonical_house(house_token) if house_token else ""
    m_base = HOUSE_BASE_DIGITS_RE.match(ht_canon) if ht_canon else None
    ht_base = m_base.group(1) if m_base else ""

    tokens_folded = [fold_ukr(tok) for tok in text_tokens]
    num_tokens = len(text_tokens)

    raw_candidates: List[Tuple[float, int, Optional[str], IndexedRecord]] = []

    for rec in pool:
        base_score = 0.0

        if num_tokens > 0:
            street_exact_hits = 0
            street_prefix_hits = 0
            city_exact_hits = 0
            city_prefix_hits = 0
            fuzzy_hits = 0
            unmatched_tokens = 0

            for idx, tok in enumerate(text_tokens):
                tok_f = tokens_folded[idx]
                is_street_exact = (
                    tok in rec.street_words or tok_f in rec.street_folded_words
                )
                is_city_exact = (
                    tok in rec.city_words or tok_f in rec.city_folded_words
                )
                is_street_prefix = not is_street_exact and any(
                    sw.startswith(tok) or sw_f.startswith(tok_f)
                    for sw, sw_f in zip(rec.street_words, rec.street_folded_words)
                )
                is_city_prefix = (
                    not is_city_exact
                    and len(tok) >= 3
                    and any(
                        cw.startswith(tok) or cw_f.startswith(tok_f)
                        for cw, cw_f in zip(rec.city_words, rec.city_folded_words)
                    )
                )

                if is_street_exact:
                    street_exact_hits += 1
                elif is_city_exact:
                    city_exact_hits += 1
                elif is_street_prefix:
                    street_prefix_hits += 1
                elif is_city_prefix:
                    city_prefix_hits += 1
                else:
                    matched_fuzzy = False
                    if len(tok) >= 4:
                        for sw, sw_f in zip(rec.street_words, rec.street_folded_words):
                            if len(sw) < 3:
                                continue
                            ratio = max(
                                difflib.SequenceMatcher(None, tok, sw).ratio(),
                                difflib.SequenceMatcher(None, tok_f, sw_f).ratio(),
                            )
                            if ratio >= 0.76:
                                fuzzy_hits += 1
                                matched_fuzzy = True
                                break
                    if not matched_fuzzy and len(tok) >= 4:
                        for cw, cw_f in zip(rec.city_words, rec.city_folded_words):
                            if len(cw) < 3:
                                continue
                            ratio = max(
                                difflib.SequenceMatcher(None, tok, cw).ratio(),
                                difflib.SequenceMatcher(None, tok_f, cw_f).ratio(),
                            )
                            if ratio >= 0.78:
                                fuzzy_hits += 1
                                matched_fuzzy = True
                                break
                    if not matched_fuzzy:
                        unmatched_tokens += 1

            if unmatched_tokens > 0:
                if num_tokens <= 2 or unmatched_tokens > 1:
                    continue
                base_score -= 40.0

            base_score += street_exact_hits * 95.0
            base_score += street_prefix_hits * 70.0
            base_score += fuzzy_hits * 35.0

            base_score += city_exact_hits * 85.0
            base_score += city_prefix_hits * 55.0

            if (city_exact_hits + city_prefix_hits) > 0 and (
                street_exact_hits + street_prefix_hits
            ) > 0:
                base_score += 110.0

            if (street_exact_hits + street_prefix_hits) > 0:
                first_street_word = rec.street_words[0] if rec.street_words else ""
                first_street_fold = (
                    rec.street_folded_words[0] if rec.street_folded_words else ""
                )
                if any(
                    first_street_word == t or first_street_fold == tf
                    for t, tf in zip(text_tokens, tokens_folded)
                ):
                    base_score += 35.0
                elif any(
                    first_street_word.startswith(t) or first_street_fold.startswith(tf)
                    for t, tf in zip(text_tokens, tokens_folded)
                ):
                    base_score += 20.0
                base_score -= min(len(rec.street_words), 5) * 2.0
            else:
                if rec.street.lower().startswith(
                    ("вул", "пров", "просп", "майдан", "пл")
                ):
                    base_score += 15.0 + min(len(rec.houses_canon_map), 25) * 0.4
                else:
                    base_score -= 20.0

            if (
                not city_filter
                and (city_exact_hits == 0 and city_prefix_hits == 0)
            ):
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

    if ht_canon and raw_candidates:
        best_tier_by_street: Dict[Tuple[str, str, str], int] = {}
        for _, h_tier, _, rec in raw_candidates:
            key = (rec.rem, rec.city, rec.street)
            if h_tier > best_tier_by_street.get(key, 0):
                best_tier_by_street[key] = h_tier

        filtered_candidates: List[Tuple[float, int, Optional[str], IndexedRecord]] = []
        for score, h_tier, m_house, rec in raw_candidates:
            key = (rec.rem, rec.city, rec.street)
            max_tier = best_tier_by_street.get(key, 0)
            if max_tier > 0 and h_tier < max_tier:
                continue
            filtered_candidates.append((score, h_tier, m_house, rec))
        raw_candidates = filtered_candidates

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
    age = (datetime.now() - dt).total_seconds()
    return age >= CACHE_MAX_AGE_SECONDS


async def _load_from_redis() -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Reads cached addresses payload from Redis if available."""
    redis_client = redis_un.get_redis_client()
    if not redis_client:
        return None, None
    try:
        raw = await redis_client.get(REDIS_ADDRESSES_KEY)
        if not raw:
            return None, None
        data = json.loads(raw)
        if isinstance(data, dict):
            items = data.get("items")
            updated_at = data.get("updated_at")
            if isinstance(items, list) and len(items) > 0:
                return items, updated_at
    except Exception as exc:
        log.warning("Failed to load addresses cache from Redis: %s", exc)
    return None, None


async def _save_to_redis(records: List[Dict[str, Any]], updated_at: str) -> bool:
    """Persists parsed addresses and timestamp into Redis."""
    redis_client = redis_un.get_redis_client()
    if not redis_client:
        return False
    try:
        payload = json.dumps(
            {
                "updated_at": updated_at,
                "source": "ztoe_live",
                "items": records,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        await redis_client.set(REDIS_ADDRESSES_KEY, payload)
        log.info("Saved %d addresses to Redis (updated_at: %s)", len(records), updated_at)
        return True
    except Exception as exc:
        log.warning("Failed to save addresses to Redis: %s", exc)
        return False


async def sync_addresses_from_ztoe() -> bool:
    """
    Downloads addresses from https://www.ztoe.com.ua/unhooking-search.php?pidcherga_id={1..12}.
    If ZTOE is available, updates the in-memory index and saves to Redis.
    If ZTOE is unavailable, leaves the existing Redis cache and in-memory index untouched.
    """
    lock = _get_sync_lock()
    if lock.locked():
        async with lock:
            return bool(_INDEXED_RECORDS)

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
                            log.warning(
                                "ZTOE responded with status %s for %s", resp.status, url
                            )
                            return []
                        raw_bytes = await resp.read()
                        html = raw_bytes.decode("cp1251", errors="ignore")
                except Exception as req_err:
                    log.warning(
                        "Error fetching ZTOE pidcherga %s: %s", pidcherga_id, req_err
                    )
                    return []

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
                log.warning(
                    "No innermost address table found for pidcherga %s", pidcherga_id
                )
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

                raw_houses = [
                    h.strip() for h in re.split(r"[,;]+", houses_raw) if h.strip()
                ]
                parsed_rows.append((rem, city, street, queue_code, raw_houses))

            return parsed_rows

        grouped_addresses: Dict[Tuple[str, str, str, int], Dict[str, None]] = {}

        try:
            async with aiohttp.ClientSession(
                timeout=timeout, connector=connector
            ) as session:
                results = await asyncio.gather(
                    *(fetch_pidcherga(session, pid) for pid in range(1, 13))
                )
                for pid_rows in results:
                    for rem, city, street, queue_code, raw_houses in pid_rows:
                        group_key = (rem, city, street, queue_code)
                        if group_key not in grouped_addresses:
                            grouped_addresses[group_key] = {}
                        for h in raw_houses:
                            grouped_addresses[group_key][h] = None
        except Exception as exc:
            log.warning(
                "sync_addresses_from_ztoe encountered an unexpected error: %s", exc
            )

        if len(grouped_addresses) < 100:
            log.warning(
                "ZTOE website unavailable or returned incomplete data (%d records). "
                "Keeping existing Redis cache untouched.",
                len(grouped_addresses),
            )
            return False

        records: List[Dict[str, Any]] = []
        for idx, ((rem, city, street, queue_code), houses_dict) in enumerate(
            grouped_addresses.items(), start=1
        ):
            houses_list = list(houses_dict.keys())
            queue_lbl = QUEUE_LABELS.get(
                queue_code, f"{queue_code // 10}.{queue_code % 10}"
            )
            records.append(
                {
                    "id": idx,
                    "rem": rem,
                    "city": city,
                    "street": street,
                    "houses": houses_list,
                    "queue": queue_code,
                    "queue_label": queue_lbl,
                }
            )

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _set_indexed_addresses(records, updated_at=now_str, source="ztoe_live")
        await _save_to_redis(records, now_str)
        return True


async def ensure_addresses_loaded() -> None:
    """
    Startup & on-demand loader:
    1. Checks if Redis has cached addresses ('ztoe_addresses_cache').
    2. If found in Redis:
       - Immediately loads them into memory.
       - Checks the cache date ('updated_at'): if older than 12 hours, fetches fresh
         data from ztoe.com.ua (and if the site is down, keeps the Redis cache).
    3. If NOT found in Redis:
       - Immediately parses ztoe.com.ua and saves the result to Redis.
    """
    items, updated_at = await _load_from_redis()

    if items:
        _set_indexed_addresses(items, updated_at=updated_at, source="redis_cache")
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
        log.info(
            "No addresses found in Redis cache. Parsing ztoe.com.ua immediately..."
        )
        await sync_addresses_from_ztoe()
