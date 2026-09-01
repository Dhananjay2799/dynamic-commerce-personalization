from math import ceil
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.product import Product
from app.schemas.product import (
    ProductListResponse,
    ProductResponse,
)


router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get(
    "",
    response_model=ProductListResponse,
)
async def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    category: str | None = None,
    brand: str | None = None,
    search: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort: Literal[
        "popular",
        "price_asc",
        "price_desc",
        "purchases",
    ] = "popular",
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    filters = []

    if category:
        pattern = f"%{category.lower()}%"

        filters.append(
            or_(
                func.lower(Product.category_code).like(pattern),
                func.lower(Product.category_l1).like(pattern),
                func.lower(Product.category_leaf).like(pattern),
            )
        )

    if brand:
        filters.append(
            func.lower(Product.brand) == brand.lower()
        )

    if search:
        pattern = f"%{search.lower()}%"

        filters.append(
            or_(
                func.lower(Product.name).like(pattern),
                func.lower(Product.brand).like(pattern),
                func.lower(Product.category_code).like(pattern),
            )
        )

    if min_price is not None:
        filters.append(Product.price >= min_price)

    if max_price is not None:
        filters.append(Product.price <= max_price)

    query = select(Product)

    count_query = select(
        func.count(Product.product_id)
    )

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    if sort == "price_asc":
        query = query.order_by(
            Product.price.asc(),
            Product.product_id.asc(),
        )

    elif sort == "price_desc":
        query = query.order_by(
            Product.price.desc(),
            Product.product_id.asc(),
        )

    elif sort == "purchases":
        query = query.order_by(
            Product.purchases.desc(),
            Product.total_events.desc(),
        )

    else:
        query = query.order_by(
            Product.total_events.desc(),
            Product.purchases.desc(),
        )

    total_result = await db.execute(count_query)
    total = int(total_result.scalar_one())

    offset = (page - 1) * page_size

    result = await db.execute(
        query
        .offset(offset)
        .limit(page_size)
    )

    products = list(
        result.scalars().all()
    )

    total_pages = (
        ceil(total / page_size)
        if total
        else 0
    )

    return ProductListResponse(
        items=products,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> Product:
    result = await db.execute(
        select(Product).where(
            Product.product_id == product_id
        )
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    return product