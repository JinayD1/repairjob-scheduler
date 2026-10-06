"""
Shared data types for the dispatch algorithms.

Everything here is a plain dataclass or type alias. There is no UI code in
this package; the modules are pure functions over these types so they can be
read, tested and reused on their own.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# The map
# ---------------------------------------------------------------------------

# A grid coordinate: (x, y). x is the column, y is the row. Using a plain
# tuple keeps cells hashable so they can go in sets and dict keys.
Cell = tuple[int, int]


@dataclass
class Grid:
    """The map. walkable[y][x] is True for streets and bridges, False for
    buildings and river water."""

    width: int
    height: int
    walkable: list[list[bool]]


# ---------------------------------------------------------------------------
# Technicians and jobs
# ---------------------------------------------------------------------------

ApplianceType = Literal["Washer", "Fridge", "Oven"]
APPLIANCE_TYPES: tuple[ApplianceType, ...] = ("Washer", "Fridge", "Oven")


@dataclass
class Technician:
    id: int  # also the tie-breaking "tech index"
    name: str
    color: str
    home: Cell
    ratings: dict[str, int]  # appliance -> 1..5
    capacity: int  # maximum jobs this tech will accept


@dataclass
class Job:
    id: int  # stable identifier; the pipeline sorts jobs by cell anyway
    cell: Cell
    appliance: ApplianceType


# distances[tech_index][job_index] = shortest-path length in steps, or
# math.inf if no path exists.
DistanceMatrix = list[list[float]]


@dataclass
class Weights:
    """The two scoring weights. They always sum to 1."""

    w_distance: float
    w_specialty: float


# ---------------------------------------------------------------------------
# Scoring and assignment
# ---------------------------------------------------------------------------


@dataclass
class PairScore:
    """How good it is to send one technician to one job."""

    tech_index: int
    job_index: int
    distance: float
    closeness: float  # 1 - distance / max_distance, in [0, 1]
    rating: int
    specialty_norm: float  # (rating - 1) / 4, in [0, 1]
    score: float
    eligible: bool  # False when rating is 1 or the job is unreachable
    ineligible_reason: Optional[Literal["rating", "unreachable"]] = None


UnassignedReason = Literal[
    "unreachable",  # no technician can reach this job at all
    "no-eligible-tech",  # reachable, but every tech has rating 1 for it
    "all-eligible-at-capacity",  # eligible techs exist but were all full
]

# assignment[job_index] = tech_index, or None if the job is unassigned.
Assignment = list[Optional[int]]


@dataclass
class DecisionLogEntry:
    """One line of the greedy decision log: a pair that was examined and what
    the loop decided to do with it."""

    step: int  # position in the sorted pair list, starting at 0
    tech_index: int
    job_index: int
    score: float
    distance: float
    outcome: Literal["assigned", "job-already-assigned", "tech-at-capacity"]


@dataclass
class GreedyResult:
    assignment: Assignment
    unassigned_reasons: dict[int, UnassignedReason]
    total_score: float
    sorted_pairs: list[PairScore]  # the candidate list in greedy order
    log: list[DecisionLogEntry]


@dataclass
class BruteForceResult:
    assignment: Assignment
    total_score: float
    evaluated: int  # complete assignments examined after pruning


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@dataclass
class RouteLeg:
    start: Cell
    end: Cell
    job_index: int  # the job this leg ends at
    path: list[Cell]  # every cell from start to end inclusive
    distance: float


@dataclass
class Route:
    tech_index: int
    stops: list[int] = field(default_factory=list)  # job indices in visiting order
    legs: list[RouteLeg] = field(default_factory=list)
    total_distance: float = 0.0
