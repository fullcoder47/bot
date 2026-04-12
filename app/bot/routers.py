from __future__ import annotations

from aiogram import Router

from app.bot.handlers.branches import router as branches_router
from app.bot.handlers.attendance import router as attendance_router
from app.bot.handlers.company import router as company_router
from app.bot.handlers.company_admin import router as company_admin_router
from app.bot.handlers.departments import router as departments_router
from app.bot.handlers.employee import router as employee_router
from app.bot.handlers.employees import router as employees_router
from app.bot.handlers.history import router as history_router
from app.bot.handlers.language import router as language_router
from app.bot.handlers.leave import router as leave_router
from app.bot.handlers.public_onboarding import router as public_onboarding_router
from app.bot.handlers.shifts import router as shifts_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.super_admin import router as super_admin_router


def build_router() -> Router:
    router = Router(name="root")
    router.include_router(start_router)
    router.include_router(language_router)
    router.include_router(public_onboarding_router)
    router.include_router(attendance_router)
    router.include_router(company_router)
    router.include_router(super_admin_router)
    router.include_router(company_admin_router)
    router.include_router(branches_router)
    router.include_router(departments_router)
    router.include_router(shifts_router)
    router.include_router(employees_router)
    router.include_router(employee_router)
    router.include_router(leave_router)
    router.include_router(history_router)
    return router
