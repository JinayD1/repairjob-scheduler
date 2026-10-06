"""
Brute-force optimal assignment by exhaustive depth-first search.

The idea
--------
Greedy picks pairs one at a time and never looks back. To know how much that
costs we need the true optimum: the assignment with the highest total score,
subject to capacity and eligibility. For a tiny instance we can simply try
every possibility.

The search tree
---------------
Process jobs in index order. At job j branch over every option for that job:
each eligible technician who still has capacity, plus "leave unassigned".
One level deeper per job; a leaf is reached once every job is decided. With
3 techs and 12 jobs that is up to 4^12 (about 16.8 million) leaves, which is
why the demo disables brute force above 12 jobs.

Rules
-----
  - Capacity: never branch into a tech who is already full, so any subtree
    that would exceed capacity is pruned before it is created.
  - Eligibility: ineligible pairs (rating 1 or unreachable) are never options.
  - Unassigned only when necessary: a leaf is accepted only if every
    unassigned job truly has no eligible tech with spare capacity in that
    final state. Because all scores are >= 0, leaving an assignable job out
    can never beat assigning it, so restricting to these "maximal"
    assignments loses nothing and avoids counting silly solutions.

Branch and bound
----------------
Exhaustive does not have to mean naive. For every job we precompute the best
score ANY eligible tech could give it. The sum of those for the jobs not yet
decided is an upper bound on what the rest of this branch can add. If
current score + bound cannot beat the best complete assignment found so far,
the whole subtree is skipped. We also try techs in descending score order so
a good solution is found early and the bound bites sooner. The result is
identical to naive enumeration, only faster.

Determinism: when two assignments tie, the first one found is kept, and the
search order is fixed, so the result is reproducible.
"""

from .greedy import round_score
from .types import Assignment, BruteForceResult, PairScore, Technician


def brute_force_assign(
    techs: list[Technician], job_count: int, table: list[list[PairScore]]
) -> BruteForceResult:
    # For each job, its eligible options sorted by score descending.
    options_per_job: list[list[PairScore]] = []
    for j in range(job_count):
        options = [table[t][j] for t in range(len(techs)) if table[t][j].eligible]
        options.sort(key=lambda p: (-p.score, p.tech_index))
        options_per_job.append(options)

    # best_remaining[j] = sum over jobs j..end of the best score each could
    # possibly get. This is the optimistic bound used for pruning.
    best_remaining = [0.0] * (job_count + 1)
    for j in range(job_count - 1, -1, -1):
        best = options_per_job[j][0].score if options_per_job[j] else 0.0
        best_remaining[j] = best_remaining[j + 1] + best

    load = [0] * len(techs)
    current: Assignment = [None] * job_count
    state = {"best_score": -1.0, "best_assignment": list(current), "evaluated": 0}

    def is_maximal() -> bool:
        """True if no unassigned job could still be given to someone."""
        for j in range(job_count):
            if current[j] is not None:
                continue
            for option in options_per_job[j]:
                if load[option.tech_index] < techs[option.tech_index].capacity:
                    return False
        return True

    def search(j: int, score: float) -> None:
        # Bound: even if every remaining job got its best possible tech,
        # could this branch beat the best so far? If not, stop here.
        if round_score(score + best_remaining[j]) <= round_score(state["best_score"]):
            return

        if j == job_count:
            state["evaluated"] += 1
            if is_maximal() and round_score(score) > round_score(state["best_score"]):
                state["best_score"] = score
                state["best_assignment"] = list(current)
            return

        # Option A: assign job j to each eligible tech with room (best first).
        for option in options_per_job[j]:
            t = option.tech_index
            if load[t] >= techs[t].capacity:
                continue  # capacity prune
            load[t] += 1
            current[j] = t
            search(j + 1, score + option.score)
            current[j] = None
            load[t] -= 1

        # Option B: leave job j unassigned. The leaf check rejects this if an
        # eligible tech still had room at the end.
        search(j + 1, score)

    search(0, 0.0)

    return BruteForceResult(
        assignment=state["best_assignment"],
        total_score=max(state["best_score"], 0.0),
        evaluated=state["evaluated"],
    )
