import dataclasses
import itertools
import math
import random
import unittest

from dispatch.bruteforce import brute_force_assign
from dispatch.config import TECHNICIANS
from dispatch.greedy import assignment_score, classify_unassigned, greedy_assign, pair_sort_key
from dispatch.scoring import (
    DEFAULT_WEIGHTS,
    closeness,
    index_pairs,
    max_reachable_distance,
    score_all_pairs,
    specialty_norm,
)
from dispatch.types import APPLIANCE_TYPES, Job, PairScore, Weights

INF = math.inf


def make_jobs(types):
    return [Job(i, (i, 0), a) for i, a in enumerate(types)]


def with_capacity(techs, capacity):
    return [dataclasses.replace(t, capacity=capacity) for t in techs]


def pair(t, j, score, distance=0.0, eligible=True):
    return PairScore(t, j, distance, 0.0, 5 if eligible else 1, 1.0, score, eligible,
                     None if eligible else "rating")


class ScoringTests(unittest.TestCase):
    def test_specialty_norm(self):
        self.assertEqual(specialty_norm(1), 0)
        self.assertEqual(specialty_norm(3), 0.5)
        self.assertEqual(specialty_norm(5), 1)

    def test_closeness(self):
        self.assertEqual(closeness(0, 20), 1)
        self.assertEqual(closeness(20, 20), 0)
        self.assertAlmostEqual(closeness(5, 20), 0.75)
        self.assertEqual(closeness(INF, 20), 0)
        self.assertEqual(closeness(0, 0), 1)

    def test_max_reachable_distance_ignores_inf(self):
        self.assertEqual(max_reachable_distance([[3, INF], [7, 2]]), 7)
        self.assertEqual(max_reachable_distance([[INF]]), 0)

    def test_score_all_pairs(self):
        jobs = make_jobs(["Washer", "Fridge", "Oven"])
        distances = [[0, 10, 20], [10, 0, INF], [20, 10, 0]]
        table = index_pairs(score_all_pairs(TECHNICIANS, jobs, distances, DEFAULT_WEIGHTS), 3, 3)
        # Maria -> Washer: distance 0, rating 5 => 1.0
        self.assertAlmostEqual(table[0][0].score, 1.0)
        # Maria -> Oven: closeness 0, rating 4 (norm 0.75) => 0.4 * 0.75
        self.assertAlmostEqual(table[0][2].score, 0.3)
        # Dev -> Oven: unreachable (and rating 1); unreachable wins
        self.assertFalse(table[1][2].eligible)
        self.assertEqual(table[1][2].ineligible_reason, "unreachable")

    def test_rating_1_is_ineligible_regardless_of_distance(self):
        jobs = make_jobs(["Oven"])
        table = index_pairs(score_all_pairs(TECHNICIANS, jobs, [[0], [0], [0]], DEFAULT_WEIGHTS), 3, 1)
        self.assertFalse(table[1][0].eligible)
        self.assertEqual(table[1][0].ineligible_reason, "rating")
        self.assertAlmostEqual(table[1][0].score, 0.6)  # still computed for display

    def test_weights(self):
        jobs = make_jobs(["Fridge"])
        d = [[10], [20], [20]]
        only_dist = score_all_pairs(TECHNICIANS, jobs, d, Weights(1, 0))[0]
        only_spec = score_all_pairs(TECHNICIANS, jobs, d, Weights(0, 1))[0]
        self.assertAlmostEqual(only_dist.score, 0.5)  # 1 - 10/20
        self.assertAlmostEqual(only_spec.score, 0.25)  # Maria Fridge 2


