import asyncio
import difflib
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
from bs4 import BeautifulSoup

from untils import redis_db as redis_un
from untils import tools
from untils.variebles import QUEUE_LABELS

log = logging.getLogger(__name__)

ADDRESSES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "addresses.json"
)

# ---------------------------------------------------------------------------
# Fallback Seed: Core streets of Zhytomyr and major towns in Zhytomyr Oblast
# Distributed across queues 11..62 (1.1..6.2)
# ---------------------------------------------------------------------------
FALLBACK_ADDRESSES: List[Dict[str, Any]] = [
    # Queue 11 (1.1)
    {
        "id": "seed_1",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Київська",
        "houses": ["1", "3", "5", "7", "9", "13", "15", "17", "21", "23", "25", "27", "29", "31", "37", "43", "47", "51", "55", "77", "79", "81"],
        "queue": 11,
        "queue_label": "1.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_2",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Михайлівська",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "14", "16", "18", "20"],
        "queue": 11,
        "queue_label": "1.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_3",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "майдан Перемоги",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "10", "12"],
        "queue": 11,
        "queue_label": "1.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_4",
        "rem": "Бердичівський",
        "city": "місто Бердичів",
        "street": "вул. Житомирська",
        "houses": ["1", "3", "5", "12", "15", "27", "43", "85", "131"],
        "queue": 11,
        "queue_label": "1.1",
        "note": "побутові споживачі",
    },

    # Queue 12 (1.2)
    {
        "id": "seed_5",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Київська",
        "houses": ["2", "4", "6", "8", "10", "12", "14", "16", "20", "22", "24", "26", "28", "48", "52", "60", "72", "88", "94/2", "112"],
        "queue": 12,
        "queue_label": "1.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_6",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Театральна",
        "houses": ["3", "5", "7", "9", "11", "13", "15", "17", "19", "21", "23"],
        "queue": 12,
        "queue_label": "1.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_7",
        "rem": "Коростенський",
        "city": "місто Коростень",
        "street": "вул. Грушевського",
        "houses": ["1", "3", "5", "7", "12", "14", "18", "22", "35", "41"],
        "queue": 12,
        "queue_label": "1.2",
        "note": "побутові споживачі",
    },

    # Queue 21 (2.1)
    {
        "id": "seed_8",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Велика Бердичівська",
        "houses": ["1", "3", "5", "7", "9", "11", "13", "15", "15а", "17", "23", "27", "31", "35", "41", "47", "53"],
        "queue": 21,
        "queue_label": "2.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_9",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "майдан Соборний",
        "houses": ["1", "2", "3", "4", "5", "6", "7/1"],
        "queue": 21,
        "queue_label": "2.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_10",
        "rem": "Звягельський",
        "city": "місто Звягель",
        "street": "вул. Шевченка",
        "houses": ["2", "4", "6", "8", "10", "16", "24", "30", "42"],
        "queue": 21,
        "queue_label": "2.1",
        "note": "побутові споживачі",
    },

    # Queue 22 (2.2)
    {
        "id": "seed_11",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Велика Бердичівська",
        "houses": ["2", "4", "6", "8", "10", "12", "14", "16", "18", "20", "26", "32", "40", "56", "64", "70"],
        "queue": 22,
        "queue_label": "2.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_12",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Івана Кочерги",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "11"],
        "queue": 22,
        "queue_label": "2.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_13",
        "rem": "Малинський",
        "city": "місто Малин",
        "street": "вул. Грушевського",
        "houses": ["2", "4", "6", "8", "15", "21", "29", "43"],
        "queue": 22,
        "queue_label": "2.2",
        "note": "побутові споживачі",
    },

    # Queue 31 (3.1)
    {
        "id": "seed_14",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Покровська",
        "houses": ["1", "3", "5", "7", "9", "11", "13", "15", "17", "21", "27", "33", "45", "59", "71", "95", "123"],
        "queue": 31,
        "queue_label": "3.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_15",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Небесної Сотні",
        "houses": ["1", "3", "5", "7", "9", "11", "13", "15", "21", "27", "33", "39", "45"],
        "queue": 31,
        "queue_label": "3.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_16",
        "rem": "Коростишівський",
        "city": "місто Коростишів",
        "street": "вул. Київська",
        "houses": ["1", "3", "5", "8", "12", "19", "25", "38", "55", "67"],
        "queue": 31,
        "queue_label": "3.1",
        "note": "побутові споживачі",
    },

    # Queue 32 (3.2)
    {
        "id": "seed_17",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Покровська",
        "houses": ["2", "4", "6", "8", "10", "12", "14", "16", "18", "20", "28", "34", "48", "62", "80", "102", "130"],
        "queue": 32,
        "queue_label": "3.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_18",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Лесі Українки",
        "houses": ["1", "3", "5", "7", "9", "11", "14", "17", "21", "28", "33", "40", "48"],
        "queue": 32,
        "queue_label": "3.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_19",
        "rem": "Бердичівський",
        "city": "місто Бердичів",
        "street": "вул. Європейська",
        "houses": ["1", "3", "5", "9", "14", "19", "24", "31", "48"],
        "queue": 32,
        "queue_label": "3.2",
        "note": "побутові споживачі",
    },

    # Queue 41 (4.1)
    {
        "id": "seed_20",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Чуднівська",
        "houses": ["1", "3", "5", "7", "9", "13", "17", "21", "35", "49", "63", "77", "89", "101", "104", "115"],
        "queue": 41,
        "queue_label": "4.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_21",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Перемоги",
        "houses": ["1", "3", "5", "7", "9", "11", "13", "15", "19", "23", "29", "35", "47", "53", "61"],
        "queue": 41,
        "queue_label": "4.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_22",
        "rem": "Коростенський",
        "city": "місто Коростень",
        "street": "вул. Героїв Чорнобиля",
        "houses": ["1", "3", "7", "11", "15", "23", "31"],
        "queue": 41,
        "queue_label": "4.1",
        "note": "побутові споживачі",
    },

    # Queue 42 (4.2)
    {
        "id": "seed_23",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Перемоги",
        "houses": ["2", "4", "6", "8", "10", "12", "14", "16", "20", "24", "32", "40", "52", "68", "74", "90"],
        "queue": 42,
        "queue_label": "4.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_24",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Кафедральна",
        "houses": ["1", "2", "3", "4", "5", "6", "8", "10", "12"],
        "queue": 42,
        "queue_label": "4.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_25",
        "rem": "Звягельський",
        "city": "місто Звягель",
        "street": "вул. Соборності",
        "houses": ["1", "3", "5", "7", "9", "13", "17", "21", "29"],
        "queue": 42,
        "queue_label": "4.2",
        "note": "побутові споживачі",
    },

    # Queue 51 (5.1)
    {
        "id": "seed_26",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "просп. Миру",
        "houses": ["1", "3", "5", "7", "9", "11", "13", "15", "17", "19", "21", "23", "25", "31", "37", "45"],
        "queue": 51,
        "queue_label": "5.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_27",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Вітрука",
        "houses": ["1", "3", "5", "7", "9", "11", "13", "15", "19", "23", "31", "41", "47"],
        "queue": 51,
        "queue_label": "5.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_28",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Селецька",
        "houses": ["1", "3", "5", "7", "9", "11", "13", "17", "21", "25", "31"],
        "queue": 51,
        "queue_label": "5.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_29",
        "rem": "Бердичівський",
        "city": "місто Бердичів",
        "street": "вул. Вінницька",
        "houses": ["2", "4", "6", "10", "18", "25", "39", "52"],
        "queue": 51,
        "queue_label": "5.1",
        "note": "побутові споживачі",
    },

    # Queue 52 (5.2)
    {
        "id": "seed_30",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "просп. Миру",
        "houses": ["2", "4", "6", "8", "10", "12", "14", "16", "18", "20", "22", "26", "32", "40"],
        "queue": 52,
        "queue_label": "5.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_31",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Корольова",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "10", "12", "14", "16", "22", "34", "46"],
        "queue": 52,
        "queue_label": "5.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_32",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Промислова",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "15", "18"],
        "queue": 52,
        "queue_label": "5.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_33",
        "rem": "Коростишівський",
        "city": "місто Коростишів",
        "street": "вул. Героїв Чорнобиля",
        "houses": ["2", "4", "6", "10", "14", "22"],
        "queue": 52,
        "queue_label": "5.2",
        "note": "побутові споживачі",
    },

    # Queue 61 (6.1)
    {
        "id": "seed_34",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Грушевського",
        "houses": ["1", "3", "5", "7", "9", "11", "13", "15", "17", "21", "25", "33", "41", "55", "67", "89"],
        "queue": 61,
        "queue_label": "6.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_35",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Східна",
        "houses": ["1", "3", "5", "7", "9", "11", "13", "17", "23", "29", "37", "45", "61", "73", "85"],
        "queue": 61,
        "queue_label": "6.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_36",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Шевченка",
        "houses": ["1", "3", "5", "7", "9", "11", "15", "21", "27", "35", "41", "53", "67", "83"],
        "queue": 61,
        "queue_label": "6.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_37",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Сергія Параджанова",
        "houses": ["1", "3", "5", "7", "9", "13", "19", "25", "33", "47"],
        "queue": 61,
        "queue_label": "6.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_38",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Домбровського",
        "houses": ["1", "3", "5", "7", "9", "11", "15", "21", "27", "33", "45"],
        "queue": 61,
        "queue_label": "6.1",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_39",
        "rem": "Малинський",
        "city": "місто Малин",
        "street": "вул. Кримська",
        "houses": ["1", "3", "5", "7", "12", "16", "24"],
        "queue": 61,
        "queue_label": "6.1",
        "note": "побутові споживачі",
    },

    # Queue 62 (6.2)
    {
        "id": "seed_40",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Князів Острозьких",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "10", "12", "15", "20", "26", "34", "48", "59"],
        "queue": 62,
        "queue_label": "6.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_41",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Богуна",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "10", "14", "18", "24", "32"],
        "queue": 62,
        "queue_label": "6.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_42",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Івана Мазепи",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "11", "17", "23", "31"],
        "queue": 62,
        "queue_label": "6.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_43",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Хлібна",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "11", "15", "19", "23"],
        "queue": 62,
        "queue_label": "6.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_44",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Ріхтера",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "12", "16", "24", "38"],
        "queue": 62,
        "queue_label": "6.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_45",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Кафедральна",
        "houses": ["1", "2", "3", "4", "5", "6", "8", "10", "12"],
        "queue": 42,
        "queue_label": "4.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_46",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Космонавтів",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "10", "14", "22", "30"],
        "queue": 62,
        "queue_label": "6.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_47",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Ціолковського",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "12", "16"],
        "queue": 62,
        "queue_label": "6.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_48",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "вул. Польова",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "10", "14", "18"],
        "queue": 62,
        "queue_label": "6.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_49",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "просп. Незалежності",
        "houses": ["1", "2", "3", "4", "5", "6", "7", "8", "10", "13", "21", "29", "45"],
        "queue": 62,
        "queue_label": "6.2",
        "note": "побутові споживачі",
    },
    {
        "id": "seed_50",
        "rem": "Житомирський",
        "city": "місто Житомир",
        "street": "майдан Житній Ринок",
        "houses": ["1", "2", "3", "4", "5"],
        "queue": 62,
        "queue_label": "6.2",
        "note": "побутові споживачі",
    },
]

