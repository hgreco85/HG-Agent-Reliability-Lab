import time
import random
from enum import Enum
from typing import Callable, Any, Optional


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    pass


class AdaptiveCircuitBreaker:
    """
    Adaptive Threshold Circuit Breaker with deterministic probe recovery and jitter backoff.
    
    Features:
    - Closed state: tracks call success/failure over a sliding window or counts.
    - Adaptive threshold: dynamic failure rate threshold that adapts based on recent volume or load.
    - Exponential backoff with configurable jitter (deterministic when seeded or passed a custom RNG/time func).
    - Half-open state: limited probe allowance to verify upstream health before fully closing.
    """
    def __init__(
        self,
        base_threshold: float = 0.5,
        min_samples: int = 5,
        base_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 60.0,
        jitter_factor: float = 0.2,
        half_open_probe_limit: int = 3,
        clock: Optional[Callable[[], float]] = None,
        rng: Optional[random.Random] = None,
    ):
        self.base_threshold = base_threshold
        self.min_samples = min_samples
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.jitter_factor = jitter_factor
        self.half_open_probe_limit = half_open_probe_limit
        
        self.clock = clock if clock is not None else time.time
        self.rng = rng if rng is not None else random.Random(0)
        
        self.state = CircuitState.CLOSED
        self.consecutive_trips = 0
        self.next_attempt_time = 0.0
        
        # Tracking metrics for adaptive evaluation
        self.success_count = 0
        self.failure_count = 0
        
        # Half-open probe tracking
        self.half_open_probes_active = 0
        self.half_open_successful_probes = 0

    def get_adaptive_threshold(self) -> float:
        """
        Compute the dynamic failure rate threshold.
        In high volume, tolerance tightens; in low volume, tolerance relaxes.
        """
        total = self.success_count + self.failure_count
        if total < self.min_samples:
            return 1.0  # Allow learning without tripping immediately
        
        # If consecutive trips occurred, lower the acceptable failure threshold
        penalty = 0.1 * min(self.consecutive_trips, 3)
        effective_threshold = max(0.1, self.base_threshold - penalty)
        return effective_threshold

    def _calculate_backoff_delay(self) -> float:
        backoff = min(
            self.max_backoff_seconds,
            self.base_backoff_seconds * (2 ** self.consecutive_trips)
        )
        if self.jitter_factor > 0:
            # Deterministic jitter bounded within [1 - jitter, 1 + jitter]
            jitter = self.rng.uniform(-self.jitter_factor, self.jitter_factor)
            backoff = backoff * (1.0 + jitter)
        return max(0.0, backoff)

    def allow_request(self) -> bool:
        now = self.clock()
        if self.state == CircuitState.OPEN:
            if now >= self.next_attempt_time:
                self.state = CircuitState.HALF_OPEN
                self.half_open_probes_active = 0
                self.half_open_successful_probes = 0
            else:
                return False
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_probes_active < self.half_open_probe_limit:
                self.half_open_probes_active += 1
                return True
            return False
        
        return True

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successful_probes += 1
            if self.half_open_successful_probes >= self.half_open_probe_limit:
                # Probe period succeeded, fully recover to CLOSED
                self.state = CircuitState.CLOSED
                self.consecutive_trips = 0
                self.success_count = 0
                self.failure_count = 0
                self.half_open_probes_active = 0
                self.half_open_successful_probes = 0
        elif self.state == CircuitState.CLOSED:
            self.success_count += 1

    def record_failure(self) -> None:
        now = self.clock()
        if self.state == CircuitState.HALF_OPEN:
            # Any failure during half-open probe trip returns to OPEN with incremented backoff
            self.consecutive_trips += 1
            self.state = CircuitState.OPEN
            self.next_attempt_time = now + self._calculate_backoff_delay()
            self.half_open_probes_active = 0
            self.half_open_successful_probes = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            total = self.success_count + self.failure_count
            if total >= self.min_samples:
                failure_rate = self.failure_count / total
                if failure_rate >= self.get_adaptive_threshold():
                    self.consecutive_trips += 1
                    self.state = CircuitState.OPEN
                    self.next_attempt_time = now + self._calculate_backoff_delay()

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if not self.allow_request():
            raise CircuitBreakerOpenException(f"Circuit is {self.state.value}")
        try:
            res = func(*args, **kwargs)
            self.record_success()
            return res
        except Exception:
            self.record_failure()
            raise
