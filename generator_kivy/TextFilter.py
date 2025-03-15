import re
import os
from .TxTToJSON import process_song_file

base_game_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 28, 29, 30, 31, 32, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 79, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 101, 102, 103, 104, 201, 202, 203, 204, 205, 206, 208, 209, 210, 211, 212, 213, 214, 215, 216, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 231, 232, 233, 234, 235, 236, 238, 239, 240, 241, 242, 243, 244, 246, 247, 248, 249, 250, 251, 253, 254, 255, 257, 259, 260, 261, 262, 263, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 401, 402, 403, 404, 405, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 600, 601, 602, 603, 604, 605, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 637, 638, 639, 640, 641, 642, 710, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 736, 737, 738, 739, 740, 832]


def filter_important_lines(combined_mod_pv_db: str, output_file, mod_folder):
    song_pack_lines = {}
    current_song_pack = None
    pv_info = {}
    prev_name = None

    for line in combined_mod_pv_db.splitlines():
        match = re.match(r'^(pv_\d+)\.difficulty\.(\w+)\.length=(\d+)', line)
        if match:
            pv_id = match.group(1)
            difficulty = match.group(2)
            length = int(match.group(3))
            if pv_id not in pv_info:
                pv_info[pv_id] = {}
            pv_info[pv_id][difficulty] = length

    for line in combined_mod_pv_db.splitlines():
        if line.startswith('song_pack='):
            current_song_pack = line.strip()
            if current_song_pack not in song_pack_lines:
                song_pack_lines[current_song_pack] = []
            continue

        match = re.match(r'^(pv_\d+)', line)
        if match and '.song_name_en=' in line:
            cur_name = line
            if current_song_pack and prev_name != cur_name:
                prev_name = cur_name
                song_pack_lines[current_song_pack].append(line)
        elif match and '.level=' in line:
            pv_id_match = re.match(r'^(pv_\d+)\.difficulty\.(\w+)\.(\d+)\.level=', line)
            if pv_id_match:
                pv_id = pv_id_match.group(1)
                difficulty = pv_id_match.group(2)
                level_num = int(pv_id_match.group(3))
                if pv_id in pv_info and difficulty in pv_info[pv_id]:
                    length = pv_info[pv_id][difficulty]
                    # Special case for extreme difficulty
                    if difficulty == 'extreme':
                        if (level_num == 1 and length == 2) or (level_num == 0 and length in [1, 2]):
                            song_pack_lines[current_song_pack].append(line)
                    # General case for other difficulties
                    elif length in [1, 2]:
                        song_pack_lines[current_song_pack].append(line)

    # Sorting and writing output
    sorted_lines = []
    difficulty_order = {'easy': 0, 'normal': 1, 'hard': 2, 'extreme': 3, 'exextreme': 4}

    for song_pack, lines in song_pack_lines.items():
        sorted_lines.append(song_pack + '\n')
        lines.sort(key=lambda x: (
            int(re.match(r'pv_(\d+)', x).group(1)) if re.match(r'pv_(\d+)', x) else float('inf'),
            -1 if '.song_name_en=' in x else difficulty_order.get(x.split('.')[2] if len(x.split('.')) > 2 else '', 5)
        ))
        sorted_lines.extend(lines)

    mod_pv_db_split = sorted_lines
    #mod_pv_db_split = verify_dsc(mod_pv_db_split, mod_folder)

    flat_text = process_song_file(mod_pv_db_split)

    return flat_text


def verify_dsc(mod_pv_db: list[str], mod_folder: str):
    """
    Processes the input file, removing lines that refer to non-existent .dsc files.
    """
    valid_lines = []
    current_song_pack = None  # Variable to store the current song pack directory

    for line in mod_pv_db:
        # Check if the line defines a new song pack
        if line.startswith('song_pack='):
            # Update the current song pack based on the new line
            current_song_pack = line.split('=')[1].strip()
            # Add the song pack line to the valid lines
            valid_lines.append(line)
        elif 'difficulty' in line and '.level=' in line:
            # Extract pv number and difficulty from the line
            parts = line.split('.')
            pv_number = parts[0]  # e.g., pv_4950
            difficulty = parts[2]  # e.g., hard
            exCheck = parts[3] # e.g 0, 1

            # Determine the difficulty level for extreme
            if 'extreme' in difficulty:
                if exCheck == '0':
                    # Normal case for extreme.0
                    script_file = f"rom/script/{pv_number}_extreme.dsc"
                elif exCheck == '1':
                    # Special case for extreme.1
                    script_file = f"rom/script/{pv_number}_extreme_1.dsc"
                else:
                    # In case there's an unexpected extreme level, skip the line
                    valid_lines.append(line)
                    continue
            else:
                # Normal case for other difficulties (e.g., hard)
                script_file = f"rom/script/{pv_number}_{difficulty}.dsc"

            # Include the mod folder in the full path
            full_path = os.path.join(mod_folder, current_song_pack, script_file)

            skip_check = False
            match = re.search(r'\d+', pv_number)  # This finds the first sequence of digits
            if int(match.group()) in base_game_ids:
                skip_check = True

            # Check if the .dsc file exists, unless it's a cover song
            if os.path.exists(full_path) or skip_check is True:
                # If the file exists, keep the line
                valid_lines.append(line)
            # If the file doesn't exist, the line is not added
        else:
            # If the line doesn't match a pattern we're processing, keep it
            valid_lines.append(line)

    return valid_lines