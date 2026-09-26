import re
from random import Random
from .items import max_groups_per_puzzle

# Fallback Digit Group count for a puzzle-type spec that doesn't embed one
# of its own -- an older-style bare type ("6de", with no trailing count),
# or a hand-written preset_overrides/fixed_puzzles entry someone hasn't
# updated. Matches this world's old global default (see options.py's
# former DigitGroupCount option, now replaced by per-type counts).
default_digit_group_count = 10

# A puzzle-type spec's "head" -- everything before an optional ':<id>' or
# '#<seed>' suffix -- is <width>d<diffchar>[m][<count>], e.g. "9dx20" or
# "6dnm10" (native params, then an optional Digit Group count last,
# always after any 'm'). The count is this world's own concept: it's
# parsed off here and never reaches the client-side puzzle engine, which
# only understands the part before it.
_HEAD_RE = re.compile(r'^(?P<native>\d+d[enhxu]m?)(?P<count>\d+)?$')


def parse_puzzle_type(spec: str) -> tuple[str, int]:
    """
    Splits a puzzle-type spec into (native_spec, digit_group_count).

    native_spec is exactly what the client-side puzzle engine understands
    -- width + 'd' + difficulty + optional 'm', plus any trailing ':<id>'
    or '#<seed>' suffix, carried over verbatim. digit_group_count is
    parsed from the trailing digits between that and the seed/id suffix
    (if present), falling back to default_digit_group_count when absent
    (so older bare types keep working), and clamped to
    [1, max_groups_per_puzzle] so a hand-written override can't request
    more Digit Groups than this world has location/item ID space for.
    """
    suffix_match = re.search(r'[:#]', spec)
    if suffix_match:
        head, suffix = spec[:suffix_match.start()], spec[suffix_match.start():]
    else:
        head, suffix = spec, ""

    match = _HEAD_RE.match(head)
    if not match:
        raise ValueError(f"Couldn't parse Keen puzzle type: {spec!r}")

    count_str = match.group("count")
    count = int(count_str) if count_str else default_digit_group_count
    count = max(1, min(count, max_groups_per_puzzle))

    return (match.group("native") + suffix, count)


def _usable_presets(
        presets: list[tuple[str, float, int]],
        preset_overrides: list[str],
        min_difficulty: int,
        max_difficulty: int) -> tuple[list[str], list[float]]:
    """
    Returns (entries, weights) for the preset pool to randomize from: either
    the override list verbatim (all equally weighted), or the built-in pool
    filtered to [min_difficulty, max_difficulty].
    """
    if preset_overrides:
        return (list(preset_overrides), [1 for _ in preset_overrides])

    def matches(p: tuple[str, float, int]) -> bool:
        return min_difficulty <= p[2] <= max_difficulty

    entries = [p[0] for p in presets if matches(p)]
    weights = [p[1] for p in presets if matches(p)]
    return (entries, weights)


def _resolve_preset(random: Random, spec: str, usable: tuple[list[str], list[float]]) -> tuple[str, int]:
    """
    Any non-empty spec -- a puzzle type ("9dx20"), an ID ("9dx20:c494"), or
    a seed ("9dx20#12345") -- is already a complete puzzle spec on its own
    (the client-side puzzle engine can generate a fresh puzzle from bare
    native params alone) and is used as-is, just split into (native_spec,
    digit_group_count) via parse_puzzle_type(). Only the empty spec ("")
    is a request to fill the slot by weighted random choice from the
    usable pool -- this is how generate_puzzle_list() fills the puzzles
    beyond the caller's fixed_puzzles list.

    Note: this does NOT accept a "<genre>:<params>" style spec (e.g.
    "keen:9dx") -- that was the full-puzzle-string convention from this
    world's earlier multi-genre days. Since the world became Keen-only,
    generate_early() unconditionally adds the "keen:" genre prefix to every
    entry generate_puzzle_list() returns (fixed or random), so a
    fixed_puzzles entry should be given WITHOUT that prefix -- "9dx20", not
    "keen:9dx20" -- or it will end up double-prefixed ("keen:keen:9dx20")
    and fail to parse.
    """
    if spec == "":
        entries, weights = usable
        if len(entries) == 0:
            raise ValueError("No valid Keen presets to randomize from -- check "
                              "min_difficulty/max_difficulty and preset_overrides.")
        spec = random.choices(entries, k=1, weights=weights)[0]

    return parse_puzzle_type(spec)


def generate_puzzle_list(
        random: Random,
        count: int,
        fixed_puzzles: list[str],
        presets: list[tuple[str, float, int]],
        preset_overrides: list[str],
        min_difficulty: int,
        max_difficulty: int) -> list[tuple[str, int]]:
    """
    Builds a list of `count` (native_puzzle_spec, digit_group_count) pairs,
    starting with `fixed_puzzles` (truncated to `count`) and filling the
    remainder by weighted random choice from the preset pool. Each
    native_puzzle_spec is a bare Keen puzzle spec ("params" or "params:id"
    or "params#seed") with any Digit Group count already split off into
    its own paired int -- see parse_puzzle_type().
    """
    fixed = fixed_puzzles[:count]
    usable = _usable_presets(presets, preset_overrides, min_difficulty, max_difficulty)

    result = [_resolve_preset(random, spec, usable) for spec in fixed]

    remaining = count - len(result)
    for _ in range(remaining):
        result.append(_resolve_preset(random, "", usable))

    return result
