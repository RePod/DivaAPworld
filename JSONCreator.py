import json
import re
import os
from .SymbolFixer import fix_song_name  # Use absolute import


def extract_mod_data_to_json(folder_path: str):
    """
    Extracts mod data from a YAML file and converts it to a list of dictionaries.

    Args:
    file_path (str): Path to the YAML file.

    Returns:
    List[Dict[str, Any]]: List of dictionaries containing the extracted mod data.
    """
    if not os.path.isdir(folder_path):
        raise ValueError(f"The path {folder_path} is not a valid directory.")

    # Search text for the specific game
    search_text = "game: Hatsune Miku Project Diva Mega Mix+"

    # Regex pattern to capture content inside 'mod_data' block
    mod_data_pattern = re.compile(r"mod_data:\s*#.*?\n\s*{([^}]*)}", re.DOTALL)

    # Initialize an empty list to collect all JSON outputs
    all_mod_data = []

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)

        if os.path.isfile(item_path):
            with open(item_path, 'r') as file:  # Open the file in read mode
                file_content = file.read()

                # Check if the search text is found
                if search_text in file_content:
                    # Search for mod_data block using regex
                    match = mod_data_pattern.search(file_content)

                    if match:
                        # Extract content inside mod_data block
                        mod_data_content = match.group(1).strip()

                        if mod_data_content == "":
                            continue

                        # Process the mod_data content
                        output = convert_to_json(mod_data_content)

                        # Append the resulting dictionary to the list
                        all_mod_data.append(output)

    return all_mod_data  # Return the list of json data


def convert_to_json(data_string):
    output = []

    # Remove leading and trailing whitespace and any surrounding brackets
    pack_data = data_string.strip()[1:-1].split('][')

    for pack in pack_data:
        # Remove leading and trailing whitespace from each pack
        pack = pack.strip()

        # Split by the first colon to separate the pack name and songs data
        pack_info = pack.split(':', 1)  # Split only once to avoid issues with colons in song names
        if len(pack_info) != 2:
            continue  # Skip malformed packs

        # Clean up the pack name to remove any unwanted characters
        pack_name = pack_info[0].strip().strip('["')  # Remove any leading '[' or '"'

        # Clean up songs data
        songs_data = pack_info[1].strip()[1:-1].strip()  # Strip outer brackets

        # Prepare the songs list
        songs_list = [
            {
                "songID": song_info[1],
                "songName": fix_song_name(song_info[0]),
                "difficulty": diffs,
                "difficultyRating": str(int(rating)) if rating.is_integer() else str(rating)
            }
            for song in (songs_data.split('], [') if '], [' in songs_data else [songs_data])
            for song_info in [song.strip().strip('[]').split(', ')]
            for i, (rating, diffs) in enumerate(zip(map(float, song_info[2:]), ["[EASY]", "[NORMAL]", "[HARD]", "[EXTREME]", "[EXEXTREME]"]))
            if i < len(diffs) and rating != 0
        ]

        output.append({"packName": pack_name, "songs": songs_list})

    return output
