# EVE Gatekeeper - Streamlit MVP

Route planner with danger overlay for EVE Online. Validation frontend for the Gatekeeper backend.

## Features

- **Interactive Universe Map**: 5432 systems rendered with Plotly
- **Security Colors**: Systems colored by security status (green=high, orange=low, red=null)
- **Risk Overlay**: Toggle to show danger levels instead of raw security
- **Route Planning**: Calculate routes with shortest/safer/paranoid profiles
- **Click-to-Select**: Click systems on map to set origin/destination
- **Route Details**: Hop-by-hop breakdown with risk scores

## Quick Start

```bash
# From EVE_Gatekeeper root - MUST use parent .venv (has backend deps)
source .venv/bin/activate

# Install streamlit-specific deps
pip install -r streamlit/requirements.txt

# Run the app
cd streamlit
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Architecture

Uses backend modules directly (no FastAPI required):

```
streamlit/
├── app.py              # Main entry point
├── requirements.txt    # Streamlit-specific deps
├── modules/
│   ├── config.py       # Colors, constants
│   ├── map_renderer.py # Plotly universe map
│   └── route_panel.py  # UI components
└── README.md
```

## Usage

1. **Set Origin/Destination**: Use dropdowns or click on map
2. **Choose Profile**:
   - Shortest: Minimum jumps, ignores danger
   - Safer: Balances distance vs risk
   - Paranoid: Prioritizes avoiding dangerous systems
3. **Click Calculate**: View route on map and details table

## Map Controls

- **Pan**: Click and drag
- **Zoom**: Scroll wheel
- **Click**: Set origin/destination (toggle with sidebar radio)
- **Hover**: System details tooltip

## Deferred Features

Not in MVP scope:
- Live zKillboard data (uses static/cached)
- Jump bridges
- Thera wormholes
- Pochven filaments
- Multi-waypoint routes
- System avoidance lists

## Development

```bash
# Lint
ruff check .

# Format
ruff format .
```