# ---------------------------------------------------------------------------
# Russian <-> Ukrainian Street Name Synonyms & Normalization Dictionary
# ---------------------------------------------------------------------------
RUSSIAN_STREET_REPLACEMENTS: List[Tuple[str, str]] = [
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
    ("святослава рихтера", "святослава ріхтера"),
    ("1 мая", "1 травня"),
    # Single word replacements
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
    ("кочерги", "кочерги"),
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
    ("соборная", "соборний"),
    ("соборный", "соборний"),
    ("королева", "корольова"),
    ("грушевского", "грушевського"),
    ("шевченко", "шевченка"),
    ("острожских", "острозьких"),
    ("богуна", "богуна"),
    ("мазепы", "мазепи"),
    ("рихтера", "ріхтера"),
    ("космонавтов", "космонавтів"),
    ("циолковского", "ціолковського"),
    ("домбровского", "домбровського"),
    ("витрука", "вітрука"),
    ("селецкая", "селецька"),
    ("житомирская", "житомирська"),
    ("житомирский", "житомирський"),
    ("житомир", "житомир"),
    ("бердичев", "бердичів"),
]

ENDINGS_SUB: List[Tuple[str, str]] = [
    (r"ская\b", "ська"),
    (r"ский\b", "ський"),
    (r"цкая\b", "цька"),
    (r"цкий\b", "цький"),
    (r"ого\b", "ого"),
]

