from random import Random


def _usable_presets(
        presets: list[tuple[str, float, int, int]],
        preset_overrides: list[str],
        min_difficulty: int,
        max_difficulty: int,
        min_size: int,
        max_size: int) -> tuple[list[str], list[float]]:
    """
    Returns (entries, weights) for the preset pool to randomize from: either
    the override list verbatim (all equally weighted), or the built-in pool
    filtered to [min_difficulty, max_difficulty] and [min_size, max_size].
    """
    if preset_overrides:
        return (list(preset_overrides), [1 for _ in preset_overrides])

    def matches(p: tuple[str, float, int, int]) -> bool:
        return min_difficulty <= p[2] <= max_difficulty and min_size <= p[3] <= max_size

    entries = [p[0] for p in presets if matches(p)]
    weights = [p[1] for p in presets if matches(p)]
    return (entries, weights)


def _resolve_preset(random: Random, spec: str, usable: tuple[list[str], list[float]]) -> str:
    """
    Any non-empty spec -- a bare parameter string ("9dx"), an ID
    ("9dx:c494"), or a seed ("9dx#12345") -- is already a complete puzzle
    string on its own (the client-side puzzle engine can generate a fresh
    puzzle from bare params alone) and is used as-is. Only the empty spec
    ("") is a request to fill the slot by weighted random choice from the
    usable pool -- this is how generate_puzzle_list() fills the puzzles
    beyond the caller's fixed_puzzles list.

    Note: this does NOT accept a "<genre>:<params>" style spec (e.g.
    "keen:9dx") -- that was the full-puzzle-string convention from this
    world's earlier multi-genre days. Since the world became Keen-only,
    generate_early() unconditionally adds the "keen:" genre prefix to every
    entry generate_puzzle_list() returns (fixed or random), so a
    fixed_puzzles entry should be given WITHOUT that prefix -- "9dx", not
    "keen:9dx" -- or it will end up double-prefixed ("keen:keen:9dx") and
    fail to parse.
    """
    if spec == "":
        entries, weights = usable
        if len(entries) == 0:
            raise ValueError("No valid Keen presets to randomize from -- check "
                              "min_difficulty/max_difficulty, min_size/max_size, "
                              "and preset_overrides.")
        return random.choices(entries, k=1, weights=weights)[0]

    return spec


def generate_puzzle_list(
        random: Random,
        count: int,
        fixed_puzzles: list[str],
        presets: list[tuple[str, float, int, int]],
        preset_overrides: list[str],
        min_difficulty: int,
        max_difficulty: int,
        min_size: int,
        max_size: int) -> list[str]:
    """
    Builds a list of `count` Keen puzzle strings ("params" or "params:id" or
    "params#seed"), starting with `fixed_puzzles` (truncated to `count`) and
    filling the remainder by weighted random choice from the preset pool.
    """
    fixed = fixed_puzzles[:count]
    usable = _usable_presets(
        presets, preset_overrides, min_difficulty, max_difficulty, min_size, max_size)

    result = [_resolve_preset(random, spec, usable) for spec in fixed]

    remaining = count - len(result)
    for _ in range(remaining):
        result.append(_resolve_preset(random, "", usable))

    return result
