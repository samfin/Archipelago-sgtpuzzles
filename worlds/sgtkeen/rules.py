from worlds.generic.Rules import set_rule
from BaseClasses import MultiWorld
from .items import max_puzzles
from .locations import digit_group_location_names


# Sets rules on locations that are always applied.
# digit_group_counts[i] is the number of Digit Group stages puzzle i actually has.
# bonus_checks_per_digit_group is the world's bonus_checks_per_digit_group option
# value -- see locations.py's digit_group_location_names(), the one place that
# decides how many locations (and what they're named) back a single Digit
# Group; every one of them gets the exact same access rule here, since they're
# released together as one milestone, not sequenced against each other.
# starting_puzzle_count is how many puzzles (by index, 0-based) are accessible from
# the start -- puzzles beyond that also need their own "Puzzle {i+1}" item before
# any of their Digit Group locations become reachable at all.
def set_rules(multiworld: MultiWorld, player: int, puzzles: list[str], digit_group_counts: list[int],
              bonus_checks_per_digit_group: int, starting_puzzle_count: int):
    for i in range(len(puzzles)):
        clue_set_name = f"Puzzle {i+1} Clue"
        unlock_name = f"Puzzle {i+1}"
        needs_unlock_item = i >= starting_puzzle_count

        for j in range(1, digit_group_counts[i] + 1):
            for location_name in digit_group_location_names(i+1, j, bonus_checks_per_digit_group):
                if needs_unlock_item:
                    set_rule(
                        multiworld.get_location(location_name, player),
                        lambda state, clue_set_name=clue_set_name, unlock_name=unlock_name, j=j:
                            state.has(unlock_name, player) and state.count(clue_set_name, player) >= j)
                else:
                    set_rule(
                        multiworld.get_location(location_name, player),
                        lambda state, clue_set_name=clue_set_name, j=j: state.count(clue_set_name, player) >= j)

        # "Puzzle {i+1} Solved" location: same requirement as the puzzle's own
        # final Digit Group (i.e. available exactly once the puzzle is fully
        # solved). Exists purely to give this world extra location capacity to
        # back the "Puzzle N" unlock items (see items.py) -- it isn't itself
        # part of the Digit Group progression, and is never split into bonus
        # checks (it's one puzzle-wide milestone, not a Digit Group).
        solved_location_name = f"Puzzle {i+1} Solved"
        final_count = digit_group_counts[i]
        if needs_unlock_item:
            set_rule(
                multiworld.get_location(solved_location_name, player),
                lambda state, clue_set_name=clue_set_name, unlock_name=unlock_name, final_count=final_count:
                    state.has(unlock_name, player) and state.count(clue_set_name, player) >= final_count)
        else:
            set_rule(
                multiworld.get_location(solved_location_name, player),
                lambda state, clue_set_name=clue_set_name, final_count=final_count:
                    state.count(clue_set_name, player) >= final_count)


# A puzzle counts as fully solved once its final Digit Group's requirement is met,
# i.e. every clue group has been revealed and (by construction) the whole grid is
# logically forced.
def set_completion_rules(multiworld: MultiWorld, player: int, puzzles: list[str],
                          digit_group_counts: list[int], target_puzzles: int):
    def solved_puzzle_count(state) -> int:
        count = 0
        for i in range(len(puzzles)):
            if state.count(f"Puzzle {i+1} Clue", player) >= digit_group_counts[i]:
                count += 1
        return count

    multiworld.completion_condition[player] = lambda state: solved_puzzle_count(state) >= target_puzzles
