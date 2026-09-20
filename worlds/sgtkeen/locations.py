from BaseClasses import Location
import typing
from .items import max_puzzles, max_groups_per_puzzle


class AdvData(typing.NamedTuple):
    id: int
    region: str = "Puzzles"


class SgtKeenLocation(Location):
    game: str = "Progressive Keen"


base_id = 9250000

# "Puzzle {i+1} Digit Group {j+1}" for i in [0, max_puzzles), j in [0, max_groups_per_puzzle).
# Checking this location means the player has correctly filled in the cells
# that become logically deducible once clue group j+1 is revealed (i.e. once
# they hold j+1 copies of "Puzzle {i+1} Clue").
advancement_table = {
    f"Puzzle {i+1} Digit Group {j+1}": AdvData(base_id + i * max_groups_per_puzzle + j)
    for i in range(max_puzzles)
    for j in range(max_groups_per_puzzle)
}

# "Puzzle {i+1} Solved" for i in [0, max_puzzles). Checking this location means
# the puzzle has been fully solved (every Digit Group's cells correctly filled
# in) -- it exists purely to give this world extra location capacity, one per
# puzzle, to back the "Puzzle N" unlock items (see items.py/rules.py): those
# are new required items with no Digit Group location of their own behind
# them, since unlocking a puzzle is a precondition for its Digit Groups, not
# an achievement within them.
advancement_table.update({
    f"Puzzle {i+1} Solved": AdvData(base_id + max_puzzles * max_groups_per_puzzle + i)
    for i in range(max_puzzles)
})

lookup_id_to_name: typing.Dict[int, str] = {data.id: location_name for location_name, data in advancement_table.items()}
