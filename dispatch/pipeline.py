"""
The dispatch pipeline. One call, `run_dispatch`, runs every algorithm in
order and returns everything a UI (or the command-line demo) needs:

  1. Canonicalise the job list (sort by cell) so results never depend on
     the order pins were placed.
  2. Dijkstra from every tech home and every job -> distance matrices.
  3. Score every (tech, job) pair.
  4. Greedy assignment with its decision log.
  5. Nearest-next-stop routes with A* paths for the greedy assignment.
  6. If the job count is small enough, brute-force optimal assignment and
     its routes, for comparison.

Everything is a pure function of (grid, techs, jobs, weights). Running it
twice with the same inputs produces identical output.
"""

from dataclasses import dataclass

from .bruteforce import brute_force_assign
from .dijkstra import build_distance_matrices
from .greedy import greedy_assign
from .routing import build_routes
from .scoring import index_pairs, max_reachable_distance, score_all_pairs
from .types import (
    Assignment,
    BruteForceResult,
    DistanceMatrix,
    Grid,
    GreedyResult,
    Job,
    PairScore,
    Route,
    Technician,
    Weights,
)


@dataclass
class DispatchResult:
    jobs: list[Job]  # canonical order; all job indices refer to this list
    tech_to_job: DistanceMatrix
    job_to_job: DistanceMatrix
    max_distance: float
    pairs: list[PairScore]
    table: list[list[PairScore]]  # table[tech_index][job_index]
    greedy: GreedyResult
    greedy_routes: list[Route]
    optimal: BruteForceResult | None  # None when brute force was skipped
    optimal_routes: list[Route] | None


def canonical_job_order(jobs: list[Job]) -> list[Job]:
    """Sort by row then column. Two pins never share a cell, so this is a
    strict total order independent of click order."""
    return sorted(jobs, key=lambda j: (j.cell[1], j.cell[0]))


def run_dispatch(
    grid: Grid,
    techs: list[Technician],
    jobs: list[Job],
    weights: Weights,
    brute_force_max_jobs: int = 12,
) -> DispatchResult:
    jobs = canonical_job_order(jobs)

    tech_to_job, job_to_job = build_distance_matrices(grid, techs, jobs)
    max_distance = max_reachable_distance(tech_to_job)

    pairs = score_all_pairs(techs, jobs, tech_to_job, weights)
    table = index_pairs(pairs, len(techs), len(jobs))

    greedy = greedy_assign(techs, len(jobs), pairs)
    greedy_routes = build_routes(grid, techs, jobs, greedy.assignment, tech_to_job, job_to_job)

    optimal = None
    optimal_routes = None
    if len(jobs) <= brute_force_max_jobs:
        optimal = brute_force_assign(techs, len(jobs), table)
        optimal_routes = build_routes(grid, techs, jobs, optimal.assignment, tech_to_job, job_to_job)

    return DispatchResult(
        jobs=jobs,
        tech_to_job=tech_to_job,
        job_to_job=job_to_job,
        max_distance=max_distance,
        pairs=pairs,
        table=table,
        greedy=greedy,
        greedy_routes=greedy_routes,
        optimal=optimal,
        optimal_routes=optimal_routes,
    )


def total_route_distance(routes: list[Route]) -> float:
    return sum(r.total_distance for r in routes)


def job_counts(assignment: Assignment, tech_count: int) -> list[int]:
    counts = [0] * tech_count
    for t in assignment:
        if t is not None:
            counts[t] += 1
    return counts