class GreedyTests(unittest.TestCase):
    def test_sort_key_order(self):
        pairs = [pair(1, 1, 0.5, 5), pair(0, 1, 0.5, 5), pair(0, 0, 0.5, 5), pair(2, 2, 0.5, 3), pair(2, 0, 0.9, 10)]
        order = [(p.tech_index, p.job_index) for p in sorted(pairs, key=pair_sort_key)]
        self.assertEqual(order, [(2, 0), (2, 2), (0, 0), (0, 1), (1, 1)])

    def test_floating_point_ties(self):
        a = pair(0, 0, 0.1 + 0.2, 10)  # 0.30000000000000004
        b = pair(1, 1, 0.3, 5)
        self.assertIs(sorted([a, b], key=pair_sort_key)[0], b)  # tied, shorter distance first

    def test_expert_wins_when_nothing_conflicts(self):
        jobs = make_jobs(["Washer", "Fridge", "Oven"])
        pairs = score_all_pairs(TECHNICIANS, jobs, [[10] * 3] * 3, DEFAULT_WEIGHTS)
        result = greedy_assign(TECHNICIANS, 3, pairs)
        self.assertEqual(result.assignment, [0, 1, 2])
        self.assertEqual(result.unassigned_reasons, {})

    def test_capacity_and_log(self):
        jobs = make_jobs(["Washer"] * 5)
        distances = [[0] * 5, [20] * 5, [20] * 5]
        result = greedy_assign(TECHNICIANS, 5, score_all_pairs(TECHNICIANS, jobs, distances, DEFAULT_WEIGHTS))
        self.assertEqual(result.assignment, [0, 0, 0, 0, 1])  # 5th washer spills to Dev (Washer 3)
        self.assertTrue(any(e.tech_index == 0 and e.job_index == 4 and e.outcome == "tech-at-capacity"
                            for e in result.log))
        self.assertEqual(sum(e.outcome == "assigned" for e in result.log), 5)

    def test_unassigned_reasons(self):
        techs = with_capacity(TECHNICIANS, 1)
        jobs = make_jobs(["Oven", "Oven", "Oven", "Washer", "Oven"])
        distances = [[5, 5, 5, INF, 5]] * 3
        pairs = score_all_pairs(techs, jobs, distances, DEFAULT_WEIGHTS)
        result = greedy_assign(techs, 5, pairs)
        self.assertEqual(sum(t is not None for t in result.assignment), 2)
        self.assertEqual(result.unassigned_reasons[3], "unreachable")
        self.assertEqual(list(result.unassigned_reasons.values()).count("all-eligible-at-capacity"), 2)

    def test_no_eligible_tech(self):
        techs = [dataclasses.replace(t, ratings={**t.ratings, "Oven": 1}) for t in TECHNICIANS]
        pairs = score_all_pairs(techs, make_jobs(["Oven"]), [[3], [3], [3]], DEFAULT_WEIGHTS)
        result = greedy_assign(techs, 1, pairs)
        self.assertEqual(result.assignment, [None])
        self.assertEqual(classify_unassigned(0, pairs), "no-eligible-tech")

    def test_never_assigns_ineligible_even_if_best_score(self):
        pairs = score_all_pairs(TECHNICIANS, make_jobs(["Oven"]), [[30], [0], [30]], DEFAULT_WEIGHTS)
        self.assertEqual(greedy_assign(TECHNICIANS, 1, pairs).assignment, [2])  # Sam, not Dev

    def test_independent_of_input_order(self):
        jobs = make_jobs(["Washer", "Fridge", "Oven", "Fridge", "Washer"])
        distances = [[3, 9, 12, 4, 3], [8, 2, 7, 6, 8], [10, 5, 1, 9, 10]]
        pairs = score_all_pairs(TECHNICIANS, jobs, distances, DEFAULT_WEIGHTS)
        a = greedy_assign(TECHNICIANS, 5, pairs)
        b = greedy_assign(TECHNICIANS, 5, list(reversed(pairs)))
        self.assertEqual(a.assignment, b.assignment)
        self.assertEqual(a.log, b.log)


