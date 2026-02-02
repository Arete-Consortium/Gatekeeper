"""Plotly-based universe map renderer."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .config import MAP_CONFIG, get_risk_color, get_security_color


def create_universe_dataframe(universe) -> pd.DataFrame:
    """Convert universe data to DataFrame for Plotly."""
    records = []
    for name, system in universe.systems.items():
        records.append(
            {
                "name": name,
                "id": system.id,
                "x": system.position.x,
                "y": system.position.y,
                "security": system.security,
                "category": system.category,
                "region": system.region_name,
                "constellation": system.constellation_name,
            }
        )
    return pd.DataFrame(records)


def create_universe_map(
    df: pd.DataFrame,
    route_systems: list[str] | None = None,
    route_risks: dict[str, float] | None = None,
    overlay_mode: str = "security",
) -> go.Figure:
    """
    Create interactive Plotly scatter map of EVE universe.

    Args:
        df: DataFrame with system data (name, x, y, security, etc.)
        route_systems: List of system names in route order
        route_risks: Dict mapping system name to risk score
        overlay_mode: "security" or "risk"

    Returns:
        Plotly Figure object
    """
    route_systems = route_systems or []
    route_risks = route_risks or {}
    route_set = set(route_systems)

    # Color systems based on overlay mode
    if overlay_mode == "risk" and route_risks:
        df["color"] = df["name"].apply(
            lambda n: get_risk_color(route_risks.get(n, 0))
            if n in route_risks
            else get_security_color(df[df["name"] == n]["security"].iloc[0])
        )
    else:
        df["color"] = df["security"].apply(get_security_color)

    # Separate route and non-route systems for different styling
    df_background = df[~df["name"].isin(route_set)]
    df_route = df[df["name"].isin(route_set)]

    fig = go.Figure()

    # Background systems (smaller, dimmer)
    fig.add_trace(
        go.Scatter(
            x=df_background["x"],
            y=df_background["y"],
            mode="markers",
            marker=dict(
                size=MAP_CONFIG["marker_size"],
                color=df_background["color"],
                opacity=0.4,
            ),
            text=df_background.apply(
                lambda r: f"<b>{r['name']}</b><br>"
                f"Security: {r['security']:.2f}<br>"
                f"Region: {r['region']}",
                axis=1,
            ),
            hovertemplate="%{text}<extra></extra>",
            name="Systems",
            customdata=df_background["name"],
        )
    )

    # Route systems (larger, brighter)
    if not df_route.empty:
        # Reorder df_route to match route_systems order
        route_order = {name: i for i, name in enumerate(route_systems)}
        df_route = df_route.copy()
        df_route["route_order"] = df_route["name"].map(route_order)
        df_route = df_route.sort_values("route_order")

        fig.add_trace(
            go.Scatter(
                x=df_route["x"],
                y=df_route["y"],
                mode="markers",
                marker=dict(
                    size=MAP_CONFIG["route_marker_size"],
                    color=df_route["color"],
                    line=dict(width=1, color="white"),
                ),
                text=df_route.apply(
                    lambda r: f"<b>{r['name']}</b><br>"
                    f"Security: {r['security']:.2f}<br>"
                    f"Region: {r['region']}<br>"
                    f"Risk: {route_risks.get(r['name'], 0):.1f}",
                    axis=1,
                ),
                hovertemplate="%{text}<extra></extra>",
                name="Route",
                customdata=df_route["name"],
            )
        )

        # Route line connecting systems
        fig.add_trace(
            go.Scatter(
                x=df_route["x"],
                y=df_route["y"],
                mode="lines",
                line=dict(
                    width=MAP_CONFIG["route_line_width"],
                    color="#FFFFFF",
                    dash="solid",
                ),
                hoverinfo="skip",
                name="Route Path",
            )
        )

    # Layout
    fig.update_layout(
        plot_bgcolor=MAP_CONFIG["background_color"],
        paper_bgcolor=MAP_CONFIG["background_color"],
        width=MAP_CONFIG["width"],
        height=MAP_CONFIG["height"],
        showlegend=False,
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="y",
            scaleratio=1,
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        dragmode="pan",
    )

    return fig


def create_route_detail_map(
    df: pd.DataFrame,
    route_systems: list[str],
    route_risks: dict[str, float],
    padding: float = 2.0,
) -> go.Figure:
    """
    Create zoomed-in map focused on route systems.

    Args:
        df: Universe DataFrame
        route_systems: Ordered list of systems in route
        route_risks: Risk scores for route systems
        padding: Extra space around route bounds

    Returns:
        Plotly Figure zoomed to route area
    """
    fig = create_universe_map(df, route_systems, route_risks, overlay_mode="risk")

    # Calculate bounds of route systems
    route_df = df[df["name"].isin(route_systems)]
    if not route_df.empty:
        x_min, x_max = route_df["x"].min(), route_df["x"].max()
        y_min, y_max = route_df["y"].min(), route_df["y"].max()

        # Add padding
        x_range = max(x_max - x_min, 1.0)
        y_range = max(y_max - y_min, 1.0)
        x_pad = x_range * padding / 10
        y_pad = y_range * padding / 10

        fig.update_xaxes(range=[x_min - x_pad, x_max + x_pad])
        fig.update_yaxes(range=[y_min - y_pad, y_max + y_pad])

    return fig
