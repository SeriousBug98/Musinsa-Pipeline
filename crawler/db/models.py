from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    Numeric,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    musinsa_brand_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    english_name: Mapped[str | None] = mapped_column(String(200))
    link_url: Mapped[str | None] = mapped_column(String(500))
    is_tracked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    rankings: Mapped[list["BrandRanking"]] = relationship(back_populates="brand")
    fans: Mapped[list["BrandFan"]] = relationship(back_populates="brand")
    new_products: Mapped[list["NewProduct"]] = relationship(back_populates="brand")


class BrandRanking(Base):
    __tablename__ = "brand_rankings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("brands.id"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    brand: Mapped["Brand"] = relationship(back_populates="rankings")


class BrandFan(Base):
    __tablename__ = "brand_fans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("brands.id"), nullable=False
    )
    fan_count: Mapped[int] = mapped_column(Integer, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    brand: Mapped["Brand"] = relationship(back_populates="fans")


class NewProduct(Base):
    __tablename__ = "new_products"
    __table_args__ = (
        UniqueConstraint("product_id", "category_code", name="uq_new_products_pid_cat"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("brands.id"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    category_code: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[int | None] = mapped_column(Integer)
    final_price: Mapped[int | None] = mapped_column(Integer)
    discount_rate: Mapped[int | None] = mapped_column(Integer)
    is_sold_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sold_out_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_count: Mapped[int | None] = mapped_column(Integer)
    first_review_count: Mapped[int | None] = mapped_column(Integer)
    review_score: Mapped[float | None] = mapped_column(Numeric(4, 1))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))

    brand: Mapped["Brand"] = relationship(back_populates="new_products")


class BrandSnapMention(Base):
    __tablename__ = "brand_snap_mentions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    brand_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("brands.id"))
    brand_name: Mapped[str] = mapped_column(String(200), nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False)
    best_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    snap_like_sum: Mapped[int | None] = mapped_column(Integer)
    snap_view_sum: Mapped[int | None] = mapped_column(Integer)
    top_snap_id: Mapped[str | None] = mapped_column(String(100))
    period: Mapped[str] = mapped_column(String(10), nullable=False, default="DAILY")
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class BrandScore(Base):
    """Read-only model. Written by the Spring Boot analyzer."""

    __tablename__ = "brand_scores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("brands.id"), nullable=False
    )
    rank_change_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    fan_growth_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    soldout_speed_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    total_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
