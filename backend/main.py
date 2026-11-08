from apscheduler.schedulers.asyncio import AsyncIOScheduler

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os

from contextlib import asynccontextmanager

from typing import Any

from fastapi.responses import Response
from dotenv import load_dotenv

load_dotenv()
_backend_env = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_backend_env):
    load_dotenv(_backend_env)

import bots.notifier_bot.bot as notify_bot
import bots.help_bot.bot as help_bot

import untils.states as states

import untils.redis_db as redis_un
from untils import notifier
from untils import subcription
from untils import cache
from untils import addresses
import db.orm.utils as db

import asyncio
import json
import secrets

import logging as log

from proto import status_pb2
from untils import stats_tracker

log.basicConfig(
    level=log.INFO,
    format="! [%(levelname)s] %(message)s"
)

BASE_PATH = "/api"
ISDB = True

DB_ONLINE = os.getenv("DB_ONLINE") == "true"
NOTIFY_PASS = os.getenv("NOTIFY_PASS")
ADMIN_STATS_PASSWORD = NOTIFY_PASS or os.getenv("ADMIN_STATS_PASSWORD") or "admstats123"
ONLINE = os.getenv("ONLINE", "false").lower() == "true"
REDIS_ONLINE = os.getenv("REDIS_ONLINE", "true").lower() == "true"
CAN_CACHE = os.getenv("CAN_CACHE", "true").lower() == "true"

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    if ONLINE:
        scheduler.add_job(notifier.check_and_notify, "cron", minute="*/30")
        scheduler.add_job(addresses.sync_addresses_from_ztoe, "interval", hours=12)
    else:
        log.info("app started in offline mode")

    if CAN_CACHE:
        scheduler.add_job(cache.cache_loop, "cron", minute="*/5")
    scheduler.start()

    global DB_ONLINE

    if DB_ONLINE:
        try:
            await db.init_db()
        except Exception as exc:
            log.warning(f"init_db() failed: {exc}")
            db.disable_db()
            global ISDB
            ISDB = False
            DB_ONLINE = False
    else:
        log.info("db disabled, offline mode")
    
    if REDIS_ONLINE:
        redis_client = await redis_un.init_redis()
        subcription.set_redis_client(redis_client)
        await subcription.load_subscriptions_from_storage()

    tasks = [
        notify_bot.start_bot,
        help_bot.start_bot
    ]

    app.state.bg_tasks = [asyncio.create_task(task()) for task in tasks]
    app.state.bg_tasks.append(asyncio.create_task(addresses.ensure_addresses_loaded()))

    yield

    states.closing = True

    for task in app.state.bg_tasks:
        task.cancel()
    scheduler.shutdown()

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(f"{BASE_PATH}/vapid_public_key")
def vapid_key():
    return {"key": VAPID_PUBLIC_KEY}

@app.post(f"{BASE_PATH}/subscribe")
async def subscribe(req: Request):
    data = await req.json()

    sub = data.get("subscription")
    if not isinstance(sub, dict):
        return {"ok": False, "msg": "Invalid subscription data"}

    queue = subcription.queue_code_from_input(data.get("queue"))

    endpoint = sub.get("endpoint")
    keys = sub.get("keys", {})
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return {"ok": False, "msg": "Invalid subscription data"}

    sub_push = {
        "endpoint": endpoint,
        "keys": {"p256dh": p256dh, "auth": auth},
        "queue": queue,
    }

    existing_queue, existing_idx = subcription.find_push_subscription(endpoint)

    if existing_idx is None:
        subcription.remember_push_subscription(sub_push)
        created = True
    else:
        subcription.forget_push_subscription(endpoint)
        subcription.remember_push_subscription(sub_push)
        created = False

    await subcription.save_subscription_db(queue, sub_push)

    await subcription.save_all_to_redis()

    return {"ok": True, "msg": "Ви пiдписались на сповiщення" if created else "Данi пiдписки оновлено"}

@app.post(f"{BASE_PATH}/unsubscribe")
async def unsubscribe(req: Request):
    data = await req.json()
    sub = data.get("subscription")

    normalized = subcription.normalize_subscription(sub)
    if not normalized:
        return {"ok": False, "msg": "Invalid subscription data"}

    endpoint = normalized.get("endpoint")
    removed = subcription.forget_push_subscription(endpoint)

    if ISDB:
        try:
            await db.delete_sub(endpoint)
        except Exception as ex:
            log.warning(f"delete_sub failed: {ex}")

    await subcription.save_all_to_redis()
    return {"ok": True, "msg": "Підписку скасовано" if removed else "Підписка не знайдена"}


