"""
Plain-English explanations built from the greedy decision log.

To explain why job J went to tech T we look at:

  - the log entry where (T, J) was assigned, and its position in the list;
  - the best OTHER eligible pair for J (the "runner-up"). If that pair
    sorted ahead of the winner it was reached earlier and skipped, and the
    only way an earlier pair for a still-free job gets skipped is "tech at
    capacity". If it sorted after the winner, it simply lost.

No randomness and nothing beyond string templates: the explanation is a
deterministic function of the log.
"""

from .greedy import pair_sort_key
from .types import Assignment, GreedyResult, Job, PairScore, Technician

UNASSIGNED_REASON_TEXT = {
    "unreachable": "no technician can reach this location (no path on the map)",
    "no-eligible-tech": "every technician has rating 1 for this appliance, so none is eligible",
    "all-eligible-at-capacity": "every eligible technician was already at capacity when this job was reached",
}


def job_label(job: Job, job_index: int) -> str:
    return f"Job {job_index + 1} ({job.appliance})"


def fmt(score: float) -> str:
    return f"{score:.2f}"


def explain_job(job_index: int, jobs: list[Job], techs: list[Technician], greedy: GreedyResult) -> str:
    """Explain the greedy outcome for one job."""
    label = job_label(jobs[job_index], job_index)
    winner_index = greedy.assignment[job_index]

    if winner_index is None:
        reason = greedy.unassigned_reasons.get(job_index, "all-eligible-at-capacity")
        text = f"{label} is unassigned: {UNASSIGNED_REASON_TEXT[reason]}."
        if reason == "all-eligible-at-capacity":
            blocked = [
                f"{techs[e.tech_index].name} ({fmt(e.score)})"
                for e in greedy.log
                if e.job_index == job_index and e.outcome == "tech-at-capacity"
            ]
            if blocked:
                text += " Skipped: " + ", ".join(blocked) + "."
        return text

    winner = techs[winner_index]
    assigned_entry = next(
        e
        for e in greedy.log
        if e.job_index == job_index and e.tech_index == winner_index and e.outcome == "assigned"
    )
    sentences = [
        f"{label} went to {winner.name} with score {fmt(assigned_entry.score)} "
        f"(decision {assigned_entry.step + 1} of {len(greedy.log)} in the sorted pair list)."
    ]

    # sorted_pairs is already in greedy order, so the first match is the best.
    winner_pair = next(
        p for p in greedy.sorted_pairs if p.job_index == job_index and p.tech_index == winner_index
    )
    runner_up: PairScore | None = next(
        (p for p in greedy.sorted_pairs if p.job_index == job_index and p.tech_index != winner_index),
        None,
    )

    if runner_up is None:
        sentences.append("No other technician was eligible for this job.")
    else:
        other = techs[runner_up.tech_index]
        if pair_sort_key(runner_up) < pair_sort_key(winner_pair):
            # Runner-up sorted ahead of the winner, so it was reached first
            # and skipped. Find out why from the log.
            skipped = next(
                (e for e in greedy.log if e.job_index == job_index and e.tech_index == runner_up.tech_index),
                None,
            )
            why = (
                "was already at capacity when this pair was reached"
                if skipped is not None and skipped.outcome == "tech-at-capacity"
                else "was skipped"
            )
            sentences.append(f"{other.name} scored higher ({fmt(runner_up.score)}) but {why}.")
        else:
            sentences.append(f"The runner-up was {other.name} at {fmt(runner_up.score)}.")

    return " ".join(sentences)


def explain_optimal_job(
    job_index: int,
    jobs: list[Job],
    techs: list[Technician],
    optimal: Assignment,
    greedy: Assignment,
    table: list[list[PairScore]],
) -> str:
    """Explain the optimal (brute force) choice for a job, contrasting it
    with greedy when they differ."""
    label = job_label(jobs[job_index], job_index)
    opt = optimal[job_index]
    gr = greedy[job_index]
    if opt is None:
        return f"{label} is unassigned in the optimal solution as well; no valid option exists."
    opt_score = fmt(table[opt][job_index].score)
    if gr == opt:
        return f"{label}: optimal agrees with greedy, {techs[opt].name} at {opt_score}."
    if gr is None:
        return f"{label}: optimal gives it to {techs[opt].name} ({opt_score}); greedy left it unassigned."
    gr_score = fmt(table[gr][job_index].score)
    return (
        f"{label}: optimal gives it to {techs[opt].name} ({opt_score}) instead of "
        f"{techs[gr].name} ({gr_score}). The lower score here is repaid by a better total elsewhere."
    )
