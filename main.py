import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

import config
from db.database import Database
from handlers import booking, cancel, common, fallback


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.BOT_TOKEN:
        sys.exit("BOT_TOKEN не задан. Скопируйте .env.example в .env и заполните его.")
    if config.ADMIN_CHAT_ID is None:
        logging.warning("ADMIN_CHAT_ID не задан — уведомления администратору отправляться не будут")

    db = Database(config.DB_PATH)
    await db.connect()

    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db  # попадает в хендлеры как аргумент db
    # common первым: /start и «В главное меню» работают из любого состояния;
    # fallback последним: ловит всё необработанное
    dp.include_routers(common.router, booking.router, cancel.router, fallback.router)

    await bot.set_my_commands([BotCommand(command="start", description="Главное меню")])
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
