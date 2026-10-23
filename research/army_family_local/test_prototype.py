import json
import unittest

from prototype import build, overlap, parse_code


def row(day, code, attacks, triples):
    return {"day": day, "code": code, "n": attacks, "s0": 0, "s1": 0,
            "s2": attacks - triples, "s3": triples,
            "destruction": 90 * attacks, "duration": 150 * attacks}


class FamilyPrototypeTests(unittest.TestCase):
    def setUp(self):
        self.static = {
            4000001: {"name": "Thrower", "housing_space": 20},
            4000002: {"name": "Titan", "housing_space": 20},
            4000003: {"name": "Barbarian", "housing_space": 1},
            4000004: {"name": "Dragon", "housing_space": 20},
        }

    def test_main_troops_ignore_setup_and_siege(self):
        troops, setup = parse_code("h0e5i1x88u10x1-3x3-1x99s3x2")
        self.assertEqual(troops, {4000001: 10, 4000003: 3, 4000099: 1})
        self.assertEqual(setup, (26000002, 90000005))

    def test_overlap_is_housing_weighted(self):
        self.assertEqual(overlap({1: 160, 2: 40}, {1: 160, 3: 40}), 0.8)

    def test_stable_family_and_rank_change(self):
        first, other = "u10x1s3x2h0e5", "u10x4s3x2h0e5"
        changed_setup = "u10x1s3x3h0e7"
        rows = [row("2026-09-18", first, 300, 150),
                row("2026-09-18", changed_setup, 100, 60),
                row("2026-09-18", other, 200, 80),
                row("2026-09-19", first, 100, 40),
                row("2026-09-19", changed_setup, 100, 55),
                row("2026-09-19", other, 300, 150)]
        result = build(rows, self.static, "2026-09-18", "2026-09-19")
        self.assertEqual(result["familyCount"], 2)
        current = {point["name"]: point for point in result["daily"]
                   if point["day"] == "2026-09-19"}
        self.assertEqual(current["Thrower"]["attackCount"], 200)
        self.assertEqual(current["Thrower"]["threeStarCount"], 95)
        self.assertEqual(current["Thrower"]["priorDayRank"], 1)
        self.assertEqual(current["Thrower"]["rankChange"], -1)
        self.assertEqual(len(current["Thrower"]["setupVariants"]), 2)
        self.assertEqual(sum(p["storedDaily"]["attackCount"] for p in result["daily"]
                             if p["day"] == "2026-09-19"), 500)
        replay = build(rows, self.static, "2026-09-18", "2026-09-19",
                       registry=json.loads(json.dumps(result))["families"])
        self.assertEqual([(f["id"], f["name"]) for f in result["families"]],
                         [(f["id"], f["name"]) for f in replay["families"]])

    def test_unmatched_army_is_reviewed(self):
        rows = [row("2026-09-18", "u10x1", 100, 50),
                row("2026-09-19", "u10x4", 20, 10)]
        result = build(rows, self.static, "2026-09-18", "2026-09-19", max_families=1)
        self.assertEqual(result["review"][1]["attackCount"], 20)
        self.assertEqual(len([point for point in result["daily"]
                              if point["day"] == "2026-09-19"]), 0)


if __name__ == "__main__":
    unittest.main()
