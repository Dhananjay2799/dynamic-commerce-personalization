from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "categories.category_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    category_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    category_l1: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    category_leaf: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    brand: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    inventory_quantity: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    total_events: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    views: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    carts: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    removes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    purchases: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    unique_users: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    unique_sessions: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    average_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    median_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    min_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    max_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    view_to_purchase_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    view_to_cart_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    last_event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    category: Mapped["Category"] = relationship(
        back_populates="products",
    )

    __table_args__ = (
        Index(
            "ix_products_category_brand",
            "category_id",
            "brand",
        ),
        Index(
            "ix_products_total_events",
            "total_events",
        ),
        Index(
            "ix_products_purchases",
            "purchases",
        ),
        Index(
            "ix_products_price",
            "price",
        ),
    )