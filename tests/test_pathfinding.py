import math
import random
import unittest

from dispatch.astar import astar
from dispatch.config import BRIDGES, RIVER_SEGMENTS, TECHNICIANS, build_city_grid
from dispatch.dijkstra import build_distance_matrices, dijkstra, distance_to
from dispatch.grid import block_rect, create_grid, manhattan, random_grid
from dispatch.types import Job


def assert_valid_path(test, grid, path, start, goal):
    test.assertEqual(path[0], start)
    test.assertEqual(path[-1], goal)
    for i, (x, y) in enumerate(path):
        test.assertTrue(grid.walkable[y][x])
        if i > 0:
            test.assertEqual(manhattan(path[i - 1], path[i]), 1)


class DijkstraTests(unittest.TestCase):
    def test_manhattan_distances_on_empty_grid(self):
        grid = create_grid(5, 5)
        run = dijkstra(grid, (0, 0))
        self.assertEqual(distance_to(run, (4, 4)), 8)
        self.assertEqual(distance_to(run, (2, 1)), 3)
        self.assertEqual(distance_to(run, (0, 0)), 0)

    def test_routes_around_a_wall(self):
        grid = create_grid(5, 5)
        block_rect(grid, 2, 0, 1, 4)  # wall at x=2, rows 0..3
        run = dijkstra(grid, (0, 0))
        self.assertEqual(distance_to(run, (4, 0)), 12)  # detour through row 4

    def test_unreachable_is_inf(self):
        grid = create_grid(5, 5)
        block_rect(grid, 2, 0, 1, 5)
        run = dijkstra(grid, (0, 0))
        self.assertEqual(distance_to(run, (4, 0)), math.inf)

    def test_early_exit_with_target(self):
        grid = create_grid(20, 20)
        full = dijkstra(grid, (0, 0))
        early = dijkstra(grid, (0, 0), target=(1, 1))
        self.assertLess(len(early.explored), len(full.explored))
        self.assertEqual(distance_to(early, (1, 1)), 2)

    def test_distance_matrices(self):
        grid = create_grid(10, 10)
        techs = [
            type(t)(**{**t.__dict__, "home": (i, 0)}) for i, t in enumerate(TECHNICIANS)
        ]
        jobs = [Job(0, (5, 5), "Washer"), Job(1, (9, 9), "Oven")]
        tech_to_job, job_to_job = build_distance_matrices(grid, techs, jobs)
        self.assertEqual(tech_to_job, [[10, 18], [9, 17], [8, 16]])
        self.assertEqual(job_to_job, [[0, 8], [8, 0]])


class AStarTests(unittest.TestCase):
    def test_shortest_path_on_empty_grid(self):
        grid = create_grid(6, 6)
        r = astar(grid, (0, 0), (5, 5))
        self.assertEqual(r.distance, 10)
        assert_valid_path(self, grid, r.path, (0, 0), (5, 5))

    def test_unreachable(self):
        grid = create_grid(5, 5)
        block_rect(grid, 2, 0, 1, 5)
        r = astar(grid, (0, 0), (4, 0))
        self.assertIsNone(r.path)
        self.assertEqual(r.distance, math.inf)

    def test_start_equals_goal(self):
        r = astar(create_grid(3, 3), (1, 1), (1, 1))
        self.assertEqual(r.path, [(1, 1)])
        self.assertEqual(r.distance, 0)

    def test_explores_far_fewer_cells_than_dijkstra(self):
        grid = create_grid(30, 30)
        a = astar(grid, (0, 0), (29, 29))
        d = dijkstra(grid, (0, 0), target=(29, 29))
        self.assertEqual(len(d.explored), 900)  # every cell is closer than the goal
        self.assertLess(len(a.explored), 100)  # the h tie-break walks straight there
        self.assertEqual(a.distance, 58)

    def test_deterministic(self):
        grid = random_grid(20, 20, 0.3, 7)
        a = astar(grid, (0, 0), (19, 19))
        b = astar(grid, (0, 0), (19, 19))
        self.assertEqual(a.path, b.path)
        self.assertEqual(a.explored, b.explored)

    def test_path_lengths_equal_dijkstra_on_random_grids(self):
        """The core correctness test: for many random grids and start/goal
        pairs, A*'s path length must equal Dijkstra's distance exactly."""
        rng = random.Random(12345)
        checked = reachable = 0
        for trial in range(40):
            w, h = rng.randint(8, 32), rng.randint(8, 32)
            grid = random_grid(w, h, 0.15 + rng.random() * 0.3, trial * 1000 + 17)
            cells = [(x, y) for y in range(h) for x in range(w) if grid.walkable[y][x]]
            if len(cells) < 2:
                continue
            for _ in range(10):
                start, goal = rng.choice(cells), rng.choice(cells)
                expected = distance_to(dijkstra(grid, start), goal)
                a = astar(grid, start, goal)
                self.assertEqual(a.distance, expected)
                checked += 1
                if math.isfinite(expected):
                    assert_valid_path(self, grid, a.path, start, goal)
                    reachable += 1
                else:
                    self.assertIsNone(a.path)
        self.assertGreater(checked, 300)
        self.assertGreater(reachable, 50)


class CityGridTests(unittest.TestCase):
    def setUp(self):
        self.grid = build_city_grid()

    def test_size(self):
        self.assertEqual((self.grid.width, self.grid.height), (40, 28))

    def test_homes_walkable_and_connected(self):
        run = dijkstra(self.grid, TECHNICIANS[0].home)
        for tech in TECHNICIANS:
            x, y = tech.home
            self.assertTrue(self.grid.walkable[y][x])
            self.assertTrue(math.isfinite(distance_to(run, tech.home)))

    def test_exactly_two_river_crossings(self):
        crossings = []
        for x in range(self.grid.width):
            rows = next(rows for x0, x1, rows in RIVER_SEGMENTS if x0 <= x <= x1)
            if self.grid.walkable[rows[0]][x] and self.grid.walkable[rows[1]][x]:
                crossings.append(x)
        self.assertEqual(crossings, [b[0] for b in BRIDGES])
        self.assertEqual(len(crossings), 2)

    def test_removing_bridges_disconnects_north_from_south(self):
        grid = build_city_grid()
        for x, rows in BRIDGES:
            grid.walkable[rows[0]][x] = False
            grid.walkable[rows[1]][x] = False
        run = dijkstra(grid, TECHNICIANS[0].home)  # Maria, north
        self.assertEqual(distance_to(run, TECHNICIANS[2].home), math.inf)  # Sam, south

    def test_every_walkable_cell_reachable(self):
        run = dijkstra(self.grid, TECHNICIANS[1].home)
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                if self.grid.walkable[y][x]:
                    self.assertTrue(math.isfinite(distance_to(run, (x, y))))


if __name__ == "__main__":
    unittest.main()
