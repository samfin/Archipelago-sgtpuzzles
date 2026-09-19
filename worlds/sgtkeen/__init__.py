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
    first; obtaining "Clue Set" items reveals later groups one at a time,
    each one making a new set of digits ("Digit Group") logically
    deducible without any guessing.
    """
    game = "Progressive Keen"
    options: SgtKeenOptions
    options_dataclass = SgtKeenOptions
    web = SgtKeenWeb()
    puzzles: list[str]
    digit_group_counts: list[int]
    solve_target: int
    world_seed: int

    item_name_to_id = {name: data.code for name, data in item_table.items()}
    location_name_to_id = {name: data.id for name, data in advancement_table.items()}

    item_name_groups = {
        "Clue Set": {f"Puzzle {i+1} Clue Set" for i in range(max_puzzles)}
    }

    location_name_groups = {
        "Digit Group": {
            f"Puzzle {i+1} Digit Group {j+1}"
            for i in range(max_puzzles)
            for j in range(max_groups_per_puzzle)
        }
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

        connection = Entrance(self.player, "Get Puzzles", menu)
        menu.exits.append(connection)
        connection.connect(region)
        self.multiworld.regions += [menu, region]

    def create_filler(self) -> Item:
        return self.create_item("Filler")

    def create_items(self):
        itempool: list[str] = []

        for i in range(len(self.puzzles)):
            item_name = f"Puzzle {i+1} Clue Set"
            itempool += [item_name] * self.digit_group_counts[i]

        # Remove existing starting items
        starting_items = self.multiworld.precollected_items[self.player]

        for item in starting_items:
            if item.name in itempool:
                itempool.remove(item.name)
            else:
                logging.warning(f"Couldn't remove {item.name} from Clue Set itempool. It's probably useless.")

        # Grant starting_clue_sets copies per puzzle as precollected items,
        # capped so at least one Digit Group location stays behind an item.
        # Each one removed from the pool is replaced with a Filler so the
        # pool still has exactly as many items as this world has locations.
        granted_starting_items = 0

        for i in range(len(self.puzzles)):
            item_name = f"Puzzle {i+1} Clue Set"
            starting_count = min(self.options.starting_clue_sets.value, self.digit_group_counts[i] - 1)
            for _ in range(starting_count):
                if item_name in itempool:
                    itempool.remove(item_name)
                    self.multiworld.push_precollected(self.create_item(item_name))
                    granted_starting_items += 1

        self.multiworld.itempool += [self.create_item(itemname) for itemname in itempool]
        self.multiworld.itempool += [self.create_filler() for _ in range(granted_starting_items)]

    def set_rules(self):
        set_rules(self.multiworld, self.player, self.puzzles, self.digit_group_counts)
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
            "solve_target": self.solve_target
        }

    def create_item(self, name: str) -> SgtKeenItem:
        item_data = item_table[name]
        classification = ItemClassification.progression if item_data.progression else ItemClassification.filler
        return SgtKeenItem(name, classification, item_data.code, self.player)
