"""
Route ordering: in what order should a technician visit their jobs?

Nearest-next-stop (a.k.a. nearest neighbour)
--------------------------------------------
Start at the technician's home. Among the jobs not yet visited, pick the one
with the smallest shortest-path distance from the current location, go
there, and repeat until no jobs remain. This is a greedy heuristic for the
travelling-salesman ordering problem: cheap (O(k^2) for k stops) and
intuitive, but not optimal. A classic failure: it happily drives past a
cluster to grab one slightly-closer job, then has to come back.

Distances between stops come from the job-to-job matrix that Dijkstra
already produced, so no extra pathfinding is needed to decide the order.
A* is used only afterwards, to get the actual cells of each leg.

Ties (two remaining jobs equally far) go to the lower job index so the
route is deterministic.
"""

from .astar import astar
from .types import Assignment, Cell, DistanceMatrix, Grid, Job, Route, RouteLeg, Technician


def nearest_next_order(
    job_indices: list[int],
    home_distances: list[float],
    job_to_job: DistanceMatrix,
) -> list[int]:
    """Visiting order for one technician's jobs.

    home_distances[j] is the distance from home to job j;
    job_to_job[a][b] is the distance from job a to job b.
    """
    remaining = set(job_indices)
    order: list[int] = []
    current: int | None = None  # None while we are still at home

    while remaining:
        best = None
        best_distance = float("inf")
        # Iterate in ascending job index so ties resolve to the lower index.
        for j in sorted(remaining):
            d = home_distances[j] if current is None else job_to_job[current][j]
            if d < best_distance:
                best, best_distance = j, d
        if best is None:
            break  # cannot happen for reachable jobs; keeps the loop safe
        order.append(best)
        remaining.remove(best)
        current = best

    return order


def build_routes(
    grid: Grid,
    techs: list[Technician],
    jobs: list[Job],
    assignment: Assignment,
    tech_to_job: DistanceMatrix,
    job_to_job: DistanceMatrix,
) -> list[Route]:
    """Full routes (order + A* paths) for every technician. Technicians with
    no jobs get an empty route."""
    routes: list[Route] = []
    for t, tech in enumerate(techs):
        assigned = [j for j, holder in enumerate(assignment) if holder == t]
        stops = nearest_next_order(assigned, tech_to_job[t], job_to_job)

        legs: list[RouteLeg] = []
        start: Cell = tech.home
        total = 0.0
        for j in stops:
            end = jobs[j].cell
            result = astar(grid, start, end)
            legs.append(RouteLeg(start, end, j, result.path or [], result.distance))
            total += result.distance
            start = end

        routes.append(Route(t, stops, legs, total))
    return routes
