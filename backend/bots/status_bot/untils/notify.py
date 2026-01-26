import bots.status_bot.untils.subs as subs
import bots.status_bot.bot as status_bot

async def notify_all(msg: str):
    ids = subs.get_subs()
    bot = status_bot.get_bot()

    sended_count = 0

    for id in ids:
        try:
            await bot.send_message(id, msg)
            sended_count += 1
        except:
            subs.remove_user(id)
    
    return sended_count

async def notify(id: int, msg: str) -> bool:
    bot = status_bot.get_bot()
    try:
        await bot.send_message(id, msg)
        return True
    except:
        return False