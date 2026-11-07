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

_push_events: list[dict[str, Any]] = []

# Graph requests in-memory counters & recent requests timestamps
_graph_stats: dict[str, Any] = {
    "total": 0,
    "by_queue": {str(k): 0 for k in QUEUE_LABELS.keys()},
    "daily": {},  # { "YYYY-MM-DD": { "total": int, "by_queue": { "11": int, ... } } }
}
_graph_recent_timestamps: list[float] = []


def _load_persisted_events():
    global _push_events, _graph_stats
    try:
        if os.path.exists(PUSH_STATS_FILE):
            with open(PUSH_STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    _push_events = data
                    log.info("Loaded %d push events from %s", len(_push_events), PUSH_STATS_FILE)
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
        to_save = _push_events[-500:]
        with open(PUSH_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
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


def record_push_event(web_sent: int, tg_sent: int, title: str = "", queue: int | None = None):
    """Record a push delivery event."""
    total = int(web_sent) + int(tg_sent)
    if total <= 0:
        return

    queue_lbl = subcription.queue_label(queue) if queue is not None else "Всі"
    event = {
        "timestamp": time.time(),
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "web_sent": int(web_sent),
        "tg_sent": int(tg_sent),
        "total_sent": total,
        "title": title or "Сповіщення",
        "queue": queue,
        "queue_label": queue_lbl,
    }

    _push_events.append(event)
    _save_push_events()

    # Try saving to Redis asynchronously if available
    try:
        client = redis_un.get_redis_client()
        if client:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(client.rpush("push_events_history", json.dumps(event)))
                loop.create_task(client.ltrim("push_events_history", -500, -1))
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

    # Persist every 10 requests or periodically
    if _graph_stats["total"] % 5 == 0:
        _save_graph_stats()

    # Async increment in Redis if available
    try:
        client = redis_un.get_redis_client()
        if client:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(client.hincrby("graph_requests:by_queue", code_str, 1))
                loop.create_task(client.incr("graph_requests:total"))
            except RuntimeError:
                pass
    except Exception:
        pass


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
        bucket["last_sent"] = ev.get("datetime")

        if ev.get("timestamp", 0) >= day_ago:
            bucket["total_24h"] += t_sent
            bucket["web_24h"] += w_sent
            bucket["tg_24h"] += g_sent
            bucket["events_24h"] += 1

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
