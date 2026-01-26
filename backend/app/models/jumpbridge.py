"""Pydantic models for Ansiblex jump bridges."""

from pydantic import BaseModel, Field


class JumpBridge(BaseModel):
    """A single Ansiblex jump bridge connection."""

    from_system: str = Field(..., description="Origin system name")
    to_system: str = Field(..., description="Destination system name")
    structure_id: int | None = Field(None, description="ESI structure ID if known")
    owner: str | None = Field(None, description="Alliance/corp that owns the bridge")


class JumpBridgeNetwork(BaseModel):
    """Collection of jump bridges for an alliance/network."""

    name: str = Field(..., description="Network name (e.g., alliance name)")
    bridges: list[JumpBridge] = Field(default_factory=list)
    enabled: bool = Field(True, description="Whether this network is active for routing")


class JumpBridgeConfig(BaseModel):
    """Jump bridge configuration with multiple networks."""

    networks: list[JumpBridgeNetwork] = Field(default_factory=list)

    def get_active_bridges(self) -> list[JumpBridge]:
        """Get all bridges from enabled networks."""
        bridges = []
        for network in self.networks:
            if network.enabled:
                bridges.extend(network.bridges)
        return bridges


class JumpBridgeImportRequest(BaseModel):
    """Request to import jump bridges from text format."""

    network_name: str = Field(..., description="Name for this bridge network")
    bridge_text: str = Field(
        ...,
        description="Jump bridge data in format: 'System1 --> System2' or 'System1 <-> System2' per line",
    )


class JumpBridgeImportResponse(BaseModel):
    """Response from importing jump bridges."""

    network_name: str
    bridges_imported: int
    bridges_skipped: int
    errors: list[str] = Field(default_factory=list)


class JumpBridgeAddRequest(BaseModel):
    """Request to add a single jump bridge."""

    from_system: str = Field(..., description="Origin system name")
    to_system: str = Field(..., description="Destination system name")
    structure_id: int | None = Field(None, description="ESI structure ID if known")
    owner: str | None = Field(None, description="Alliance/corp that owns the bridge")


class JumpBridgeStats(BaseModel):
    """Statistics about jump bridge networks."""

    total_networks: int
    active_networks: int
    total_bridges: int
    active_bridges: int
    systems_connected: int
    bridges_by_network: dict[str, int]


class BridgeValidationIssue(BaseModel):
    """A single validation issue for a bridge."""

    from_system: str
    to_system: str
    issue: str
    severity: str = Field(..., description="Severity level: 'error' or 'warning'")


class BridgeValidationResult(BaseModel):
    """Result of validating a bridge network."""

    network_name: str
    total_bridges: int
    valid_bridges: int
    issues: list[BridgeValidationIssue] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if there are any errors (warnings are ok)."""
        return not any(i.severity == "error" for i in self.issues)


class BulkBridgeRequest(BaseModel):
    """Request to add or remove multiple bridges."""

    bridges: list[JumpBridgeAddRequest] = Field(..., description="List of bridges to add/remove")


class BulkBridgeResponse(BaseModel):
    """Response from bulk bridge operation."""

    succeeded: int
    failed: int
    errors: list[str] = Field(default_factory=list)
