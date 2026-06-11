"""Business logic for onboarding tour progress."""


def merge_seen(current: list[str], new: list[str]) -> list[str]:
    """Set-union merge preserving order: current ids first, then unseen new ids."""
    merged = list(current)
    known = set(current)
    for step_id in new:
        if step_id not in known:
            merged.append(step_id)
            known.add(step_id)
    return merged
