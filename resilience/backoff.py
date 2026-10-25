import random
from typing import Optional, Callable


def full_jitter_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    rng: Optional[random.Random] = None,
) -> float:
    """Full Jitter: sleep between 0 and min(max_delay, base_delay * 2 ** attempt)."""
    if attempt < 0:
        raise ValueError("attempt must be non-negative")
    ceiling = min(max_delay, base_delay * (2 ** attempt))
    rand = rng if rng is not None else random
    return rand.uniform(0, ceiling)


def equal_jitter_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    rng: Optional[random.Random] = None,
) -> float:
    """Equal Jitter: half ceiling fixed, half ceiling randomized."""
    if attempt < 0:
        raise ValueError("attempt must be non-negative")
    ceiling = min(max_delay, base_delay * (2 ** attempt))
    half = ceiling / 2.0
    rand = rng if rng is not None else random
    return half + rand.uniform(0, half)


def decorrelated_jitter_backoff(
    prev_delay: float,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    rng: Optional[random.Random] = None,
) -> float:
    """Decorrelated Jitter: uniform between base_delay and prev_delay * 3."""
    rand = rng if rng is not None else random
    ceiling = min(max_delay, max(base_delay, prev_delay * 3.0))
    return rand.uniform(base_delay, ceiling)
