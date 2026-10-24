import unittest
from circuit_breaker.adaptive import (
    AdaptiveCircuitBreaker,
    CircuitState,
    CircuitBreakerOpenException,
)


class DeterministicClock:
    def __init__(self, initial_time: float = 0.0):
        self.current_time = initial_time

    def __call__(self) -> float:
        return self.current_time

    def advance(self, seconds: float) -> None:
        self.current_time += seconds


class TestAdaptiveThresholdCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.clock = DeterministicClock(100.0)

    def test_adaptive_threshold_trip_on_failure_rate(self):
        breaker = AdaptiveCircuitBreaker(
            base_threshold=0.5,
            min_threshold=0.2,
            window_size=4,
            base_cooldown=10.0,
            time_func=self.clock,
        )

        self.assertEqual(breaker.state, CircuitState.CLOSED)
        self.assertAlmostEqual(breaker.current_threshold, 0.5)

        # 2 successes, 2 failures in a window of 4 -> 50% failure rate
        breaker.call(lambda: "ok")
        breaker.call(lambda: "ok")
        self.assertEqual(breaker.state, CircuitState.CLOSED)

        with self.assertRaises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("fail 1")))
        self.assertEqual(breaker.state, CircuitState.CLOSED)

        # Reaches window of 4 with 2 failures (50%), hits threshold of 0.5 -> OPEN
        with self.assertRaises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("fail 2")))

        self.assertEqual(breaker.state, CircuitState.OPEN)
        self.assertEqual(breaker.consecutive_opens, 1)

        # Immediate next call fails fast with CircuitBreakerOpenException
        with self.assertRaises(CircuitBreakerOpenException):
            breaker.call(lambda: "should not run")

    def test_half_open_probe_recovery_success(self):
        breaker = AdaptiveCircuitBreaker(
            base_threshold=0.4,
            window_size=2,
            base_cooldown=5.0,
            consecutive_half_open_successes=2,
            time_func=self.clock,
        )

        # Fail twice to trip open
        for _ in range(2):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("error")))
            except RuntimeError:
                pass

        self.assertEqual(breaker.state, CircuitState.OPEN)

        # Before cooldown elapsed: fail fast
        self.clock.advance(4.9)
        with self.assertRaises(CircuitBreakerOpenException):
            breaker.call(lambda: "probe")

        # Advance past cooldown: transitions to HALF_OPEN on first call
        self.clock.advance(0.2)
        res1 = breaker.call(lambda: "probe 1 ok")
        self.assertEqual(res1, "probe 1 ok")
        self.assertEqual(breaker.state, CircuitState.HALF_OPEN)
        self.assertEqual(breaker.half_open_consecutive_successes, 1)

        # Second probe succeeds, meeting requirement of 2 successes -> back to CLOSED
        res2 = breaker.call(lambda: "probe 2 ok")
        self.assertEqual(res2, "probe 2 ok")
        self.assertEqual(breaker.state, CircuitState.CLOSED)
        self.assertEqual(breaker.half_open_consecutive_successes, 0)

    def test_half_open_probe_failure_reopens_circuit(self):
        breaker = AdaptiveCircuitBreaker(
            base_threshold=0.5,
            window_size=2,
            base_cooldown=5.0,
            consecutive_half_open_successes=2,
            time_func=self.clock,
        )

        # Force OPEN state
        for _ in range(2):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("initial error")))
            except RuntimeError:
                pass
        self.assertEqual(breaker.state, CircuitState.OPEN)

        # Cooldown expires
        self.clock.advance(5.1)
        # First probe succeeds
        breaker.call(lambda: "first probe passed")
        self.assertEqual(breaker.state, CircuitState.HALF_OPEN)

        # Second probe fails -> should immediately trip back to OPEN
        with self.assertRaises(RuntimeError):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("probe failed")))

        self.assertEqual(breaker.state, CircuitState.OPEN)
        self.assertEqual(breaker.consecutive_opens, 2)

    def test_deterministic_jitter_backoff_and_adaptive_threshold_escalation(self):
        breaker = AdaptiveCircuitBreaker(
            base_threshold=0.5,
            min_threshold=0.2,
            base_cooldown=10.0,
            max_cooldown=50.0,
            time_func=self.clock,
        )

        # Attempt 1: backoff without jitter = 10.0, with 0.1 jitter = 11.0
        self.assertAlmostEqual(breaker.get_jitter_backoff(attempt=1, jitter_factor=0.0), 10.0)
        self.assertAlmostEqual(breaker.get_jitter_backoff(attempt=1, jitter_factor=0.1), 11.0)

        # Attempt 2: 10 * 2^1 = 20.0, with -0.05 jitter = 19.0
        self.assertAlmostEqual(breaker.get_jitter_backoff(attempt=2, jitter_factor=0.0), 20.0)
        self.assertAlmostEqual(breaker.get_jitter_backoff(attempt=2, jitter_factor=-0.05), 19.0)

        # Attempt 4: capped at max_cooldown (50.0)
        self.assertAlmostEqual(breaker.get_jitter_backoff(attempt=4, jitter_factor=0.0), 50.0)

        # Test adaptive threshold degradation over consecutive opens
        self.assertAlmostEqual(breaker.current_threshold, 0.5)
        breaker.consecutive_opens = 2
        # 0.5 - (2 * 0.1) = 0.3
        self.assertAlmostEqual(breaker.current_threshold, 0.3)

        # Clamp to min_threshold
        breaker.consecutive_opens = 5
        # 0.5 - (5 * 0.1) = 0.0 -> clamped to min_threshold 0.2
        self.assertAlmostEqual(breaker.current_threshold, 0.2)


if __name__ == "__main__":
    unittest.main()