ABBREVIATIONS_PATTERN = re.compile(
    r"\b(вул|вулиця|ул|улица|пров|провулок|пер|переулок|пр-т|просп|проспект|майдан|пл|площа|площадь|м|місто|г|город|с|село|смт|буд|будинок|д|дом|кв)\b\.?",
    re.IGNORECASE,
)

HOUSE_PATTERN = re.compile(
    r"^\d+([а-яa-zіїєґ]|\/[0-9а-яa-zіїєґ]+|-[0-9а-яa-zіїєґ]+)?$", re.IGNORECASE
)
ORDINAL_PATTERN = re.compile(r"^\d+-(й|а|е|я|ій)$", re.IGNORECASE)
STREET_TYPE_PATTERN = re.compile(
    r"^(пров|провулок|пер|переулок|пр-т|просп|проспект|лінія|вул|вулиця|тупик|проїзд)\.?",
    re.IGNORECASE,
)
HOUSE_MARKER_PATTERN = re.compile(r"^(буд|будинок|д|дом|кв)\.?$", re.IGNORECASE)

LATIN_TO_CYR_HOUSE = {"a": "а", "b": "б", "c": "в", "d": "г", "k": "к"}


def canonical_house(house_str: str) -> str:
    """Normalize house number string for comparison (lowercase, latin->cyr suffix)."""
    h = house_str.strip().lower().replace(" ", "")
    for lat, cyr in LATIN_TO_CYR_HOUSE.items():
        h = h.replace(lat, cyr)
    return h


