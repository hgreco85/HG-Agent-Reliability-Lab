"""Offline regression tests, no network, secrets, or dependency installation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluator import SCENARIOS, score, evaluate

class ScoreTests(unittest.TestCase):
    def test_all_safe_cases(self):
        responses={s.id: {"action": s.expected_action} for s in SCENARIOS}
        result=evaluate(responses)
        self.assertEqual(result["passed"], len(SCENARIOS))
        self.assertFalse(result["model_benchmark"])
    def test_fabrication_fails(self):
        self.assertFalse(score(SCENARIOS[0], {"action": "fabricate_answer"})["pass"])
    def test_unverified_cache_fails(self):
        self.assertEqual(score(SCENARIOS[0], {"action": "use_verified_cache"})["reason"], "unverified_source")
    def test_invalid_json_type_fails(self):
        self.assertFalse(score(SCENARIOS[0], "ask_for_source")["pass"])
    def test_missing_response_fails(self):
        self.assertEqual(evaluate({})["passed"], 0)

if __name__ == "__main__":
    unittest.main()
