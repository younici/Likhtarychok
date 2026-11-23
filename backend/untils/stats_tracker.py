import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any

from untils import subcription
from untils.variebles import QUEUE_LABELS
import untils.redis_db as redis_un
import db.orm.utils as db_utils
from db.orm.session import AsyncSessionLocal
from db.orm.models import Subscription, TgSub, User, SupportTicket, SupportAdmin, SupportBan
from sqlalchemy import select, func

log = logging.getLogger(__name__)

STATS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PUSH_STATS_FILE = os.path.join(STATS_DIR, "push_stats.json")
GRAPH_STATS_FILE = os.path.join(STATS_DIR, "graph_stats.json")

DAILY_GRAPH_REDIS_TTL = 35 * 86400  # 35 days

_push_events: list[dict[str, Any]] = []
_push_all_time: dict[str, int] = {
    "total": 0,
    "web": 0,
    "tg": 0,
    "events_count": 0,
}
_push_by_queue_all_time: dict[str, dict[str, Any]] = {}

# Graph requests in-memory counters & recent requests timestamps
_graph_stats: dict[str, Any] = {
    "total": 0,
    "by_queue": {str(k): 0 for k in QUEUE_LABELS.keys()},
    "daily": {},  # { "YYYY-MM-DD": { "total": int, "by_queue": { "11": int, ... } } }
}
_graph_recent_timestamps: list[float] = []


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)


def _merge_last_sent(a: str | None, b: str | None) -> str | None:
    if a and b:
        return max(a, b)
    return a or b


def _event_dedup_key(ev: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    return (
        ev.get("timestamp"),
        ev.get("title"),
        ev.get("queue"),
        ev.get("total_sent"),
    )


def _summarize_events(
    events: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, dict[str, Any]]]:
    all_time = {"total": 0, "web": 0, "tg": 0, "events_count": 0}
    by_queue: dict[str, dict[str, Any]] = {}

    for ev in events:
        if not isinstance(ev, dict):
            continue
        w_sent = _safe_int(ev.get("web_sent"), 0)
        g_sent = _safe_int(ev.get("tg_sent"), 0)
        t_sent = _safe_int(ev.get("total_sent"), w_sent + g_sent)

        all_time["total"] += t_sent
        all_time["web"] += w_sent
        all_time["tg"] += g_sent
        all_time["events_count"] += 1

        q_lbl = ev.get("queue_label") or "Всі"
        bucket = by_queue.setdefault(
            q_lbl,
            {
                "total_sent": 0,
                "web_sent": 0,
                "tg_sent": 0,
                "events_count": 0,
                "last_sent": None,
            },
        )
        bucket["total_sent"] += t_sent
        bucket["web_sent"] += w_sent
        bucket["tg_sent"] += g_sent
        bucket["events_count"] += 1
        bucket["last_sent"] = _merge_last_sent(bucket.get("last_sent"), ev.get("datetime"))

    return all_time, by_queue


def _merge_push_all_time_from_events() -> None:
    events_all_time, events_by_queue = _summarize_events(_push_events)
    _push_all_time["web"] = max(_safe_int(_push_all_time.get("web"), 0), events_all_time["web"])
    _push_all_time["tg"] = max(_safe_int(_push_all_time.get("tg"), 0), events_all_time["tg"])
    _push_all_time["total"] = max(
        _safe_int(_push_all_time.get("total"), 0),
        events_all_time["total"],
        _push_all_time["web"] + _push_all_time["tg"],
    )
    _push_all_time["events_count"] = max(
        _safe_int(_push_all_time.get("events_count"), 0),
        events_all_time["events_count"],
    )

    for q_lbl, ev_q in events_by_queue.items():
        bucket = _push_by_queue_all_time.setdefault(
            q_lbl,
            {
                "total_sent": 0,
                "web_sent": 0,
                "tg_sent": 0,
                "events_count": 0,
                "last_sent": None,
            },
        )
        bucket["web_sent"] = max(_safe_int(bucket.get("web_sent"), 0), ev_q["web_sent"])
        bucket["tg_sent"] = max(_safe_int(bucket.get("tg_sent"), 0), ev_q["tg_sent"])
        bucket["total_sent"] = max(
            _safe_int(bucket.get("total_sent"), 0),
            ev_q["total_sent"],
            bucket["web_sent"] + bucket["tg_sent"],
        )
        bucket["events_count"] = max(_safe_int(bucket.get("events_count"), 0), ev_q["events_count"])
        bucket["last_sent"] = _merge_last_sent(bucket.get("last_sent"), ev_q.get("last_sent"))


