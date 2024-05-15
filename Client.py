from typing import Optional
import ast
import asyncio
import colorama
import os
import pymem
from pathlib import Path
import json
import time
import hashlib
import re

import settings
from settings import get_settings
import tkinter as tk
from tkinter import filedialog

from CommonClient import (
    CommonContext,
    get_base_parser,
    logger,
    server_loop,
    gui_enabled,
)

from NetUtils import NetworkItem, ClientStatus

def find_mod_pv():
    host = get_settings()

    # Access the megamix_options attribute
    megamix_options = host.megamix_options

    # Access the mod_path option specifically
    mod_path = megamix_options.mod_path

    return mod_path


def load_json_file(file_name: str) -> dict:
    """Import a JSON file from the package using pkgutil."""

    import pkgutil
    # Load the contents of the file
    file_contents = pkgutil.get_data(__name__, file_name)

    # Decode the contents (assuming it's encoded as UTF-8)
    decoded_contents = file_contents.decode('utf-8')

    # Parse the JSON string into a Python dictionary
    json_data = json.loads(decoded_contents)

    return json_data


def load_external_text_file(file_path: str) -> str:
    """Load a text file from outside the package."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def save_external_text_file(file_path: str, contents: str):
    """Save modified contents to a text file outside the package."""
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(contents)


def process_json_data(json_data):
    """Process JSON data into a dictionary."""
    processed_data = {}

    # Iterate over each entry in the JSON data
    for entry in json_data:
        song_id = int(entry.get('songID'))
        song_data = {
            'songName': entry.get('songName'),
            'singers': entry.get('singers'),
            'DLC': entry.get('DLC'),
            'difficulty': entry.get('difficulty'),
            'difficultyRating': entry.get('difficultyRating')
        }

        # Check if song ID already exists in the dictionary
        if song_id in processed_data:
            # If yes, append the new song data to the existing list
            processed_data[song_id].append(song_data)
        else:
            # If no, create a new list with the song data
            processed_data[song_id] = [song_data]

    return processed_data


def erase_song_list(file_path):
    difficulties = ["easy", "normal", "hard", "extreme", "exExtreme"]
    difficulty_replacements = {
        "easy.length=1": "easy.length=0",
        "normal.length=1": "normal.length=0",
        "hard.length=1": "hard.length=0",
        "extreme.length=1": "extreme.length=0",
        "extreme.length=2": "extreme.length=0",
    }

    with open(file_path, 'r', encoding='utf-8') as file:
        file_data = file.read()

    # Perform the replacements
    for search_text, replace_text in difficulty_replacements.items():
        file_data = file_data.replace(search_text, replace_text)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(file_data)


def replace_line_with_text(file_path, search_text, new_line):
    try:
        # Read the file content with specified encoding
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        print(f"Error: Unable to decode file '{file_path}' with UTF-8 encoding.")
        return

    # Find the line containing the search text
    found = False
    for i, line in enumerate(lines):
        if search_text in line:
            lines[i] = new_line + '\n'
            found = True
            break

    # If the search text was not found, print an error and return
    if not found:
        print(f"Error: '{search_text}' not found in the file.")
        return

    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(''.join(lines))


def convert_difficulty(difficulty):
    """Convert difficulty string to lowercase."""
    difficulty_map = {
        '[EASY]': 'easy',
        '[NORMAL]': 'normal',
        '[HARD]': 'hard',
        '[EXTREME]': 'extreme',
        '[EXEXTREME]': 'exExtreme'
    }
    return difficulty_map.get(difficulty, None)


def song_unlock(file_path, song_info, json_data):
    """Unlock a song based on its name and difficulty."""
    # Use regular expression to extract song name and difficulty
    match = re.match(r'([^\[\]]+)\s*\[(\w+)\]', song_info)
    if match:
        song_name = match.group(1).strip()
        difficulty = match.group(2)
    else:
        logger.info("Invalid song info format.")
        return None

    converted_difficulty = convert_difficulty(f"[{difficulty.upper()}]")

    if converted_difficulty is None:
        print(f"Invalid difficulty: {difficulty}")
        return None
    # Search for the song name in the JSON data
    for song_id, song_data_list in json_data.items():
        # Iterate over each song data dictionary in the list
        for song_data in song_data_list:
            # Access the songName attribute
            json_name = song_data['songName']
            if json_name == song_name:
                modify_mod_pv(file_path, song_id, converted_difficulty)
                return

    # If the song is not found
    logger.info(f"Song '{song_name}' not found in the JSON data.")
    return


def modify_mod_pv(file_path, song_id, difficulty):
    search_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + difficulty + ".length=0"
    replace_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + difficulty + ".length="
    if difficulty == 'exExtreme':
        search_text = search_text.replace("exExtreme", "extreme")
        replace_text = replace_text.replace("exExtreme", "extreme")
        replace_text += "2"
    else:
        replace_text += "1"

    replace_line_with_text(file_path, search_text, replace_text)


class MegaMixContext(CommonContext):
    """MegaMix Game Context"""

    def __init__(self, server_address: Optional[str], password: Optional[str]) -> None:
        super().__init__(server_address, password)

        self.game = "Hatsune Miku Project Diva Mega Mix+"
        self.mod_pv = find_mod_pv()
        self.jsonData = process_json_data(load_json_file("songData.json"))
        self.previous_received = []

        self.items_handling = 0b001 | 0b010 | 0b100  #Receive items from other worlds, starting inv, and own items
        self.location_ids = None
        self.location_name_to_ap_id = None
        self.location_ap_id_to_name = None
        self.item_name_to_ap_id = None
        self.item_ap_id_to_name = None

        self.seed_name = None
        self.options = None

        self.obtained_items_queue = asyncio.Queue()
        self.critical_section_lock = asyncio.Lock()

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict):

        if cmd == "Connected":
            self.location_ids = set(args["missing_locations"] + args["checked_locations"])
            self.options = args["slot_data"]

            asyncio.create_task(self.send_msgs([{"cmd": "GetDataPackage", "games": ["Hatsune Miku Project Diva Mega Mix+"]}]))

            # if we dont have the seed name from the RoomInfo packet, wait until we do.
            while not self.seed_name:
                time.sleep(1)

        if cmd == "ReceivedItems":
            # If receiving an item, only append that item
            asyncio.create_task(self.receive_item())

        if cmd == "RoomInfo":
            self.seed_name = args['seed_name']

        elif cmd == "DataPackage":
            if not self.location_ids:
                # Connected package not recieved yet, wait for datapackage request after connected package
                return
            self.location_name_to_ap_id = args["data"]["games"]["Hatsune Miku Project Diva Mega Mix+"]["location_name_to_id"]
            self.location_name_to_ap_id = {
                name: loc_id for name, loc_id in
                self.location_name_to_ap_id.items() if loc_id in self.location_ids
            }
            self.location_ap_id_to_name = {v: k for k, v in self.location_name_to_ap_id.items()}
            self.item_name_to_ap_id = args["data"]["games"]["Hatsune Miku Project Diva Mega Mix+"]["item_name_to_id"]
            self.item_ap_id_to_name = {v: k for k, v in self.item_name_to_ap_id.items()}

            erase_song_list(self.mod_pv)

            # If receiving data package, resync previous items
            asyncio.create_task(self.receive_item())

        elif cmd == "LocationInfo":
            if len(args["locations"]) > 1:
                # initial request on first connect.
                self.patch_if_recieved_all_data()
            else:
                # request after an item is obtained
                asyncio.create_task(self.obtained_items_queue.put(args["locations"][0]))

    async def receive_item(self):
        async with self.critical_section_lock:

            if not self.item_ap_id_to_name:
                await self.wait_for_initial_connection_info()

            for network_item in self.items_received:
                if network_item not in self.previous_received:
                    self.previous_received.append(network_item)
                    item_name = self.item_ap_id_to_name[network_item.item]
                    song_unlock(self.mod_pv, item_name, self.jsonData)


def launch():
    """
    Launch a client instance (wrapper / args parser)
    """

    async def main(args):
        """
        Launch a client instance (threaded)
        """
        ctx = MegaMixContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        await ctx.exit_event.wait()
        await ctx.shutdown()

    parser = get_base_parser(description="Mega Mix Client")
    args, _ = parser.parse_known_args()

    colorama.init()
    asyncio.run(main(args))
    colorama.deinit()
