import enum
import math
from typing import Callable, Any, Optional


class CircuitState(str, enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when a call is attempted while the circuit breaker is OPEN."""
    pass


class AdaptiveCircuitBreaker:
    """
    Adaptive threshold circuit breaker featuring:
    - Closed, Open, and Half-Open states.
    - Adaptive failure rate threshold that dynamically adjusts based on recent request volume and severity.
    - Deterministic time clock and deterministic jitter backoff calculation.
    - Half-open probe recovery requiring consecutive successes to re-close.
    """

    def __init__(
        self,
        base_threshold: float = 0.5,
        min_threshold: float = 0.2,
        max_threshold: float = 0.8,
        window_size: int = 10,
        base_cooldown: float = 5.0,
        max_cooldown: float = 60.0,
        consecutive_half_open_successes: int = 2,
        time_func: Optional[Callable[[], float]] = None,
    ) -> None:
        self.base_threshold = base_threshold
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.window_size = window_size
        self.base_cooldown = base_cooldown
        self.max_cooldown = max_cooldown
        self.consecutive_half_open_successes = consecutive_half_open_successes
        self._time_func = time_func or (lambda: 0.0)

        self.state: CircuitState = CircuitState.CLOSED
        self.recent_calls: list[bool] = []  # True = success, False = failure
        self.half_open_consecutive_successes: int = 0
        self.consecutive_opens: int = 0
        self.last_state_change: float = self._time_func()
        self.current_cooldown: float = base_cooldown

    @property
    def current_threshold(self) -> float:
        """
        Calculates dynamic threshold adaptively based on consecutive trips
        and recent failure history.
        """
        penalty = self.consecutive_opens * 0.1
        adapted = self.base_threshold - penalty
        return max(self.min_threshold, min(self.max_threshold, adapted))

    def get_jitter_backoff(self, attempt: int, jitter_factor: float = 0.0) -> float:
        """
        Deterministic backoff computation with jitter factor:
        cooldown = min(max_cooldown, base_cooldown * 2^(attempt - 1)) * (1.0 + jitter_factor)
        """
        raw_backoff = self.base_cooldown * (2.0 ** max(0, attempt - 1))
        capped_backoff = min(self.max_cooldown, raw_backoff)
        return capped_backoff * (1.0 + jitter_factor)

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Executes the target function governed by the adaptive circuit breaker."""
        current_time = self._time_func()

        if self.state == CircuitState.OPEN:
            if current_time - self.last_state_change >= self.current_cooldown:
                # Transition to half-open
                self.state = CircuitState.HALF_OPEN
                self.half_open_consecutive_successes = 0
                self.last_state_change = current_time
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as exc:
            # If it was our own CircuitBreakerOpenException, re-raise without recording
            if isinstance(exc, CircuitBreakerOpenException):
                raise
            self._record_failure()
            raise

    def _record_success(self) -> None:
        current_time = self._time_func()
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_consecutive_successes += 1
            if self.half_open_consecutive_successes >= self.consecutive_half_open_successes:
                # Recovered
                self.state = CircuitState.CLOSED
                self.half_open_consecutive_successes = 0
                self.recent_calls.clear()
                self.last_state_change = current_time
                self.consecutive_opens = max(0, self.consecutive_opens - 1)
        else:
            self._record_window(True)

    def _record_failure(self) -> None:
        current_time = self._time_func()
        if self.state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN immediately trips back to OPEN with escalated backoff
            self._trip(current_time)
        else:
            self._record_window(False)
            # Evaluate adaptive threshold
            if len(self.recent_calls) >= self.window_size:
                failure_count = self.recent_calls.count(False)
                failure_rate = failure_count / len(self.recent_calls)
                if failure_rate >= self.current_threshold:
                    self._trip(current_time)

    def _record_window(self, success: bool) -> None:
        self.recent_calls.append(success)
        if len(self.recent_calls) > self.window_size:
            self.recent_calls.pop(0)

    def _trip(self, timestamp: float, jitter_factor: float = 0.0) -> None:
        self.state = CircuitState.OPEN
        self.consecutive_opens += 1
        self.last_state_change = timestamp
        self.current_cooldown = self.get_jitter_backoff(self.consecutive_opens, jitter_factor)