def normalize_text(text: str) -> str:
    """
    Normalizes street / city text:
    1. Lowercase.
    2. Normalize apostrophes.
    3. Dictionary replacements for Russian street names.
    4. Adjective ending conversions (ская -> ська, etc.).
    5. Russian letters (ы->и, э->е, ъ->'', ё->ьо).
    6. Remove abbreviations (вул., м., буд., etc.).
    7. Remove punctuation except internal hyphens / apostrophes.
    8. Collapse whitespace.
    """
    if not text:
        return ""

    t = text.lower()
    t = re.sub(r"[’`ʼ\"]", "'", t)

    for ru, ua in RUSSIAN_STREET_REPLACEMENTS:
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
    """
    Folds vowel differences (и/і/ї, е/є) and apostrophes for phonetic / fuzzy matching.
    """
    return (
        text.replace("і", "и")
        .replace("ї", "и")
        .replace("є", "е")
        .replace("'", "")
        .replace("`", "")
        .replace("-", " ")
    )


def parse_search_query(raw_query: str) -> Tuple[List[str], Optional[str]]:
    """
    Extracts text tokens and house number from raw search query.
    Examples:
      'Київська 21' -> (['київська'], '21')
      'м. Житомир, вул. Велика Бердичівська, 15а' -> (['житомир', 'велика', 'бердичівська'], '15а')
      'киевская' -> (['київська'], None)
      'Чуднівська 104' -> (['чуднівська'], '104')
      'Бердичів Житомирська 131' -> (['бердичів', 'житомирська'], '131')
      '1 пров. Калиновий 5' -> (['1', 'калиновий'], '5')
    """
    cleaned = raw_query.replace(",", " ").replace(";", " ")
    parts = cleaned.split()

    house_token: Optional[str] = None
    text_parts: List[str] = []

    i = 0
    while i < len(parts):
        token = parts[i]
        next_token = parts[i + 1] if i + 1 < len(parts) else ""

        # Case: "буд. 15" or "дом 21"
        if HOUSE_MARKER_PATTERN.match(token) and next_token:
            house_token = next_token
            i += 2
            continue

        if HOUSE_PATTERN.match(token):
            # Check if this is an ordinal for street name (e.g. "1 пров. Калиновий" or "1-й")
            if ORDINAL_PATTERN.match(token) or (
                STREET_TYPE_PATTERN.match(next_token) and token.isdigit()
            ):
                text_parts.append(token)
            else:
                house_token = token
        else:
            text_parts.append(token)
        i += 1

    normalized_text = normalize_text(" ".join(text_parts))
    text_tokens = [tok for tok in normalized_text.split() if tok]

    return text_tokens, house_token


