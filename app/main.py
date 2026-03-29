from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.middlewares.auth import AuthContextMiddleware
from app.bot.middlewares.db import DbSessionMiddleware
from app.bot.routers import build_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import create_db_engine, create_session_factory, init_db


async def main() -> None:
    settings = get_settings()
    setup_logging()

    logger = logging.getLogger(__name__)
    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()

    dispatcher.update.outer_middleware(DbSessionMiddleware(session_factory))
    dispatcher.update.outer_middleware(AuthContextMiddleware(settings))
    dispatcher.include_router(build_router())

    await init_db(engine)
    logger.info("Bot is starting.")

    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        logger.info("Bot is shutting down.")
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
