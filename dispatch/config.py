"""
Configuration: technicians, the city map, and preset pin layouts.

This mirrors src/config/ in the TypeScript app exactly, so the Python and
TypeScript versions produce the same assignments for the same pins.
"""

from .grid import block_rect, create_grid, open_rect
from .types import ApplianceType, Cell, Grid, Job, Technician

# ---------------------------------------------------------------------------
# Technicians
# ---------------------------------------------------------------------------

TECH_CAPACITY = 4
MAX_JOBS = 15
BRUTE_FORCE_MAX_JOBS = 12

TECHNICIANS: list[Technician] = [
    Technician(
        id=0,
        name="Maria",
        color="#d6336c",
        home=(2, 9),
        ratings={"Washer": 5, "Fridge": 2, "Oven": 4},
        capacity=TECH_CAPACITY,
    ),
    Technician(
        id=1,
        name="Dev",
        color="#1c7ed6",
        home=(37, 1),
        ratings={"Washer": 3, "Fridge": 5, "Oven": 1},
        capacity=TECH_CAPACITY,
    ),
    Technician(
        id=2,
        name="Sam",
        color="#2f9e44",
        home=(20, 26),
        ratings={"Washer": 2, "Fridge": 4, "Oven": 5},
        capacity=TECH_CAPACITY,
    ),
]

# ---------------------------------------------------------------------------
# The city map: 40 x 28 with buildings and a river crossed by two bridges
# ---------------------------------------------------------------------------

GRID_WIDTH = 40
GRID_HEIGHT = 28

# River segments: for each column range, the two rows that are water.
# Adjacent segments overlap by one row so the water is contiguous and no
# diagonal gap exists that a 4-directional path could slip through.
RIVER_SEGMENTS = [
    # (x0, x1, (row_a, row_b))
    (0, 13, (12, 13)),
    (14, 27, (13, 14)),
    (28, 39, (14, 15)),
]

# The two bridges: a single column of walkable cells across the river.
BRIDGES = [
    # (x, (row_a, row_b))
    (8, (12, 13)),
    (30, (14, 15)),
]

# Buildings as (x, y, width, height).
BUILDINGS = [
    # North of the river
    (2, 2, 6, 4),
    (12, 1, 8, 3),
    (24, 2, 5, 5),
    (33, 3, 5, 4),
    (10, 7, 5, 3),
    (20, 7, 6, 3),
    (30, 9, 7, 2),
    (4, 9, 3, 2),
    # South of the river
    (3, 17, 6, 4),
    (14, 18, 8, 3),
    (26, 19, 6, 4),
    (35, 18, 4, 5),
    (8, 23, 10, 3),
    (22, 24, 6, 3),
    (32, 25, 6, 2),
    (0, 15, 3, 1),
]


def build_city_grid() -> Grid:
    grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
    for x0, x1, rows in RIVER_SEGMENTS:
        block_rect(grid, x0, rows[0], x1 - x0 + 1, 2)
    for x, rows in BRIDGES:
        open_rect(grid, x, rows[0], 1, 2)
    for x, y, w, h in BUILDINGS:
        block_rect(grid, x, y, w, h)
    return grid


def is_river_cell(cell: Cell) -> bool:
    x, y = cell
    return any(x0 <= x <= x1 and y in rows for x0, x1, rows in RIVER_SEGMENTS)


def is_bridge_cell(cell: Cell) -> bool:
    x, y = cell
    return any(x == bx and y in rows for bx, rows in BRIDGES)


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

# (x, y, appliance)
PresetPin = tuple[int, int, ApplianceType]

DEMO_PINS: list[PresetPin] = [
    (6, 1, "Washer"),
    (22, 5, "Fridge"),
    (31, 1, "Fridge"),
    (17, 10, "Oven"),
    (36, 11, "Washer"),
    (11, 16, "Oven"),
    (24, 17, "Washer"),
    (4, 24, "Fridge"),
    (30, 23, "Oven"),
    (20, 27, "Fridge"),
]

# Found by scripts/findGreedyTrap.ts in the TypeScript project: greedy
# reaches about 77% of optimal here with the default weights. Seven of the
# eleven jobs are ovens, which Dev (Oven 1) can never take, so only Maria and
# Sam (8 slots) can. Greedy fills some of those slots with fridges and a
# washer that score a little higher for Maria/Sam individually than for Dev,
# leaving Dev idle and three ovens unassigned. Optimal gives all the fridges
# to Dev, which frees Maria and Sam to cover every oven.
GREEDY_TRAP_PINS: list[PresetPin] = [
    (29, 2, "Oven"),
    (8, 5, "Oven"),
    (30, 7, "Oven"),
    (33, 7, "Oven"),
    (35, 7, "Oven"),
    (27, 10, "Oven"),
    (7, 11, "Fridge"),
    (6, 14, "Fridge"),
    (22, 22, "Washer"),
    (38, 24, "Fridge"),
    (4, 26, "Oven"),
]


def pins_to_jobs(pins: list[PresetPin]) -> list[Job]:
    """Turn preset pins into Job objects. The id is the cell key, which is
    independent of the order the pins are listed."""
    return [Job(id=y * GRID_WIDTH + x, cell=(x, y), appliance=a) for x, y, a in pins]
