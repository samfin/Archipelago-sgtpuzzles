from Options import Choice, OptionGroup, Range, \
    StartInventoryPool, PerGameCommonOptions, OptionList
from dataclasses import dataclass
from .items import max_puzzles, max_groups_per_puzzle

# Keen-only preset pool: (parameter string, weight, coarse difficulty tier,
# grid size). Coarse difficulty tiers: 0 = Easy, 1 = Normal, 2 = Hard,
# 3 = Extreme. "Unreasonable" ('u') presets are deliberately excluded: that
# tier requires recursive guessing in the base solver, which is incompatible
# with a puzzle whose whole point is that every stage is reachable by pure
# deduction.
genrePresets = {
    "keen": [
        ("4de", 1, 0, 4),
        ("5de", 1, 0, 5),
        ("5dem", 1, 0, 5),
        ("6de", 1, 0, 6),
        ("6dn", 1, 1, 6),
        ("6dnm", 1, 1, 6),
        ("9dn", 1, 1, 9),
        ("6dh", 1, 2, 6),
        ("9dh", 1, 2, 9),
        ("6dx", 1, 3, 6),
        ("9dx", 1, 3, 9),
    ]
}

# Grid sizes actually present in the pool above, used to bound the Minimum/
# Maximum Puzzle Size options below. Bumping these automatically follows if
# the pool ever gains a new size.
min_supported_size = min(p[3] for p in genrePresets["keen"])
max_supported_size = max(p[3] for p in genrePresets["keen"])


class PuzzleCount(Range):
    """
    Number of independent Keen puzzles to generate. Each one runs its own
    Clue Set / Digit Group progression chain.
    """
    range_start = 1
    range_end = max_puzzles
    default = 1


class DigitGroupCount(Range):
    """
    Number of progression stages per puzzle: how many "Clue Set" items it
    takes to reveal every clue, and how many "Digit Group" locations it's
    worth. The puzzle's clues are grouped and ordered (client-side) to
    produce as close to this many logically-forced stages as possible.
    """
    display_name = "Digit Groups Per Puzzle"
    range_start = 1
    range_end = max_groups_per_puzzle
    default = 10


class StartingClueSets(Range):
    """
    Number of "Clue Set" copies to grant as starting inventory for each
    puzzle (removed from the item pool). Capped at digit_group_count - 1
    per puzzle so at least one Digit Group location remains behind an item.
    """
    range_start = 0
    range_end = max_groups_per_puzzle - 1
    default = 0


class CompletionPercentage(Range):
    """
    Percent of puzzles which must be fully solved (every Digit Group
    obtained) to finish the world, rounding up.

    If you set this to a low value, it is HIGHLY RECOMMENDED to disable
    release on world completion.
    """
    display_name = "Target Completion Percentage"
    range_start = 10
    range_end = 100
    default = 100


class MinimumDifficulty(Choice):
    """
    Minimum difficulty to select generated puzzles from.
    """
    default = 0
    option_easy = 0
    option_normal = 1
    option_hard = 2
    option_extreme = 3


class MaximumDifficulty(Choice):
    """
    Maximum difficulty to select generated puzzles from. Takes priority over
    Minimum Difficulty if it is lower.

    "Extreme" puzzles are still guaranteed solvable by pure logical
    deduction (no guessing) -- there is no "Unreasonable" option because
    that tier requires guessing, which this world's logic can't express.
    """
    default = 2
    option_easy = 0
    option_normal = 1
    option_hard = 2
    option_extreme = 3


class MinimumSize(Range):
    """
    Minimum grid size (width/height) to select generated puzzles from, e.g.
    6 for 6x6.
    """
    display_name = "Minimum Puzzle Size"
    range_start = min_supported_size
    range_end = max_supported_size
    default = min_supported_size


class MaximumSize(Range):
    """
    Maximum grid size (width/height) to select generated puzzles from.
    Takes priority over Minimum Puzzle Size if it is lower.
    """
    display_name = "Maximum Puzzle Size"
    range_start = min_supported_size
    range_end = max_supported_size
    default = max_supported_size


class PresetOverrides(OptionList):
    """
    List of Keen presets to randomize from, replacing the built-in pool.

    Presets are parameter strings like 6de (6x6, Easy) or 9dh (9x9, Hard).
    The letter after the size is the difficulty (e = Easy, n = Normal,
    h = Hard, x = Extreme); an optional trailing "m" restricts clues to
    multiplication only. "Unreasonable" ('u') presets are not supported.
    """
    default = []


class FixedPuzzles(OptionList):
    """
    List of additional puzzles to include. These puzzles will be placed at
    the start of the list. The remaining list (up to puzzle_count) will be
    filled from the preset pool.

    You can specify by parameter string (6de), seed (6de#12345), or
    ID (6de:c494).
    """
    default = []


sgtkeen_option_groups = [
    OptionGroup("Puzzle Options", [
        PuzzleCount,
        DigitGroupCount,
        StartingClueSets,
        CompletionPercentage,
        MinimumDifficulty,
        MaximumDifficulty,
        MinimumSize,
        MaximumSize,
        PresetOverrides,
        FixedPuzzles
    ])
]


@dataclass
class SgtKeenOptions(PerGameCommonOptions):
    puzzle_count: PuzzleCount
    digit_group_count: DigitGroupCount
    starting_clue_sets: StartingClueSets
    completion_percentage: CompletionPercentage
    min_difficulty: MinimumDifficulty
    max_difficulty: MaximumDifficulty
    min_size: MinimumSize
    max_size: MaximumSize
    preset_overrides: PresetOverrides
    fixed_puzzles: FixedPuzzles

    start_inventory_pool: StartInventoryPool
