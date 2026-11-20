import random
from typing import Optional


def calculate_jitter_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter_mode: str = "full",
    seed: Optional[int] = None,
) -> float:
    """
    Calculate exponential backoff with deterministic jitter if seed is provided.

    Supported jitter modes:
      - 'none': standard exponential backoff min(max_delay, base_delay * 2^attempt)
      - 'full': uniform random between 0 and min(max_delay, base_delay * 2^attempt)
      - 'equal': half constant, half random: (exp_delay / 2) + uniform(0, exp_delay / 2)
      - 'decorrelated': sleep = min(max_delay, uniform(base_delay, prev_sleep * 3))
    """
    if attempt < 0:
        raise ValueError("Attempt must be non-negative")
    if base_delay <= 0:
        raise ValueError("base_delay must be positive")
    if max_delay <= 0:
        raise ValueError("max_delay must be positive")

    rng = random.Random(seed) if seed is not None else random.Random()

    raw_delay = base_delay * (2 ** attempt)
    bounded_delay = min(max_delay, raw_delay)

    if jitter_mode == "none":
        return float(bounded_delay)
    elif jitter_mode == "full":
        return rng.uniform(0.0, bounded_delay)
    elif jitter_mode == "equal":
        half = bounded_delay / 2.0
        return half + rng.uniform(0.0, half)
    elif jitter_mode == "decorrelated":
        # Standard decorrelated jitter formula for given attempt
        # When calculated independently: uniform(base_delay, bounded_delay * 3)
        return min(max_delay, rng.uniform(base_delay, max(base_delay, bounded_delay)))
    else:
        raise ValueError(f"Unknown jitter_mode: {jitter_mode}")
