from enum import Enum
from typing import Optional, Callable
import time


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is rejected by an open circuit breaker."""
    pass


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_time: float = 10.0,
        half_open_success_threshold: int = 2,
        time_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if recovery_time < 0:
            raise ValueError("recovery_time must be non-negative")
        if half_open_success_threshold <= 0:
            raise ValueError("half_open_success_threshold must be positive")

        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.half_open_success_threshold = half_open_success_threshold
        self._time_fn = time_fn if time_fn is not None else time.time

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0

    def _evaluate_state(self) -> None:
        now = self._time_fn()
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= self.recovery_time:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0

    def allow_request(self) -> bool:
        self._evaluate_state()
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def execute(self, func: Callable, *args, **kwargs):
        if not self.allow_request():
            raise CircuitBreakerOpenException("Circuit breaker is OPEN")
        try:
            res = func(*args, **kwargs)
            self.on_success()
            return res
        except Exception as exc:
            self.on_failure()
            raise exc

    def on_success(self) -> None:
        self._evaluate_state()
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def on_failure(self) -> None:
        self.last_failure_time = self._time_fn()
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
