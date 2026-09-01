from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    category_id: int
    name: str

    category_code: str | None
    category_l1: str | None
    category_leaf: str | None

    brand: str | None

    price: float
    inventory_quantity: int
    image_url: str | None

    total_events: int
    views: int
    carts: int
    purchases: int

    view_to_purchase_rate: float
    view_to_cart_rate: float

    last_event_time: datetime


class ProductListResponse(BaseModel):
    items: list[ProductResponse]

    page: int
    page_size: int
    total: int
    total_pages: int