# ---------------------------------------------------------------------------
# In-Memory Index
# ---------------------------------------------------------------------------
class IndexedRecord:
    __slots__ = (
        "raw",
        "norm_street",
        "norm_city",
        "norm_full",
        "street_words",
        "houses",
        "houses_lower_map",
        "houses_canon_map",
        "is_zhytomyr",
    )

    def __init__(self, item: Dict[str, Any]):
        self.raw = item
        self.norm_street = normalize_text(item.get("street", ""))
        self.norm_city = normalize_text(item.get("city", ""))
        self.norm_full = f"{self.norm_city} {self.norm_street}".strip()
        self.street_words = self.norm_street.split()

        raw_houses: List[str] = item.get("houses", [])
        self.houses = raw_houses
        self.houses_lower_map: Dict[str, str] = {
            h.strip().lower(): h.strip() for h in raw_houses if h.strip()
        }
        self.houses_canon_map: Dict[str, str] = {
            canonical_house(h): h.strip() for h in raw_houses if h.strip()
        }
        self.is_zhytomyr = "житомир" in self.norm_city


_INDEXED_RECORDS: List[IndexedRecord] = []
_UPDATED_AT: Optional[str] = None
_SOURCE: str = "fallback_seed"


def _set_indexed_addresses(
    items: List[Dict[str, Any]], updated_at: Optional[str], source: str
) -> None:
    global _INDEXED_RECORDS, _UPDATED_AT, _SOURCE
    _INDEXED_RECORDS = [IndexedRecord(item) for item in items]
    _UPDATED_AT = updated_at
    _SOURCE = source
    log.info(
        "Addresses index updated: %d items loaded (source: %s, updated_at: %s)",
        len(_INDEXED_RECORDS),
        source,
        updated_at,
    )


def get_meta() -> Dict[str, Any]:
    """Returns metadata about the currently loaded address index."""
    return {
        "total_indexed": len(_INDEXED_RECORDS),
        "updated_at": _UPDATED_AT,
        "source": _SOURCE,
    }


def _format_result(record: IndexedRecord, matched_house: Optional[str]) -> Dict[str, Any]:
    item = record.raw
    houses_list = record.houses
    preview_slice = houses_list[:12]
    preview_str = ", ".join(preview_slice) + ("…" if len(houses_list) > 12 else "")
    queue_code = item.get("queue", 11)
    queue_label = item.get(
        "queue_label", QUEUE_LABELS.get(queue_code, f"{queue_code // 10}.{queue_code % 10}")
    )

    return {
        "id": item.get("id"),
        "rem": item.get("rem", ""),
        "city": item.get("city", ""),
        "street": item.get("street", ""),
        "houses": houses_list,
        "houses_preview": preview_str,
        "matched_house": matched_house,
        "queue": str(queue_code),
        "queue_label": str(queue_label),
        "note": item.get("note", "побутові споживачі"),
        "display": f"{item.get('city', '')}, {item.get('street', '')}",
    }


