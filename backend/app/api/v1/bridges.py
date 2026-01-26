"""Jump bridge API v1 endpoints."""

from fastapi import APIRouter, HTTPException, Query

from ...models.jumpbridge import (
    BridgeValidationResult,
    BulkBridgeRequest,
    BulkBridgeResponse,
    JumpBridge,
    JumpBridgeAddRequest,
    JumpBridgeConfig,
    JumpBridgeImportRequest,
    JumpBridgeImportResponse,
    JumpBridgeNetwork,
    JumpBridgeStats,
)
from ...services.jumpbridge import (
    add_bridge,
    bulk_add_bridges,
    bulk_remove_bridges,
    clear_bridge_cache,
    delete_network,
    get_bridge_route_info,
    get_bridge_stats,
    import_bridges,
    load_bridge_config,
    remove_bridge,
    toggle_network,
    validate_bridge,
    validate_network,
)

router = APIRouter()


@router.get(
    "/",
    response_model=JumpBridgeConfig,
    summary="List all jump bridge networks",
    description="Returns all configured jump bridge networks and their bridges.",
)
def list_networks() -> JumpBridgeConfig:
    """Get all jump bridge networks."""
    return load_bridge_config()


@router.post(
    "/import",
    response_model=JumpBridgeImportResponse,
    summary="Import jump bridges",
    description="Import jump bridges from text format.",
)
def import_bridge_network(
    request: JumpBridgeImportRequest,
    replace: bool = Query(
        True,
        description="Replace existing network (true) or merge (false)",
    ),
) -> JumpBridgeImportResponse:
    """
    Import jump bridges from text format.

    Supported formats:
    - "System1 <-> System2" (bidirectional)
    - "System1 --> System2" (also bidirectional - bridges are always 2-way)
    - "System1 - System2" (simple format)

    Lines starting with # are ignored as comments.

    Example:
    ```
    # Delve bridges
    1DQ1-A <-> 8QT-H4
    49-U6U <-> PUIG-F
    ```
    """
    clear_bridge_cache()
    return import_bridges(
        network_name=request.network_name,
        bridge_text=request.bridge_text,
        replace=replace,
    )


@router.get(
    "/stats",
    response_model=JumpBridgeStats,
    summary="Get jump bridge statistics",
    description="Returns statistics about all jump bridge networks.",
)
def get_stats() -> JumpBridgeStats:
    """Get statistics about jump bridge networks."""
    return get_bridge_stats()


@router.get(
    "/route-compare",
    summary="Compare routes with and without bridges",
    description="Show how bridges affect routing between two systems.",
)
def compare_bridge_routes(
    from_system: str = Query(..., description="Origin system name"),
    to_system: str = Query(..., description="Destination system name"),
) -> dict:
    """
    Compare routing with and without jump bridges.

    Shows:
    - Route length without bridges
    - Route length with bridges
    - Number of jumps saved
    - Number of bridges used
    """
    return get_bridge_route_info(from_system, to_system)


@router.get(
    "/validate",
    summary="Validate a single bridge",
    description="Check if a bridge connection is valid according to game rules.",
)
def validate_single_bridge(
    from_system: str = Query(..., description="Origin system name"),
    to_system: str = Query(..., description="Destination system name"),
) -> dict:
    """
    Validate a single bridge connection.

    Checks:
    - Both systems exist
    - Systems are different
    - Neither system is highsec (Ansiblex cannot be anchored)
    - Neither system is wormhole space
    - Warning if cross-region
    """
    issues = validate_bridge(from_system, to_system)
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    return {
        "valid": len(errors) == 0,
        "from_system": from_system,
        "to_system": to_system,
        "errors": [i.issue for i in errors],
        "warnings": [i.issue for i in warnings],
    }


@router.patch(
    "/{network_name}",
    summary="Toggle network status",
    description="Enable or disable a jump bridge network.",
)
def toggle_bridge_network(
    network_name: str,
    enabled: bool = Query(..., description="Enable or disable the network"),
) -> dict:
    """Enable or disable a jump bridge network."""
    clear_bridge_cache()
    if toggle_network(network_name, enabled):
        return {"status": "ok", "network": network_name, "enabled": enabled}
    raise HTTPException(status_code=404, detail=f"Network '{network_name}' not found")


