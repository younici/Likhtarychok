import untils.subcription as sub
import untils.redis_db as redis_db
import db.orm.utils as db
# import bots.status_bot.untils.subs as stats_sub

async def notify_delete_tg_sub(id: int):
    subAnsw = sub.forget_telegram_subscription(id)
    redisAnsw = await redis_db.delete_tg_subscription(id)
    dbAnsw = await db.delete_tg_subscriber(id)
    return subAnsw, redisAnsw, dbAnsw

async def notify_delete_web_sub(endpoint):
    subAnsw = sub.forget_push_subscription(endpoint)
    redisAnsw = await redis_db.delete_push_subscription(endpoint)
    dbAnsw = await db.delete_sub(endpoint)
    return subAnsw, redisAnsw, dbAnsw


# added for status bot
# async def status_save_tg(id: int):
#     pass

# async def status_dell_tg(id: int):
#     pass