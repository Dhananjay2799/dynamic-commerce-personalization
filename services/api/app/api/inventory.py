from math import ceil

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy import (
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.core.database import get_db
from app.models.product import (
    Product,
)
from app.schemas.inventory import (
    InventoryListResponse,
)


router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
)


@router.get(
    "",
    response_model=(
        InventoryListResponse
    ),
)
async def list_inventory(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=24,
        ge=1,
        le=100,
    ),
    category: str | None = None,
    low_stock: bool = False,
    low_stock_threshold: int = (
        Query(
            default=25,
            ge=0,
            le=10000,
        )
    ),
    db: AsyncSession = Depends(
        get_db
    ),
) -> InventoryListResponse:
    filters = []

    if category:
        pattern = (
            f"%{category.lower()}%"
        )

        filters.append(
            or_(
                func.lower(
                    Product.category_code
                ).like(
                    pattern
                ),
                func.lower(
                    Product.category_l1
                ).like(
                    pattern
                ),
                func.lower(
                    Product.category_leaf
                ).like(
                    pattern
                ),
            )
        )

    if low_stock:
        filters.append(
            Product.inventory_quantity
            <= low_stock_threshold
        )

    query = select(
        Product
    )

    count_query = select(
        func.count(
            Product.product_id
        )
    )

    if filters:
        query = query.where(
            *filters
        )

        count_query = (
            count_query.where(
                *filters
            )
        )

    total_result = await db.execute(
        count_query
    )

    total = int(
        total_result.scalar_one()
    )

    offset = (
        page - 1
    ) * page_size

    result = await db.execute(
        query
        .order_by(
            Product.inventory_quantity
            .asc(),
            Product.product_id
            .asc(),
        )
        .offset(
            offset
        )
        .limit(
            page_size
        )
    )

    products = list(
        result.scalars().all()
    )

    total_pages = (
        ceil(
            total
            / page_size
        )
        if total
        else 0
    )

    return InventoryListResponse(
        items=products,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(
            total_pages
        ),
    )