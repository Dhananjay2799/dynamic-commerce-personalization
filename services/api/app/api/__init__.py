from fastapi import APIRouter

from app.api.categories import (
    router as categories_router,
)
from app.api.events import (
    router as events_router,
)
from app.api.inventory import (
    router as inventory_router,
)
from app.api.products import (
    router as products_router,
)
from app.api.recommendations import (
    router as recommendations_router,
)


api_router = APIRouter(
    prefix="/api/v1",
)

api_router.include_router(
    products_router
)

api_router.include_router(
    categories_router
)

api_router.include_router(
    inventory_router
)

api_router.include_router(
    events_router
)

api_router.include_router(
    recommendations_router
)