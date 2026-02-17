"""SQLAlchemy models for EVE Gatekeeper.

These models are designed for future database storage of universe data.
Currently, the app uses JSON files for data storage.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Region(Base):
    """EVE Online region."""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    faction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    systems: Mapped[list["SolarSystem"]] = relationship(back_populates="region")

    def __repr__(self) -> str:
        return f"<Region(id={self.id}, name={self.name})>"


class SolarSystem(Base):
    """EVE Online solar system."""

    __tablename__ = "solar_systems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"), nullable=False)
    constellation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    security_status: Mapped[float] = mapped_column(Float, nullable=False)
    security_class: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # highsec, lowsec, nullsec, wh
    position_x: Mapped[float] = mapped_column(Float, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, nullable=False)
    position_z: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    region: Mapped["Region"] = relationship(back_populates="systems")
    connections_from: Mapped[list["Stargate"]] = relationship(
        "Stargate",
        foreign_keys="Stargate.source_system_id",
        back_populates="source_system",
    )
    connections_to: Mapped[list["Stargate"]] = relationship(
        "Stargate",
        foreign_keys="Stargate.destination_system_id",
        back_populates="destination_system",
    )

    __table_args__ = (Index("ix_solar_systems_region_security", "region_id", "security_class"),)

    def __repr__(self) -> str:
        return f"<SolarSystem(id={self.id}, name={self.name}, security={self.security_status})>"


class Stargate(Base):
    """Stargate connection between two systems."""

    __tablename__ = "stargates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_system_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("solar_systems.id"), nullable=False
    )
    destination_system_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("solar_systems.id"), nullable=False
    )

    # Relationships
    source_system: Mapped["SolarSystem"] = relationship(
        "SolarSystem",
        foreign_keys=[source_system_id],
        back_populates="connections_from",
    )
    destination_system: Mapped["SolarSystem"] = relationship(
        "SolarSystem",
        foreign_keys=[destination_system_id],
        back_populates="connections_to",
    )

    __table_args__ = (
        Index("ix_stargates_source", "source_system_id"),
        Index("ix_stargates_destination", "destination_system_id"),
    )

    def __repr__(self) -> str:
        return f"<Stargate(source={self.source_system_id}, dest={self.destination_system_id})>"


class KillRecord(Base):
    """Cached kill data from zKillboard."""

    __tablename__ = "kill_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # zKillboard kill ID
    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("solar_systems.id"), nullable=False)
    kill_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ship_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    victim_corporation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    victim_alliance_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attacker_count: Mapped[int] = mapped_column(Integer, default=0)
    is_pod: Mapped[bool] = mapped_column(default=False)
    total_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (Index("ix_kill_records_system_time", "system_id", "kill_time"),)

    def __repr__(self) -> str:
        return f"<KillRecord(id={self.id}, system={self.system_id})>"


class CacheEntry(Base):
    """Generic cache storage for API responses."""

    __tablename__ = "cache_entries"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (Index("ix_cache_entries_expires", "expires_at"),)

    def __repr__(self) -> str:
        return f"<CacheEntry(key={self.key})>"


class RouteBookmark(Base):
    """Saved route bookmarks for quick access."""

    __tablename__ = "route_bookmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    from_system: Mapped[str] = mapped_column(String(100), nullable=False)
    to_system: Mapped[str] = mapped_column(String(100), nullable=False)
    profile: Mapped[str] = mapped_column(String(50), default="shortest")
    avoid_systems: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    use_bridges: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_route_bookmarks_character", "character_id"),
        Index("ix_route_bookmarks_from_to", "from_system", "to_system"),
    )

    def __repr__(self) -> str:
        return f"<RouteBookmark(id={self.id}, name={self.name})>"


class Subscription(Base):
    """User subscription for premium features."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False)  # "monthly" or "annual"
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="inactive"
    )  # active, canceled, past_due, inactive
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_subscriptions_character", "character_id"),
        Index("ix_subscriptions_stripe_customer", "stripe_customer_id"),
    )

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, character_id={self.character_id}, status={self.status})>"
