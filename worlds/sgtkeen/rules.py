from worlds.generic.Rules import set_rule
from BaseClasses import MultiWorld
from .items import max_puzzles


# Sets rules on locations that are always applied.
# digit_group_counts[i] is the number of Digit Group stages puzzle i actually has.
def set_rules(multiworld: MultiWorld, player: int, puzzles: list[str], digit_group_counts: list[int]):
    for i in range(len(puzzles)):
        item_name = f"Puzzle {i+1} Clue Set"
        for j in range(1, digit_group_counts[i] + 1):
            location_name = f"Puzzle {i+1} Digit Group {j}"
            set_rule(
                multiworld.get_location(location_name, player),
                lambda state, item_name=item_name, j=j: state.count(item_name, player) >= j)


# A puzzle counts as fully solved once its final Digit Group's requirement is met,
# i.e. every clue group has been revealed and (by construction) the whole grid is
# logically forced.
def set_completion_rules(multiworld: MultiWorld, player: int, puzzles: list[str],
                          digit_group_counts: list[int], target_puzzles: int):
    def solved_puzzle_count(state) -> int:
        count = 0
        for i in range(len(puzzles)):
            if state.count(f"Puzzle {i+1} Clue Set", player) >= digit_group_counts[i]:
                count += 1
        return count

    multiworld.completion_condition[player] = lambda state: solved_puzzle_count(state) >= target_puzzles