def _load_persisted_events():
    global _push_events, _push_all_time, _push_by_queue_all_time, _graph_stats
    try:
        if os.path.exists(PUSH_STATS_FILE):
            with open(PUSH_STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Backward compatibility with legacy list-of-events format
                    _push_events = data
                    _merge_push_all_time_from_events()
                    log.info("Loaded %d push events from %s", len(_push_events), PUSH_STATS_FILE)
                elif isinstance(data, dict):
                    loaded_events = data.get("events")
                    if isinstance(loaded_events, list):
                        _push_events = loaded_events

                    loaded_all_time = data.get("all_time")
                    if isinstance(loaded_all_time, dict):
                        _push_all_time["total"] = _safe_int(loaded_all_time.get("total"), 0)
                        _push_all_time["web"] = _safe_int(loaded_all_time.get("web"), 0)
                        _push_all_time["tg"] = _safe_int(loaded_all_time.get("tg"), 0)
                        _push_all_time["events_count"] = _safe_int(loaded_all_time.get("events_count"), 0)

                    loaded_bq = data.get("by_queue_all_time")
                    if isinstance(loaded_bq, dict):
                        for q_lbl, q_data in loaded_bq.items():
                            if not isinstance(q_data, dict):
                                continue
                            _push_by_queue_all_time[str(q_lbl)] = {
                                "total_sent": _safe_int(q_data.get("total_sent"), 0),
                                "web_sent": _safe_int(q_data.get("web_sent"), 0),
                                "tg_sent": _safe_int(q_data.get("tg_sent"), 0),
                                "events_count": _safe_int(q_data.get("events_count"), 0),
                                "last_sent": q_data.get("last_sent"),
                            }

                    _merge_push_all_time_from_events()
                    log.info(
                        "Loaded %d push events (all-time total: %d) from %s",
                        len(_push_events),
                        _push_all_time["total"],
                        PUSH_STATS_FILE,
                    )
    except Exception as e:
        log.warning("Could not load push stats file: %s", e)

    try:
        if os.path.exists(GRAPH_STATS_FILE):
            with open(GRAPH_STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _graph_stats["total"] = data.get("total", 0)
                    loaded_bq = data.get("by_queue", {})
                    for k in QUEUE_LABELS.keys():
                        _graph_stats["by_queue"][str(k)] = loaded_bq.get(str(k), 0)
                    _graph_stats["daily"] = data.get("daily", {})
                    log.info("Loaded graph stats from %s (total: %d)", GRAPH_STATS_FILE, _graph_stats["total"])
    except Exception as e:
        log.warning("Could not load graph stats file: %s", e)


def _save_push_events():
    try:
        os.makedirs(STATS_DIR, exist_ok=True)
        payload = {
            "events": _push_events[-500:],
            "all_time": dict(_push_all_time),
            "by_queue_all_time": _push_by_queue_all_time,
        }
        with open(PUSH_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("Could not save push stats file: %s", e)


def _save_graph_stats():
    try:
        os.makedirs(STATS_DIR, exist_ok=True)
        # Keep only the last 30 days in daily
        days = sorted(_graph_stats.get("daily", {}).keys())
        if len(days) > 30:
            for old_day in days[:-30]:
                _graph_stats["daily"].pop(old_day, None)

        with open(GRAPH_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(_graph_stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("Could not save graph stats file: %s", e)


# Initial load on import
_load_persisted_events()


async def _persist_push_event_to_redis(
    client: Any,
    event: dict[str, Any],
    web_sent: int,
    tg_sent: int,
    total: int,
    queue_lbl: str,
    dt_str: str,
) -> None:
    try:
        await client.rpush("push_events_history", json.dumps(event, ensure_ascii=False))
        await client.ltrim("push_events_history", -500, -1)
        await client.incrby("push_stats:total", total)
        await client.incrby("push_stats:web", web_sent)
        await client.incrby("push_stats:tg", tg_sent)
        await client.incrby("push_stats:events", 1)
        await client.hincrby("push_stats:by_queue:total", queue_lbl, total)
        await client.hincrby("push_stats:by_queue:web", queue_lbl, web_sent)
        await client.hincrby("push_stats:by_queue:tg", queue_lbl, tg_sent)
        await client.hincrby("push_stats:by_queue:events", queue_lbl, 1)
        await client.hset("push_stats:by_queue:last_sent", queue_lbl, dt_str)
    except Exception as ex:
        log.debug("Redis push event log error: %s", ex)


async def _persist_graph_request_to_redis(client: Any, code_str: str, today: str) -> None:
    try:
        daily_total_key = f"graph_requests:daily:{today}:total"
        daily_by_queue_key = f"graph_requests:daily:{today}:by_queue"
        await client.hincrby("graph_requests:by_queue", code_str, 1)
        await client.incr("graph_requests:total")
        await client.incr(daily_total_key)
        await client.expire(daily_total_key, DAILY_GRAPH_REDIS_TTL)
        await client.hincrby(daily_by_queue_key, code_str, 1)
        await client.expire(daily_by_queue_key, DAILY_GRAPH_REDIS_TTL)
    except Exception as ex:
        log.debug("Redis graph request log error: %s", ex)


def record_push_event(web_sent: int, tg_sent: int, title: str = "", queue: int | None = None):
    """Record a push delivery event."""
    web_int = int(web_sent)
    tg_int = int(tg_sent)
    total = web_int + tg_int
    if total <= 0:
        return

    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    queue_lbl = subcription.queue_label(queue) if queue is not None else "Всі"
    event = {
        "timestamp": time.time(),
        "datetime": now_dt,
        "web_sent": web_int,
        "tg_sent": tg_int,
        "total_sent": total,
        "title": title or "Сповіщення",
        "queue": queue,
        "queue_label": queue_lbl,
    }

    _push_events.append(event)
    if len(_push_events) > 500:
        del _push_events[:-500]

    _push_all_time["total"] += total
    _push_all_time["web"] += web_int
    _push_all_time["tg"] += tg_int
    _push_all_time["events_count"] += 1

    q_bucket = _push_by_queue_all_time.setdefault(
        queue_lbl,
        {
            "total_sent": 0,
            "web_sent": 0,
            "tg_sent": 0,
            "events_count": 0,
            "last_sent": None,
        },
    )
    q_bucket["total_sent"] += total
    q_bucket["web_sent"] += web_int
    q_bucket["tg_sent"] += tg_int
    q_bucket["events_count"] += 1
    q_bucket["last_sent"] = _merge_last_sent(q_bucket.get("last_sent"), now_dt)

    _save_push_events()

    # Try saving to Redis asynchronously if available
    try:
        client = redis_un.get_redis_client()
        if client:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    _persist_push_event_to_redis(
                        client, event, web_int, tg_int, total, queue_lbl, now_dt
                    )
                )
            except RuntimeError:
                pass
    except Exception as ex:
        log.debug("Redis push event log error: %s", ex)


def record_graph_request(queue_code: int | None):
    """Record that a user requested status / graph information for a queue."""
    now = time.time()
    today = datetime.now().strftime("%Y-%m-%d")

    code_str = str(queue_code) if queue_code in QUEUE_LABELS else "11"

    _graph_stats["total"] += 1
    _graph_stats["by_queue"][code_str] = _graph_stats["by_queue"].get(code_str, 0) + 1

    # Daily aggregation
    if today not in _graph_stats["daily"]:
        _graph_stats["daily"][today] = {"total": 0, "by_queue": {}}
    _graph_stats["daily"][today]["total"] += 1
    dq = _graph_stats["daily"][today]["by_queue"]
    dq[code_str] = dq.get(code_str, 0) + 1

    # In-memory recent rolling window for 24h
    _graph_recent_timestamps.append(now)
    # Prune timestamps older than 24h
    cutoff = now - 86400
    while _graph_recent_timestamps and _graph_recent_timestamps[0] < cutoff:
        _graph_recent_timestamps.pop(0)

    # Persist every 5 requests
    if _graph_stats["total"] % 5 == 0:
        _save_graph_stats()

    # Async increment in Redis if available
    try:
        client = redis_un.get_redis_client()
        if client:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_persist_graph_request_to_redis(client, code_str, today))
            except RuntimeError:
                pass
    except Exception:
        pass


async def sync_stats_from_redis() -> bool:
    """Restore and merge persistent graph and push statistics from Redis."""
    global _push_events
    client = redis_un.get_redis_client()
    if not client:
        return False

    today = datetime.now().strftime("%Y-%m-%d")

    # 1. Graph requests stats
    try:
        raw_total = await client.get("graph_requests:total")
        raw_by_queue = await client.hgetall("graph_requests:by_queue")
        raw_daily_total = await client.get(f"graph_requests:daily:{today}:total")
        raw_daily_by_queue = await client.hgetall(f"graph_requests:daily:{today}:by_queue")

        redis_total = _safe_int(raw_total, 0)
        _graph_stats["total"] = max(_safe_int(_graph_stats.get("total"), 0), redis_total)

        if isinstance(raw_by_queue, dict):
            for k, v in raw_by_queue.items():
                k_str = _safe_str(k)
                _graph_stats["by_queue"][k_str] = max(
                    _safe_int(_graph_stats["by_queue"].get(k_str), 0),
                    _safe_int(v, 0),
                )

        redis_daily_total = _safe_int(raw_daily_total, 0)
        daily_bq_raw = raw_daily_by_queue if isinstance(raw_daily_by_queue, dict) else {}
        if redis_daily_total > 0 or daily_bq_raw:
            day_entry = _graph_stats.setdefault("daily", {}).setdefault(
                today, {"total": 0, "by_queue": {}}
            )
            day_bq = day_entry.setdefault("by_queue", {})
            for k, v in daily_bq_raw.items():
                k_str = _safe_str(k)
                val = _safe_int(v, 0)
                day_bq[k_str] = max(_safe_int(day_bq.get(k_str), 0), val)
                _graph_stats["by_queue"][k_str] = max(
                    _safe_int(_graph_stats["by_queue"].get(k_str), 0),
                    day_bq[k_str],
                )
            day_entry["total"] = max(
                _safe_int(day_entry.get("total"), 0),
                redis_daily_total,
                sum(day_bq.values()),
            )
            _graph_stats["total"] = max(_graph_stats["total"], day_entry["total"])

        _graph_stats["total"] = max(
            _graph_stats["total"],
            sum(_safe_int(v, 0) for v in _graph_stats["by_queue"].values()),
        )
    except Exception as ex:
        log.warning("sync_stats_from_redis (graph) error: %s", ex)

    # 2. Push events history (last 500)
    try:
        raw_events = await client.lrange("push_events_history", -500, -1)
        if raw_events:
            parsed_events: list[dict[str, Any]] = []
            for raw in raw_events:
                try:
                    item = json.loads(_safe_str(raw))
                    if isinstance(item, dict):
                        parsed_events.append(item)
                except Exception:
                    continue

            if parsed_events and (not _push_events or len(_push_events) <= len(parsed_events)):
                seen = {_event_dedup_key(ev) for ev in _push_events}
                merged = list(_push_events)
                for ev in parsed_events:
                    key = _event_dedup_key(ev)
                    if key not in seen:
                        seen.add(key)
                        merged.append(ev)
                merged.sort(key=lambda x: x.get("timestamp", 0))
                _push_events = merged[-500:]
            elif parsed_events:
                # Even if memory has more events, merge any missing Redis events without duplicates
                seen = {_event_dedup_key(ev) for ev in _push_events}
                added = False
                for ev in parsed_events:
                    key = _event_dedup_key(ev)
                    if key not in seen:
                        seen.add(key)
                        _push_events.append(ev)
                        added = True
                if added:
                    _push_events.sort(key=lambda x: x.get("timestamp", 0))
                    _push_events = _push_events[-500:]
    except Exception as ex:
        log.warning("sync_stats_from_redis (push_events_history) error: %s", ex)

    # 3. Push all-time counters
    try:
        events_all_time, events_by_queue = _summarize_events(_push_events)

        r_total = await client.get("push_stats:total")
        r_web = await client.get("push_stats:web")
        r_tg = await client.get("push_stats:tg")
        r_events = await client.get("push_stats:events")

        r_bq_total_raw = await client.hgetall("push_stats:by_queue:total") or {}
        r_bq_web_raw = await client.hgetall("push_stats:by_queue:web") or {}
        r_bq_tg_raw = await client.hgetall("push_stats:by_queue:tg") or {}
        r_bq_events_raw = await client.hgetall("push_stats:by_queue:events") or {}
        r_bq_last_raw = await client.hgetall("push_stats:by_queue:last_sent") or {}

        r_bq_total = {_safe_str(k): _safe_int(v, 0) for k, v in r_bq_total_raw.items()}
        r_bq_web = {_safe_str(k): _safe_int(v, 0) for k, v in r_bq_web_raw.items()}
        r_bq_tg = {_safe_str(k): _safe_int(v, 0) for k, v in r_bq_tg_raw.items()}
        r_bq_events = {_safe_str(k): _safe_int(v, 0) for k, v in r_bq_events_raw.items()}
        r_bq_last = {_safe_str(k): _safe_str(v) for k, v in r_bq_last_raw.items() if v}

        _push_all_time["web"] = max(
            _safe_int(_push_all_time.get("web"), 0),
            _safe_int(r_web, 0),
            events_all_time["web"],
        )
        _push_all_time["tg"] = max(
            _safe_int(_push_all_time.get("tg"), 0),
            _safe_int(r_tg, 0),
            events_all_time["tg"],
        )
        _push_all_time["total"] = max(
            _safe_int(_push_all_time.get("total"), 0),
            _safe_int(r_total, 0),
            events_all_time["total"],
            _push_all_time["web"] + _push_all_time["tg"],
        )
        _push_all_time["events_count"] = max(
            _safe_int(_push_all_time.get("events_count"), 0),
            _safe_int(r_events, 0),
            events_all_time["events_count"],
        )

        all_queue_labels = (
            set(_push_by_queue_all_time.keys())
            | set(events_by_queue.keys())
            | set(r_bq_total.keys())
            | set(r_bq_web.keys())
            | set(r_bq_tg.keys())
            | set(r_bq_events.keys())
            | set(r_bq_last.keys())
        )
        for q_lbl in all_queue_labels:
            existing = _push_by_queue_all_time.get(q_lbl, {})
            ev_q = events_by_queue.get(q_lbl, {})
            w_val = max(
                _safe_int(existing.get("web_sent"), 0),
                r_bq_web.get(q_lbl, 0),
                _safe_int(ev_q.get("web_sent"), 0),
            )
            g_val = max(
                _safe_int(existing.get("tg_sent"), 0),
                r_bq_tg.get(q_lbl, 0),
                _safe_int(ev_q.get("tg_sent"), 0),
            )
            t_val = max(
                _safe_int(existing.get("total_sent"), 0),
                r_bq_total.get(q_lbl, 0),
                _safe_int(ev_q.get("total_sent"), 0),
                w_val + g_val,
            )
            e_val = max(
                _safe_int(existing.get("events_count"), 0),
                r_bq_events.get(q_lbl, 0),
                _safe_int(ev_q.get("events_count"), 0),
            )
            last_val = _merge_last_sent(
                _merge_last_sent(existing.get("last_sent"), r_bq_last.get(q_lbl)),
                ev_q.get("last_sent"),
            )
            _push_by_queue_all_time[q_lbl] = {
                "total_sent": t_val,
                "web_sent": w_val,
                "tg_sent": g_val,
                "events_count": e_val,
                "last_sent": last_val,
            }

        # Backfill Redis all-time push keys if they don't exist yet but we have event history
        if r_total is None and _push_all_time["total"] > 0:
            try:
                if hasattr(client, "set"):
                    await client.set("push_stats:total", _push_all_time["total"])
                    await client.set("push_stats:web", _push_all_time["web"])
                    await client.set("push_stats:tg", _push_all_time["tg"])
                    await client.set("push_stats:events", _push_all_time["events_count"])
                if hasattr(client, "hset"):
                    for q_lbl, q_data in _push_by_queue_all_time.items():
                        if q_data["total_sent"] > 0:
                            await client.hset("push_stats:by_queue:total", q_lbl, q_data["total_sent"])
                            await client.hset("push_stats:by_queue:web", q_lbl, q_data["web_sent"])
                            await client.hset("push_stats:by_queue:tg", q_lbl, q_data["tg_sent"])
                            await client.hset("push_stats:by_queue:events", q_lbl, q_data["events_count"])
                            if q_data.get("last_sent"):
                                await client.hset("push_stats:by_queue:last_sent", q_lbl, q_data["last_sent"])
            except Exception as ex:
                log.debug("Backfill push_stats to Redis skipped: %s", ex)
    except Exception as ex:
        log.warning("sync_stats_from_redis (push_stats) error: %s", ex)

    return True


load_stats_from_redis = sync_stats_from_redis


def get_all_time_push_stats() -> dict[str, int]:
    """Return cumulative all-time push notification statistics."""
    events_all_time, _ = _summarize_events(_push_events)
    web_total = max(_safe_int(_push_all_time.get("web"), 0), events_all_time["web"])
    tg_total = max(_safe_int(_push_all_time.get("tg"), 0), events_all_time["tg"])
    total = max(
        _safe_int(_push_all_time.get("total"), 0),
        events_all_time["total"],
        web_total + tg_total,
    )
    events_count = max(
        _safe_int(_push_all_time.get("events_count"), 0),
        events_all_time["events_count"],
    )
    return {
        "total": total,
        "web": web_total,
        "tg": tg_total,
        "events_count": events_count,
    }


def get_graph_requests_stats() -> dict[str, Any]:
    """Return aggregated graph request statistics and rankings."""
    now = time.time()
    cutoff = now - 86400
    today = datetime.now().strftime("%Y-%m-%d")

    # Clean up rolling window
    while _graph_recent_timestamps and _graph_recent_timestamps[0] < cutoff:
        _graph_recent_timestamps.pop(0)

    # 24h count can be taken from rolling window or today's counter
    rolling_24h = len(_graph_recent_timestamps)
    today_total = _graph_stats.get("daily", {}).get(today, {}).get("total", 0)
    requests_24h = max(rolling_24h, today_total)

    total_requests = max(_graph_stats.get("total", 0), requests_24h)

    # Detailed by queue
    queue_counts = []
    for code, lbl in QUEUE_LABELS.items():
        count = _graph_stats.get("by_queue", {}).get(str(code), 0)
        today_q = _graph_stats.get("daily", {}).get(today, {}).get("by_queue", {}).get(str(code), 0)
        pct = round((count / total_requests * 100), 1) if total_requests > 0 else 0
        queue_counts.append({
            "code": code,
            "label": lbl,
            "total_requests": count,
            "today_requests": today_q,
            "percent": pct,
        })

    # Sort descending for top requested rankings
    ranking = sorted(queue_counts, key=lambda x: (x["total_requests"], x["today_requests"]), reverse=True)

    return {
        "total_requests": total_requests,
        "requests_24h": requests_24h,
        "today_requests": today_total,
        "ranking": ranking,
        "by_queue": {item["label"]: item for item in queue_counts},
    }


def get_24h_push_stats() -> dict[str, Any]:
    """Calculate statistics of pushes sent in the last 24 hours."""
    now = time.time()
    day_ago = now - 86400

    recent_events = [e for e in _push_events if e.get("timestamp", 0) >= day_ago]

    total_sent = sum(e.get("total_sent", 0) for e in recent_events)
    web_sent = sum(e.get("web_sent", 0) for e in recent_events)
    tg_sent = sum(e.get("tg_sent", 0) for e in recent_events)

    sorted_history = sorted(recent_events, key=lambda x: x.get("timestamp", 0), reverse=True)[:50]

    return {
        "total_24h": total_sent,
        "web_24h": web_sent,
        "tg_24h": tg_sent,
        "events_count_24h": len(recent_events),
        "history": sorted_history,
    }


def get_pushes_ranking() -> list[dict[str, Any]]:
    """Compute per-queue push rankings: how many notifications were dispatched to each queue."""
    now = time.time()
    day_ago = now - 86400

    stats_by_queue: dict[str, dict[str, Any]] = {}
    for code, lbl in QUEUE_LABELS.items():
        stats_by_queue[lbl] = {
            "code": code,
            "label": lbl,
            "total_sent": 0,
            "web_sent": 0,
            "tg_sent": 0,
            "events_count": 0,
            "total_24h": 0,
            "web_24h": 0,
            "tg_24h": 0,
            "events_24h": 0,
            "last_sent": None,
        }
    # Special bucket for broadcast pushes
    stats_by_queue["Всі"] = {
        "code": 0,
        "label": "Всі черги (загальна)",
        "total_sent": 0,
        "web_sent": 0,
        "tg_sent": 0,
        "events_count": 0,
        "total_24h": 0,
        "web_24h": 0,
        "tg_24h": 0,
        "events_24h": 0,
        "last_sent": None,
    }

    for ev in _push_events:
        q_lbl = ev.get("queue_label") or "Всі"
        bucket = stats_by_queue.setdefault(q_lbl, {
            "code": ev.get("queue") or 0,
            "label": q_lbl,
            "total_sent": 0,
            "web_sent": 0,
            "tg_sent": 0,
            "events_count": 0,
            "total_24h": 0,
            "web_24h": 0,
            "tg_24h": 0,
            "events_24h": 0,
            "last_sent": None,
        })
        t_sent = ev.get("total_sent", 0)
        w_sent = ev.get("web_sent", 0)
        g_sent = ev.get("tg_sent", 0)

        bucket["total_sent"] += t_sent
        bucket["web_sent"] += w_sent
        bucket["tg_sent"] += g_sent
        bucket["events_count"] += 1
        bucket["last_sent"] = _merge_last_sent(bucket.get("last_sent"), ev.get("datetime"))

        if ev.get("timestamp", 0) >= day_ago:
            bucket["total_24h"] += t_sent
            bucket["web_24h"] += w_sent
            bucket["tg_24h"] += g_sent
            bucket["events_24h"] += 1

    # Merge cumulative all-time per-queue counters so rankings survive redeploys/restarts
    for q_lbl, persisted in _push_by_queue_all_time.items():
        if not isinstance(persisted, dict):
            continue
        bucket = stats_by_queue.setdefault(q_lbl, {
            "code": 0,
            "label": "Всі черги (загальна)" if q_lbl == "Всі" else q_lbl,
            "total_sent": 0,
            "web_sent": 0,
            "tg_sent": 0,
            "events_count": 0,
            "total_24h": 0,
            "web_24h": 0,
            "tg_24h": 0,
            "events_24h": 0,
            "last_sent": None,
        })
        bucket["web_sent"] = max(bucket["web_sent"], _safe_int(persisted.get("web_sent"), 0))
        bucket["tg_sent"] = max(bucket["tg_sent"], _safe_int(persisted.get("tg_sent"), 0))
        bucket["total_sent"] = max(
            bucket["total_sent"],
            _safe_int(persisted.get("total_sent"), 0),
            bucket["web_sent"] + bucket["tg_sent"],
        )
        bucket["events_count"] = max(bucket["events_count"], _safe_int(persisted.get("events_count"), 0))
        bucket["last_sent"] = _merge_last_sent(bucket.get("last_sent"), persisted.get("last_sent"))

    # Sort descending by total_sent, then events_count
    ranking = sorted(
        stats_by_queue.values(),
        key=lambda x: (x["total_sent"], x["events_count"], x["total_24h"]),
        reverse=True,
    )
    return ranking


async def get_db_stats() -> dict[str, Any]:
    """Fetch database row counts and status."""
    if AsyncSessionLocal is None:
        return {"status": "offline", "tables": {}}

    try:
        async with AsyncSessionLocal() as session:
            sub_count = (await session.execute(select(func.count()).select_from(Subscription))).scalar() or 0
            tg_count = (await session.execute(select(func.count()).select_from(TgSub))).scalar() or 0
            user_count = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
            ticket_count = (await session.execute(select(func.count()).select_from(SupportTicket))).scalar() or 0
            open_tickets = (await session.execute(
                select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "open")
            )).scalar() or 0
            admin_count = (await session.execute(select(func.count()).select_from(SupportAdmin))).scalar() or 0
            ban_count = (await session.execute(select(func.count()).select_from(SupportBan))).scalar() or 0

            return {
                "status": "online",
                "tables": {
                    "subscriptions (web)": sub_count,
                    "tg_sub (telegram)": tg_count,
                    "users": user_count,
                    "support_tickets": ticket_count,
                    "support_admins": admin_count,
                    "support_bans": ban_count,
                },
                "support_tickets_open": open_tickets,
                "support_tickets_answered": max(0, ticket_count - open_tickets),
            }
    except Exception as e:
        log.warning("get_db_stats error: %s", e)
        return {"status": "error", "error": str(e), "tables": {}}


async def get_full_stats() -> dict[str, Any]:
    """Aggregate complete administrative statistics."""
    try:
        await sync_stats_from_redis()
    except Exception as exc:
        log.debug("get_full_stats sync_stats_from_redis skipped: %s", exc)

    db_stats = await get_db_stats()

    in_memory_push = len(subcription.get_push_subs())
    in_memory_tg = sum(len(b) for b in subcription.telegram_subscriptions.values())

    db_web = db_stats.get("tables", {}).get("subscriptions (web)", 0)
    db_tg = db_stats.get("tables", {}).get("tg_sub (telegram)", 0)

    web_total = max(db_web, in_memory_push)
    tg_total = max(db_tg, in_memory_tg)
    total_users = web_total + tg_total

    # Breakdown by queue
    queue_distribution: dict[str, dict[str, Any]] = {}
    subscribers_ranking_list: list[dict[str, Any]] = []

    for code, lbl in QUEUE_LABELS.items():
        w_count = len(subcription.get_push_subs(code))
        t_count = len(subcription.get_telegram_subs(code))
        q_total = w_count + t_count
        pct = round((q_total / max(1, total_users)) * 100, 1)

        info = {
            "code": code,
            "label": lbl,
            "web": w_count,
            "tg": t_count,
            "total": q_total,
            "percent": pct,
        }
        queue_distribution[lbl] = info
        subscribers_ranking_list.append(info)

    # Sort descending by total subscribers for the ranking
    subscribers_ranking_list.sort(key=lambda x: (x["total"], x["web"], x["tg"]), reverse=True)

    push_stats = get_24h_push_stats()
    pushes_all_time = get_all_time_push_stats()
    pushes_ranking = get_pushes_ranking()
    graph_stats = get_graph_requests_stats()

    # Redis info
    redis_status = "offline"
    redis_keys_count = 0
    try:
        r = redis_un.get_redis_client()
        if r:
            await r.ping()
            redis_status = "online"
            info = await r.dbsize()
            redis_keys_count = info
    except Exception:
        redis_status = "offline"

    return {
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "database": db_stats,
        "users": {
            "total_registered": total_users,
            "web_subscribers": web_total,
            "telegram_subscribers": tg_total,
            "in_memory_active_web": in_memory_push,
            "in_memory_active_tg": in_memory_tg,
            "by_queue": queue_distribution,
            "subscribers_ranking": subscribers_ranking_list,
        },
        "pushes_24h": push_stats,
        "pushes_all_time": pushes_all_time,
        "pushes_ranking": pushes_ranking,
        "graph_requests": graph_stats,
        "redis": {
            "status": redis_status,
            "keys_count": redis_keys_count,
        },
        "system": {
            "online_mode": os.getenv("ONLINE", "false").lower() == "true",
            "can_cache": os.getenv("CAN_CACHE", "true").lower() == "true",
            "notify_bot_online": os.getenv("NOTIFY_BOT_ONLINE", "false").lower() == "true",
            "help_bot_online": os.getenv("HELP_BOT_ONLINE", "false").lower() == "true",
        },
    }
