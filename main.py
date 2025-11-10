import asyncio
from datetime import datetime 
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pywebpush import webpush, WebPushException
import json, os

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

import untils.redis_db as redis_un

from db.orm.utils import init_db, save_sub, get_all_sub

from untils.parser import parse
from dotenv import load_dotenv


load_dotenv()

_redis_client = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
NOTIFY_PASS = os.getenv("NOTIFY_PASS")
BASE_DIR = Path(__file__).resolve().parent
SITE_DIR = BASE_DIR / "site"


app.mount("/site", StaticFiles(directory=SITE_DIR), name="site")

subscriptions = []

def get_subs():
    return subscriptions

@app.get("/vapid_public_key")
def vapid_key():
    return {"key": VAPID_PUBLIC_KEY}

@app.post("/subscribe")
async def subscribe(req: Request):
    data = await req.json()

    endpoint = data.get("endpoint")
    keys = data.get("keys", {})
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return {"ok": False, "msg": "Invalid subscription data"}

    sub_push = {
        "endpoint": endpoint,
        "keys": {"p256dh": p256dh, "auth": auth}
    }

    sub_db = {
        "endpoint": endpoint,
        "p256dh": p256dh,
        "auth": auth
    }

    # Проверка на дубликат
    exists = any(s.get("endpoint") == endpoint for s in subscriptions)
    if not exists:
        subscriptions.append(sub_push)
        await _redis_client.rpush("subscriptions", json.dumps(sub_push))
        await save_sub(sub_db)
        return {"ok": True, "msg": "Ви підписались на сповіщення"}

    return {"ok": True, "msg": "Ви вже підписані на сповіщення"}


@app.post("/notify")
async def notify(req: Request):
    body = await req.json()
    message = body.get("message")
    sent = 0

    if NOTIFY_PASS != body.get("pass"):
        return {"msg": "incorrect password"}

    for sub in subscriptions:
        try:
            # Если sub из Redis — приведи в нужный формат
            if isinstance(sub, str):
                sub = json.loads(sub)
            # Если нет ключа keys — сформируй его вручную
            if "keys" not in sub:
                sub = {
                    "endpoint": sub["endpoint"],
                    "keys": {
                        "p256dh": sub["p256dh"],
                        "auth": sub["auth"]
                    }
                }

            webpush(
                subscription_info=sub,
                data=json.dumps({"title": body.get("title"), "body": message}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:kostantinreksa@gmail.com"},
            )
            sent += 1

        except WebPushException as ex:
            print(f"⚠️ Push failed for {sub.get('endpoint', '')[:40]}...: {ex}")

            return {"msg": f"⚠️ Push failed for {sub.get('endpoint', '')[:40]}...: {ex}"}

    return {"sent": sent}

@app.get("/")
def index():
    return FileResponse(SITE_DIR / "index.html")

@app.get("/sw.js")
def service_worker():
    return FileResponse(SITE_DIR / "sw.js")

@app.get("/status")
def get_status():
    return {"Status": parse()}

@app.on_event("startup")
async def start():
    global _redis_client, subscriptions

    await init_db()

    _redis_client = await redis_un.init_redis()
    subs_data = await redis_un.load_subscriptions()

    if subs_data:
        subscriptions = [json.loads(s) if isinstance(s, str) else s for s in subs_data]
        print(f"✅ Загружено подписок: {len(subscriptions)}")
    else:
        subscriptions = []
        print("ℹ️ Подписок не найдено в Redis.")
        subscriptions = await get_all_sub()
        if not subscriptions:
            print("Подписки в базе данных не найдены")
        else:
            print(f"Количество подписок из базы данных {len(subscriptions)}")
            await save_all_to_redis(subscriptions)
    
    asyncio.create_task(check_and_notify())

async def save_all_to_redis(subscriptions):
    if not subscriptions:
        return

    serialized = [json.dumps({
        "endpoint": s.endpoint,
        "keys": {
            "p256dh": s.p256dh,
            "auth": s.auth
        }
    }) for s in subscriptions]

    await _redis_client.rpush("subscriptions", *serialized)
    print(f"✅ Загружено подписок в Redis: {len(serialized)}")


CHECK_INTERVAL = 60 * 15  # проверять каждые 15 минут

async def check_and_notify():
    while True:
        try:
            status = parse()
            now = datetime.now()
            # индекс текущего часа
            current_hour = now.hour

            # если через 1 час будет отключение
            if current_hour + 1 < len(status) and status[current_hour] == 0 and status[current_hour + 1] == 1:
                await send_push_all(
                    title="⚠️ Скоро відключення світла",
                    body=f"Через одну годину (в {current_hour+1}:00) планується відключення світла по графіку."
                )

        except Exception as e:
            print(f"[error] {e}")

        await asyncio.sleep(CHECK_INTERVAL)

async def send_push_all(title: str, body: str):
    subscriptions = get_subs()

    sent = 0
    for sub in subscriptions:
        try:
            if isinstance(sub, str):
                sub = json.loads(sub)
            webpush(
                subscription_info=sub,
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:kostantinreksa@gmail.com"},
            )
            sent += 1
        except Exception as ex:
            print(f"⚠️ Push failed: {ex}")
    print(f"✅ Отправлено уведомлений: {sent}")
