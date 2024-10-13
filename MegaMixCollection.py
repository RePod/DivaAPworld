# Local
from .Items import SongData
from .SymbolFixer import fix_song_name
from .JSONCreator import extract_mod_data_to_json

# Python
import random
from typing import Dict, List, Tuple
from collections import ChainMap

from .DataHandler import (
    load_zipped_json_file,
)


class MegaMixCollections:
    """Contains all the data of MegaMix, loaded from songData.json"""

    LEEK_NAME: str = "Leek"
    LEEK_CODE: int = 1

    song_items: Dict[str, SongData] = {}
    song_locations: Dict[str, int] = {}
    
    filler_item_names: Dict[str, int] = {
        "SAFE": 2,
    }
    filler_item_weights: Dict[str, int] = {
        "SAFE": 1,
    }

    def __init__(self) -> None:
        self.item_names_to_id = ChainMap({self.LEEK_NAME: self.LEEK_CODE}, self.filler_item_names, self.song_items)
        self.location_names_to_id = ChainMap(self.song_locations)

        difficulty_mapping = {
            "[EASY]": 0,
            "[NORMAL]": 2,
            "[HARD]": 4,
            "[EXTREME]": 6,
            "[EXEXTREME]": 8
        }
        json_data = load_zipped_json_file("songData.json")
        mod_data = extract_mod_data_to_json("Players")
        base_game_ids = set()

        for song in json_data:
            song_id = int(song['songID'])
            base_game_ids.add(song_id)  # Get list of all base game ids
            song_name = fix_song_name(song['songName'])  # Fix song name if needed
            song_name = song_name + " " + song['difficulty']
            singers = song['singers']
            dlc = song['DLC'].lower() == "true"
            difficulty = song['difficulty']
            difficulty_rating = float(song["difficultyRating"])
            # item_id = song_id x 10, ex: id 420 becomes 4200
            item_id = (song_id * 10) + difficulty_mapping.get(difficulty, "Difficulty not found")

            self.song_items[song_name] = SongData(item_id, song_id, song_name, singers, dlc, False, difficulty,
                                                  difficulty_rating)

        if mod_data:
            for song in mod_data:
                cover_song = False
                song_id = int(song['songID'])
                if song_id in base_game_ids:
                    cover_song = True
                song_name = fix_song_name(song['songName'])  # Fix song name if needed
                song_name = song_name + " " + song['difficulty']
                singers = []  # Avoid filtering modded songs due to non-vocaloid songs being listed as "Miku"
                difficulty = song['difficulty']
                difficulty_rating = float(song["difficultyRating"])
                # item_id = song_id x 10, ex: id 420 becomes 4200
                if not cover_song:
                    item_id = (song_id * 10) + difficulty_mapping.get(difficulty, "Difficulty not found")
                else:
                    item_id = (song_id * 10) + difficulty_mapping.get(difficulty,
                                                                      "Difficulty not found") + 1  # Give cover songs the same ids but make it odd

                self.song_items[song_name] = SongData(item_id, song_id, song_name, singers, False, True, difficulty,
                                                      difficulty_rating)

        self.item_names_to_id.update({name: data.code for name, data in self.song_items.items()})

        for song_name, song_data in self.song_items.items():
            if song_data.code % 2 != 0:  # Fix code for covers
                for i in range(2):
                    self.song_locations[f"{song_name}-{i}"] = (song_data.code + i - 1)
                continue

            for i in range(2):
                self.song_locations[f"{song_name}-{i}"] = (song_data.code + i)

    def get_songs_with_settings(self, dlc: bool, mod_ids: List[int], allowed_diff: List[int], disallowed_singer: List[str], diff_lower: float, diff_higher: float) -> Tuple[List[str], List[int]]:
        """Gets a list of all songs that match the filter settings. Difficulty thresholds are inclusive."""
        filtered_list = []
        id_list = []
        song_groups = {}

        for songKey, songData in self.song_items.items():

            singer_found = False
            song_id = songData.songID

            # If song is DLC and DLC is disabled, skip song
            if songData.DLC and not dlc:
                continue

            # Skip modded song if not intended for this player
            if songData.modded and song_id not in mod_ids:
                continue

            # Do not give base game version if modded cover available for this player
            if not songData.modded and song_id in mod_ids:
                continue

            # Skip song if disallowed singer is found
            if not songData.modded:
                for singer in disallowed_singer:
                    if singer in songData.singers:
                        singer_found = True
                if singer_found:
                    continue

            # Check if a group for this songID already exists
            if song_id in song_groups:
                # Append the current songData object to the existing group
                song_groups[song_id].append(songData)
            else:
                # Create a new group with the current songData object
                song_groups[song_id] = [songData]

        for song_id, group in song_groups.items():
            valid_difficulties = []

            # Check if song matches filter settings
            for song_item in group:
                if song_item.difficulty in ["[EASY]", "[NORMAL]", "[HARD]", "[EXTREME]", "[EXEXTREME]"]:
                    difficulty_index = ["[EASY]", "[NORMAL]", "[HARD]", "[EXTREME]", "[EXEXTREME]"].index(
                        song_item.difficulty)
                    if difficulty_index in allowed_diff and diff_lower <= song_item.difficultyRating <= diff_higher:
                        valid_difficulties.append(song_item.difficulty)

            # If there are valid difficulty selections
            if valid_difficulties:
                # Randomly choose one of the valid difficulty selections
                selected_difficulty = random.choice(valid_difficulties)

                # Find the song_item that matches the selected difficulty
                for song_item in group:
                    if song_item.difficulty == selected_difficulty:
                        # Append the song name to the selected_songs list
                        filtered_list.append(song_item.songName)
                        id_list.append(song_item.songID)
                        break  # Stop searching once a match is found

        return filtered_list, id_list
