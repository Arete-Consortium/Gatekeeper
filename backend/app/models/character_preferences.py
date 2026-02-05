"""Character preferences models for multi-character support.

Stores per-character settings including:
- Routing preferences (default profile, avoided systems)
- UI preferences (default map view, theme)
- Alert settings (notifications, thresholds)
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class RoutingPreferences(BaseModel):
    """Routing preferences for a character."""

    default_profile: str = Field("safer", description="Default routing profile")
    avoid_systems: list[str] = Field(default_factory=list, description="Systems to always avoid")
    avoid_lists: list[str] = Field(
        default_factory=list, description="Named avoidance lists to apply"
    )
    use_bridges: bool = Field(False, description="Use Ansiblex bridges by default")
    use_thera: bool = Field(False, description="Use Thera wormholes by default")
    use_pochven: bool = Field(False, description="Use Pochven filaments by default")
    use_wormholes: bool = Field(False, description="Use user-submitted wormholes by default")


class AlertPreferences(BaseModel):
    """Alert preferences for a character."""

    enabled: bool = Field(True, description="Enable kill alerts")
    min_value_isk: float = Field(0, description="Minimum kill value for alerts")
    include_pods: bool = Field(True, description="Include pod kills in alerts")
    watch_systems: list[str] = Field(default_factory=list, description="Systems to watch for kills")
    watch_regions: list[str] = Field(default_factory=list, description="Regions to watch for kills")
    discord_webhook: str | None = Field(None, description="Discord webhook URL for alerts")
    slack_webhook: str | None = Field(None, description="Slack webhook URL for alerts")


class UIPreferences(BaseModel):
    """UI preferences for a character."""

    theme: str = Field("dark", description="UI theme (dark, light)")
    default_map_zoom: float = Field(1.0, description="Default map zoom level")
    show_risk_overlay: bool = Field(True, description="Show risk overlay on map")
    show_kills_overlay: bool = Field(True, description="Show kills overlay on map")
    compact_mode: bool = Field(False, description="Use compact UI mode on mobile")


class CharacterPreferences(BaseModel):
    """Complete preferences for a character."""

    character_id: int = Field(..., description="EVE character ID")
    character_name: str = Field(..., description="EVE character name")
    routing: RoutingPreferences = Field(default_factory=lambda: RoutingPreferences())
    alerts: AlertPreferences = Field(default_factory=lambda: AlertPreferences())
    ui: UIPreferences = Field(default_factory=lambda: UIPreferences())
    home_system: str | None = Field(None, description="Home system for routing")
    notes: str | None = Field(None, description="Personal notes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CharacterPreferencesUpdate(BaseModel):
    """Update model for character preferences (all fields optional)."""

    routing: RoutingPreferences | None = None
    alerts: AlertPreferences | None = None
    ui: UIPreferences | None = None
    home_system: str | None = None
    notes: str | None = None


class ActiveCharacterResponse(BaseModel):
    """Response model for active character info."""

    character_id: int
    character_name: str
    is_active: bool = True
    preferences: CharacterPreferences | None = None
    location: dict[str, Any] | None = None


class CharacterSwitchRequest(BaseModel):
    """Request to switch active character."""

    character_id: int = Field(..., description="Character ID to switch to")


class CharacterListResponse(BaseModel):
    """Response model for listing all characters."""

    characters: list[ActiveCharacterResponse]
    active_character_id: int | None = None
    total_count: int = 0