def naive_optimal(techs, job_count, table):
    """Reference oracle: try all (techs + 1) ** job_count assignments with no
    pruning at all. Obviously correct, only usable for tiny inputs."""
    best = 0.0
    choices = list(range(len(techs))) + [None]
    for assignment in itertools.product(choices, repeat=job_count):
        load = [0] * len(techs)
        ok = True
        for j, t in enumerate(assignment):
            if t is None:
                continue
            if not table[t][j].eligible:
                ok = False
            load[t] += 1
            if load[t] > techs[t].capacity:
                ok = False
        if ok:
            best = max(best, assignment_score(list(assignment), table))
    return best


class BruteForceTests(unittest.TestCase):
    def test_obvious_optimum(self):
        jobs = make_jobs(["Washer", "Fridge", "Oven"])
        table = index_pairs(score_all_pairs(TECHNICIANS, jobs, [[10] * 3] * 3, DEFAULT_WEIGHTS), 3, 3)
        self.assertEqual(brute_force_assign(TECHNICIANS, 3, table).assignment, [0, 1, 2])

    def test_beats_greedy_on_hand_built_trap(self):
        # Capacity 1. Job 0: Maria 0.9, Dev 0.8. Job 1: Maria 0.7 only.
        # Greedy: Maria/job0 = 0.9 total. Optimal: Dev/job0 + Maria/job1 = 1.5.
        techs = with_capacity(TECHNICIANS[:2], 1)
        table = [[pair(0, 0, 0.9), pair(0, 1, 0.7)], [pair(1, 0, 0.8), pair(1, 1, 0.0, eligible=False)]]
        greedy = greedy_assign(techs, 2, [p for row in table for p in row])
        self.assertEqual(greedy.assignment, [0, None])
        optimal = brute_force_assign(techs, 2, table)
        self.assertEqual(optimal.assignment, [1, 0])
        self.assertAlmostEqual(optimal.total_score, 1.5)

    def test_respects_capacity_and_eligibility(self):
        jobs = make_jobs(["Oven"] * 10)
        table = index_pairs(score_all_pairs(TECHNICIANS, jobs, [[3] * 10, [1] * 10, [5] * 10], DEFAULT_WEIGHTS), 3, 10)
        result = brute_force_assign(TECHNICIANS, 10, table)
        counts = [result.assignment.count(t) for t in range(3)]
        self.assertEqual(counts, [4, 0, 4])
        self.assertEqual(result.assignment.count(None), 2)

    def test_matches_naive_enumeration(self):
        rng = random.Random(99)
        for _ in range(40):
            n = rng.randint(2, 6)
            jobs = make_jobs([rng.choice(APPLIANCE_TYPES) for _ in range(n)])
            techs = [dataclasses.replace(t, capacity=rng.randint(1, 3)) for t in TECHNICIANS]
            distances = [[INF if rng.random() < 0.1 else rng.randint(0, 39) for _ in jobs] for _ in techs]
            pairs = score_all_pairs(techs, jobs, distances, DEFAULT_WEIGHTS)
            table = index_pairs(pairs, 3, n)
            result = brute_force_assign(techs, n, table)
            self.assertAlmostEqual(result.total_score, naive_optimal(techs, n, table), places=9)
            self.assertAlmostEqual(assignment_score(result.assignment, table), result.total_score, places=9)
            greedy = greedy_assign(techs, n, pairs)
            self.assertLessEqual(greedy.total_score, result.total_score + 1e-9)

    def test_twelve_jobs_is_fast(self):
        import time

        rng = random.Random(2024)
        jobs = make_jobs([rng.choice(APPLIANCE_TYPES) for _ in range(12)])
        distances = [[rng.randint(0, 59) for _ in jobs] for _ in TECHNICIANS]
        table = index_pairs(score_all_pairs(TECHNICIANS, jobs, distances, DEFAULT_WEIGHTS), 3, 12)
        t0 = time.perf_counter()
        result = brute_force_assign(TECHNICIANS, 12, table)
        self.assertLess(time.perf_counter() - t0, 5.0)
        self.assertEqual(len(result.assignment), 12)


if __name__ == "__main__":
    unittest.main()
