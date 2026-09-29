import logging
from math import ceil
from BaseClasses import Item, Region, Entrance, ItemClassification
from .items import SgtKeenItem, item_table, max_puzzles, max_groups_per_puzzle, max_bonus_checks_per_digit_group, filler_flavor_names
from .locations import SgtKeenLocation, advancement_table, digit_group_location_names
from .options import SgtKeenOptions, genrePresets, sgtkeen_option_groups
from .rules import set_rules, set_completion_rules
from .randomizer import generate_puzzle_list
from worlds.AutoWorld import World, WebWorld

file_version = 1
world_version = "0.3.0"

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
    bonus_checks_per_digit_group: int
    solve_target: int
    world_seed: int

    item_name_to_id = {name: data.code for name, data in item_table.items()}
    location_name_to_id = {name: data.id for name, data in advancement_table.items()}

    item_name_groups = {
        "Clue": {f"Puzzle {i+1} Clue" for i in range(max_puzzles)},
        "Puzzle Unlock": {f"Puzzle {i+1}" for i in range(max_puzzles)},
        # Every name create_filler() can produce -- plain "Filler" plus all
        # of its purely-cosmetic re-flavorings -- grouped together so a
        # player can still hint/plando/reference "the filler items" as one
        # group despite them now having 11 different possible names.
        "Filler": {"Filler", *filler_flavor_names},
    }

    location_name_groups = {
        # Every "Digit Group" location name this world can ever create --
        # both the unnumbered form (bonus_checks_per_digit_group == 0) and
        # every numbered "-1".."-(max_bonus_checks_per_digit_group + 1)"
        # variant (bonus_checks_per_digit_group > 0) -- so a player can
        # hint/plando/reference "the Digit Group locations" as one group
        # regardless of which naming scheme this seed's options ended up
        # using. Built from the same digit_group_location_names() helper
        # that create_regions() uses -- at bonus_checks_per_digit_group == 0
        # AND at the worst case (max bonus checks) -- rather than
        # duplicating its naming rule here. Calling the helper with only
        # the max value would miss the unnumbered form entirely (it
        # returns only the numbered names once its bonus_checks argument is
        # positive), so both ends of the range are unioned in explicitly;
        # every value in between produces a subset of the max case's
        # numbered names, so nothing between 0 and the max is missed.
        "Digit Group": {
            name
            for i in range(max_puzzles)
            for j in range(max_groups_per_puzzle)
            for bonus in (0, max_bonus_checks_per_digit_group)
            for name in digit_group_location_names(i + 1, j + 1, bonus)
        },
        "Solved": {f"Puzzle {i+1} Solved" for i in range(max_puzzles)}
    }

    def generate_early(self):
        self.world_seed = self.random.getrandbits(32)

        puzzle_count = self.options.puzzle_count.value
        fixed_puzzles = self.options.fixed_puzzles.value[:puzzle_count]

        # generate_puzzle_list returns (native_puzzle_spec, digit_group_count)
        # pairs -- see options.py's Fixed Puzzles/Preset Overrides docs and
        # randomizer.parse_puzzle_type() for the "<size>d<diff>[m][<clues>]"
        # puzzle-type grammar each spec/override entry is parsed from. The
        # web client's ArchipelagoPuzzle.fromArchipelagoString expects each
        # slot-data puzzle string to start with a genre prefix
        # ("<genre>:<params>..."), so prefix every native spec with this
        # world's only genre now that it's Keen-only; the digit_group_count
        # half of each pair is this world's own concept and was already
        # split off by generate_puzzle_list, so it's carried separately
        # rather than ending up as part of the puzzle string at all.
        puzzle_specs = generate_puzzle_list(
            random=self.random,
            count=puzzle_count,
            fixed_puzzles=fixed_puzzles,
            presets=genrePresets["keen"],
            preset_overrides=self.options.preset_overrides.value,
            min_difficulty=min(self.options.min_difficulty.value, self.options.max_difficulty.value),
            max_difficulty=self.options.max_difficulty.value)

        self.puzzles = [f"keen:{native}" for native, _ in puzzle_specs]

        # Each puzzle's own target stage count, per its puzzle type's
        # embedded Digit Group count (or randomizer.default_digit_group_count
        # when a type didn't specify one) -- no longer a single value shared
        # by every puzzle regardless of size, since a small grid can't
        # support the same path length as a large one.
        self.digit_group_counts = [count for _, count in puzzle_specs]

        # Number of puzzles (by index, 0-based) accessible from the start --
        # capped at len(self.puzzles) so a YAML asking for more starting
        # puzzles than actually exist doesn't misbehave. Every puzzle at or
        # beyond this count needs its own "Puzzle N" item before any of its
        # Digit Group locations become accessible (see rules.py/create_items()).
        self.starting_puzzle_count = min(self.options.starting_puzzles.value, len(self.puzzles))

        self.bonus_checks_per_digit_group = self.options.bonus_checks_per_digit_group.value

        self.solve_target = ceil(len(self.puzzles) * (self.options.completion_percentage / 100))

    def create_regions(self):
        menu = Region("Menu", self.player, self.multiworld)
        region = Region("Puzzles", self.player, self.multiworld)

        for i in range(len(self.puzzles)):
            for j in range(self.digit_group_counts[i]):
                # bonus_checks_per_digit_group == 0 (the default) returns
                # just the one unnumbered name, so this loop creates exactly
                # the same single location per group as before in that case
                # -- see locations.py/digit_group_location_names().
                for loc_name in digit_group_location_names(i + 1, j + 1, self.bonus_checks_per_digit_group):
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
        # Purely cosmetic: 75% of the time this is plain "Filler"; the
        # other 25%, it's one of filler_flavor_names, picked uniformly at
        # random (each of the 10 flavor names -- including each of the 4
        # "Cluster N" variants -- individually has a flat 2.5% chance).
        # All of these share ItemClassification.filler and are otherwise
        # completely interchangeable -- no logic anywhere distinguishes
        # them -- so this only affects what name/flavor text the player
        # sees. Uses self.random (not the stdlib random module) so the
        # choice is deterministic per seed, like the rest of generation.
        if self.random.random() < 0.75:
            name = "Filler"
        else:
            name = self.random.choice(filler_flavor_names)
        return self.create_item(name)

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
        # Starting Clue Bonus (an additional option, on top of the
        # universal "1 Clue per puzzle" above): grants extra precollected
        # Clues -- beyond the 1 every puzzle already gets -- to whichever
        # puzzles are accessible from the very start (i < starting_puzzle_
        # count). A puzzle unlocked later via its own "Puzzle N" item is
        # unaffected regardless of this option's value, matching Starting
        # Clue Bonus's own description ("puzzles accessible from the
        # start"). Capped per puzzle at digit_group_counts[i] so this can
        # never try to precollect more copies of a puzzle's Clue than
        # actually exist in its pool -- min(1 + bonus, digit_group_counts[i])
        # rather than 1 + bonus outright.
        starting_clue_bonus = self.options.starting_clue_bonus.value

        granted_starting_items = 0

        for i in range(len(self.puzzles)):
            clue_set_name = f"Puzzle {i+1} Clue"
            target_count = 1
            if i < self.starting_puzzle_count and starting_clue_bonus > 0:
                target_count = min(1 + starting_clue_bonus, self.digit_group_counts[i])

            for _ in range(target_count):
                if clue_set_name not in itempool:
                    # Shouldn't happen given the cap above, but never try to
                    # precollect more copies than the pool actually has.
                    break
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
        # Each Digit Group now backs (self.bonus_checks_per_digit_group + 1)
        # locations instead of always exactly 1 -- see create_regions() and
        # locations.py/digit_group_location_names() -- so the pool's target
        # size has to scale by the same factor to still match this world's
        # actual total location count.
        checks_per_group = self.bonus_checks_per_digit_group + 1
        total_locations = sum(self.digit_group_counts) * checks_per_group + len(self.puzzles)
        current_pool_size = len(itempool) + granted_starting_items
        shortfall = total_locations - current_pool_size
        if shortfall > 0:
            self.multiworld.itempool += [self.create_filler() for _ in range(shortfall)]

    def set_rules(self):
        set_rules(self.multiworld, self.player, self.puzzles, self.digit_group_counts, self.bonus_checks_per_digit_group, self.starting_puzzle_count)
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
            "bonus_checks_per_digit_group": self.bonus_checks_per_digit_group,
            "solve_target": self.solve_target
        }

    def create_item(self, name: str) -> SgtKeenItem:
        item_data = item_table[name]
        classification = ItemClassification.progression if item_data.progression else ItemClassification.filler
        return SgtKeenItem(name, classification, item_data.code, self.player)
