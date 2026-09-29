from BaseClasses import Item
import typing

base_id = 9250000

# Maximum number of independent Keen puzzles a world can have active at once.
# This only sizes the item/location ID space; actual count is set by the
# puzzle_count option.
max_puzzles = 50

# Maximum number of progression stages (Clue copies / Digit Group
# locations) any single puzzle can have. Actual per-puzzle target comes
# from that puzzle's own type string (the optional trailing Digit Group
# count in e.g. "9dx20" -- see randomizer.parse_puzzle_type()), clamped to
# this value.
max_groups_per_puzzle = 50

# Maximum value of the bonus_checks_per_digit_group option (see
# options.py): how many EXTRA locations a single Digit Group can be
# split into on top of its own one, when that option is positive. Only
# sizes the reserved location ID space for the numbered
# "Digit Group J-1".."Digit Group J-(V+1)" naming scheme (see
# locations.py's digit_group_location_names()); actual per-world value
# is set by the option itself.
max_bonus_checks_per_digit_group = 19


class ItemData(typing.NamedTuple):
    code: int
    progression: bool = True


class SgtKeenItem(Item):
    game: str = "Progressive Keen"


# One progressive item per puzzle slot. Receiving the Nth copy of
# "Puzzle {i+1} Clue" reveals that puzzle's Nth clue group client-side,
# and is what the "Puzzle {i+1} Digit Group N" location's access rule counts.
item_table = {
    f"Puzzle {i+1} Clue": ItemData(base_id + i)
    for i in range(max_puzzles)
}

# One unlock item per puzzle slot. A puzzle beyond the world's
# starting_puzzles count isn't accessible at all -- none of its Digit Group
# locations can be checked -- until its own "Puzzle {i+1}" item is received,
# in addition to the usual Clue count for whichever Digit Group is being
# checked (see rules.py). Puzzles within the starting count never need this
# item; it's simply never created for them (see __init__.py's create_items()).
item_table.update({
    f"Puzzle {i+1}": ItemData(base_id + max_puzzles + i)
    for i in range(max_puzzles)
})

item_table["Filler"] = ItemData(base_id + 2 * max_puzzles, False)

# Purely cosmetic re-flavorings of the plain "Filler" item above -- same
# ItemClassification.filler behavior (no progression, no logic depends on
# which of these a player receives), just a different display name/flavor
# text. create_filler() (in __init__.py) picks "Filler" itself 75% of the
# time and one of these, uniformly at random, the other 25% -- see its own
# comment for the exact odds. Each still needs its own unique item code
# since Archipelago items are keyed by (name, code) pair, even though none
# of these differ functionally from "Filler" or from each other.
filler_flavor_names = [
    "Cluster 67",
    "Cluster 69",
    "Cluster 42",
    "Cluster 3.14",
    "Progressive Key",
    "Dive",
    "Ledge Grab",
    "Triple Jump",
    "Wall Kick",
    "Kick",
]
item_table.update({
    name: ItemData(base_id + 2 * max_puzzles + 1 + i, False)
    for i, name in enumerate(filler_flavor_names)
})

lookup_id_to_name: typing.Dict[int, str] = {data.code: item_name for item_name, data in item_table.items()}
