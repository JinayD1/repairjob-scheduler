"""
Scoring: how good is it to send technician T to job J?

Each (tech, job) pair gets a single number in [0, 1] that blends two things:

    closeness      = 1 - distance / max_distance
                     1.0 when the tech is at the job, 0.0 for the farthest
                     reachable pair currently on the map. Normalising by
                     the current maximum keeps the value in [0, 1] whatever
                     the map size, but it also means every score shifts a
                     little when a far-away pin is added or removed.

    specialty_norm = (rating - 1) / 4
                     maps the 1..5 rating onto 0..1.

    score = w_distance * closeness + w_specialty * specialty_norm

The weights sum to 1, so the score is a weighted average and also in [0, 1].

Hard rule: a rating of 1 ("cannot service this appliance") makes the pair
ineligible no matter how close the tech is. Likewise a pair whose distance
is infinite (no path) is ineligible. Ineligible pairs are still returned,
with eligible=False, so a UI can show them, but every assignment algorithm
must skip them.
"""

import math

from .types import DistanceMatrix, Job, PairScore, Technician, Weights

DEFAULT_WEIGHTS = Weights(w_distance=0.6, w_specialty=0.4)

# A rating at or below this value makes the tech ineligible for the job.
INELIGIBLE_RATING = 1


def specialty_norm(rating: int) -> float:
    return (rating - 1) / 4


def max_reachable_distance(distances: DistanceMatrix) -> float:
    """Largest finite distance in the matrix, or 0 if there is none.

    Infinite distances are ignored, otherwise one unreachable pin would make
    closeness meaningless for everyone.
    """
    best = 0.0
    for row in distances:
        for d in row:
            if math.isfinite(d) and d > best:
                best = d
    return best


def closeness(distance: float, max_distance: float) -> float:
    if not math.isfinite(distance):
        return 0.0
    if max_distance == 0:
        # Every reachable pair has distance 0: everything is maximally close.
        return 1.0
    return 1 - distance / max_distance


def score_all_pairs(
    techs: list[Technician],
    jobs: list[Job],
    distances: DistanceMatrix,
    weights: Weights,
) -> list[PairScore]:
    """Score every (tech, job) pair. Returned in tech-major order; greedy
    re-sorts the list anyway."""
    max_distance = max_reachable_distance(distances)
    pairs: list[PairScore] = []

    for t, tech in enumerate(techs):
        for j, job in enumerate(jobs):
            distance = distances[t][j]
            rating = tech.ratings[job.appliance]
            close = closeness(distance, max_distance)
            spec = specialty_norm(rating)
            score = weights.w_distance * close + weights.w_specialty * spec

            eligible = True
            reason = None
            if not math.isfinite(distance):
                eligible, reason = False, "unreachable"
            elif rating <= INELIGIBLE_RATING:
                eligible, reason = False, "rating"

            pairs.append(
                PairScore(
                    tech_index=t,
                    job_index=j,
                    distance=distance,
                    closeness=close,
                    rating=rating,
                    specialty_norm=spec,
                    score=score,
                    eligible=eligible,
                    ineligible_reason=reason,
                )
            )
    return pairs


def index_pairs(pairs: list[PairScore], tech_count: int, job_count: int) -> list[list[PairScore]]:
    """Convenience lookup table: table[tech_index][job_index]."""
    table: list[list[PairScore | None]] = [[None] * job_count for _ in range(tech_count)]
    for p in pairs:
        table[p.tech_index][p.job_index] = p
    return table  # type: ignore[return-value]
