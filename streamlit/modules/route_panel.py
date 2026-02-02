"""Route calculation UI components."""

from __future__ import annotations

import streamlit as st

from .config import ROUTING_PROFILES


def render_system_selector(
    label: str,
    system_names: list[str],
    key: str,
    default: str | None = None,
) -> str | None:
    """
    Render system search/select dropdown.

    Args:
        label: Label for the select box
        system_names: List of all system names
        key: Unique Streamlit key
        default: Default system name

    Returns:
        Selected system name or None
    """
    # Find default index
    default_idx = 0
    if default and default in system_names:
        default_idx = system_names.index(default)

    selected = st.selectbox(
        label,
        options=system_names,
        index=default_idx,
        key=key,
        placeholder="Search for a system...",
    )
    return selected


def render_route_controls(system_names: list[str]) -> dict:
    """
    Render sidebar route input controls.

    Args:
        system_names: List of all system names

    Returns:
        Dict with origin, destination, profile, and options
    """
    st.sidebar.header("Route Planner")

    # Get current values from session state for click-to-select
    default_origin = st.session_state.get("origin_system", "Jita")
    default_dest = st.session_state.get("dest_system", "Amarr")

    origin = render_system_selector(
        "Origin",
        system_names,
        "origin_select",
        default=default_origin if default_origin in system_names else "Jita",
    )

    destination = render_system_selector(
        "Destination",
        system_names,
        "dest_select",
        default=default_dest if default_dest in system_names else "Amarr",
    )

    st.sidebar.divider()

    profile = st.sidebar.radio(
        "Routing Profile",
        options=list(ROUTING_PROFILES.keys()),
        format_func=lambda p: f"{p.capitalize()} - {ROUTING_PROFILES[p]}",
        key="profile_select",
    )

    st.sidebar.divider()

    calculate = st.sidebar.button(
        "Calculate Route",
        type="primary",
        use_container_width=True,
        key="calculate_btn",
    )

    return {
        "origin": origin,
        "destination": destination,
        "profile": profile,
        "calculate": calculate,
    }


def render_route_stats(route_response) -> None:
    """
    Render route statistics summary.

    Args:
        route_response: RouteResponse from compute_route
    """
    st.sidebar.divider()
    st.sidebar.subheader("Route Stats")

    # Key metrics
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Total Jumps", route_response.total_jumps)
    col2.metric("Max Risk", f"{route_response.max_risk:.1f}")

    col3, col4 = st.sidebar.columns(2)
    col3.metric("Avg Risk", f"{route_response.avg_risk:.1f}")
    col4.metric("Profile", route_response.profile.capitalize())

    # Security breakdown
    st.sidebar.caption("Security Breakdown")
    highsec = sum(1 for h in route_response.path if h.risk_score < 25)
    lowsec = sum(1 for h in route_response.path if 25 <= h.risk_score < 50)
    nullsec = sum(1 for h in route_response.path if h.risk_score >= 50)

    breakdown_cols = st.sidebar.columns(3)
    breakdown_cols[0].markdown(f"🟢 **{highsec}** High")
    breakdown_cols[1].markdown(f"🟡 **{lowsec}** Low")
    breakdown_cols[2].markdown(f"🔴 **{nullsec}** Null")


def render_route_table(route_response, universe) -> None:
    """
    Render hop-by-hop route details table.

    Args:
        route_response: RouteResponse from compute_route
        universe: Universe data for system details
    """
    st.subheader("Route Details")

    # Build table data
    table_data = []
    for i, hop in enumerate(route_response.path):
        system = universe.systems.get(hop.system_name)
        security = system.security if system else 0.0
        region = system.region_name if system else "Unknown"

        # Risk indicator
        if hop.risk_score < 10:
            risk_indicator = "🟢"
        elif hop.risk_score < 25:
            risk_indicator = "🟡"
        elif hop.risk_score < 50:
            risk_indicator = "🟠"
        else:
            risk_indicator = "🔴"

        # Connection type indicator
        conn_type = hop.connection_type
        if conn_type == "bridge":
            conn_icon = "🌉"
        elif conn_type == "thera":
            conn_icon = "🕳️"
        elif conn_type == "pochven":
            conn_icon = "⚡"
        else:
            conn_icon = "→" if i > 0 else "📍"

        table_data.append(
            {
                "#": i,
                "": conn_icon,
                "System": hop.system_name,
                "Security": f"{security:.2f}",
                "Region": region,
                "Risk": f"{risk_indicator} {hop.risk_score:.1f}",
            }
        )

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "#": st.column_config.NumberColumn(width="small"),
            "": st.column_config.TextColumn(width="small"),
            "System": st.column_config.TextColumn(width="medium"),
            "Security": st.column_config.TextColumn(width="small"),
            "Region": st.column_config.TextColumn(width="medium"),
            "Risk": st.column_config.TextColumn(width="small"),
        },
    )


def render_danger_warning(route_response) -> None:
    """Show warning for dangerous systems in route."""
    dangerous_systems = [
        hop.system_name for hop in route_response.path if hop.risk_score >= 50
    ]

    if dangerous_systems:
        st.warning(
            f"⚠️ **{len(dangerous_systems)} dangerous systems** in route: "
            f"{', '.join(dangerous_systems[:5])}"
            f"{'...' if len(dangerous_systems) > 5 else ''}"
        )
