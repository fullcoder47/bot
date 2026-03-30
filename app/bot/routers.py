from __future__ import annotations

from aiogram import Router

from app.bot.handlers.company import router as company_router
from app.bot.handlers.company_admin import router as company_admin_router
from app.bot.handlers.language import router as language_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.super_admin import router as super_admin_router


def build_router() -> Router:
    router = Router(name="root")
    router.include_router(start_router)
    router.include_router(language_router)
    router.include_router(company_router)
    router.include_router(super_admin_router)
    router.include_router(company_admin_router)
    return router
