from pydantic import (
    BaseModel,
    ConfigDict,
)


class InventoryItemResponse(
    BaseModel
):
    model_config = ConfigDict(
        from_attributes=True
    )

    product_id: int
    category_id: int

    name: str

    category_code: str | None
    category_l1: str | None
    category_leaf: str | None

    brand: str | None

    inventory_quantity: int


class InventoryListResponse(
    BaseModel
):
    items: list[
        InventoryItemResponse
    ]

    page: int
    page_size: int

    total: int
    total_pages: int