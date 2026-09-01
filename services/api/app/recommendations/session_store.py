import json

from app.core.config import settings
from app.core.redis import redis_client
from app.schemas.event import SessionEventRequest


def session_events_key(
    session_id: str,
) -> str:
    return f"session:{session_id}:events"


async def store_event(
    event: SessionEventRequest,
) -> None:
    key = session_events_key(
        event.session_id
    )

    payload = json.dumps(
        event.model_dump(
            mode="json"
        )
    )

    async with redis_client.pipeline(
        transaction=True
    ) as pipe:
        pipe.rpush(
            key,
            payload,
        )

        pipe.ltrim(
            key,
            -settings.session_max_events,
            -1,
        )

        pipe.expire(
            key,
            settings.session_ttl_seconds,
        )

        await pipe.execute()


async def get_session_events(
    session_id: str,
) -> list[dict]:
    key = session_events_key(
        session_id
    )

    records = await redis_client.lrange(
        key,
        0,
        -1,
    )

    return [
        json.loads(record)
        for record in records
    ]