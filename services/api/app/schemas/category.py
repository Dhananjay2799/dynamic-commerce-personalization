from pydantic import BaseModel, ConfigDict


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: int

    category_code: str | None
    category_l1: str | None
    category_leaf: str | None

    total_events: int
    views: int
    carts: int
    purchases: int

    unique_products: int
    unique_users: int

    view_to_purchase_rate: float