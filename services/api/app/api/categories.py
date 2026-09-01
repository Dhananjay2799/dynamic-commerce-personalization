from math import ceil

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.core.database import get_db
from app.models.category import (
    Category,
)
from app.schemas.category import (
    CategoryListResponse,
)


router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


@router.get(
    "",
    response_model=(
        CategoryListResponse
    ),
)
async def list_categories(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    db: AsyncSession = Depends(
        get_db
    ),
) -> CategoryListResponse:
    total_result = (
        await db.execute(
            select(
                func.count(
                    Category.category_id
                )
            )
        )
    )

    total = int(
        total_result.scalar_one()
    )

    offset = (
        page - 1
    ) * page_size

    result = await db.execute(
        select(
            Category
        )
        .order_by(
            Category.total_events
            .desc(),
            Category.purchases
            .desc(),
            Category.category_id
            .asc(),
        )
        .offset(
            offset
        )
        .limit(
            page_size
        )
    )

    categories = list(
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

    return CategoryListResponse(
        items=categories,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(
            total_pages
        ),
    )