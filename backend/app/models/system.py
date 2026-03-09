from pydantic import BaseModel


class Position(BaseModel):
    x: float
    y: float


class System(BaseModel):
    name: str
    id: int
    region_id: int
    region_name: str = ""
    constellation_id: int = 0
    constellation_name: str = ""
    security: float
    category: str  # highsec, lowsec, nullsec, wh
    position: Position
    # Station data for jump planning (cyno lighting)
    has_npc_station: bool = False
    station_count: int = 0
    # SDE classification flags
    hub: bool = False
    border: bool = False
    corridor: bool = False
    fringe: bool = False
    luminosity: float = 0.0
    # Star data
    spectral_class: str = "G"
    # NPC station count
    npc_stations: int = 0


class Gate(BaseModel):
    from_system: str
    to_system: str
    distance: float = 1.0


class UniverseMetadata(BaseModel):
    version: str
    source: str
    last_updated: str


class Universe(BaseModel):
    metadata: UniverseMetadata
    systems: dict[str, System]
    gates: list[Gate]


class SystemSummary(BaseModel):
    name: str
    security: float
    category: str
    region_id: int
    region_name: str = ""
    constellation_id: int = 0
    constellation_name: str = ""


class SystemListResponse(BaseModel):
    """Paginated response for system list."""

    items: list[SystemSummary]
    pagination: "PaginationMeta"

    model_config = {"from_attributes": True}


# Avoid circular import - import at end
from ..core.pagination import PaginationMeta  # noqa: E402

SystemListResponse.model_rebuild()
