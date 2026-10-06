import unittest

from dispatch.config import (
    BRUTE_FORCE_MAX_JOBS,
    DEMO_PINS,
    GREEDY_TRAP_PINS,
    GRID_WIDTH,
    TECHNICIANS,
    build_city_grid,
    pins_to_jobs,
)
from dispatch.explain import UNASSIGNED_REASON_TEXT, explain_job, explain_optimal_job
from dispatch.grid import create_grid
from dispatch.pipeline import canonical_job_order, job_counts, run_dispatch, total_route_distance
from dispatch.routing import build_routes, nearest_next_order
from dispatch.scoring import DEFAULT_WEIGHTS
from dispatch.types import Job, Weights

GRID = build_city_grid()


def job(x, y, appliance):
    return Job(y * GRID_WIDTH + x, (x, y), appliance)


SAMPLE = [
    job(10, 5, "Washer"),
    job(30, 2, "Fridge"),
    job(20, 22, "Oven"),
    job(5, 22, "Fridge"),
    job(33, 22, "Washer"),
    job(15, 11, "Oven"),
    job(25, 16, "Washer"),
]


def run(jobs, weights=DEFAULT_WEIGHTS):
    return run_dispatch(GRID, TECHNICIANS, jobs, weights, BRUTE_FORCE_MAX_JOBS)


class RoutingTests(unittest.TestCase):
    def test_goes_to_closest_remaining(self):
        home = [10, 2, 6]
        jj = [[0, 3, 1], [3, 0, 9], [1, 9, 0]]
        self.assertEqual(nearest_next_order([0, 1, 2], home, jj), [1, 0, 2])

    def test_only_given_jobs(self):
        jj = [[0, 1, 1], [1, 0, 1], [1, 1, 0]]
        self.assertEqual(nearest_next_order([0, 2], [5, 1, 3], jj), [2, 0])
        self.assertEqual(nearest_next_order([], [5, 1, 3], jj), [])

    def test_ties_go_to_lower_index(self):
        jj = [[0, 2, 2], [2, 0, 2], [2, 2, 0]]
        self.assertEqual(nearest_next_order([2, 1, 0], [4, 4, 4], jj), [0, 1, 2])

    def test_nearest_next_is_not_optimal(self):
        # Number line, home at 0, jobs at +1, +10, -9.
        pos = [1, 10, -9]
        home = [abs(p) for p in pos]
        jj = [[abs(a - b) for b in pos] for a in pos]

        def cost(order):
            total, cur = 0, None
            for j in order:
                total += home[j] if cur is None else jj[cur][j]
                cur = j
            return total

        nn = nearest_next_order([0, 1, 2], home, jj)
        self.assertEqual(nn, [0, 1, 2])
        self.assertEqual(cost(nn), 29)
        self.assertEqual(cost([2, 0, 1]), 28)  # strictly better

    def test_build_routes(self):
        grid = create_grid(12, 12)
        import dataclasses

        techs = [dataclasses.replace(TECHNICIANS[0], home=(0, 0)), TECHNICIANS[1], TECHNICIANS[2]]
        jobs = [Job(0, (5, 0), "Washer"), Job(1, (2, 0), "Washer"), Job(2, (5, 5), "Washer")]
        t2j = [[5, 2, 10], [99] * 3, [99] * 3]
        j2j = [[0, 3, 5], [3, 0, 8], [5, 8, 0]]
        routes = build_routes(grid, techs, jobs, [0, 0, 0], t2j, j2j)
        maria = routes[0]
        self.assertEqual(maria.stops, [1, 0, 2])
        self.assertEqual(maria.total_distance, 2 + 3 + 5)
        for leg in maria.legs:
            self.assertEqual(leg.path[0], leg.start)
            self.assertEqual(leg.path[-1], leg.end)
            self.assertEqual(len(leg.path) - 1, leg.distance)
        self.assertEqual(routes[1].stops, [])
        self.assertEqual(routes[1].total_distance, 0)


