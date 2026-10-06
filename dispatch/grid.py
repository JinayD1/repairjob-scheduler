"""
Grid helpers shared by Dijkstra, A*, and the demo.

The map is a rectangle of cells. A cell is either walkable (street or bridge)
or blocked (building or river). Movement is 4-directional and every step
costs exactly 1, so the shortest-path distance between two cells is simply
the number of steps.
"""

import random

from .types import Cell, Grid

# The four orthogonal moves, in a fixed order so results are deterministic.
DIRECTIONS: tuple[Cell, ...] = (
    (0, -1),  # up
    (1, 0),  # right
    (0, 1),  # down
    (-1, 0),  # left
)


def in_bounds(grid: Grid, cell: Cell) -> bool:
    x, y = cell
    return 0 <= x < grid.width and 0 <= y < grid.height


def is_walkable(grid: Grid, cell: Cell) -> bool:
    x, y = cell
    return in_bounds(grid, cell) and grid.walkable[y][x]


def neighbors(grid: Grid, cell: Cell) -> list[Cell]:
    """Walkable neighbours of a cell, in DIRECTIONS order."""
    x, y = cell
    result = []
    for dx, dy in DIRECTIONS:
        nxt = (x + dx, y + dy)
        if is_walkable(grid, nxt):
            result.append(nxt)
    return result


def manhattan(a: Cell, b: Cell) -> int:
    """|dx| + |dy|.

    With 4-directional unit-cost movement this is the shortest possible path
    length if there were no obstacles, so it never over-estimates the true
    distance. That property ("admissible") is exactly what A* needs from its
    heuristic.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def create_grid(width: int, height: int) -> Grid:
    """An empty, fully walkable grid."""
    return Grid(width, height, [[True] * width for _ in range(height)])


def block_rect(grid: Grid, x0: int, y0: int, w: int, h: int) -> None:
    """Mark a rectangle of cells as blocked (used for buildings and river)."""
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            if in_bounds(grid, (x, y)):
                grid.walkable[y][x] = False


def open_rect(grid: Grid, x0: int, y0: int, w: int, h: int) -> None:
    """Mark a rectangle of cells as walkable (used to cut bridges)."""
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            if in_bounds(grid, (x, y)):
                grid.walkable[y][x] = True


def random_grid(width: int, height: int, density: float, seed: int) -> Grid:
    """A random grid where each cell is blocked with probability `density`.

    Only used by tests. Seeded so the "random" grids are reproducible.
    """
    rng = random.Random(seed)
    grid = create_grid(width, height)
    for y in range(height):
        for x in range(width):
            grid.walkable[y][x] = rng.random() >= density
    return grid


def render(grid: Grid, overlay: dict[Cell, str] | None = None) -> str:
    """ASCII picture of the grid: '.' street, '#' blocked, plus any overlay
    characters (routes, pins, homes) the caller wants drawn on top."""
    overlay = overlay or {}
    lines = []
    header = "   " + "".join(str(x % 10) for x in range(grid.width))
    lines.append(header)
    for y in range(grid.height):
        row = f"{y:2d} "
        for x in range(grid.width):
            ch = overlay.get((x, y))
            if ch is None:
                ch = "." if grid.walkable[y][x] else "#"
            row += ch
        lines.append(row)
    return "\n".join(lines)