@app.post(f"{BASE_PATH}/notify")
async def notify(req: Request):
    body: dict[str, Any] = await req.json()
    message = body.get("message")
    title = body.get("title")

    if NOTIFY_PASS != body.get("pass"):
        return {"msg": "incorrect password"}

    return await notifier.notify_all(title=title, message=message)

@app.post(f"{BASE_PATH}/admin/stats")
@app.post(f"{BASE_PATH}{BASE_PATH}/admin/stats")
@app.post("/admin/stats")
@app.post(f"{BASE_PATH}/stats")
@app.post("/stats")
@app.get(f"{BASE_PATH}/admin/stats")
@app.get("/admin/stats")
async def get_admin_stats(req: Request):
    password = None
    try:
        body = await req.json()
        if isinstance(body, dict):
            password = body.get("password")
    except Exception:
        pass

    if not password:
        password = req.headers.get("x-admin-password")

    given_pass = str(password or "")
    is_valid = False
    if NOTIFY_PASS and secrets.compare_digest(given_pass, str(NOTIFY_PASS)):
        is_valid = True
    elif ADMIN_STATS_PASSWORD and secrets.compare_digest(given_pass, str(ADMIN_STATS_PASSWORD)):
        is_valid = True

    if not password or not is_valid:
        return Response(
            content=json.dumps({"ok": False, "error": "Невірний пароль"}),
            status_code=401,
            media_type="application/json",
        )

    data = await stats_tracker.get_full_stats()
    return {"ok": True, "stats": data}


@app.get(f"{BASE_PATH}/status")
async def get_status(queue: str | None = None):
    queue_code = subcription.queue_code_from_input(queue)
    stats_tracker.record_graph_request(queue_code)
    return {"Status": await notifier.parse_status_for_queue(queue_code)}


def _extract_grpc_web_message(raw: bytes) -> bytes:
    """Return the protobuf payload from a gRPC-web frame or raw body."""
    if len(raw) >= 5 and raw[0] in (0x00, 0x01, 0x80):
        try:
            msg_len = int.from_bytes(raw[1:5], "big")
            return raw[5 : 5 + msg_len]
        except Exception:
            return raw
    return raw


def _grpc_status_payload(statuses: list[int]) -> bytes:
    response_msg = status_pb2.StatusResponse(status=statuses)
    message_bytes = response_msg.SerializeToString()
    data_frame = b"\x00" + len(message_bytes).to_bytes(4, "big") + message_bytes

    trailers = b"grpc-status:0\r\ngrpc-message:\r\n"
    trailer_frame = b"\x80" + len(trailers).to_bytes(4, "big") + trailers

    return data_frame + trailer_frame


@app.post(f"{BASE_PATH}/grpc/StatusService/GetStatus")
async def grpc_get_status(req: Request):
    """gRPC-web endpoint for status polling."""
    body = await req.body()
    message = _extract_grpc_web_message(body)

    queue = None
    try:
        parsed = status_pb2.StatusRequest()
        parsed.ParseFromString(message)
        queue = parsed.queue
    except Exception:
        queue = req.query_params.get("queue")

    queue_code = subcription.queue_code_from_input(queue)
    stats_tracker.record_graph_request(queue_code)
    statuses = await notifier.parse_status_for_queue(queue_code)
    payload = _grpc_status_payload(statuses)

    return Response(
        content=payload,
        media_type="application/grpc-web+proto",
        headers={
            "grpc-status": "0",
            "grpc-message": "",
            "Access-Control-Expose-Headers": "grpc-status, grpc-message",
        },
    )


@app.get(f"{BASE_PATH}/addresses/search")
@app.get("/addresses/search")
async def search_addresses(q: str = "", limit: int = 12):
    limit = max(1, min(30, limit))
    meta = addresses.get_meta()
    results = addresses.search_addresses(q, limit=limit)
    return {
        "ok": True,
        "query": q,
        "results": results,
        "total_indexed": meta["total_indexed"],
        "updated_at": meta["updated_at"],
        "source": meta["source"],
    }


@app.get(f"{BASE_PATH}/addresses/meta")
@app.get("/addresses/meta")
async def get_addresses_meta():
    return {"ok": True, **addresses.get_meta()}
