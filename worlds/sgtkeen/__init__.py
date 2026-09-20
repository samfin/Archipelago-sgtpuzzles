import logging
from math import ceil
from BaseClasses import Item, Region, Entrance, ItemClassification
from .items import SgtKeenItem, item_table, max_puzzles, max_groups_per_puzzle
from .locations import SgtKeenLocation, advancement_table
from .options import SgtKeenOptions, genrePresets, sgtkeen_option_groups
from .rules import set_rules, set_completion_rules
from .randomizer import generate_puzzle_list
from worlds.AutoWorld import World, WebWorld

file_version = 1
world_version = "0.2.0"

class SgtKeenWeb(WebWorld):
    option_groups = sgtkeen_option_groups


class SgtKeenWorld(World):
    """
    A Keen (KenKen-style) puzzle from Simon Tatham's Portable Puzzle
    Collection, played through a progressive reveal: a puzzle's clues are
    grouped into an ordered chain. Only the first clue group is visible at
    first; obtaining "Clue" items reveals later groups one at a time,
    each one making a new set of digits ("Digit Group") logically
    deducible without any guessing.
    """
    game = "Progressive Keen"
    options: SgtKeenOptions
    options_dataclass = SgtKeenOptions
    web = SgtKeenWeb()
    puzzles: list[str]
    digit_group_counts: list[int]
    starting_puzzle_count: int
    solve_target: int
    world_seed: int

    item_name_to_id = {name: data.code for name, data in item_table.items()}
    location_name_to_id = {name: data.id for name, data in advancement_table.items()}

    item_name_groups = {
        "Clue": {f"Puzzle {i+1} Clue" for i in range(max_puzzles)},
        "Puzzle Unlock": {f"Puzzle {i+1}" for i in range(max_puzzles)}
    }

    location_name_groups = {
        "Digit Group": {
            f"Puzzle {i+1} Digit Group {j+1}"
            for i in range(max_puzzles)
            for j in range(max_groups_per_puzzle)
        },
        "Solved": {f"Puzzle {i+1} Solved" for i in range(max_puzzles)}
    }

    def generate_early(self):
        self.world_seed = self.random.getrandbits(32)

        puzzle_count = self.options.puzzle_count.value
        fixed_puzzles = self.options.fixed_puzzles.value[:puzzle_count]

        # generate_puzzle_list returns bare Keen puzzle strings ("6de",
        # "6de#12345", "6de:c494" -- see options.py's Fixed Puzzles/Preset
        # Overrides docs). The web client's ArchipelagoPuzzle.fromArchipelagoString
        # expects each slot-data puzzle string to start with a genre prefix
        # ("<genre>:<params>..."), so prefix every entry with this world's
        # only genre now that it's Keen-only.
        self.puzzles = [
            f"keen:{p}"
            for p in generate_puzzle_list(
                random=self.random,
                count=puzzle_count,
                fixed_puzzles=fixed_puzzles,
                presets=genrePresets["keen"],
                preset_overrides=self.options.preset_overrides.value,
                min_difficulty=min(self.options.min_difficulty.value, self.options.max_difficulty.value),
                max_difficulty=self.options.max_difficulty.value,
                min_size=min(self.options.min_size.value, self.options.max_size.value),
                max_size=self.options.max_size.value)
        ]

        # Every puzzle gets the same target stage count for now; this is a
        # list (rather than a single int) so a future option could vary it
        # per puzzle without changing the rest of the pipeline.
        self.digit_group_counts = [self.options.digit_group_count.value for _ in self.puzzles]

        # Number of puzzles (by index, 0-based) accessible from the start --
        # capped at len(self.puzzles) so a YAML asking for more starting
        # puzzles than actually exist doesn't misbehave. Every puzzle at or
        # beyond this count needs its own "Puzzle N" item before any of its
        # Digit Group locations become accessible (see rules.py/create_items()).
        self.starting_puzzle_count = min(self.options.starting_puzzles.value, len(self.puzzles))

        self.solve_target = ceil(len(self.puzzles) * (self.options.completion_percentage / 100))

    def create_regions(self):
        menu = Region("Menu", self.player, self.multiworld)
        region = Region("Puzzles", self.player, self.multiworld)

        for i in range(len(self.puzzles)):
            for j in range(self.digit_group_counts[i]):
                loc_name = f"Puzzle {i+1} Digit Group {j+1}"
                loc_data = advancement_table[loc_name]
                new_location = SgtKeenLocation(self.player, loc_name, loc_data.id, region)
                region.locations.append(new_location)

            # One "Puzzle {i+1} Solved" location per puzzle (every puzzle, not
            # just ones needing an unlock item) -- see locations.py/rules.py.
            # It exists purely to give this world extra location capacity to
            # back the "Puzzle N" unlock items introduced alongside
            # puzzle-locking, since those are new required items with no
            # Digit Group location of their own behind them.
            solved_name = f"Puzzle {i+1} Solved"
            solved_data = advancement_table[solved_name]
            solved_location = SgtKeenLocation(self.player, solved_name, solved_data.id, region)
            region.locations.append(solved_location)

        connection = Entrance(self.player, "Get Puzzles", menu)
        menu.exits.append(connection)
        connection.connect(region)
        self.multiworld.regions += [menu, region]

    def create_filler(self) -> Item:
        return self.create_item("Filler")

    def create_items(self):
        itempool: list[str] = []

        for i in range(len(self.puzzles)):
            clue_set_name = f"Puzzle {i+1} Clue"
            itempool += [clue_set_name] * self.digit_group_counts[i]

            # Every puzzle beyond the starting count needs its own unlock item
            # before any of its Digit Group locations become accessible at all
            # (see rules.py). Starting puzzles never need one -- it's simply
            # never created for them.
            if i >= self.starting_puzzle_count:
                itempool.append(f"Puzzle {i+1}")

        # Remove existing starting items
        starting_items = self.multiworld.precollected_items[self.player]

        for item in starting_items:
            if item.name in itempool:
                itempool.remove(item.name)
            else:
                logging.warning(f"Couldn't remove {item.name} from Clue itempool. It's probably useless.")

        # Every puzzle -- not just the starting_puzzle_count that are
        # accessible immediately -- is granted exactly 1 Clue as starting
        # inventory (precollected, so it's part of the initial state rather
        # than something that has to be found in the pool). For a starting
        # puzzle this is what makes it playable from the very first location
        # check. For a puzzle beyond the starting count, it's what makes
        # receiving that puzzle's own "Puzzle N" item alone enough to unlock
        # its first Digit Group -- previously that also needed a *separate*
        # found "Puzzle N Clue" item, effectively gating every non-
        # starting puzzle behind two independently-placed progression items
        # before its own locations opened up at all. That double gating was
        # unnecessarily deep (it also directly contributed to "not enough
        # reachable locations"-style fill failures once puzzle_count grew well
        # past starting_puzzles, since almost nothing was reachable until both
        # items for a given puzzle happened to be placed) and isn't what the
        # feature was meant to require -- "unlocking" a puzzle should be
        # enough progress on its own to start it. Each one removed from the
        # pool is replaced with a Filler below so removing it doesn't shrink
        # the pool -- the final top-up after this (see below) is what accounts
        # for the "Puzzle N" unlock items added above, which have no Digit
        # Group location of their own.
        granted_starting_items = 0

        for i in range(len(self.puzzles)):
            clue_set_name = f"Puzzle {i+1} Clue"
            if clue_set_name in itempool:
                itempool.remove(clue_set_name)
                self.multiworld.push_precollected(self.create_item(clue_set_name))
                granted_starting_items += 1

        self.multiworld.itempool += [self.create_item(itemname) for itemname in itempool]
        self.multiworld.itempool += [self.create_filler() for _ in range(granted_starting_items)]

        # This world now has one "Puzzle {i+1} Solved" location per puzzle in
        # addition to its Digit Group locations (see create_regions()), which
        # is exactly the extra capacity needed to back the "Puzzle N" unlock
        # items added to itempool above (new required items with no Digit
        # Group location of their own). Top up with Filler so the pool still
        # matches this world's total location count exactly, the same
        # deterministic-size convention used everywhere else in this method,
        # rather than relying on the generic multiworld fill step to pad an
        # undersized pool on its own.
        total_locations = sum(self.digit_group_counts) + len(self.puzzles)
        current_pool_size = len(itempool) + granted_starting_items
        shortfall = total_locations - current_pool_size
        if shortfall > 0:
            self.multiworld.itempool += [self.create_filler() for _ in range(shortfall)]

    def set_rules(self):
        set_rules(self.multiworld, self.player, self.puzzles, self.digit_group_counts, self.starting_puzzle_count)
        set_completion_rules(self.multiworld, self.player, self.puzzles, self.digit_group_counts, self.solve_target)

    def fill_slot_data(self):
        return {
            "world_seed": self.world_seed,
            "seed_name": self.multiworld.seed_name,
            "player_name": self.player_name,
            "player_id": self.player,
            "file_version": file_version,
            "world_version": world_version,
            "race": self.multiworld.is_race,
            "puzzles": self.puzzles,
            "digit_group_counts": self.digit_group_counts,
            "starting_puzzle_count": self.starting_puzzle_count,
            "solve_target": self.solve_target
        }

    def create_item(self, name: str) -> SgtKeenItem:
        item_data = item_table[name]
        classification = ItemClassification.progression if item_data.progression else ItemClassification.filler
        return SgtKeenItem(name, classification, item_data.code, self.player)
