from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction_event import InteractionEvent
from app.recommendations.session_store import store_event
from app.schemas.event import SessionEventRequest


logger = logging.getLogger(__name__)


async def persist_event(
    db: AsyncSession,
    event: SessionEventRequest,
) -> InteractionEvent:
    record = InteractionEvent(
        session_id=event.session_id,
        event_type=event.event_type,
        product_id=event.product_id,
        category_id=event.category_id,
        event_metadata=event.metadata,
        occurred_at=event.timestamp,
    )

    db.add(record)

    try:
        await db.commit()
        await db.refresh(record)

    except Exception:
        await db.rollback()
        raise

    return record


async def update_online_state(
    event: SessionEventRequest,
) -> bool:
    try:
        await store_event(event)

        return True

    except Exception:
        logger.exception(
            "Failed to update Redis online state "
            "for session %s.",
            event.session_id,
        )

        return False