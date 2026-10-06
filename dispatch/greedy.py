"""
Greedy assignment: "best pair first".

The idea
--------
A greedy algorithm makes the locally best choice at each step and never
revisits it. Here the "choice" is a (tech, job) pair and "best" means the
highest score:

    1. Score every eligible (tech, job) pair.
    2. Sort the pairs from best to worst.
    3. Walk down the list. For each pair, if the job is still free and the
       tech still has room, assign it. Otherwise skip it.

It is fast (sorting dominates: O(P log P) for P pairs) and easy to explain
("Job 7 went to Dev because that was the best remaining option"), which is
why dispatch systems often start here. It is NOT guaranteed to find the best
total: grabbing a 0.90 pair early can block two 0.85 pairs later. The
brute-force module exists to measure exactly how much is lost.

Determinism
-----------
Ties are common (two jobs of the same type at the same distance). The sort
key breaks them in a fixed order: higher score, then shorter distance, then
lower tech index, then lower job index. Because the pipeline indexes jobs in
a canonical order, the output never depends on the order pins were placed.

Decision log
------------
Every pair that is examined is written to a log with its outcome
("assigned", "job already assigned", "tech at capacity"). The explain module
turns that log into sentences such as "Sam scored higher (0.86) but was
already at capacity when this pair was reached".
"""

from .types import (
    Assignment,
    DecisionLogEntry,
    GreedyResult,
    PairScore,
    Technician,
    UnassignedReason,
)


def round_score(score: float) -> float:
    """Round to 9 decimal places to absorb floating-point noise, so two
    mathematically tied scores compare as equal."""
    return round(score, 9)


def pair_sort_key(p: PairScore):
    """Sort key: best first. Python sorts ascending, so negate the score."""
    return (-round_score(p.score), p.distance, p.tech_index, p.job_index)


def greedy_assign(techs: list[Technician], job_count: int, pairs: list[PairScore]) -> GreedyResult:
    # Step 1: keep only the eligible pairs.
    eligible = [p for p in pairs if p.eligible]

    # Step 2: sort best-first with deterministic tie-breaking.
    sorted_pairs = sorted(eligible, key=pair_sort_key)

    # Step 3: walk the list.
    assignment: Assignment = [None] * job_count
    load = [0] * len(techs)
    log: list[DecisionLogEntry] = []
    total_score = 0.0

    for step, pair in enumerate(sorted_pairs):
        if assignment[pair.job_index] is not None:
            outcome = "job-already-assigned"
        elif load[pair.tech_index] >= techs[pair.tech_index].capacity:
            outcome = "tech-at-capacity"
        else:
            outcome = "assigned"
            assignment[pair.job_index] = pair.tech_index
            load[pair.tech_index] += 1
            total_score += pair.score
        log.append(
            DecisionLogEntry(
                step=step,
                tech_index=pair.tech_index,
                job_index=pair.job_index,
                score=pair.score,
                distance=pair.distance,
                outcome=outcome,
            )
        )

    # Step 4: explain every job that is still unassigned.
    unassigned_reasons: dict[int, UnassignedReason] = {}
    for j in range(job_count):
        if assignment[j] is None:
            unassigned_reasons[j] = classify_unassigned(j, pairs)

    return GreedyResult(assignment, unassigned_reasons, total_score, sorted_pairs, log)


def classify_unassigned(job_index: int, pairs: list[PairScore]) -> UnassignedReason:
    """Why did this job end up with nobody? Checked in order of severity:
      - unreachable: no technician has a finite distance to it.
      - no-eligible-tech: reachable, but every tech has rating 1 for it.
      - all-eligible-at-capacity: it had eligible techs, so the only way it
        could be skipped is that each of them was full when reached.
    """
    for_job = [p for p in pairs if p.job_index == job_index]
    if all(p.ineligible_reason == "unreachable" for p in for_job):
        return "unreachable"
    if all(not p.eligible for p in for_job):
        return "no-eligible-tech"
    return "all-eligible-at-capacity"


def assignment_score(assignment: Assignment, table: list[list[PairScore]]) -> float:
    """Total score of any assignment, using the same pair scores."""
    return sum(table[t][j].score for j, t in enumerate(assignment) if t is not None)
