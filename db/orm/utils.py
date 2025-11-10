from db.orm.base import Base
from db.orm.session import engine
from sqlalchemy.ext.asyncio import AsyncSession
from db.orm.session import AsyncSessionLocal
from sqlalchemy import select
from fastapi import Request

from db.orm.models.subscription import Subscription

import db.orm.models

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def save_sub(data):
    if "subscription" in data:
        sub = data["subscription"]
        keys = sub.get("keys", {})
        endpoint = sub.get("endpoint")
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")
    else:
        endpoint = data.get("endpoint")
        p256dh = data.get("p256dh")
        auth = data.get("auth")

    if not endpoint or not p256dh or not auth:
        print("⚠️ save_sub(): invalid data", data)
        return False

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(Subscription).where(Subscription.endpoint == endpoint)
        )

        if existing:
            return True

        new_sub = Subscription(
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        )
        session.add(new_sub)
        await session.commit()
        await session.refresh(new_sub)

    print(f"✅ Subscription saved: {endpoint[:50]}...")
    return True

async def get_all_sub():
    async with AsyncSessionLocal() as conn:
        res = await conn.execute(select(Subscription))
        return res.scalars().all()