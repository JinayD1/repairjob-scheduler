"""
JSON-friendly views of the pipeline output, for the web server.

The web page never computes anything itself: it posts the pins and the
weight to the server, and this module turns the Python results into plain
dicts and lists that `json.dumps` can serialise. Three payloads:

    config_payload()                  the map, techs, presets, limits
    dispatch_payload(pins, w_dist)    run_dispatch() for a pin layout
    explore_payload(tech_index, cell) A* vs Dijkstra explored cells

JSON has no representation for infinity, so unreachable distances become
null here and the page treats null as "unreachable".
"""

import math
from typing import Any

from .astar import astar
from .config import (
    BRIDGES,
    BRUTE_FORCE_MAX_JOBS,
    DEMO_PINS,
    GREEDY_TRAP_PINS,
    MAX_JOBS,
    TECHNICIANS,
    build_city_grid,
    is_bridge_cell,
    is_river_cell,
    pins_to_jobs,
)
from .dijkstra import dijkstra
from .explain import UNASSIGNED_REASON_TEXT, explain_job, explain_optimal_job
from .pipeline import run_dispatch
from .scoring import DEFAULT_WEIGHTS
from .types import APPLIANCE_TYPES, Cell, Route, Weights

GRID = build_city_grid()


def _num(value: float):
    """inf -> None, so the value survives json.dumps."""
    return None if value is None or not math.isfinite(value) else value


def config_payload() -> dict[str, Any]:
    river = [[x, y] for y in range(GRID.height) for x in range(GRID.width) if is_river_cell((x, y))]
    bridges = [[x, y] for y in range(GRID.height) for x in range(GRID.width) if is_bridge_cell((x, y))]
    return {
        "grid": {"width": GRID.width, "height": GRID.height, "walkable": GRID.walkable, "river": river, "bridges": bridges},
        "techs": [
            {"id": t.id, "name": t.name, "color": t.color, "home": list(t.home), "ratings": t.ratings, "capacity": t.capacity}
            for t in TECHNICIANS
        ],
        "presets": {
            "demo": [{"x": x, "y": y, "appliance": a} for x, y, a in DEMO_PINS],
            "trap": [{"x": x, "y": y, "appliance": a} for x, y, a in GREEDY_TRAP_PINS],
        },
        "appliance_types": list(APPLIANCE_TYPES),
        "max_jobs": MAX_JOBS,
        "brute_force_max_jobs": BRUTE_FORCE_MAX_JOBS,
        "default_weights": {"w_distance": DEFAULT_WEIGHTS.w_distance, "w_specialty": DEFAULT_WEIGHTS.w_specialty},
        "bridge_count": len(BRIDGES),
    }


def _route(route: Route) -> dict[str, Any]:
    return {
        "tech_index": route.tech_index,
        "stops": route.stops,
        "legs": [
            {"job_index": leg.job_index, "distance": _num(leg.distance), "path": [list(c) for c in leg.path]}
            for leg in route.legs
        ],
        "total_distance": _num(route.total_distance),
    }


def validate_pins(raw: Any) -> list[tuple[int, int, str]]:
    """Turn untrusted request JSON into (x, y, appliance) tuples, dropping
    anything that is not a walkable, non-home cell with a known appliance.
    Duplicates (same cell) keep the first occurrence."""
    pins: list[tuple[int, int, str]] = []
    seen: set[Cell] = set()
    homes = {t.home for t in TECHNICIANS}
    if not isinstance(raw, list):
        return pins
    for item in raw:
        try:
            x, y, appliance = int(item["x"]), int(item["y"]), str(item["appliance"])
        except (KeyError, TypeError, ValueError):
            continue
        cell = (x, y)
        if appliance not in APPLIANCE_TYPES or cell in seen or cell in homes:
            continue
        if not (0 <= x < GRID.width and 0 <= y < GRID.height and GRID.walkable[y][x]):
            continue
        seen.add(cell)
        pins.append((x, y, appliance))
        if len(pins) >= MAX_JOBS:
            break
    return pins


def dispatch_payload(raw_pins: Any, w_distance: float) -> dict[str, Any]:
    w = min(1.0, max(0.0, float(w_distance)))
    weights = Weights(w_distance=w, w_specialty=round(1 - w, 6))
    pins = validate_pins(raw_pins)
    result = run_dispatch(GRID, TECHNICIANS, pins_to_jobs(pins), weights, BRUTE_FORCE_MAX_JOBS)  # type: ignore[arg-type]
    jobs = result.jobs
    greedy = result.greedy
    optimal = result.optimal

    table = [
        [
            {
                "distance": _num(p.distance),
                "closeness": p.closeness,
                "rating": p.rating,
                "specialty_norm": p.specialty_norm,
                "score": p.score,
                "eligible": p.eligible,
                "ineligible_reason": p.ineligible_reason,
            }
            for p in row
        ]
        for row in result.table
    ]

    payload: dict[str, Any] = {
        "weights": {"w_distance": weights.w_distance, "w_specialty": weights.w_specialty},
        "jobs": [{"id": j.id, "x": j.cell[0], "y": j.cell[1], "appliance": j.appliance} for j in jobs],
        "max_distance": _num(result.max_distance),
        "table": table,
        "greedy": {
            "assignment": greedy.assignment,
            "total_score": greedy.total_score,
            "unassigned_reasons": {str(j): r for j, r in greedy.unassigned_reasons.items()},
            "log": [
                {"step": e.step, "tech_index": e.tech_index, "job_index": e.job_index, "score": e.score, "outcome": e.outcome}
                for e in greedy.log
            ],
        },
        "greedy_routes": [_route(r) for r in result.greedy_routes],
        "optimal": None,
        "optimal_routes": None,
        "explanations": {
            "greedy": [explain_job(j, jobs, TECHNICIANS, greedy) for j in range(len(jobs))],
            "optimal": None,
        },
        "unassigned_text": UNASSIGNED_REASON_TEXT,
    }
    if optimal is not None and result.optimal_routes is not None:
        payload["optimal"] = {"assignment": optimal.assignment, "total_score": optimal.total_score, "evaluated": optimal.evaluated}
        payload["optimal_routes"] = [_route(r) for r in result.optimal_routes]
        payload["explanations"]["optimal"] = [
            explain_optimal_job(j, jobs, TECHNICIANS, optimal.assignment, greedy.assignment, result.table)
            for j in range(len(jobs))
        ]
    return payload


def explore_payload(tech_index: int, x: int, y: int) -> dict[str, Any]:
    tech = TECHNICIANS[max(0, min(len(TECHNICIANS) - 1, int(tech_index)))]
    goal = (int(x), int(y))
    a = astar(GRID, tech.home, goal)
    d = dijkstra(GRID, tech.home, goal)
    return {
        "path": [list(c) for c in a.path] if a.path else None,
        "distance": _num(a.distance),
        "astar_explored": [list(c) for c in a.explored],
        "dijkstra_explored": [list(c) for c in d.explored],
    }
