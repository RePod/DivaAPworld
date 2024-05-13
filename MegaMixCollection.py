from .Items import SongData
from typing import Dict, List
from collections import ChainMap
import random
def load_json_file(file_name: str) -> dict:
    """Import a JSON file from the package using pkgutil."""

    import pkgutil
    import json
    # Load the contents of the file
    file_contents = pkgutil.get_data(__name__, file_name)

    # Decode the contents (assuming it's encoded as UTF-8)
    decoded_contents = file_contents.decode('utf-8')

    # Parse the JSON string into a Python dictionary
    json_data = json.loads(decoded_contents)

    return json_data


class MegaMixCollections:

    """Contains all the data of Muse Dash, loaded from MuseDashData.txt."""
    STARTING_CODE = 2900000

    LEEK_NAME: str = "Leek"
    LEEK_CODE: int = STARTING_CODE

    song_items: Dict[str, SongData] = {}
    song_locations: Dict[str, int] = {}

    def __init__(self) -> None:
        self.item_names_to_id = ChainMap({self.LEEK_NAME: self.LEEK_CODE}, self.song_items)
        self.location_names_to_id = ChainMap(self.song_locations)

        item_id_index = self.STARTING_CODE + 50

        json_data = load_json_file("songData.json")

        for song in json_data:
            song_id = int(song['songID'])
            song_name = song['songName'] + " " + song['difficulty'] + " " + song["difficultyRating"] + " ★"
            singers = song['singers']
            dlc = song['DLC'].lower() == "true"
            difficulty = song['difficulty']
            difficulty_rating = float(song["difficultyRating"])

            self.song_items[song_name] = SongData(item_id_index, song_id, song_name, singers, dlc, difficulty, difficulty_rating)
            item_id_index += 1

        self.item_names_to_id.update({name: data.code for name, data in self.song_items.items()})

        location_id_index = self.STARTING_CODE

        for name in self.song_items.keys():
            self.song_locations[f"{name}-0"] = location_id_index
            self.song_locations[f"{name}-1"] = location_id_index + 1
            location_id_index += 2

    def get_songs_with_settings(self, dlc: bool, allowed_diff: List[int],
                                diff_lower: int, diff_higher: int) -> List[str]:
        """Gets a list of all songs that match the filter settings. Difficulty thresholds are inclusive."""
        filtered_list = []

        song_groups = {}

        for songKey, songData in self.song_items.items():
            # If song is DLC and DLC is disabled, skip song
            if songData.DLC and not dlc:
                continue

            song_id = songData.songID

            # Check if a group for this songID already exists
            if song_id in song_groups:
                # Append the current songData object to the existing group
                song_groups[song_id].append(songData)
            else:
                # Create a new group with the current songData object
                song_groups[song_id] = [songData]

        for song_id, group in song_groups.items():
            valid_difficulties = []

            for song_item in group:

                if 0 in allowed_diff and song_item.difficulty == "[EASY]" and diff_lower <= song_item.difficultyRating <= diff_higher:
                    valid_difficulties.append("[EASY]")

                if 1 in allowed_diff and song_item.difficulty == "[NORMAL]" and diff_lower <= song_item.difficultyRating <= diff_higher:
                    valid_difficulties.append("[NORMAL]")

                if 2 in allowed_diff and song_item.difficulty == "[HARD]" and diff_lower <= song_item.difficultyRating <= diff_higher:
                    valid_difficulties.append("[HARD]")

                if 3 in allowed_diff and song_item.difficulty == "[EXTREME]" and diff_lower <= song_item.difficultyRating <= diff_higher:
                    valid_difficulties.append("[EXTREME]")

                if 4 in allowed_diff and song_item.difficulty == "[EXEXTREME]" and diff_lower <= song_item.difficultyRating <= diff_higher:
                    valid_difficulties.append("[EXEXTREME]")

            # If there are valid difficulty selections
            if valid_difficulties:
                # Randomly choose one of the valid difficulty selections
                selected_difficulty = random.choice(valid_difficulties)

                # Find the song_item that matches the selected difficulty
                for song_item in group:
                    if song_item.difficulty == selected_difficulty:
                        # Append the song name to the selected_songs list
                        filtered_list.append(song_item.songName)
                        break  # Stop searching once a match is found


        return filtered_list
