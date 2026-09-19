from BaseClasses import Item
import typing

base_id = 9250000

# Maximum number of independent Keen puzzles a world can have active at once.
# This only sizes the item/location ID space; actual count is set by the
# puzzle_count option.
max_puzzles = 200

# Maximum number of progression stages (Clue Set copies / Digit Group
# locations) any single puzzle can have. Actual per-world target is set by
# the digit_group_count option.
max_groups_per_puzzle = 50


class ItemData(typing.NamedTuple):
    code: int
    progression: bool = True


class SgtKeenItem(Item):
    game: str = "Progressive Keen"


# One progressive item per puzzle slot. Receiving the Nth copy of
# "Puzzle {i+1} Clue Set" reveals that puzzle's Nth clue group client-side,
# and is what the "Puzzle {i+1} Digit Group N" location's access rule counts.
item_table = {
    f"Puzzle {i+1} Clue Set": ItemData(base_id + i)
    for i in range(max_puzzles)
}

# One unlock item per puzzle slot. A puzzle beyond the world's
# starting_puzzles count isn't accessible at all -- none of its Digit Group
# locations can be checked -- until its own "Puzzle {i+1}" item is received,
# in addition to the usual Clue Set count for whichever Digit Group is being
# checked (see rules.py). Puzzles within the starting count never need this
# item; it's simply never created for them (see __init__.py's create_items()).
item_table.update({
    f"Puzzle {i+1}": ItemData(base_id + max_puzzles + i)
    for i in range(max_puzzles)
})

item_table["Filler"] = ItemData(base_id + 2 * max_puzzles, False)

lookup_id_to_name: typing.Dict[int, str] = {data.code: item_name for item_name, data in item_table.items()}