@router.delete(
    "/{network_name}",
    summary="Delete a network",
    description="Delete a jump bridge network entirely.",
)
def delete_bridge_network(network_name: str) -> dict:
    """Delete a jump bridge network."""
    clear_bridge_cache()
    if delete_network(network_name):
        return {"status": "ok", "deleted": network_name}
    raise HTTPException(status_code=404, detail=f"Network '{network_name}' not found")


@router.get(
    "/{network_name}",
    response_model=JumpBridgeNetwork,
    summary="Get a specific network",
    description="Returns details for a specific jump bridge network.",
)
def get_network(network_name: str) -> JumpBridgeNetwork:
    """Get a specific jump bridge network."""
    config = load_bridge_config()
    for network in config.networks:
        if network.name == network_name:
            return network
    raise HTTPException(status_code=404, detail=f"Network '{network_name}' not found")


@router.post(
    "/{network_name}/bridges",
    response_model=JumpBridge,
    status_code=201,
    summary="Add a single bridge",
    description="Add a single jump bridge to an existing network.",
)
def add_single_bridge(
    network_name: str,
    request: JumpBridgeAddRequest,
) -> JumpBridge:
    """Add a single jump bridge to a network."""
    clear_bridge_cache()
    success, message = add_bridge(
        network_name=network_name,
        from_system=request.from_system,
        to_system=request.to_system,
        structure_id=request.structure_id,
        owner=request.owner,
    )
    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=400, detail=message)
    return JumpBridge(
        from_system=request.from_system,
        to_system=request.to_system,
        structure_id=request.structure_id,
        owner=request.owner,
    )


@router.delete(
    "/{network_name}/bridges",
    summary="Remove a single bridge",
    description="Remove a single jump bridge from a network.",
)
def remove_single_bridge(
    network_name: str,
    from_system: str = Query(..., description="Origin system name"),
    to_system: str = Query(..., description="Destination system name"),
) -> dict:
    """Remove a single jump bridge from a network."""
    clear_bridge_cache()
    success, message = remove_bridge(
        network_name=network_name,
        from_system=from_system,
        to_system=to_system,
    )
    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=400, detail=message)
    return {"status": "ok", "removed": f"{from_system} <-> {to_system}"}


@router.get(
    "/{network_name}/validate",
    response_model=BridgeValidationResult,
    summary="Validate a network",
    description="Validate all bridges in a network against game rules.",
)
def validate_bridge_network(network_name: str) -> BridgeValidationResult:
    """
    Validate all bridges in a network.

    Returns validation issues including:
    - Highsec systems (error - cannot anchor Ansiblex)
    - Wormhole systems (error - cannot anchor Ansiblex)
    - Cross-region bridges (warning - unusual but valid)
    """
    return validate_network(network_name)


@router.post(
    "/{network_name}/bridges/bulk",
    response_model=BulkBridgeResponse,
    summary="Bulk add bridges",
    description="Add multiple bridges to a network in one request.",
)
def bulk_add_to_network(
    network_name: str,
    request: BulkBridgeRequest,
) -> BulkBridgeResponse:
    """Add multiple bridges to a network."""
    clear_bridge_cache()
    bridges = [(b.from_system, b.to_system, b.structure_id, b.owner) for b in request.bridges]
    return bulk_add_bridges(network_name, bridges)


@router.delete(
    "/{network_name}/bridges/bulk",
    response_model=BulkBridgeResponse,
    summary="Bulk remove bridges",
    description="Remove multiple bridges from a network in one request.",
)
def bulk_remove_from_network(
    network_name: str,
    request: BulkBridgeRequest,
) -> BulkBridgeResponse:
    """Remove multiple bridges from a network."""
    clear_bridge_cache()
    bridges = [(b.from_system, b.to_system) for b in request.bridges]
    return bulk_remove_bridges(network_name, bridges)
