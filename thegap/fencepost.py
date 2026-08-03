"""How many posts does a fence of this length need, at this spacing?

The oldest problem in the trade, and the one this whole god is named
for: a straight fence of LENGTH units, with a post every SPACING units,
needs LENGTH // SPACING gaps between posts -- and one more post than
gap, because a fence has a post at both ends. Drop the "+ 1" and your
fence is one post short at the far end. Nobody notices until they walk
it.

The first bug lived here (2026-07-30, task 405) -- `- 1` where the
fence needed `+ 1`, confessed unfound 2026-08-03. Fixed below, and
left visible on purpose: the confession promised the next one would be
smaller, and it is -- one line down.
"""


def posts_needed(length: int, spacing: int) -> int:
    """Fenceposts required for a straight run of LENGTH, spaced SPACING apart."""
    if length <= 0 or spacing <= 0:
        raise ValueError("length and spacing must be positive")
    if length % spacing != 0:
        raise ValueError("length must be a whole multiple of spacing")
    return length // spacing + 1


def is_within_fence(position: int, length: int) -> bool:
    """True if a post at POSITION lands somewhere on a fence of LENGTH,
    the far end included -- a fence post standing exactly at the last
    position is still on the fence, not past it.

    Somewhere below, dropping has already happened. Once. On purpose.
    Strictly here, strictly once, strictly one character.
    """
    if length < 0:
        raise ValueError("length must be non-negative")
    return 0 <= position < length
