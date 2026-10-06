"""
A* search: shortest path from one cell to one specific goal cell.

The idea
--------
A* is Dijkstra with a sense of direction. Dijkstra orders its frontier by
g(n), the cost already spent to reach cell n. A* orders it by

    f(n) = g(n) + h(n)

where h(n) is a heuristic *estimate* of the remaining cost from n to the
goal. Cells that look like they lead toward the goal get popped first, so
A* usually settles far fewer cells than Dijkstra before finding the goal.

Why the result is still optimal
-------------------------------
As long as h never over-estimates the true remaining cost ("admissible"),
the first time A* pops the goal no cheaper path can exist. Our heuristic is
Manhattan distance, which on a 4-directional grid with unit step costs is
exactly the distance with all obstacles removed, so it can only be <= the
real distance. Manhattan distance is also "consistent" (h(a) <= 1 + h(b) for
neighbours a and b), which is what lets us treat a cell as final the first
time we pop it, exactly like Dijkstra.

Tie-breaking
------------
On an open grid many cells share the same f value (every cell inside the
bounding box of start and goal has f equal to the straight-line Manhattan
distance). If ties were broken arbitrarily A* would wander across the whole
box. We break ties in favour of the SMALLER h, i.e. the cell closer to the
goal, by pushing (f, h, counter, cell) onto the heap. f stays the primary
key so optimality is unaffected; A* just marches straight at the goal.

Path reconstruction
-------------------
For each cell we remember which cell we came from when we found its best g.
Once the goal pops, we walk those links backwards to the start.
"""

import heapq
import math
from dataclasses import dataclass

from .grid import manhattan, neighbors
from .types import Cell, Grid


@dataclass
class AStarResult:
    path: list[Cell] | None  # start..goal inclusive, or None if unreachable
    distance: float  # len(path) - 1, or inf
    explored: list[Cell]  # cells settled (popped), in order


def astar(grid: Grid, start: Cell, goal: Cell) -> AStarResult:
    if start == goal:
        return AStarResult([start], 0, [start])

    g: dict[Cell, float] = {start: 0}  # cost so far
    came_from: dict[Cell, Cell] = {}
    settled: set[Cell] = set()
    explored: list[Cell] = []

    counter = 0
    h0 = manhattan(start, goal)
    # (f, h, counter, cell): ordered by f, then h, then insertion order.
    frontier: list[tuple[float, int, int, Cell]] = [(h0, h0, counter, start)]

    while frontier:
        _, _, _, current = heapq.heappop(frontier)
        if current in settled:
            continue
        settled.add(current)
        explored.append(current)

        if current == goal:
            # Walk the came_from chain backwards from the goal to the start.
            path = [goal]
            while path[-1] in came_from:
                path.append(came_from[path[-1]])
            path.reverse()
            return AStarResult(path, len(path) - 1, explored)

        for nxt in neighbors(grid, current):
            if nxt in settled:
                continue
            tentative_g = g[current] + 1
            if tentative_g < g.get(nxt, math.inf):
                g[nxt] = tentative_g
                came_from[nxt] = current
                h = manhattan(nxt, goal)
                counter += 1
                # Priority is f = g + h. This line is the only real
                # difference from Dijkstra, which would use just g.
                heapq.heappush(frontier, (tentative_g + h, h, counter, nxt))

    return AStarResult(None, math.inf, explored)
