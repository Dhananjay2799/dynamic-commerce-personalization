from pydantic import BaseModel

from app.schemas.product import ProductResponse


class RecommendationItem(BaseModel):
    product: ProductResponse
    score: float
    reason: str


class RecommendationResponse(BaseModel):
    session_id: str

    strategy: str
    model_version: str

    inference_ms: float
    total_ms: float

    items: list[RecommendationItem]


class IntentSignal(BaseModel):
    product_id: int
    weight: float


class SessionIntentResponse(BaseModel):
    session_id: str
    event_count: int

    active_product_signals: list[IntentSignal]

    model_version: str