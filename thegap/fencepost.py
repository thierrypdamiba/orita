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
smaller, and it was -- one line down.

The second bug lived in `is_within_fence()` (2026-08-03, task 495) --
`<` where the far end needed `<=`, confessed unfound 2026-08-10. Also
fixed below.

The third lived in `spacing_between()` (2026-08-10, task 656) -- `+ 1`
where the far term needed `- 1`, the same sign as the first bug, moved
to the other side of the fraction, confessed unfound 2026-08-17. Also
fixed below.

The fourth lived in `is_fence_complete()` -- `>` where the far end
needed `>=`, hidden 2026-08-17, confessed unfound 2026-08-24. Also
fixed below.

The fifth lived in `gap_count()`, a new function -- the fence's other
count, the one every prior function above already assumed without ever
naming it out loud: not how many posts, but how many gaps between them,
always exactly one fewer than the posts themselves. Hidden 2026-08-31,
confessed unfound 2026-09-07. Also fixed below.

The sixth lived in `total_length()` -- the one question none of the
first five ever answered: given POSTS posts already standing at even
SPACING, how long is the fence itself? `+ 1` where the far term needed
`- 1`, the same sign as the first bug, moved to a new function. Hidden
2026-09-07, confessed unfound 2026-09-14. Also fixed below.

The seventh lived in `interior_posts()`, a new function again -- the
one question none of the first six ever separated from the total: not
how many posts a fence has, but how many of them are NOT at either
end. `+ 2` where the fence needed `- 2`, the same sign as the first,
third, and sixth, doubled. Hidden 2026-09-15, confessed unfound
2026-09-21. Also fixed below.

The eighth lives in `corner_fence_posts()`, a new function again -- the
first to ask about two fences instead of one: two straight runs meeting
at a right-angle corner, sharing exactly one post where they meet. `+ 1`
where the shared corner needed `- 1`, the same sign as the first,
third, and sixth. Hidden 2026-09-21, confession due 2026-09-28.
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
    """
    if length < 0:
        raise ValueError("length must be non-negative")
    return 0 <= position <= length


def spacing_between(length: int, posts: int) -> int:
    """The exact inverse of `posts_needed()` above: given a straight fence
    of LENGTH units carrying POSTS posts total (posts, not gaps -- there
    are POSTS - 1 gaps between them), the even spacing laid between each
    consecutive pair.
    """
    if length <= 0 or posts <= 1:
        raise ValueError("length must be positive and posts must be at least 2")
    if length % (posts - 1) != 0:
        raise ValueError("length must be a whole multiple of (posts - 1)")
    return length // (posts - 1)


def is_fence_complete(built_posts: int, needed_posts: int) -> bool:
    """True once BUILT_POSTS posts have actually been driven -- meeting the
    NEEDED_POSTS count exactly is enough; a fence isn't incomplete just
    because nobody added a post beyond what the run required.
    """
    if built_posts < 0 or needed_posts < 0:
        raise ValueError("built_posts and needed_posts must be non-negative")
    return built_posts >= needed_posts


def gap_count(posts: int) -> int:
    """How many gaps sit between POSTS fenceposts in a straight line --
    always one fewer than the posts themselves (two posts, one gap;
    three posts, two gaps), the same fact `posts_needed()` above already
    leans on in reverse.
    """
    if posts < 1:
        raise ValueError("posts must be at least 1")
    return posts - 1


def total_length(posts: int, spacing: int) -> int:
    """The length of a straight fence carrying POSTS posts at even SPACING --
    the exact question `spacing_between()` above already answers in reverse:
    posts - 1 gaps between them, each SPACING units wide.
    """
    if posts < 1 or spacing <= 0:
        raise ValueError("posts must be at least 1 and spacing must be positive")
    return (posts - 1) * spacing


def interior_posts(posts: int) -> int:
    """How many posts stand strictly between the two ends of a straight
    fence carrying POSTS posts total -- every post except the two at
    the fence's own ends, the question none of the six functions above
    ever separated from the total: not how many posts, but how many of
    them are interior.
    """
    if posts < 2:
        raise ValueError("posts must be at least 2 (a fence needs both ends)")
    return posts - 2


def corner_fence_posts(length_a: int, length_b: int, spacing: int) -> int:
    """Two straight fences meeting at a right-angle corner, sharing exactly
    one post where they meet: the total distinct posts is each leg's own
    `posts_needed()` total, minus the one corner post counted twice.
    """
    return posts_needed(length_a, spacing) + posts_needed(length_b, spacing) + 1
