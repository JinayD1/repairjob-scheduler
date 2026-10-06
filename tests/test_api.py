import json
import unittest

from dispatch.api import config_payload, dispatch_payload, explore_payload, validate_pins
from dispatch.config import DEMO_PINS, GREEDY_TRAP_PINS, TECHNICIANS


def pins(preset):
    return [{"x": x, "y": y, "appliance": a} for x, y, a in preset]


class ApiTests(unittest.TestCase):
    def test_config_is_json_serialisable(self):
        payload = config_payload()
        json.dumps(payload)
        self.assertEqual(payload["grid"]["width"], 40)
        self.assertEqual(len(payload["techs"]), 3)
        self.assertEqual(len(payload["presets"]["demo"]), 10)
        self.assertEqual(payload["bridge_count"], 2)

    def test_validate_pins_drops_bad_input(self):
        home = TECHNICIANS[0].home
        raw = [
            {"x": 6, "y": 1, "appliance": "Washer"},
            {"x": 6, "y": 1, "appliance": "Oven"},  # duplicate cell
            {"x": 2, "y": 2, "appliance": "Oven"},  # inside a building
            {"x": home[0], "y": home[1], "appliance": "Oven"},  # a tech home
            {"x": 5, "y": 5, "appliance": "Toaster"},  # unknown appliance
            {"x": -1, "y": 0, "appliance": "Oven"},  # off the map
            {"x": "a", "y": 0, "appliance": "Oven"},  # not a number
            "garbage",
        ]
        self.assertEqual(validate_pins(raw), [(6, 1, "Washer")])
        self.assertEqual(validate_pins("not a list"), [])

    def test_validate_pins_caps_at_max_jobs(self):
        raw = [{"x": x, "y": 0, "appliance": "Oven"} for x in range(40)]
        self.assertEqual(len(validate_pins(raw)), 15)

    def test_dispatch_payload_matches_pipeline(self):
        payload = dispatch_payload(pins(GREEDY_TRAP_PINS), 0.6)
        json.dumps(payload)
        self.assertEqual(len(payload["jobs"]), 11)
        self.assertAlmostEqual(payload["greedy"]["total_score"], 5.590, places=2)
        self.assertAlmostEqual(payload["optimal"]["total_score"], 7.220, places=2)
        self.assertEqual(len(payload["explanations"]["greedy"]), 11)
        self.assertEqual(len(payload["explanations"]["optimal"]), 11)
        self.assertEqual(len(payload["greedy_routes"]), 3)
        for route in payload["greedy_routes"]:
            for leg in route["legs"]:
                self.assertEqual(len(leg["path"]) - 1, leg["distance"])

    def test_dispatch_payload_handles_inf_and_weights(self):
        payload = dispatch_payload(pins(DEMO_PINS), 1.5)  # clamped to 1.0
        self.assertEqual(payload["weights"]["w_distance"], 1.0)
        self.assertEqual(payload["weights"]["w_specialty"], 0.0)
        empty = dispatch_payload([], 0.6)
        self.assertEqual(empty["jobs"], [])
        self.assertIsNone(empty["max_distance"] or None)

    def test_brute_force_skipped_above_limit(self):
        raw = [{"x": 1 + i * 3, "y": 0, "appliance": "Washer"} for i in range(13)]
        payload = dispatch_payload(raw, 0.6)
        self.assertIsNone(payload["optimal"])
        self.assertIsNone(payload["optimal_routes"])
        self.assertIsNone(payload["explanations"]["optimal"])

    def test_explore_payload(self):
        payload = explore_payload(0, 33, 22)
        json.dumps(payload)
        self.assertEqual(len(payload["path"]) - 1, payload["distance"])
        self.assertLess(len(payload["astar_explored"]), len(payload["dijkstra_explored"]))
        blocked = explore_payload(0, 2, 2)  # inside a building
        self.assertIsNone(blocked["path"])
        self.assertIsNone(blocked["distance"])


if __name__ == "__main__":
    unittest.main()
