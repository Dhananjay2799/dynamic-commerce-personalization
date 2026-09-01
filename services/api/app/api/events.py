import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.event import (
    EventResponse,
    SessionEventRequest,
)
from app.telemetry.service import (
    persist_event,
    update_online_state,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/events",
    tags=["telemetry"],
)


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_event(
    event: SessionEventRequest,
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    try:
        record = await persist_event(
            db=db,
            event=event,
        )

    except Exception as exc:
        logger.exception(
            "Failed to persist interaction event."
        )

        raise HTTPException(
            status_code=503,
            detail="Unable to persist telemetry event.",
        ) from exc

    online_state_updated = (
        await update_online_state(event)
    )

    return EventResponse(
        accepted=True,
        event_id=record.id,
        session_id=event.session_id,
        event_type=event.event_type,
        persisted=True,
        online_state_updated=online_state_updated,
    )