import re
import json
from ..SymbolFixer import fix_song_name


def extract_song_info(mod_pv_db: list[str]):
    song_packs = {}
    current_song = None
    current_name = ""
    current_pack = None
    line_counts = {}
    conflicts = []

    for line in mod_pv_db:
        if 'song_pack=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                current_pack = parts[1].strip()
                if current_pack not in song_packs:
                    song_packs[current_pack] = []

        match = re.match(r'^pv_(\d+)', line)
        if match:
            song_number = int(match.group(1))
            current_song = {
                'songID': str(song_number),
                'songName': current_name,
                'difficulties': []
            }
            if current_pack:
                song_packs[current_pack].append(current_song)

            pv_id = match.group(0)
            if pv_id not in line_counts:
                line_counts[pv_id] = 0
            line_counts[pv_id] += 1

            if line_counts[pv_id] > 6:
                conflicts.append(pv_id)

        if 'song_name_en=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                song_name = parts[1].strip()
                cleaned_song_name = fix_song_name(song_name)
                current_song['songName'] = cleaned_song_name
                current_name = cleaned_song_name

        if line.startswith('pv_') and '.difficulty.' in line and '.level=' in line:
            parts = line.split('.')
            difficulty = parts[-3]
            ex_check = parts[-2]
            if ex_check == "1":
                difficulty = "exExtreme"
            rating_str = parts[-1]
            match = re.match(r'level=PV_LV_(\d+)_(\d+)', rating_str)
            if match:
                main_number = int(match.group(1))
                decimal_part = int(match.group(2)) / 10 if match.group(2) else 0.0
                rating = main_number + decimal_part
                if rating.is_integer():
                    rating = int(rating)
                current_song['difficulties'].append({
                    'difficulty': '[' + difficulty.upper() + ']',
                    'difficultyRating': str(rating)
                })

    flattened_packs = []

    for pack_name, pack_songs in song_packs.items():
        flattened_pack = {'packName': pack_name, 'songs': []}
        for song in pack_songs:
            for difficulty_info in song['difficulties']:
                flattened_song = {
                    'songID': song['songID'],
                    'songName': song['songName'],
                    'difficulty': difficulty_info['difficulty'],
                    'difficultyRating': difficulty_info['difficultyRating']
                }
                flattened_pack['songs'].append(flattened_song)
        flattened_packs.append(flattened_pack)

    return flattened_packs, conflicts


def process_song_file(mod_pv_db: list[str]):

    songs_info, conflicts = extract_song_info(mod_pv_db)

    #if conflicts:
    #    messagebox.showerror("Conflict Detected", f"Conflicts detected for the following pv_ IDs: {conflicts}")
    #    return

    if songs_info:
        compressed_data = compress_song_data(songs_info)
        return compressed_data


def compress_song_data(json_data):
    # Create a dictionary to map difficulties to list indices
    difficulty_map = {
        "[EASY]": 0,
        "[NORMAL]": 1,
        "[HARD]": 2,
        "[EXTREME]": 3,
        "[EXEXTREME]": 4
    }

    # Initialize a dictionary to hold the grouped song data
    grouped_songs = {}

    # Iterate through each pack in the JSON data
    for pack in json_data:
        pack_name = pack["packName"].replace("'","''")

        # Iterate through each song in the song list
        for song in pack["songs"]:
            song_id = song["songID"]
            difficulty = song["difficulty"]
            rating = int(song["difficultyRating"]) if float(song["difficultyRating"]).is_integer() else float(song["difficultyRating"])

            # If this is the first time we're seeing this song, initialize its entry
            if song_id not in grouped_songs:
                # Initialize with packName, songName, songID, and 5 zeros for difficulties
                grouped_songs[song_id] = [pack_name, song["songName"], song_id] + [0] * 5

            # Place the rating in the correct position based on the difficulty
            grouped_songs[song_id][difficulty_map[difficulty] + 3] = rating

    # Initialize a dictionary to group songs by packName for output
    grouped_packs = {}

    # Group the songs by their pack names
    for song_data in grouped_songs.values():
        pack_name = song_data[0]
        if pack_name not in grouped_packs:
            grouped_packs[pack_name] = []

        # Append the song data without duplicating the pack name
        grouped_packs[pack_name].append(song_data[1:])  # Skip the pack name in this list

    # Initialize an empty dictionary to store the final output
    song_packs = {}

    for pack_name, songs in grouped_packs.items():
        # For each pack, use a list to represent the song data
        song_list = []

        for song in songs:
            # Initialize a list for each song, starting with name and id
            song_data = [song[0], int(song[1]), optimize_diffs(song[2:7])]

            # Add the song data to the song list
            song_list.append(song_data)

        # Assign the compressed song list to the pack name in the main dictionary
        song_packs[pack_name] = song_list

    # Convert the dictionary to a compressed JSON string (no indent, no extra spaces)
    output_json = json.dumps(song_packs, separators=(',', ':'))
    #output_json = output_json.replace("'", "''") # Escape ' for YAML entry
    #output_json = output_json.replace('"', "'")

    return f"'{output_json}'"  # Surround the entire output with quotes and strip spaces

def optimize_diffs(diffs):
    val = 0

    for diff in diffs:
        if not isinstance(diff, int):
            diff = int(diff) | 1 << 4

        val = (val << 5) | diff

    return val
