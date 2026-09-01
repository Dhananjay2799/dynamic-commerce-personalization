from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
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

    purchases: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    unique_products: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    unique_users: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    view_to_purchase_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="category",
    )

    __table_args__ = (
        Index(
            "ix_categories_category_code",
            "category_code",
        ),
        Index(
            "ix_categories_category_l1",
            "category_l1",
        ),
    )