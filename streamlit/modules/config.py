"""Configuration constants for Gatekeeper Streamlit app."""

# Security status colors (matching EVE in-game)
SECURITY_COLORS = {
    1.0: "#2E8B57",  # High: Deep green
    0.9: "#2E8B57",
    0.8: "#3CB371",
    0.7: "#3CB371",
    0.6: "#90EE90",
    0.5: "#90EE90",  # High-Low boundary
    0.4: "#FFA500",  # Low: Orange
    0.3: "#FFA500",
    0.2: "#FF4500",
    0.1: "#FF4500",
    0.0: "#DC143C",  # Null: Crimson
    -0.1: "#DC143C",
    -0.5: "#8B0000",  # Deep null: Dark red
    -1.0: "#8B0000",
}

# Risk score colors (from risk_config.json)
RISK_COLORS = {
    (0, 10): "#3AF57A",  # Safe: Bright green
    (10, 25): "#A6F53A",  # Caution: Yellow-green
    (25, 50): "#F5D33A",  # Warning: Gold
    (50, 75): "#F58C3A",  # Dangerous: Orange
    (75, 100): "#F53A3A",  # Deadly: Red
}

# Routing profiles
ROUTING_PROFILES = {
    "shortest": "Shortest path (ignore danger)",
    "safer": "Balance jumps vs safety",
    "paranoid": "Prioritize safety over distance",
}

# Map display settings
MAP_CONFIG = {
    "width": 900,
    "height": 700,
    "marker_size": 4,
    "route_marker_size": 8,
    "route_line_width": 2,
    "background_color": "#0E1117",  # Streamlit dark theme
    "grid_color": "#1F2937",
}

# UI Constants
UI_CONFIG = {
    "page_title": "EVE Gatekeeper",
    "page_icon": "🚀",
    "layout": "wide",
}


def get_security_color(security: float) -> str:
    """Get hex color for security status."""
    if security >= 0.9:
        return "#2E8B57"
    elif security >= 0.7:
        return "#3CB371"
    elif security >= 0.5:
        return "#90EE90"
    elif security >= 0.3:
        return "#FFA500"
    elif security > 0.0:
        return "#FF4500"
    elif security > -0.5:
        return "#DC143C"
    else:
        return "#8B0000"


def get_risk_color(score: float) -> str:
    """Get hex color for risk score."""
    for (low, high), color in RISK_COLORS.items():
        if low <= score <= high:
            return color
    return "#FFFFFF"


def get_security_category(security: float) -> str:
    """Get security category from status."""
    if security >= 0.5:
        return "highsec"
    elif security > 0.0:
        return "lowsec"
    else:
        return "nullsec"
