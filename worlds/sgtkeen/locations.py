from BaseClasses import Location
import typing
from .items import max_puzzles, max_groups_per_puzzle, max_bonus_checks_per_digit_group


class AdvData(typing.NamedTuple):
    id: int
    region: str = "Puzzles"


class SgtKeenLocation(Location):
    game: str = "Progressive Keen"


base_id = 9250000

# One Digit Group milestone is either a single location (the plain
# "Puzzle {i+1} Digit Group {j+1}" name, used when the world's
# bonus_checks_per_digit_group option is 0 -- the default, and this
# world's original behavior) or, when that option is positive, a run of
# (bonus + 1) uniformly-renamed locations "Puzzle {i+1} Digit Group
# {j+1}-1" .. "Puzzle {i+1} Digit Group {j+1}-(bonus+1)", all released by
# the exact same access rule (see rules.py's set_rules()) -- see
# digit_group_location_names() below, the one place that decides a
# group's actual location name(s), shared by every caller so they can
# never disagree.
#
# Which naming scheme (and how many bonus slots) a given world actually
# uses is a per-seed YAML choice, not something this static, module-
# load-time table can know -- so both schemes get their own permanently-
# reserved id block, each sized for its own worst case, exactly like
# max_puzzles/max_groups_per_puzzle already do for puzzle count and
# Digit Group count. A seed that doesn't use every reserved name simply
# never creates a Location for it (see __init__.py's create_regions());
# reserving the id costs nothing.

# Block 1 -- the unnumbered names, for bonus_checks_per_digit_group == 0.
# "Puzzle {i+1} Digit Group {j+1}" for i in [0, max_puzzles), j in [0, max_groups_per_puzzle).
advancement_table = {
    f"Puzzle {i+1} Digit Group {j+1}": AdvData(base_id + i * max_groups_per_puzzle + j)
    for i in range(max_puzzles)
    for j in range(max_groups_per_puzzle)
}
_block1_size = max_puzzles * max_groups_per_puzzle

# Block 2 -- the numbered bonus-check names, for bonus_checks_per_digit_group > 0.
# "Puzzle {i+1} Digit Group {j+1}-{k+1}" for i in [0, max_puzzles),
# j in [0, max_groups_per_puzzle), k in [0, max_bonus_checks_per_digit_group]
# (max_bonus_checks_per_digit_group + 1 slots per group, covering "bonus + 1"
# total checks at the option's own maximum value).
_bonus_slots = max_bonus_checks_per_digit_group + 1
_block2_base = base_id + _block1_size
advancement_table.update({
    f"Puzzle {i+1} Digit Group {j+1}-{k+1}": AdvData(
        _block2_base + i * max_groups_per_puzzle * _bonus_slots + j * _bonus_slots + k)
    for i in range(max_puzzles)
    for j in range(max_groups_per_puzzle)
    for k in range(_bonus_slots)
})
_block2_size = max_puzzles * max_groups_per_puzzle * _bonus_slots

# Block 3 -- "Puzzle {i+1} Solved" for i in [0, max_puzzles). Checking this
# location means the puzzle has been fully solved (every Digit Group's
# cells correctly filled in) -- it exists purely to give this world extra
# location capacity, one per puzzle, to back the "Puzzle N" unlock items
# (see items.py/rules.py): those are new required items with no Digit
# Group location of their own behind them, since unlocking a puzzle is a
# precondition for its Digit Groups, not an achievement within them.
_block3_base = _block2_base + _block2_size
advancement_table.update({
    f"Puzzle {i+1} Solved": AdvData(_block3_base + i)
    for i in range(max_puzzles)
})

lookup_id_to_name: typing.Dict[int, str] = {data.id: location_name for location_name, data in advancement_table.items()}


def digit_group_location_names(puzzle_number: int, group_number: int, bonus_checks: int) -> list[str]:
    """
    The location name(s) for one Digit Group milestone (puzzle_number and
    group_number both 1-indexed, matching the location names themselves).

    With bonus_checks <= 0 (the bonus_checks_per_digit_group option's
    default), a group is exactly one location, named as this world
    always has: "Puzzle {puzzle_number} Digit Group {group_number}".

    With bonus_checks == V > 0, a group is (V + 1) locations, uniformly
    renamed "Puzzle {puzzle_number} Digit Group {group_number}-1" through
    "...-(V + 1)" -- all released together, by the exact same access rule
    as the group itself (see rules.py's set_rules()). They exist purely
    to add more locations -- and so more items -- to a group's single
    milestone, never to require any extra player action to reach: the
    solve requirement for the group (filling in its own forced cells) is
    unchanged either way.
    """
    base = f"Puzzle {puzzle_number} Digit Group {group_number}"
    if bonus_checks <= 0:
        return [base]
    return [f"{base}-{k+1}" for k in range(bonus_checks + 1)]
