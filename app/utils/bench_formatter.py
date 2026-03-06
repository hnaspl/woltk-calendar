"""Shared bench/queue formatting utilities.

Used by Discord webhook rendering and any other output that needs to display
bench player lists with a configurable display limit.
"""

from __future__ import annotations

from app.constants import ROLE_LABELS, get_bench_display_limit


def format_bench_entries(
    bench: list[dict],
    *,
    guild_id: int | None = None,
    limit: int | None = None,
) -> dict | None:
    """Format bench player entries for display.

    Args:
        bench: List of signup dicts with ``character.name`` and ``chosen_role``.
        guild_id: Guild whose bench limit setting to use (each guild can set
                  its own via ``settings.bench_display_limit``, max 100).
        limit: Explicit override.  When provided, *guild_id* is ignored.

    Returns:
        A dict ``{"text": str, "count": int}`` ready to embed, or ``None``
        if the bench is empty.
    """
    if not bench:
        return None

    if limit is None:
        limit = get_bench_display_limit(guild_id)

    entries: list[str] = []
    for s in bench[:limit]:
        char_name = s.get("character", {}).get("name", "?")
        role = s.get("chosen_role", "")
        role_label = ROLE_LABELS.get(role, role.replace("_", " ").title())
        entries.append(f"{role_label}: {char_name}")

    text = "\n".join(entries)
    if len(bench) > limit:
        text += f"\n*+{len(bench) - limit} more on bench*"

    return {"text": text, "count": len(bench)}
