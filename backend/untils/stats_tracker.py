import json
import logging
import os
import time
from datetime import datetime
from typing import Any

from untils import subcription
import untils.redis_db as redis_un
import db.orm.utils as db_utils
from db.orm.session import AsyncSessionLocal
from db.orm.models import Subscription, TgSub, User, SupportTicket, SupportAdmin, SupportBan
from sqlalchemy import select, func

log = logging.getLogger(__name__)

STATS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "push_stats.json")

_push_events: list[dict[str, Any]] = []

def _load_persisted_events():
    global _push_events
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    _push_events = data
                    log.info("Loaded %d push events from %s", len(_push_events), STATS_FILE)
    except Exception as e:
        log.warning("Could not load push stats file: %s", e)

def _save_persisted_events():
    try:
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        # Keep last 500 events
        to_save = _push_events[-500:]
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("Could not save push stats file: %s", e)

# Initial load
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
    _save_persisted_events()

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


def get_24h_push_stats() -> dict[str, Any]:
    """Calculate statistics of pushes sent in the last 24 hours."""
    now = time.time()
    day_ago = now - 86400

    recent_events = [e for e in _push_events if e.get("timestamp", 0) >= day_ago]

    total_sent = sum(e.get("total_sent", 0) for e in recent_events)
    web_sent = sum(e.get("web_sent", 0) for e in recent_events)
    tg_sent = sum(e.get("tg_sent", 0) for e in recent_events)

    # Return newest first
    sorted_history = sorted(recent_events, key=lambda x: x.get("timestamp", 0), reverse=True)[:50]

    return {
        "total_24h": total_sent,
        "web_24h": web_sent,
        "tg_24h": tg_sent,
        "events_count_24h": len(recent_events),
        "history": sorted_history,
    }


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
    from untils.variebles import QUEUE_LABELS
    for code, lbl in QUEUE_LABELS.items():
        w_count = len(subcription.get_push_subs(code))
        t_count = len(subcription.get_telegram_subs(code))
        queue_distribution[lbl] = {
            "code": code,
            "web": w_count,
            "tg": t_count,
            "total": w_count + t_count,
        }

    push_stats = get_24h_push_stats()

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
        },
        "pushes_24h": push_stats,
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
