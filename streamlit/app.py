"""EVE Gatekeeper Streamlit MVP - Route Planner with Danger Overlay."""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend to path for direct imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Backend imports (must be after path setup)
from app.services.data_loader import load_universe  # noqa: E402
from app.services.routing import compute_route  # noqa: E402

# Local modules
from modules.config import UI_CONFIG  # noqa: E402
from modules.map_renderer import create_universe_dataframe, create_universe_map  # noqa: E402
from modules.route_panel import (  # noqa: E402
    render_danger_warning,
    render_route_controls,
    render_route_stats,
    render_route_table,
)
from streamlit_plotly_events import plotly_events  # noqa: E402

import streamlit as st  # noqa: E402

# Page config
st.set_page_config(
    page_title=UI_CONFIG["page_title"],
    page_icon=UI_CONFIG["page_icon"],
    layout=UI_CONFIG["layout"],
)


@st.cache_data(ttl=3600)
def load_data():
    """Load and cache universe data."""
    universe = load_universe()
    df = create_universe_dataframe(universe)
    system_names = sorted(df["name"].tolist())
    return universe, df, system_names


def main():
    """Main app entry point."""
    st.title("EVE Gatekeeper")
    st.caption("Route planner with danger overlay")

    # Load data
    universe, df, system_names = load_data()

    # Initialize session state
    if "route_result" not in st.session_state:
        st.session_state.route_result = None
    if "origin_system" not in st.session_state:
        st.session_state.origin_system = "Jita"
    if "dest_system" not in st.session_state:
        st.session_state.dest_system = "Amarr"
    if "click_mode" not in st.session_state:
        st.session_state.click_mode = "origin"

    # Sidebar controls
    controls = render_route_controls(system_names)

    # Click mode toggle in sidebar
    st.sidebar.divider()
    st.sidebar.caption("Click on map to set:")
    click_mode = st.sidebar.radio(
        "Select mode",
        ["origin", "destination"],
        key="click_mode_radio",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.click_mode = click_mode

    # Overlay toggle
    st.sidebar.divider()
    overlay_mode = st.sidebar.radio(
        "Map Overlay",
        ["security", "risk"],
        format_func=lambda x: x.capitalize(),
        horizontal=True,
    )

    # Calculate route
    if controls["calculate"]:
        if controls["origin"] and controls["destination"]:
            if controls["origin"] == controls["destination"]:
                st.sidebar.error("Origin and destination must be different")
            else:
                try:
                    route = compute_route(
                        controls["origin"],
                        controls["destination"],
                        profile=controls["profile"],
                    )
                    st.session_state.route_result = route
                    st.session_state.origin_system = controls["origin"]
                    st.session_state.dest_system = controls["destination"]
                except ValueError as e:
                    st.sidebar.error(str(e))
        else:
            st.sidebar.error("Select both origin and destination")

    # Get route data for display
    route = st.session_state.route_result
    route_systems = []
    route_risks = {}

    if route:
        route_systems = [hop.system_name for hop in route.path]
        route_risks = {hop.system_name: hop.risk_score for hop in route.path}
        render_route_stats(route)

    # Main area: Map
    st.subheader("Universe Map")

    # Create map figure
    fig = create_universe_map(
        df,
        route_systems=route_systems,
        route_risks=route_risks,
        overlay_mode=overlay_mode,
    )

    # Render interactive map
    selected_points = plotly_events(
        fig,
        click_event=True,
        key="universe_map",
    )

    # Handle click-to-select
    if selected_points:
        point = selected_points[0]
        point_idx = point.get("pointIndex")
        curve_number = point.get("curveNumber", 0)

        # Determine which trace was clicked
        if curve_number == 0:
            # Background systems trace
            non_route_df = df[~df["name"].isin(route_systems)]
            if point_idx is not None and point_idx < len(non_route_df):
                clicked_system = non_route_df.iloc[point_idx]["name"]
                if st.session_state.click_mode == "origin":
                    st.session_state.origin_system = clicked_system
                    st.toast(f"Origin set to {clicked_system}")
                else:
                    st.session_state.dest_system = clicked_system
                    st.toast(f"Destination set to {clicked_system}")
                st.rerun()
        elif curve_number == 1 and route_systems:
            # Route systems trace
            if point_idx is not None and point_idx < len(route_systems):
                clicked_system = route_systems[point_idx]
                if st.session_state.click_mode == "origin":
                    st.session_state.origin_system = clicked_system
                    st.toast(f"Origin set to {clicked_system}")
                else:
                    st.session_state.dest_system = clicked_system
                    st.toast(f"Destination set to {clicked_system}")
                st.rerun()

    # Route details
    if route:
        render_danger_warning(route)
        render_route_table(route, universe)

    # Footer
    st.divider()
    st.caption(
        f"Data: {universe.metadata.system_count} systems | "
        f"Last updated: {universe.metadata.last_updated}"
    )


if __name__ == "__main__":
    main()
