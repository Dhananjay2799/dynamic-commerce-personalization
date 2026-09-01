from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


ProductEventType = Literal[
    "product_impression",
    "view_item",
    "product_click",
    "dwell_time",
    "scroll_depth",
    "add_to_cart",
    "remove_from_cart",
    "purchase",
]

SessionEventType = Literal[
    "product_impression",
    "view_item",
    "product_click",
    "dwell_time",
    "scroll_depth",
    "add_to_cart",
    "remove_from_cart",
    "purchase",
    "category_view",
    "search",
]


class SessionEventRequest(BaseModel):
    session_id: str = Field(
        min_length=8,
        max_length=128,
    )

    event_type: SessionEventType

    product_id: int | None = None
    category_id: int | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    @model_validator(mode="after")
    def validate_product_event(
        self,
    ) -> "SessionEventRequest":
        product_events = {
            "product_impression",
            "view_item",
            "product_click",
            "dwell_time",
            "scroll_depth",
            "add_to_cart",
            "remove_from_cart",
            "purchase",
        }

        if (
            self.event_type in product_events
            and self.product_id is None
        ):
            raise ValueError(
                f"{self.event_type} requires product_id."
            )

        return self


class EventResponse(BaseModel):
    accepted: bool

    event_id: UUID

    session_id: str
    event_type: str

    persisted: bool
    online_state_updated: bool