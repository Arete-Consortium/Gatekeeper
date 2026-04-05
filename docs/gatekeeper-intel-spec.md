# Gatekeeper — Intel Enhancement Spec
**Version:** 1.0  
**Date:** 2026-03-11  
**Scope:** Five targeted enhancements derived from EVE-Prism feature analysis, integrated into existing Gatekeeper architecture.

---

## Context

Gatekeeper is an operational decision-support tool for active play: route planning, live intel, and situational awareness. The following specs extend the existing Intel page (Kill Feed / Intel Parser / Fleet / Alerts tabs) and Route Planner without introducing scope creep or redundancy with Sentinel.

All enhancements use the existing `shared/esi/` client. No new external dependencies required.

---

## Enhancement 1 — Pilot Threat Card

**Where:** Kill Feed tab — click any pilot name  
**Also surfaces in:** Intel Parser results, Fleet tab pilot list

### What It Does
A flyout card that loads on pilot name click. Answers the single most important question in EVE: *"Should I engage this person?"*

### Data Points (all available via ESI + zKillboard)
| Field | Source | Notes |
|---|---|---|
| Portrait + name | ESI `/characters/{id}/` | |
| Corp / Alliance | ESI `/characters/{id}/` | Clickable → Corp Card |
| Security status | ESI `/characters/{id}/` | Color-coded |
| Mass Balance score | Computed from zKill data | See formula below |
| Active timezone | Computed from kill timestamps | Peak activity window |
| Cyno flag | zKill loss history | Has lost cynos? Flies them? |
| Awox flag | Kill history | Has killed own corp members? |
| Last active system | zKill recent kills | |
| Solo / fleet ratio | zKill aggregates | |
| Threat rating | Composite | Color-coded: Green / Yellow / Red |

### Mass Balance Formula
```
for each killmail:
    pilot_share += ship_mass / num_attackers   # kills
    pilot_loss  += ship_mass                   # losses (T2 ×2, T3 ×3)
    # logi/command ships excluded from loss side if specialized modules fitted

mass_balance = pilot_share / pilot_loss
# >1.0 = net destroyer. <1.0 = net feeder. 1.0 = neutral.
```

### UI Behavior
- Opens as a side panel or modal — does not navigate away from kill feed
- Loads in <500ms target (ESI data cached via existing ETag client)
- "Add to Watchlist" action (feeds into Alerts tab)
- "View in zKillboard" external link

### ESI Endpoints
- `GET /characters/{character_id}/`
- `GET /characters/{character_id}/corporationhistory/`
- zKillboard API: `https://zkillboard.com/api/stats/characterID/{id}/`

---

## Enhancement 2 — System Summary Card

**Where:** Kill Feed tab — click any system name  
**Also surfaces in:** Map hover/click, Route Planner waypoints, Hot Systems panel

### What It Does
Contextual system card that answers: *"What am I flying into?"*

### Data Points
| Field | Source |
|---|---|
| System name, security, region | ESI SDE |
| Controlling alliance (sov) | ESI `/sovereignty/map/` |
| Most active organizations (last 24hr) | zKill aggregates |
| Recent fleet compositions seen | zKill killmails |
| Ship kills / pod kills (1hr / 6hr / 24hr) | ESI `/universe/system_kills/` |
| Gate jumps | ESI `/universe/system_jumps/` |
| NPC kills | ESI `/universe/system_kills/` |
| Structures (Keepstar, Fortizar, etc.) | ESI `/universe/structures/` |
| Route to nearest trade hub | Existing Route Planner logic |

### UI Behavior
- Same flyout pattern as Pilot Card — consistent UX
- "Avoid this system" button → pushes directly to Route Planner avoid list
- Activity sparkline for last 24hr (kills over time)
- Color-coded threat level based on kill rate vs. baseline

---

## Enhancement 3 — Threats Tab (Operative Report)

**Where:** New tab in Intel page — `Kill Feed | Intel Parser | Fleet | Alerts | Threats`

### What It Does
Prism's Operative Report, integrated with Gatekeeper's route context. Answers: *"Where is the danger right now, and where is it going?"*

### Layout
```
[ Time Range: 1hr | 6hr | 24hr ]   [ Sec: All | Null | Low | High ]   [ Show: Top 10 | 25 | 50 ]

Hot Systems Table:
  System | Region | Sec | Kills (current) | Trend | Predicted (+1hr) | Predicted (+2hr) | Action

[ Map overlay toggle: show hotzone heatmap on main map ]
```

### Prediction Model
Simple — not ML. Use rolling averages:
```
baseline = avg kills per hour over last 7 days for this system
current  = kills in last 1hr
trend    = current / baseline  # >1.5 = heating up, <0.5 = cooling

predicted_1hr = current * trend_decay_factor (0.7)
predicted_2hr = predicted_1hr * trend_decay_factor (0.7)
```
This matches Prism's approach and is defensible without overclaiming precision.

