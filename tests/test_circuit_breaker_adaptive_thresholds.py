import unittest
import random
from circuit_breaker.adaptive_breaker import (
    AdaptiveCircuitBreaker,
    CircuitState,
    CircuitBreakerOpenException,
)


class FakeClock:
    def __init__(self, initial_time: float = 1000.0):
        self._time = initial_time

    def time(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds


class TestAdaptiveThresholdCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock(1000.0)
        # Deterministic seed for reproducible jitter calculations
        self.rng = random.Random(42)
        self.breaker = AdaptiveCircuitBreaker(
            base_threshold=0.5,
            min_samples=4,
            base_backoff_seconds=2.0,
            max_backoff_seconds=30.0,
            jitter_factor=0.1,
            half_open_probe_limit=3,
            clock=self.clock.time,
            rng=self.rng,
        )

    def test_adaptive_threshold_tripping(self):
        """Verify circuit trips only when failure rate crosses dynamic threshold after min_samples."""
        # min_samples is 4, base threshold is 0.5
        self.assertTrue(self.breaker.allow_request())
        self.breaker.record_failure()
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)  # total=1 < 4

        self.breaker.record_success()
        self.breaker.record_success()
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)  # total=3 < 4

        # 4th sample is a failure -> total=4, failures=2 -> rate=0.5 -> meets threshold 0.5
        self.breaker.record_failure()
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        self.assertFalse(self.breaker.allow_request())

    def test_half_open_probe_recovery(self):
        """Verify half-open state allows limited probes and closes upon full probe success."""
        # Trip the breaker directly
        for _ in range(4):
            self.breaker.record_failure()
        self.assertEqual(self.breaker.state, CircuitState.OPEN)

        # Wait out backoff
        self.clock.advance(10.0)

        # Probe 1
        self.assertTrue(self.breaker.allow_request())
        self.assertEqual(self.breaker.state, CircuitState.HALF_OPEN)
        self.breaker.record_success()

        # Probe 2
        self.assertTrue(self.breaker.allow_request())
        self.breaker.record_success()

        # Probe 3
        self.assertTrue(self.breaker.allow_request())
        self.breaker.record_success()

        # After 3 successful probes, circuit should recover to CLOSED
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        self.assertTrue(self.breaker.allow_request())

    def test_half_open_probe_failure_reopens(self):
        """Verify that a failure during half-open probe trips the circuit back to OPEN."""
        for _ in range(4):
            self.breaker.record_failure()
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        initial_trips = self.breaker.consecutive_trips

        self.clock.advance(10.0)
        self.assertTrue(self.breaker.allow_request())
        self.assertEqual(self.breaker.state, CircuitState.HALF_OPEN)

        # Failure during probe
        self.breaker.record_failure()
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        self.assertGreater(self.breaker.consecutive_trips, initial_trips)
        self.assertFalse(self.breaker.allow_request())

    def test_deterministic_jitter_backoff_and_execute(self):
        """Verify backoff jitter calculation is deterministic with fixed RNG seed and execute wrapper works."""
        call_count = 0

        def faulty_service(should_fail=False):
            nonlocal call_count
            call_count += 1
            if should_fail:
                raise RuntimeError("Service failed")
            return "OK"

        # Successful executions
        res = self.breaker.execute(faulty_service, should_fail=False)
        self.assertEqual(res, "OK")

        # Cause trip via execute
        for _ in range(4):
            try:
                self.breaker.execute(faulty_service, should_fail=True)
            except RuntimeError:
                pass

        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        expected_delay = self.breaker.next_attempt_time - self.clock.time()
        # Backoff: base=2.0 * 2^1 = 4.0; with jitter in [-0.1, 0.1] range: [3.6, 4.4]
        self.assertGreaterEqual(expected_delay, 3.6)
        self.assertLessEqual(expected_delay, 4.4)

        # Executing while open should raise CircuitBreakerOpenException
        with self.assertRaises(CircuitBreakerOpenException):
            self.breaker.execute(faulty_service, should_fail=False)


if __name__ == "__main__":
    unittest.main()