def search_addresses(query: str, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Smart address search with Google Maps-like capabilities:
    - Autocomplete / prefix matching
    - Ukrainian & Russian street name recognition
    - Letter folding (и <-> і, е <-> є)
    - Fuzzy matching via difflib.SequenceMatcher for typo tolerance
    - House number resolution with scoring boost
    - City prioritisation (Zhytomyr boost unless another city specified)
    """
    clean_query = query.strip()
    if not clean_query:
        # Return popular streets in Zhytomyr
        top = [
            _format_result(rec, None)
            for rec in _INDEXED_RECORDS
            if rec.is_zhytomyr
        ][:limit]
        if len(top) < limit:
            remaining = [
                _format_result(rec, None)
                for rec in _INDEXED_RECORDS
                if not rec.is_zhytomyr
            ][: (limit - len(top))]
            top.extend(remaining)
        return top

    text_tokens, house_token = parse_search_query(clean_query)
    query_norm = normalize_text(clean_query)
    query_folded = fold_ukr(query_norm)

    # Detect if user specifically queried another city
    city_keywords = ["бердичів", "коростень", "звягель", "новоград", "малин", "коростишів", "станишівка"]
    city_explicit = any(ck in query_norm for ck in city_keywords)

    candidates: List[Tuple[float, IndexedRecord, Optional[str]]] = []

    for rec in _INDEXED_RECORDS:
        score = 0.0
        norm_street = rec.norm_street
        norm_city = rec.norm_city
        street_folded = fold_ukr(norm_street)
        city_folded = fold_ukr(norm_city)

        # 1. Match against street name
        if norm_street.startswith(query_norm) or (text_tokens and norm_street.startswith(text_tokens[0])):
            score += 100.0
        elif street_folded.startswith(query_folded) or (text_tokens and street_folded.startswith(fold_ukr(text_tokens[0]))):
            score += 90.0

        # Check each text token
        matched_tokens = 0
        partial_matched_tokens = 0

        for token in text_tokens:
            tok_fold = fold_ukr(token)
            # Exact substring match in street
            if token in norm_street or tok_fold in street_folded:
                matched_tokens += 1
            # Match in city
            elif token in norm_city or tok_fold in city_folded:
                matched_tokens += 1
            else:
                # Fuzzy matching against street words
                fuzzy_found = False
                for sword in rec.street_words:
                    sword_fold = fold_ukr(sword)
                    if sword.startswith(token) or sword_fold.startswith(tok_fold):
                        fuzzy_found = True
                        break
                    ratio = max(
                        difflib.SequenceMatcher(None, token, sword).ratio(),
                        difflib.SequenceMatcher(None, tok_fold, sword_fold).ratio(),
                    )
                    if ratio >= 0.72:
                        fuzzy_found = True
                        break
                if fuzzy_found:
                    partial_matched_tokens += 1

        if text_tokens:
            if matched_tokens == len(text_tokens):
                score += 70.0
            elif (matched_tokens + partial_matched_tokens) == len(text_tokens):
                score += 40.0
            elif matched_tokens > 0:
                score += 20.0
            else:
                # No text token matched this record
                continue

        # Zhytomyr bonus
        if not city_explicit and rec.is_zhytomyr:
            score += 30.0

        # House number resolution
        matched_house: Optional[str] = None
        if house_token:
            ht_canon = canonical_house(house_token)
            if ht_canon in rec.houses_canon_map:
                score += 150.0
                matched_house = rec.houses_canon_map[ht_canon]
            else:
                # Prefix matching for house numbers (e.g. "15" -> "15а")
                for h_can, h_orig in rec.houses_canon_map.items():
                    if h_can.startswith(ht_canon):
                        score += 80.0
                        matched_house = h_orig
                        break

        if score > 0:
            candidates.append((score, rec, matched_house))

    # Sort: highest score first, then Zhytomyr priority, then street name
    candidates.sort(
        key=lambda c: (c[0], 1 if c[1].is_zhytomyr else 0, -len(c[1].street_words)),
        reverse=True,
    )

    results = [_format_result(rec, mh) for _, rec, mh in candidates[:limit]]
    return results


# ---------------------------------------------------------------------------
# Scraping from ztoe.com.ua
# ---------------------------------------------------------------------------
async def sync_addresses_from_ztoe() -> bool:
    """
    Downloads addresses from https://www.ztoe.com.ua/unhooking-search.php?pidcherga_id={1..12}
    Decodes windows-1251 table and groups entries by queue.
    Saves to data/addresses.json and updates in-memory index.
    """
    log.info("Starting addresses synchronization from ztoe.com.ua...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
    }
    timeout = aiohttp.ClientTimeout(total=45)

    grouped_addresses: Dict[Tuple[str, str, str, int, str], Dict[str, None]] = {}
    total_parsed_rows = 0

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for pidcherga_id in range(1, 13):
                url = f"https://www.ztoe.com.ua/unhooking-search.php?pidcherga_id={pidcherga_id}"
                try:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status != 200:
                            log.warning("ZTOE responded with status %s for %s", resp.status, url)
                            continue
                        raw_bytes = await resp.read()
                        html = raw_bytes.decode("cp1251", errors="ignore")
                except Exception as req_err:
                    log.warning("Error fetching ZTOE pidcherga %s: %s", pidcherga_id, req_err)
                    continue

                soup = BeautifulSoup(html, "html.parser")
                tables = soup.find_all("table")
                target_table = None
                for tbl in tables:
                    txt = tbl.get_text()
                    if "Населений пункт" in txt or "Назва вулиці" in txt:
                        target_table = tbl
                        break
                if target_table is None and tables:
                    target_table = tables[0]

                if not target_table:
                    log.warning("No address table found for pidcherga %s", pidcherga_id)
                    continue

                rows = target_table.find_all("tr")
                for row in rows:
                    tds = row.find_all("td")
                    if len(tds) < 7:
                        continue

                    rem = tds[0].get_text(strip=True)
                    city = tds[1].get_text(strip=True)
                    street = tds[2].get_text(strip=True)
                    houses_raw = tds[3].get_text(strip=True)
                    cherga_str = tds[4].get_text(strip=True)
                    pidcherga_str = tds[5].get_text(strip=True)
                    note = tds[6].get_text(strip=True)

                    # Skip table header
                    if "РЕМ" in rem or "Населений пункт" in city:
                        continue

                    if cherga_str.isdigit() and pidcherga_str.isdigit():
                        queue_code = int(cherga_str) * 10 + int(pidcherga_str)
                    else:
                        queue_code = tools.index_to_queue(pidcherga_id)

                    raw_houses = [
                        h.strip()
                        for h in re.split(r"[,;]+", houses_raw)
                        if h.strip()
                    ]

                    group_key = (rem, city, street, queue_code, note or "побутові споживачі")
                    if group_key not in grouped_addresses:
                        grouped_addresses[group_key] = {}
                    for h in raw_houses:
                        grouped_addresses[group_key][h] = None
                    total_parsed_rows += 1

                await asyncio.sleep(0.3)

    except Exception as exc:
        log.warning("sync_addresses_from_ztoe encountered an unexpected error: %s", exc)

    if len(grouped_addresses) < 50:
        log.warning(
            "Parsed only %d address records from ZTOE (threshold is 50). Keeping existing index.",
            len(grouped_addresses),
        )
        return False

    records: List[Dict[str, Any]] = []
    for idx, ((rem, city, street, queue_code, note), houses_dict) in enumerate(
        grouped_addresses.items(), start=1
    ):
        houses_list = list(houses_dict.keys())
        queue_lbl = QUEUE_LABELS.get(
            queue_code, f"{queue_code // 10}.{queue_code % 10}"
        )
        records.append(
            {
                "id": f"ztoe_{idx}",
                "rem": rem,
                "city": city,
                "street": street,
                "houses": houses_list,
                "queue": queue_code,
                "queue_label": queue_lbl,
                "note": note,
            }
        )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "updated_at": now_str,
        "source": "ztoe_live",
        "items": records,
    }

    try:
        os.makedirs(os.path.dirname(ADDRESSES_FILE), exist_ok=True)
        with open(ADDRESSES_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        log.info("Saved %d addresses to %s", len(records), ADDRESSES_FILE)
    except Exception as save_err:
        log.warning("Failed to save addresses to %s: %s", ADDRESSES_FILE, save_err)

    _set_indexed_addresses(records, updated_at=now_str, source="ztoe_live")

    # Sync to Redis if available
    try:
        redis_client = redis_un.get_redis_client()
        if redis_client:
            await redis_client.set(
                "ztoe_addresses_cache", json.dumps(payload, ensure_ascii=False)
            )
            log.info("Saved addresses cache to Redis")
    except Exception as redis_err:
        log.warning("Failed to save addresses to Redis: %s", redis_err)

    return True


async def ensure_addresses_loaded() -> None:
    """
    Ensures address data is loaded in memory.
    If addresses.json exists and is fresh (< 12 hours), loads it.
    If missing or older than 12h, and ONLINE is enabled, triggers sync_addresses_from_ztoe().
    """
    online = os.getenv("ONLINE", "false").lower() == "true"
    needs_sync = False

    if os.path.exists(ADDRESSES_FILE):
        try:
            mtime = os.path.getmtime(ADDRESSES_FILE)
            age = (datetime.now() - datetime.fromtimestamp(mtime)).total_seconds()
            if age > 43200:  # 12 hours
                needs_sync = True
            with open(ADDRESSES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("items", [])
                if items:
                    _set_indexed_addresses(
                        items,
                        updated_at=data.get("updated_at"),
                        source=data.get("source", "cache_file"),
                    )
        except Exception as read_err:
            log.warning("Failed reading %s: %s", ADDRESSES_FILE, read_err)
            needs_sync = True
    else:
        needs_sync = True

    if online and needs_sync:
        log.info("Addresses cache is outdated or missing; starting background sync...")
        await sync_addresses_from_ztoe()


def _init_sync() -> None:
    """
    Synchronous initialisation at module import time to guarantee
    immediate readiness before any async tasks or lifespan runs.
    """
    if os.path.exists(ADDRESSES_FILE):
        try:
            with open(ADDRESSES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("items", [])
                if items:
                    _set_indexed_addresses(
                        items,
                        updated_at=data.get("updated_at"),
                        source=data.get("source", "cache_file"),
                    )
                    return
        except Exception as exc:
            log.warning("Could not pre-load %s: %s", ADDRESSES_FILE, exc)

    _set_indexed_addresses(FALLBACK_ADDRESSES, updated_at=None, source="fallback_seed")


# Immediate synchronous initialization on import
_init_sync()
