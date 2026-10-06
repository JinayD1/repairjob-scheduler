"""
Command-line demo: run the whole pipeline on a preset and print the map,
the routes, the scores and the explanations.

    python3 demo.py            # the 10-pin demo layout
    python3 demo.py trap       # the greedy-trap layout
    python3 demo.py trap 0.3   # ... with w_distance = 0.3 (w_specialty = 0.7)
    python3 demo.py explore    # compare cells explored by A* and Dijkstra
"""

import sys

from dispatch.astar import astar
from dispatch.config import (
    BRUTE_FORCE_MAX_JOBS,
    DEMO_PINS,
    GREEDY_TRAP_PINS,
    TECHNICIANS,
    build_city_grid,
    pins_to_jobs,
)
from dispatch.dijkstra import dijkstra
from dispatch.explain import explain_job, explain_optimal_job
from dispatch.grid import render
from dispatch.pipeline import DispatchResult, job_counts, run_dispatch, total_route_distance
from dispatch.scoring import DEFAULT_WEIGHTS
from dispatch.types import Cell, Route, Weights

GRID = build_city_grid()


def draw(result: DispatchResult, routes: list[Route], title: str) -> None:
    """ASCII map: routes as lower-case letters (m/d/s), pins as job numbers
    (last digit), homes as upper-case letters."""
    overlay: dict[Cell, str] = {}
    for route in routes:
        letter = TECHNICIANS[route.tech_index].name[0].lower()
        for leg in route.legs:
            for cell in leg.path:
                overlay[cell] = letter
    for j, job in enumerate(result.jobs):
        overlay[job.cell] = str((j + 1) % 10)
    for tech in TECHNICIANS:
        overlay[tech.home] = tech.name[0]
    print(f"\n=== {title} ===")
    print(render(GRID, overlay))


def report(result: DispatchResult) -> None:
    greedy, optimal = result.greedy, result.optimal
    print("\n--- Summary ---")
    print(f"greedy total score   {greedy.total_score:.3f}")
    if optimal is None:
        print(f"optimal              skipped (more than {BRUTE_FORCE_MAX_JOBS} jobs)")
    else:
        pct = 100 * greedy.total_score / optimal.total_score if optimal.total_score else 100
        print(f"optimal total score  {optimal.total_score:.3f}  (greedy is {pct:.1f}% of optimal)")
        print(f"brute force examined {optimal.evaluated} complete assignments after pruning")
    print(f"greedy drive distance {total_route_distance(result.greedy_routes):.0f} steps")
    counts = job_counts(greedy.assignment, len(TECHNICIANS))
    print("jobs per tech        " + ", ".join(f"{t.name} {c}" for t, c in zip(TECHNICIANS, counts)))

    print("\n--- Greedy routes ---")
    for route in result.greedy_routes:
        tech = TECHNICIANS[route.tech_index]
        stops = " -> ".join(f"job {j + 1}" for j in route.stops) or "(none)"
        print(f"{tech.name:6s} home -> {stops}   ({route.total_distance:.0f} steps)")

    print("\n--- Why each job went where it did (greedy) ---")
    for j in range(len(result.jobs)):
        print(explain_job(j, result.jobs, TECHNICIANS, greedy))

    if optimal is not None:
        print("\n--- Optimal vs greedy ---")
        for j in range(len(result.jobs)):
            if optimal.assignment[j] != greedy.assignment[j]:
                print(explain_optimal_job(j, result.jobs, TECHNICIANS, optimal.assignment, greedy.assignment, result.table))

    print("\n--- Score table (rows: techs, columns: jobs) ---")
    header = "        " + " ".join(f"{j + 1:>6d}" for j in range(len(result.jobs)))
    print(header)
    for t, tech in enumerate(TECHNICIANS):
        cells = []
        for j in range(len(result.jobs)):
            p = result.table[t][j]
            cells.append(f"{p.score:6.2f}" if p.eligible else "     x")
        print(f"{tech.name:6s}  " + " ".join(cells))
    print("(x = ineligible: rating 1 or unreachable)")


def explore_demo() -> None:
    start = TECHNICIANS[0].home
    goal = (33, 22)
    a = astar(GRID, start, goal)
    d = dijkstra(GRID, start, goal)
    overlay: dict[Cell, str] = {}
    for cell in d.explored:
        overlay[cell] = "d"
    for cell in a.explored:
        overlay[cell] = "A" if overlay.get(cell) == "d" else "a"
    for cell in a.path or []:
        overlay[cell] = "*"
    overlay[start] = "S"
    overlay[goal] = "G"
    print(render(GRID, overlay))
    print(f"\npath length {a.distance:.0f}; Dijkstra settled {len(d.explored)} cells, A* settled {len(a.explored)}")
    print("d = Dijkstra only, A = both, a = A* only, * = the path")


def main(argv: list[str]) -> None:
    if argv and argv[0] == "explore":
        explore_demo()
        return
    pins = GREEDY_TRAP_PINS if argv and argv[0] == "trap" else DEMO_PINS
    weights = DEFAULT_WEIGHTS
    if len(argv) > 1:
        w = float(argv[1])
        weights = Weights(w_distance=w, w_specialty=round(1 - w, 6))

    result = run_dispatch(GRID, TECHNICIANS, pins_to_jobs(pins), weights, BRUTE_FORCE_MAX_JOBS)
    draw(result, result.greedy_routes, "Greedy assignment")
    if result.optimal_routes is not None:
        draw(result, result.optimal_routes, "Optimal assignment")
    report(result)


if __name__ == "__main__":
    main(sys.argv[1:])
