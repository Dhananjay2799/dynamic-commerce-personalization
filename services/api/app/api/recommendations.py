from time import perf_counter

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.product import Product
from app.recommendations.intent import (
    build_product_weights,
)
from app.recommendations.model import (
    get_recommendation_model,
)
from app.recommendations.session_store import (
    get_session_events,
)
from app.schemas.product import (
    ProductResponse,
)
from app.schemas.recommendation import (
    IntentSignal,
    RecommendationItem,
    RecommendationResponse,
    SessionIntentResponse,
)


router = APIRouter(
    tags=["recommendations"],
)


@router.get(
    "/recommendations",
    response_model=RecommendationResponse,
)
async def recommendations(
    session_id: str,
    limit: int = Query(
        default=12,
        ge=1,
        le=50,
    ),
    db: AsyncSession = Depends(
        get_db
    ),
) -> RecommendationResponse:
    request_started = perf_counter()

    events = await get_session_events(
        session_id
    )

    product_weights = (
        build_product_weights(
            events
        )
    )

    model = (
        get_recommendation_model()
    )

    inference_started = perf_counter()

    (
        strategy,
        candidates,
    ) = model.recommend(
        product_weights=product_weights,
        limit=limit,
    )

    inference_ms = (
        perf_counter()
        - inference_started
    ) * 1000

    ids = [
        candidate.product_id
        for candidate in candidates
    ]

    if ids:
        result = await db.execute(
            select(Product).where(
                Product.product_id.in_(
                    ids
                )
            )
        )

        products = {
            product.product_id: product
            for product
            in result.scalars().all()
        }
    else:
        products = {}

    items = []

    for candidate in candidates:
        product = products.get(
            candidate.product_id
        )

        if product is None:
            continue

        items.append(
            RecommendationItem(
                product=ProductResponse
                .model_validate(
                    product
                ),
                score=round(
                    candidate.score,
                    6,
                ),
                reason=(
                    candidate.reason
                ),
            )
        )

    total_ms = (
        perf_counter()
        - request_started
    ) * 1000

    return RecommendationResponse(
        session_id=session_id,
        strategy=strategy,
        model_version=(
            model.MODEL_VERSION
        ),
        inference_ms=round(
            inference_ms,
            3,
        ),
        total_ms=round(
            total_ms,
            3,
        ),
        items=items,
    )


@router.get(
    "/sessions/{session_id}/intent",
    response_model=SessionIntentResponse,
)
async def session_intent(
    session_id: str,
) -> SessionIntentResponse:
    events = await get_session_events(
        session_id
    )

    weights = build_product_weights(
        events
    )

    strongest = sorted(
        weights.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:10]

    model = (
        get_recommendation_model()
    )

    return SessionIntentResponse(
        session_id=session_id,
        event_count=len(events),
        active_product_signals=[
            IntentSignal(
                product_id=product_id,
                weight=round(
                    weight,
                    4,
                ),
            )
            for product_id, weight
            in strongest
        ],
        model_version=(
            model.MODEL_VERSION
        ),
    )