from worlds.AutoWorld import World
from BaseClasses import Region, Item, ItemClassification, Entrance, Tutorial
from typing import List, ClassVar, Type
from math import floor
from Options import PerGameCommonOptions

from .Options import MegaMixOptions
from .Items import MegaMixSongItem, MegaMixFixedItem
from .Locations import MegaMixLocation
from .MegaMixCollection import MegaMixCollections
from worlds.LauncherComponents import Component, components, Type, launch_subprocess

import settings
import typing


def launch_client():
    from .Client import launch
    launch_subprocess(launch, name="MegaMixClient")


components.append(Component(
    "Mega Mix Client",
    "MegaMixClient",
    func=launch_client,
    component_type=Type.CLIENT
))


class MegaMixSettings(settings.Group):
    class ModPath(settings.LocalFolderPath):
        """Path to diva mods folder"""

    mod_path: ModPath = ModPath(
        "C:/Program Files (x86)/Steam/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods")


class MegaMixWorld(World):
    """Hatsune Miku: Project Diva Mega Mix+ is a rhythm game where you hit notes to the beat of one of 250+ songs.
    Play through a selection of randomly chosen songs, collecting leeks
    until you have enough to play and complete the goal song!"""

    # World Options
    game = "Hatsune Miku Project Diva Mega Mix+"

    settings: typing.ClassVar[MegaMixSettings]
    options_dataclass: typing.ClassVar[PerGameCommonOptions] = MegaMixOptions
    options: MegaMixOptions

    topology_present = False

    # Necessary Data
    mm_collection = MegaMixCollections()

    item_name_to_id = {name: code for name, code in mm_collection.item_names_to_id.items()}
    location_name_to_id = {name: code for name, code in mm_collection.location_names_to_id.items()}

    # Working Data
    victory_song_name: str = ""
    starting_songs: List[str]
    included_songs: List[str]
    needed_token_count: int
    location_count: int

    def generate_early(self):
        (lower_diff_threshold, higher_diff_threshold) = self.get_difficulty_range()
        allowed_difficulties = self.get_available_difficulties()

        # The minimum amount of songs to make an ok rando would be Starting Songs + 10 interim songs + Goal song.
        # - Interim songs being equal to max starting song count.
        # Note: The worst settings still allow 25 songs (Streamer Mode + No DLC).
        starter_song_count = self.options.starting_song_count.value

        while True:
            # In most cases this should only need to run once
            available_song_keys = self.mm_collection.get_songs_with_settings(self.options.allow_megamix_dlc_songs, allowed_difficulties, lower_diff_threshold, higher_diff_threshold)

            available_song_keys = self.handle_plando(available_song_keys)

            count_needed_for_start = max(0, starter_song_count - len(self.starting_songs))
            if len(available_song_keys) + len(self.included_songs) >= count_needed_for_start + 11:
                final_song_list = available_song_keys
                break

            # If the above fails, we want to adjust the difficulty thresholds.
            # Easier first, then harder
            if lower_diff_threshold <= 1 and higher_diff_threshold >= 11:
                raise Exception("Failed to find enough songs, even with maximum difficulty thresholds.")
            elif lower_diff_threshold <= 1:
                higher_diff_threshold += 1
            else:
                lower_diff_threshold -= 1

        self.create_song_pool(final_song_list)

        for song in self.starting_songs:
            self.multiworld.push_precollected(self.create_item(song))

    def handle_plando(self, available_song_keys: List[str]) -> List[str]:
        song_items = self.mm_collection.song_items

        start_items = self.options.start_inventory.value.keys()
        include_songs = self.options.include_songs.value
        exclude_songs = self.options.exclude_songs.value

        self.starting_songs = [s for s in start_items if s in song_items]
        self.included_songs = [s for s in include_songs if s in song_items and s not in self.starting_songs]

        return [s for s in available_song_keys if s not in start_items
                and s not in include_songs and s not in exclude_songs]

    def create_song_pool(self, available_song_keys: List[str]):
        starting_song_count = self.options.starting_song_count.value
        additional_song_count = self.options.additional_song_count.value

        self.random.shuffle(available_song_keys)

        # First, we must double check if the player has included too many guaranteed songs
        included_song_count = len(self.included_songs)
        if included_song_count > additional_song_count:
            # If so, we want to thin the list, thus let's get the goal song and starter songs while we are at it.
            self.random.shuffle(self.included_songs)
            self.victory_song_name = self.included_songs.pop()
            while len(self.included_songs) > additional_song_count:
                next_song = self.included_songs.pop()
                if len(self.starting_songs) < starting_song_count:
                    self.starting_songs.append(next_song)
        else:
            # If not, choose a random victory song from the available songs
            chosen_song = self.random.randrange(0, len(available_song_keys) + included_song_count)
            if chosen_song < included_song_count:
                self.victory_song_name = self.included_songs[chosen_song]
                del self.included_songs[chosen_song]
            else:
                self.victory_song_name = available_song_keys[chosen_song - included_song_count]
                del available_song_keys[chosen_song - included_song_count]

        # Next, make sure the starting songs are fufilled
        if len(self.starting_songs) < starting_song_count:
            for _ in range(len(self.starting_songs), starting_song_count):
                if len(available_song_keys) > 0:
                    self.starting_songs.append(available_song_keys.pop())
                else:
                    self.starting_songs.append(self.included_songs.pop())

        # Then attempt to fufill any remaining songs for interim songs
        if len(self.included_songs) < additional_song_count:
            for _ in range(len(self.included_songs), self.options.additional_song_count):
                if len(available_song_keys) <= 0:
                    break
                self.included_songs.append(available_song_keys.pop())

        self.location_count = 2 * (len(self.starting_songs) + len(self.included_songs))

    def create_item(self, name: str) -> Item:
        if name == self.mm_collection.LEEK_NAME:
            return MegaMixFixedItem(name, ItemClassification.progression_skip_balancing,
                                     self.mm_collection.LEEK_CODE, self.player)

        song = self.mm_collection.song_items.get(name)
        return MegaMixSongItem(name, self.player, song)

    def create_items(self) -> None:
        song_keys_in_pool = self.included_songs.copy()

        # Note: Item count will be off if plando is involved.
        item_count = self.get_leek_count()

        # First add all goal song tokens
        for _ in range(0, item_count):
            self.multiworld.itempool.append(self.create_item(self.mm_collection.LEEK_NAME))

        # Then add 1 copy of every song
        item_count += len(self.included_songs)
        for song in self.included_songs:
            self.multiworld.itempool.append(self.create_item(song))

        # At this point, if a player is using traps, it's possible that they have filled all locations
        items_left = self.location_count - item_count
        if items_left <= 0:
            return

        # All remaining spots are filled with duplicate songs. Duplicates are set to useful instead of progression
        # to cut down on the number of progression items that Mega mix puts into the pool.

        # This is for the extraordinary case of needing to fill a lot of items.
        while items_left > len(song_keys_in_pool):
            for key in song_keys_in_pool:
                item = self.create_item(key)
                item.classification = ItemClassification.useful
                self.multiworld.itempool.append(item)

            items_left -= len(song_keys_in_pool)
            continue

        # Otherwise add a random assortment of songs
        self.random.shuffle(song_keys_in_pool)
        for i in range(0, items_left):
            item = self.create_item(song_keys_in_pool[i])
            item.classification = ItemClassification.useful
            self.multiworld.itempool.append(item)

    def create_regions(self) -> None:
        menu_region = Region("Menu", self.player, self.multiworld)
        song_select_region = Region("Song Select", self.player, self.multiworld)
        self.multiworld.regions += [menu_region, song_select_region]
        menu_region.connect(song_select_region)

        # Make a collection of all songs available for this rando.
        # 1. All starting songs
        # 2. All other songs shuffled
        # Doing it in this order ensures that starting songs are first in line to getting 2 locations.
        # Final song is excluded as for the purpose of this rando, it doesn't matter.

        all_selected_locations = self.starting_songs.copy()
        included_song_copy = self.included_songs.copy()

        self.random.shuffle(included_song_copy)
        all_selected_locations.extend(included_song_copy)

        # Make a region per song/album, then adds 1-2 item locations to them
        for i in range(0, len(all_selected_locations)):
            name = all_selected_locations[i]
            region = Region(name, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            song_select_region.connect(region, name, lambda state, place=name: state.has(place, self.player))

            # Mega mix requires 2 locations per song to be *interesting*. Balanced out by filler.
            region.add_locations({
                    name + "-0": self.mm_collection.song_locations[name + "-0"],
                    name + "-1": self.mm_collection.song_locations[name + "-1"]
            }, MegaMixLocation)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: \
            state.has(self.mm_collection.LEEK_NAME, self.player, self.get_leek_win_count())

    def get_leek_count(self) -> int:
        multiplier = self.options.leek_count_percentage.value / 100.0
        song_count = len(self.starting_songs) + len(self.included_songs)
        return max(1, floor(song_count * multiplier))

    def get_leek_win_count(self) -> int:
        multiplier = self.options.leek_win_count_percentage.value / 100.0
        leek_count = self.get_leek_count()
        return max(1, floor(leek_count * multiplier))

    def get_difficulty_range(self) -> List[float]:

        # This is ugly I know don't look at it
        number_to_option_value = {
            0: 1,
            1: 1.5,
            2: 2,
            3: 2.5,
            4: 3,
            5: 3.5,
            6: 4,
            7: 4.5,
            8: 5,
            9: 5.5,
            10: 6,
            11: 6.5,
            12: 7,
            13: 7.5,
            14: 8,
            15: 8.5,
            16: 9,
            17: 9.5,
            18: 10
        }

        difficulty_rating = int(self.options.song_difficulty_rating)

        # Valid difficulties are between 1 and 10.
        difficulty_bounds = [1, 10]
        if difficulty_rating == 1:
            difficulty_bounds[0] = 1
            difficulty_bounds[1] = 4
        elif difficulty_rating == 2:
            difficulty_bounds[0] = 4
            difficulty_bounds[1] = 6
        elif difficulty_rating == 3:
            difficulty_bounds[0] = 6
            difficulty_bounds[1] = 8
        elif difficulty_rating == 4:
            difficulty_bounds[0] = 7
            difficulty_bounds[1] = 9
        elif difficulty_rating == 5:
            difficulty_bounds[0] = 8
            difficulty_bounds[1] = 10
        elif difficulty_rating == 6:
            minimum_difficulty = number_to_option_value.get(self.options.song_difficulty_rating_min, None)
            maximum_difficulty = number_to_option_value.get(self.options.song_difficulty_rating_max, None)

            difficulty_bounds[0] = min(minimum_difficulty, maximum_difficulty)
            difficulty_bounds[1] = max(minimum_difficulty, maximum_difficulty)

        return difficulty_bounds

    def get_available_difficulties(self) -> List[int]:
        difficulty_choice = int(self.options.song_difficulty_mode)
        available_difficulties = []

        difficulty_bounds = [0, 4]
        minimum_difficulty = 0
        maximum_difficulty = 4

        if difficulty_choice == 1:
            available_difficulties.append(0)
        elif difficulty_choice == 2:
            available_difficulties.append(1)
        elif difficulty_choice == 3:
            available_difficulties.append(2)
        elif difficulty_choice == 4:
            available_difficulties.append(3)
        elif difficulty_choice == 5:
            available_difficulties.append(4)
        elif difficulty_choice == 6:

            minimum_difficulty = self.options.song_difficulty_min.value
            maximum_difficulty = self.options.song_difficulty_max.value

        if difficulty_choice == 0 or difficulty_choice == 6:
            difficulty_bounds[0] = min(minimum_difficulty, maximum_difficulty)
            difficulty_bounds[1] = max(minimum_difficulty, maximum_difficulty)

            for difficulty in range(difficulty_bounds[0], difficulty_bounds[1] + 1):
                available_difficulties.append(difficulty)

        return available_difficulties

    def fill_slot_data(self):
        return {
            "victoryLocation": self.victory_song_name,
            "leekWinCount": self.get_leek_win_count(),
            "scoreGradeNeeded": self.options.grade_needed.value,
        }
