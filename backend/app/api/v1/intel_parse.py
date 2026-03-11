"""Intel Chat Parser API v1 endpoints.

Provides an endpoint for parsing pasted intel/local chat text
and extracting system names with status indicators.
"""

from fastapi import APIRouter

from ...models.intel import IntelParseRequest, IntelParseResponse
from ...services.intel_chat_parser import parse_intel_text

router = APIRouter(prefix="/intel-parse", tags=["intel-parse"])


@router.post(
    "/parse",
    response_model=IntelParseResponse,
    summary="Parse intel chat text",
    description=(
        "Parse pasted EVE Online intel/local chat text. "
        "Extracts system names, status (clear/hostile/unknown), "
        "and hostile counts. Returns unknown lines that could not be parsed."
    ),
)
async def parse_intel_chat(request: IntelParseRequest) -> IntelParseResponse:
    """Parse intel/local chat text and extract system information."""
    return parse_intel_text(request.text)
