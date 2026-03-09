from fastapi import APIRouter, HTTPException, Query

from ..models.route import RouteResponse
from ..services.data_loader import load_risk_config, load_universe
from ..services.risk_engine import compute_risk, risk_to_color
from ..services.routing import compute_route

router = APIRouter()


@router.get("/config")
async def map_config() -> dict:
    universe = load_universe()
    cfg = load_risk_config()

    systems_payload = {}
    for name, sys in universe.systems.items():
        risk = compute_risk(name)
        color = risk_to_color(risk.score)
        systems_payload[name] = {
            "id": sys.id,
            "region_id": sys.region_id,
            "region_name": sys.region_name,
            "constellation_id": sys.constellation_id,
            "constellation_name": sys.constellation_name,
            "security": sys.security,
            "category": sys.category,
            "position": sys.position.dict(),
            "risk_score": risk.score,
            "risk_color": color,
        }

    gates_payload = [
        {"from_system": g.from_system, "to_system": g.to_system}
        for g in universe.gates
    ]

    return {
        "metadata": universe.metadata.dict(),
        "systems": systems_payload,
        "gates": gates_payload,
        "layers": cfg.map_layers,
    }


@router.get("/route", response_model=RouteResponse)
def get_route(
    from_system: str = Query(..., alias="from"),
    to_system: str = Query(..., alias="to"),
    profile: str = Query("shortest"),
) -> RouteResponse:
    cfg = load_risk_config()
    if profile not in cfg.routing_profiles:
        raise HTTPException(status_code=400, detail=f"Unknown routing profile: {profile}")
    try:
        return compute_route(from_system, to_system, profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
