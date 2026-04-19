"""Path safety helpers for user-provided filenames."""

from __future__ import annotations

from pathlib import Path


def safe_join(base: Path, user_filename: str) -> Path:
    """Safely join a user-supplied filename under a base directory.

    Rejects absolute paths and any traversal that would escape ``base``.

    Args:
        base: The trusted base directory. Resolved before comparison.
        user_filename: The untrusted filename (or relative path) to append.

    Returns:
        The resolved, safe path inside ``base``.

    Raises:
        ValueError: If ``user_filename`` is empty, absolute, or would resolve
            outside ``base``.
    """
    if not user_filename:
        raise ValueError("filename must not be empty")

    candidate = Path(user_filename)
    if candidate.is_absolute():
        raise ValueError(
            f"absolute paths are not allowed: {user_filename!r}"
        )

    base_resolved = base.resolve()
    joined = (base_resolved / candidate).resolve()

    try:
        joined.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(
            f"path traversal detected: {user_filename!r} escapes {base!s}"
        ) from exc

    return joined
