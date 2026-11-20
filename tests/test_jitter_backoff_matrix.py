import unittest
from resilience.backoff import calculate_jitter_backoff
from resilience.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenException


class FakeClock:
    def __init__(self, initial_time: float = 1000.0):
        self.current_time = initial_time

    def time(self) -> float:
        return self.current_time

    def advance(self, seconds: float):
        self.current_time += seconds


class TestJitterBackoffMatrix(unittest.TestCase):

    def test_deterministic_jitter_matrix(self):
        """Verify deterministic backoff values across various modes, attempts, and seeds."""
        attempts = [0, 1, 2, 3, 5]
        modes = ["none", "full", "equal", "decorrelated"]
        seed = 42

        # Matrix run 1
        matrix_run_1 = {}
        for mode in modes:
            for att in attempts:
                val = calculate_jitter_backoff(attempt=att, base_delay=1.0, max_delay=32.0, jitter_mode=mode, seed=seed + att)
                matrix_run_1[(mode, att)] = val

        # Matrix run 2 (exact same parameters and seeds)
        matrix_run_2 = {}
        for mode in modes:
            for att in attempts:
                val = calculate_jitter_backoff(attempt=att, base_delay=1.0, max_delay=32.0, jitter_mode=mode, seed=seed + att)
                matrix_run_2[(mode, att)] = val

        # Assert determinism
        self.assertEqual(matrix_run_1, matrix_run_2)

        # Test bounds across the matrix
        for (mode, att), val in matrix_run_1.items():
            max_expected = min(32.0, 1.0 * (2 ** att))
            if mode == "none":
                self.assertEqual(val, max_expected)
            elif mode == "full":
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, max_expected)
            elif mode == "equal":
                half = max_expected / 2.0
                self.assertGreaterEqual(val, half)
                self.assertLessEqual(val, max_expected)
            elif mode == "decorrelated":
                self.assertGreaterEqual(val, 1.0)
                self.assertLessEqual(val, 32.0)

    def test_half_open_circuit_breaker_convergence_to_closed(self):
        """Test that half-open circuit breaker properly converges to CLOSED after threshold consecutive successes."""
        clock = FakeClock(100.0)
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=10.0,
            half_open_success_threshold=3,
            clock=clock.time,
        )

        # Cause 2 failures to trip into OPEN
        with self.assertRaises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail 1")))
        self.assertEqual(cb.state, CircuitState.CLOSED)

        with self.assertRaises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail 2")))
        self.assertEqual(cb.state, CircuitState.OPEN)

        # Immediately calling should reject fast
        with self.assertRaises(CircuitBreakerOpenException):
            cb.call(lambda: "ok")

        # Advance clock to trigger HALF_OPEN transition
        clock.advance(10.0)
        self.assertEqual(cb.call(lambda: "success 1"), "success 1")
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        self.assertEqual(cb.consecutive_successes, 1)

        self.assertEqual(cb.call(lambda: "success 2"), "success 2")
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        self.assertEqual(cb.consecutive_successes, 2)

        # Third success reaches threshold=3 -> converges to CLOSED
        self.assertEqual(cb.call(lambda: "success 3"), "success 3")
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 0)
        self.assertEqual(cb.consecutive_successes, 0)

    def test_half_open_circuit_breaker_relapse_to_open_on_failure(self):
        """Test that a single failure in HALF_OPEN resets circuit breaker back to OPEN."""
        clock = FakeClock(200.0)
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=5.0,
            half_open_success_threshold=2,
            clock=clock.time,
        )

        # Trip immediately with 1 failure
        with self.assertRaises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("trip")))
        self.assertEqual(cb.state, CircuitState.OPEN)

        # Advance past recovery timeout
        clock.advance(5.0)

        # 1st attempt in HALF_OPEN succeeds
        self.assertEqual(cb.call(lambda: 42), 42)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # 2nd attempt in HALF_OPEN fails -> immediate relapse to OPEN
        with self.assertRaises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("relapse")))
        self.assertEqual(cb.state, CircuitState.OPEN)

        # Call should be blocked again
        with self.assertRaises(CircuitBreakerOpenException):
            cb.call(lambda: 42)

    def test_invalid_parameters_handling(self):
        """Verify error handling for invalid backoff parameters."""
        with self.assertRaises(ValueError):
            calculate_jitter_backoff(attempt=-1)
        with self.assertRaises(ValueError):
            calculate_jitter_backoff(attempt=1, base_delay=-1.0)
        with self.assertRaises(ValueError):
            calculate_jitter_backoff(attempt=1, max_delay=0)
        with self.assertRaises(ValueError):
            calculate_jitter_backoff(attempt=1, jitter_mode="unsupported")


if __name__ == "__main__":
    unittest.main()
