import re
import os
from typing import List, Dict, Any
from .SymbolFixer import fix_song_name  # Use absolute import


def sanitize_song_pack_name(song_pack: str) -> str:
    """
    Sanitizes the song pack name to make it safe for use as a Windows folder name.
    Allows characters that are valid in Windows folder names, while removing some potentially dangerous characters.

    Args:
    song_pack (str): The original song pack name.

    Returns:
    str: The sanitized song pack name.
    """
    # Define allowed characters for Windows folder names
    allowed_characters = r'[^a-zA-Z0-9 !#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~]'  # Spaces and common special characters allowed in folder names

    # Remove illegal characters
    sanitized_name = re.sub(allowed_characters, '', song_pack)

    # Normalize whitespace: replace multiple spaces with a single space
    sanitized_name = re.sub(r'\s+', ' ', sanitized_name).strip()

    # Ensure it's not empty after sanitization
    return sanitized_name if sanitized_name else "Untitled"


def process_mod_data(mod_data_content: str) -> List[Dict[str, Any]]:
    """
    Processes the mod_data content and extracts song data.

    Args:
    mod_data_content (str): The content of the mod_data section as a string.

    Returns:
    List[Dict[str, Any]]: List of dictionaries containing the extracted mod data.
    """
    # Define the difficulties mapping
    difficulties = ["[EASY]", "[NORMAL]", "[HARD]", "[EXTREME]", "[EXEXTREME]"]

    # List to store the generated JSON entries
    json_entries = []

    # Split the mod_data content into individual song entries
    song_entries = mod_data_content.split(']')  # Split by ']' to separate entries
    song_entries = [entry.strip() for entry in song_entries if entry.strip()]  # Remove empty entries

    # Process each song entry
    for song_entry in song_entries:

        if not len(song_entry.strip()) > 1:
            continue
        # Remove any leading bracket or special characters
        if song_entry.startswith('"['):
            song_entry = song_entry[2:]
        # Remove any leading bracket or special characters
        elif song_entry.startswith('['):
            song_entry = song_entry[1:]

        # Split the cleaned song entry by commas
        song_data = song_entry.split(',')

        # Extract song pack, name, ID, and difficulties
        if len(song_data) < 4:
            continue  # Skip if not enough data

        song_pack = sanitize_song_pack_name(song_data[0].strip())
        song_name = song_data[1].strip()
        song_name = fix_song_name(song_name)  # Fix song name
        song_id = song_data[2].strip()
        difficulty_ratings = song_data[3:]  # All the difficulty ratings (Easy to ExExtreme)

        # Loop through difficulties and generate JSON if a difficulty exists
        for i, rating in enumerate(difficulty_ratings):
            rating = rating.strip()
            if rating != "0":  # If the difficulty exists (not 0)
                difficulty_label = difficulties[i]

                # Create a JSON entry
                json_entry = {
                    "songPack": song_pack,
                    "songID": song_id,
                    "songName": song_name,
                    "difficulty": difficulty_label,
                    "difficultyRating": rating
                }
                json_entries.append(json_entry)

    return json_entries  # Return the list of dictionaries


def extract_mod_data_to_json(folder_path: str) -> List[Dict[str, Any]]:
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

    # List to store the generated JSON entries
    json_entries = []

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

                        # Process the mod_data content
                        json_entries.extend(process_mod_data(mod_data_content))

    return json_entries  # Return the list of dictionaries
