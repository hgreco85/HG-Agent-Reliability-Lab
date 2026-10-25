import unittest
import random
from resilience.backoff import full_jitter_backoff, equal_jitter_backoff, decorrelated_jitter_backoff
from resilience.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenException


class SimulatedClock:
    def __init__(self, initial_time: float = 0.0) -> None:
        self.current_time = initial_time

    def __call__(self) -> float:
        return self.current_time

    def advance(self, seconds: float) -> None:
        self.current_time += seconds


class TestJitterBackoffMatrix(unittest.TestCase):
    def test_deterministic_full_jitter_bounds_and_reproducibility(self):
        base_delay = 1.0
        max_delay = 32.0
        seed = 42

        rng1 = random.Random(seed)
        run1 = [full_jitter_backoff(i, base_delay=base_delay, max_delay=max_delay, rng=rng1) for i in range(10)]

        rng2 = random.Random(seed)
        run2 = [full_jitter_backoff(i, base_delay=base_delay, max_delay=max_delay, rng=rng2) for i in range(10)]

        self.assertEqual(run1, run2, "Deterministic seed must produce identical jitter values across runs")

        for attempt, delay in enumerate(run1):
            ceiling = min(max_delay, base_delay * (2 ** attempt))
            self.assertGreaterEqual(delay, 0.0, f"Delay {delay} must be >= 0")
            self.assertLessEqual(delay, ceiling, f"Delay {delay} must be <= ceiling {ceiling}")

    def test_deterministic_equal_and_decorrelated_jitter_matrix(self):
        seed = 1337
        rng = random.Random(seed)
        base_delay = 2.0
        max_delay = 50.0

        for attempt in range(6):
            delay = equal_jitter_backoff(attempt, base_delay=base_delay, max_delay=max_delay, rng=rng)
            ceiling = min(max_delay, base_delay * (2 ** attempt))
            half = ceiling / 2.0
            self.assertGreaterEqual(delay, half)
            self.assertLessEqual(delay, ceiling)

        prev = base_delay
        for _ in range(8):
            next_delay = decorrelated_jitter_backoff(prev, base_delay=base_delay, max_delay=max_delay, rng=rng)
            self.assertGreaterEqual(next_delay, base_delay)
            self.assertLessEqual(next_delay, max_delay)
            prev = next_delay

    def test_half_open_circuit_breaker_convergence_to_closed(self):
        clock = SimulatedClock(100.0)
        cb = CircuitBreaker(
            failure_threshold=3,
            recovery_time=15.0,
            half_open_success_threshold=2,
            time_fn=clock,
        )

        self.assertEqual(cb.state, CircuitState.CLOSED)

        # Trip to OPEN
        cb.on_failure()
        cb.on_failure()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        cb.on_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.allow_request())

        # Attempt before recovery window should stay OPEN
        clock.advance(10.0)
        self.assertFalse(cb.allow_request())
        self.assertEqual(cb.state, CircuitState.OPEN)

        # Advance past recovery window -> transitions to HALF_OPEN
        clock.advance(5.0)
        self.assertTrue(cb.allow_request())
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # Success 1: still HALF_OPEN
        cb.on_success()
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # Success 2: converges to CLOSED
        cb.on_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.allow_request())

    def test_half_open_circuit_breaker_relapse_to_open(self):
        clock = SimulatedClock(0.0)
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_time=5.0,
            half_open_success_threshold=2,
            time_fn=clock,
        )

        cb.on_failure()
        cb.on_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)

        clock.advance(5.0)
        self.assertTrue(cb.allow_request())
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # Failure during HALF_OPEN immediately returns to OPEN
        cb.on_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.allow_request())

        with self.assertRaises(CircuitBreakerOpenException):
            cb.execute(lambda: "ok")


if __name__ == "__main__":
    unittest.main()
