from enum import Enum
from typing import Callable, Any
import time


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    pass


class CircuitBreaker:
    """
    Circuit Breaker with configurable failure threshold, recovery timeout,
    and required consecutive successes in HALF_OPEN to converge back to CLOSED.
    """
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 5.0,
        half_open_success_threshold: int = 2,
        clock: Callable[[], float] = time.time,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold
        self.clock = clock

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.consecutive_successes = 0
        self.last_state_change = self.clock()

    def _check_and_update_state(self):
        now = self.clock()
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.consecutive_successes = 0
                self.last_state_change = now

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        self._check_and_update_state()

        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenException("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.half_open_success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.consecutive_successes = 0
                self.last_state_change = self.clock()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def on_failure(self):
        now = self.clock()
        if self.state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN immediately trips back to OPEN
            self.state = CircuitState.OPEN
            self.consecutive_successes = 0
            self.last_state_change = now
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = now
