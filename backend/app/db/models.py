"""SQLAlchemy models for EVE Gatekeeper.

These models are designed for future database storage of universe data.
Currently, the app uses JSON files for data storage.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    """Registered user with subscription info."""

    __tablename__ = "users"

    character_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_name: Mapped[str] = mapped_column(String(100), nullable=False)
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free", nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User(character_id={self.character_id}, tier={self.subscription_tier})>"


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


class WormholeConnectionDB(Base):
    """User-submitted wormhole connection between two systems."""

    __tablename__ = "wormhole_connections"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    from_system: Mapped[str] = mapped_column(String(100), nullable=False)
    from_system_id: Mapped[int] = mapped_column(Integer, nullable=False)
    to_system: Mapped[str] = mapped_column(String(100), nullable=False)
    to_system_id: Mapped[int] = mapped_column(Integer, nullable=False)
    wormhole_type: Mapped[str] = mapped_column(String(20), nullable=False, default="UNKNOWN")
    mass_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    life_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    bidirectional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_lifetime_hours: Mapped[float] = mapped_column(Float, nullable=False, default=16.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_sig: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    to_sig: Mapped[str] = mapped_column(String(20), nullable=False, default="")

    __table_args__ = (
        Index("ix_wormhole_connections_from", "from_system"),
        Index("ix_wormhole_connections_to", "to_system"),
        Index("ix_wormhole_connections_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<WormholeConnectionDB(id={self.id}, {self.from_system} -> {self.to_system})>"


class JumpBridgeConnectionDB(Base):
    """User-submitted Ansiblex jump bridge connection between two systems."""

    __tablename__ = "jumpbridge_connections"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    from_system: Mapped[str] = mapped_column(String(100), nullable=False)
    from_system_id: Mapped[int] = mapped_column(Integer, nullable=False)
    to_system: Mapped[str] = mapped_column(String(100), nullable=False)
    to_system_id: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_alliance: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_jumpbridge_connections_from", "from_system"),
        Index("ix_jumpbridge_connections_to", "to_system"),
        Index("ix_jumpbridge_connections_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<JumpBridgeConnectionDB(id={self.id}, {self.from_system} \u00bb {self.to_system})>"


class WebhookSubscriptionDB(Base):
    """Persistent webhook subscription for kill alerts."""

    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    webhook_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    systems: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    regions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    include_pods: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ship_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WebhookSubscriptionDB(id={self.id}, type={self.webhook_type})>"


class KillHistoryRecord(Base):
    """Persisted kill history record (full kill data as JSON)."""

    __tablename__ = "kill_history"

    kill_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(Integer, nullable=False)
    region_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_pod: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index("ix_kill_history_system", "system_id"),
        Index("ix_kill_history_region", "region_id"),
        Index("ix_kill_history_received", "received_at"),
    )

    def __repr__(self) -> str:
        return f"<KillHistoryRecord(kill_id={self.kill_id}, system={self.system_id})>"


class PageviewRecord(Base):
    """Persisted pageview event for analytics."""

    __tablename__ = "pageviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    client_ip: Mapped[str] = mapped_column(String(45), nullable=False, default="unknown")
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_pageviews_path", "path"),
        Index("ix_pageviews_viewed_at", "viewed_at"),
    )

    def __repr__(self) -> str:
        return f"<PageviewRecord(id={self.id}, path={self.path})>"
