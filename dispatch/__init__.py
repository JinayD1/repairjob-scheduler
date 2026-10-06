"""
Technician dispatch algorithms, in plain Python.

Read the modules in this order:

    grid.py        the map, neighbours, Manhattan distance
    dijkstra.py    shortest paths from one cell to every cell
    astar.py       shortest path to one goal, guided by a heuristic
    scoring.py     how good is (tech, job)?
    greedy.py      best-pair-first assignment with a decision log
    routing.py     nearest-next-stop ordering of each tech's jobs
    bruteforce.py  the true optimum, for comparison
    explain.py     English sentences built from the decision log
    pipeline.py    run_dispatch(): everything in one call
    config.py      technicians, the city map, preset pin layouts
"""

from .pipeline import DispatchResult, run_dispatch  # noqa: F401