### Route Integration
- Each hot system row has "Avoid" button → adds to Route Planner avoid list instantly
- If a system on the user's current planned route appears in the top 25 — surface a warning banner on the Route page

### ESI Endpoints
- `GET /universe/system_kills/` (poll every 60s — ESI cache window)
- `GET /universe/system_jumps/`
- zKillboard for historical baseline

---

## Enhancement 4 — Fleet Tab: Pilot Name Lookup

**Where:** Existing Fleet tab — extend current ship-count paste analyzer

### What It Changes
Currently: paste ship types → get threat assessment of fleet composition.  
After: paste pilot names from EVE fleet window → get **aggregate pilot threat assessment**.

### New Input Mode
```
[ Ship Composition ]  [ Pilot Names ]   ← add second input mode toggle

Paste from EVE fleet window (F1 → pilots list) or type names manually.
```

### Output (Pilot Names mode)
- Individual threat cards for each pilot (same card as Enhancement 1)
- Aggregate stats: avg mass balance, timezone cluster, cyno count in fleet, known awoxers flagged
- "Danger pilots" surfaced at top — anyone Red-flagged
- Overall fleet threat rating

### Notes
- Name → character ID lookup via ESI `/characters/?names=` (batch endpoint, efficient)
- Cache pilot profiles aggressively — 24hr TTL is fine for historical stats
- This makes Fleet tab significantly more valuable than Prism's fleet optimizer, which required CEO API access. This works with zero corp auth.

---

## Enhancement 5 — Alerts Tab: Hotzone Subscription

**Where:** Existing Alerts tab — add new subscription type alongside Kill Alerts

### What It Adds
Currently: Kill Alerts only (Discord/Slack webhook, filtered by system/region/value/ship type).  
After: add **Hotzone Alerts** subscription type.

### New Subscription Type: Hotzone Alert
```
Alert Name (optional)
Webhook URL + Type (Discord/Slack) — reuse existing field
Trigger: [ System exceeds X kills/hr ] OR [ System appears in Top 25 hotzones ]
Scope: [ Specific systems ] | [ Region ] | [ On my active route ]
Cooldown: [ 15min | 1hr | 4hr ]  ← prevent spam
```

### "On My Active Route" Trigger
This is the high-value addition. If the user has a route planned in the Route Planner, a Hotzone Alert scoped to that route will fire when any waypoint system enters the danger threshold. Practical use case: you set a route for a freighter run, go AFK for 30 min, get pinged when Uedama heats up.

### Route Planner Integration
- Route Planner gets a passive indicator: systems on route that are currently in the hot list show a warning icon
- No new UI needed beyond the icon — the Threats tab and Alerts tab do the heavy lifting

---

## Implementation Order

| Priority | Enhancement | Effort | Value | Dependency |
|---|---|---|---|---|
| 1 | Pilot Threat Card | Medium | Highest | zKill API integration |
| 2 | System Summary Card | Low | High | Shares data layer with #1 |
| 3 | Threats Tab | Medium | High | Hot Systems panel already exists — extend it |
| 4 | Alerts: Hotzone Subscription | Low | High | Threats tab data layer |
| 5 | Fleet: Pilot Name Lookup | Medium | Medium | Pilot Threat Card (#1) |

Enhancements 2 and 4 are largely free once #1 and #3 are built — they reuse the same data layer. Build #1 and #3 first, the rest falls out.

---

## Shared Data Layer

All five enhancements draw from the same two sources. Build these once, use everywhere:

```python
# shared/esi/intel.py

async def get_pilot_stats(character_id: int) -> PilotStats:
    """ESI character data + zKill aggregates. Cached 24hr."""

async def get_system_activity(system_id: int, hours: int = 24) -> SystemActivity:
    """ESI kills/jumps + zKill recent mails. Cached 60s."""

async def get_hotzone_systems(limit: int = 50) -> list[HotzoneSystem]:
    """Top systems by kill rate with trend calculation. Cached 60s."""
```

Single cache layer (Redis or simple in-memory with TTL) prevents redundant ESI calls across all five features.

---

## What This Gives You vs. Prism

| Capability | Prism | Gatekeeper (after) |
|---|---|---|
| Pilot profiling | ✅ Deep | ✅ Deep + integrated into workflow |
| System intelligence | ✅ | ✅ + route integration |
| Hotzone prediction | ✅ +2hr | ✅ +2hr + route warnings + push alerts |
| Fleet assessment | ✅ CEO API required | ✅ Zero auth required |
| Route awareness | ❌ | ✅ Native |
| Push notifications | ❌ | ✅ Discord/Slack |
| Still alive | ❌ | ✅ |

Gatekeeper ends up doing everything Prism did operationally, plus route-awareness that Prism never had, plus push notifications Prism never had — without requiring CEO API keys.
