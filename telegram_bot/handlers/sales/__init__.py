"""Sales funnel routers — composite router for all sales handlers."""

from aiogram import Router

from .basic import router as basic_router
from .common import router as common_router
from .custom import router as custom_router
from .diy import router as diy_router
from .payment import router as payment_router
from .quiz import router as quiz_router
from .welcome import router as welcome_router


def get_sales_router() -> Router:
    """Assemble all sales sub-routers into one router."""
    sales = Router()
    # Payment router first to handle payment callbacks before basic
    sales.include_router(payment_router)
    sales.include_router(welcome_router)
    sales.include_router(quiz_router)
    sales.include_router(diy_router)
    sales.include_router(basic_router)
    sales.include_router(custom_router)
    sales.include_router(common_router)
    return sales
