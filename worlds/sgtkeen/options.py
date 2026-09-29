from Options import Choice, OptionGroup, Range, \
    StartInventoryPool, PerGameCommonOptions, OptionList
from dataclasses import dataclass
from .items import max_puzzles, max_groups_per_puzzle, max_bonus_checks_per_digit_group

# Keen-only preset pool: (parameter string, weight, coarse difficulty tier).
# Coarse difficulty tiers: 0 = Easy, 1 = Normal, 2 = Hard, 3 = Extreme.
# "Unreasonable" ('u') presets are deliberately excluded: that tier requires
# recursive guessing in the base solver, which is incompatible with a puzzle
# whose whole point is that every stage is reachable by pure deduction.
#
# The parameter string is exactly what a "puzzle type" is -- grid size,
# difficulty, an optional trailing "m" (multiplication-only), and now an
# optional trailing digit-group count, e.g. "9dx20" (9x9, Extreme, 20
# Digit Groups). That count is this world's own concept: randomizer.py
# splits it back off before the string is ever handed to the client-side
# puzzle engine, which only understands the part before it. A type with no
# count embedded (an older-style bare "6de", or a hand-written override/
# fixed-puzzle entry) falls back to randomizer.default_digit_group_count.
#
# There used to be a separate grid-size field here, filtered by the
# Minimum/Maximum Puzzle Size options -- both the field and those options
# are gone now that picking sizes means picking which puzzle types are in
# the pool (built-in or via Preset Overrides) rather than filtering a
# range. Smaller grids are given proportionally fewer Digit Groups below:
# a 4x4 or 5x5 puzzle has far fewer cages than a 9x9 one, so the same
# path length doesn't fit both.
genrePresets = {
    "keen": [
        ("4de5", 1, 0),
        ("5de7", 1, 0),
        ("5dem7", 1, 0),
        ("6de10", 1, 0),
        ("6dn10", 1, 1),
        ("6dnm10", 1, 1),
        ("9dn18", 1, 1),
        ("6dh10", 1, 2),
        ("9dh18", 1, 2),
        ("6dx10", 1, 3),
        ("9dx18", 1, 3),
    ]
}


class PuzzleCount(Range):
    """
    Number of independent Keen puzzles to generate. Each one runs its own
    Clue / Digit Group progression chain.
    """
    range_start = 1
    range_end = max_puzzles
    default = 1


class StartingPuzzles(Range):
    """
    Number of puzzles that are accessible from the start. Each one starts
    with exactly 1 "Clue" item already granted (removed from the item
    pool). Every other puzzle is entirely inaccessible -- none of its Digit
    Group locations can be checked -- until its own "Puzzle N" item is
    received, and it starts with 0 Clues of its own: both the "Puzzle N"
    item and at least one "Puzzle N Clue" are required before any
    progress can be made on it. Capped at puzzle_count.
    """
    display_name = "Starting Puzzles"
    range_start = 1
    range_end = max_puzzles
    default = 1


class StartingClueBonus(Range):
    """
    Extra "Clue" items to grant, on top of the 1 every puzzle already
    starts with, for each puzzle that's accessible from the start (see
    Starting Puzzles). Puzzles unlocked later via their own "Puzzle N"
    item are unaffected -- they always start with exactly 1 Clue,
    regardless of this setting.

    Automatically capped per puzzle so it can never grant more Clues than
    that puzzle actually has (its own Digit Group count -- see Preset
    Overrides/Fixed Puzzles for how that's set per puzzle type).
    """
    display_name = "Starting Clue Bonus"
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


class BonusChecksPerDigitGroup(Range):
    """
    Extra locations to award for each Digit Group, on top of the one it
    already has, all released together the moment that Digit Group is
    solved (same requirement as today -- this never asks for any extra
    player action, it just adds more locations to that one milestone).

    0 (the default) keeps this world's original behavior exactly: one
    location per Digit Group, named "Puzzle N Digit Group J". Any value
    above 0 renames EVERY Digit Group's locations to the numbered form
    "Puzzle N Digit Group J-1", "Puzzle N Digit Group J-2", and so on,
    with (this value + 1) total locations per Digit Group -- e.g. a
    value of 2 makes each Digit Group release "...J-1", "...J-2", and
    "...J-3" together.
    """
    display_name = "Bonus Checks Per Digit Group"
    range_start = 0
    range_end = max_bonus_checks_per_digit_group
    default = 0


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


class PresetOverrides(OptionList):
    """
    List of Keen puzzle types to randomize from, replacing the built-in
    pool (see Minimum/Maximum Difficulty for filtering the built-in pool
    instead, without replacing it).

    Each entry is a puzzle type string: <size>d<difficulty>[m][<clues>],
    e.g. 6de (6x6, Easy), 9dh (9x9, Hard), or 9dx20 (9x9, Extreme, with
    20 Digit Groups). The letter after the size is the difficulty
    (e = Easy, n = Normal, h = Hard, x = Extreme); an optional "m" right
    after that restricts clues to multiplication only; an optional
    number after THAT sets how many Digit Groups (progression stages /
    "Clue" copies) the puzzle is worth -- if omitted, it defaults to 10.
    "Unreasonable" ('u') presets are not supported.
    """
    default = []


class FixedPuzzles(OptionList):
    """
    List of additional puzzles to include. These puzzles will be placed at
    the start of the list. The remaining list (up to puzzle_count) will be
    filled from the preset pool.

    You can specify by puzzle type (6de or 9dx20 -- see Preset Overrides
    for the full type-string grammar, including the optional Digit Group
    count), seed (6de#12345, 9dx20#12345), or ID (6de:c494, 9dx20:c494).
    """
    default = []


sgtkeen_option_groups = [
    OptionGroup("Puzzle Options", [
        PuzzleCount,
        StartingPuzzles,
        StartingClueBonus,
        CompletionPercentage,
        BonusChecksPerDigitGroup,
        MinimumDifficulty,
        MaximumDifficulty,
        PresetOverrides,
        FixedPuzzles
    ])
]


@dataclass
class SgtKeenOptions(PerGameCommonOptions):
    puzzle_count: PuzzleCount
    starting_puzzles: StartingPuzzles
    starting_clue_bonus: StartingClueBonus
    completion_percentage: CompletionPercentage
    bonus_checks_per_digit_group: BonusChecksPerDigitGroup
    min_difficulty: MinimumDifficulty
    max_difficulty: MaximumDifficulty
    preset_overrides: PresetOverrides
    fixed_puzzles: FixedPuzzles

    start_inventory_pool: StartInventoryPool