class PipelineTests(unittest.TestCase):
    def test_independent_of_pin_order(self):
        a = run(SAMPLE)
        b = run(list(reversed(SAMPLE)))
        c = run([SAMPLE[3], SAMPLE[0], SAMPLE[6], SAMPLE[1], SAMPLE[5], SAMPLE[2], SAMPLE[4]])
        self.assertEqual(a.jobs, b.jobs)
        self.assertEqual(a.greedy.assignment, b.greedy.assignment)
        self.assertEqual(a.greedy.log, b.greedy.log)
        self.assertEqual(a.greedy_routes, b.greedy_routes)
        self.assertEqual(a.greedy.assignment, c.greedy.assignment)

    def test_canonical_order(self):
        ordered = canonical_job_order(SAMPLE)
        keys = [(j.cell[1], j.cell[0]) for j in ordered]
        self.assertEqual(keys, sorted(keys))

    def test_all_assigned_and_routed(self):
        r = run(SAMPLE)
        self.assertTrue(all(t is not None for t in r.greedy.assignment))
        routed = sorted(j for route in r.greedy_routes for j in route.stops)
        self.assertEqual(routed, list(range(len(SAMPLE))))
        self.assertGreater(total_route_distance(r.greedy_routes), 0)
        counts = job_counts(r.greedy.assignment, 3)
        self.assertEqual(sum(counts), len(SAMPLE))
        self.assertTrue(all(c <= 4 for c in counts))

    def test_route_legs_match_distance_matrices(self):
        r = run(SAMPLE)
        for route in r.greedy_routes:
            prev = None
            for leg in route.legs:
                expected = r.tech_to_job[route.tech_index][leg.job_index] if prev is None else r.job_to_job[prev][leg.job_index]
                self.assertEqual(leg.distance, expected)
                prev = leg.job_index

    def test_brute_force_skipped_above_limit(self):
        many = [job(1 + i * 3, 0, "Washer") for i in range(13)]
        r = run(many)
        self.assertIsNone(r.optimal)
        self.assertEqual(len(r.greedy.unassigned_reasons), 1)  # 13 washers, 12 slots

    def test_optimal_never_worse_than_greedy(self):
        r = run(SAMPLE)
        self.assertGreaterEqual(r.optimal.total_score, r.greedy.total_score - 1e-9)

    def test_weights_change_scores(self):
        a = run(SAMPLE, Weights(1, 0))
        b = run(SAMPLE, Weights(0, 1))
        self.assertNotAlmostEqual(a.table[0][0].score, b.table[0][0].score)

    def test_empty(self):
        r = run([])
        self.assertEqual(r.greedy.assignment, [])
        self.assertEqual(r.greedy.total_score, 0)
        self.assertEqual(r.optimal.total_score, 0)


class ExplanationTests(unittest.TestCase):
    def test_assigned_job_explanation(self):
        r = run(SAMPLE)
        for j in range(len(r.jobs)):
            text = explain_job(j, r.jobs, TECHNICIANS, r.greedy)
            self.assertIn(f"Job {j + 1} ({r.jobs[j].appliance})", text)
            self.assertIn(f"went to {TECHNICIANS[r.greedy.assignment[j]].name}", text)

    def test_capacity_mentioned_when_higher_scorer_was_full(self):
        washers = [job(i, 7, "Washer") for i in range(1, 7)]  # six washers next to Maria
        r = run(washers)
        spill = [j for j, t in enumerate(r.greedy.assignment) if t != 0]
        self.assertEqual(len(spill), 2)
        for j in spill:
            text = explain_job(j, r.jobs, TECHNICIANS, r.greedy)
            self.assertIn("Maria scored higher", text)
            self.assertIn("already at capacity", text)

    def test_unassigned_explanation(self):
        r = run([job(1 + i * 3, 0, "Washer") for i in range(13)])
        j = next(iter(r.greedy.unassigned_reasons))
        text = explain_job(j, r.jobs, TECHNICIANS, r.greedy)
        self.assertIn("is unassigned", text)
        self.assertIn(UNASSIGNED_REASON_TEXT["all-eligible-at-capacity"], text)

    def test_optimal_explanation(self):
        r = run(SAMPLE)
        for j in range(len(r.jobs)):
            text = explain_optimal_job(j, r.jobs, TECHNICIANS, r.optimal.assignment, r.greedy.assignment, r.table)
            self.assertIn(f"Job {j + 1}", text)


class PresetTests(unittest.TestCase):
    def test_pins_walkable(self):
        for x, y, _ in DEMO_PINS + GREEDY_TRAP_PINS:
            self.assertTrue(GRID.walkable[y][x])

    def test_demo_all_assigned(self):
        r = run(pins_to_jobs(DEMO_PINS))
        self.assertTrue(all(t is not None for t in r.greedy.assignment))

    def test_greedy_trap_gap(self):
        r = run(pins_to_jobs(GREEDY_TRAP_PINS))
        ratio = r.greedy.total_score / r.optimal.total_score
        self.assertLess(ratio, 0.85)
        # Same numbers as the TypeScript version.
        self.assertAlmostEqual(r.greedy.total_score, 5.590, places=2)
        self.assertAlmostEqual(r.optimal.total_score, 7.220, places=2)


if __name__ == "__main__":
    unittest.main()
