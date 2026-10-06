"""
Dijkstra's algorithm: single-source shortest paths on the grid.

The idea
--------
Start at a source cell with distance 0. Keep a "frontier" of discovered cells
ordered by their tentative distance (a priority queue; Python's heapq module
gives us one). Repeatedly take the closest frontier cell, mark it as settled
(its distance is now final), and "relax" each neighbour: if going through the
settled cell gives the neighbour a shorter distance than it had before,
update it and push it on the frontier.

Why is the closest frontier cell's distance final? Every edge costs at least
1 (here exactly 1), so no path through a farther frontier cell could ever
come back and reach this cell more cheaply. That invariant is the heart of
Dijkstra and the reason it requires non-negative edge weights.

Dijkstra has no idea where the "goal" is, because it has no single goal: one
run gives the shortest distance from the source to EVERY cell. That is just
what we want for a distance matrix, where one tech home needs distances to
all jobs at once.

Because every step costs 1, Dijkstra on this grid behaves identically to a
breadth-first search. We still write it with a priority queue so the code
would work unchanged if some cells were slower than others.
"""

import heapq
import math
from dataclasses import dataclass

from .grid import neighbors
from .types import Cell, DistanceMatrix, Grid, Job, Technician


@dataclass
class DijkstraResult:
    distances: dict[Cell, float]  # cell -> shortest distance; missing = unreachable
    explored: list[Cell]  # cells settled, in the order they were settled


def dijkstra(grid: Grid, source: Cell, target: Cell | None = None) -> DijkstraResult:
    """Run Dijkstra from `source`.

    If `target` is given, stop as soon as the target is settled (used by the
    A*-vs-Dijkstra comparison). Otherwise settle every reachable cell.
    """
    distances: dict[Cell, float] = {source: 0}
    settled: set[Cell] = set()
    explored: list[Cell] = []

    # heapq orders tuples lexicographically, so we push
    # (distance, insertion_counter, cell). The counter breaks ties between
    # equal distances in insertion order, which keeps the exploration order
    # deterministic and also avoids ever comparing two cells directly.
    counter = 0
    frontier: list[tuple[float, int, Cell]] = [(0, counter, source)]

    while frontier:
        dist, _, current = heapq.heappop(frontier)

        # A cell can be pushed several times with decreasing tentative
        # distances. Only the first pop (the smallest) matters; skip the rest.
        if current in settled:
            continue
        settled.add(current)
        explored.append(current)

        if current == target:
            break

        # Relaxation step: offer each neighbour a path through `current`.
        for nxt in neighbors(grid, current):
            if nxt in settled:
                continue
            candidate = dist + 1  # every step costs 1
            if candidate < distances.get(nxt, math.inf):
                distances[nxt] = candidate
                counter += 1
                heapq.heappush(frontier, (candidate, counter, nxt))

    return DijkstraResult(distances, explored)


def distance_to(result: DijkstraResult, cell: Cell) -> float:
    """Distance from the run's source to `cell`, or inf if unreachable."""
    return result.distances.get(cell, math.inf)


def build_distance_matrices(
    grid: Grid, techs: list[Technician], jobs: list[Job]
) -> tuple[DistanceMatrix, DistanceMatrix]:
    """Build (tech_to_job, job_to_job).

    One Dijkstra run from each technician's home gives that tech's row. One
    run from each job gives the job-to-job matrix, which the routing step
    uses to measure the distance from one stop to the next.
    """
    tech_to_job: DistanceMatrix = []
    for tech in techs:
        run = dijkstra(grid, tech.home)
        tech_to_job.append([distance_to(run, job.cell) for job in jobs])

    job_to_job: DistanceMatrix = []
    for src in jobs:
        run = dijkstra(grid, src.cell)
        job_to_job.append([distance_to(run, dst.cell) for dst in jobs])

    return tech_to_job, job_to_job
