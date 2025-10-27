from typing import Optional
import asyncio
import colorama
import os
import json
import time
from pathlib import Path
from .DataHandler import (
    game_paths,
    load_json_file,
    song_unlock,
)
from CommonClient import (
    ClientCommandProcessor,
    get_base_parser,
    logger,
    server_loop,
    gui_enabled,
)
tracker_loaded = False
try:
    from worlds.tracker.TrackerClient import TrackerGameContext as SuperContext
    tracker_loaded = True
except ModuleNotFoundError:
    from CommonClient import CommonContext as SuperContext
from NetUtils import NetworkItem, ClientStatus, Permission


class DivaClientCommandProcessor(ClientCommandProcessor):
    def _cmd_uncleared(self):
        """List received songs with available checks and the goal song if unlocked"""
        asyncio.create_task(self.ctx.get_uncleared())

    def _cmd_leek(self):
        """Display number of Leeks obtained, how many needed, and the goal song"""
        asyncio.create_task(self.ctx.get_leek_info())

    def _cmd_auto_remove(self):
        """Toggle to automatically remove already cleared songs after a song clear"""
        asyncio.create_task(self.ctx.toggle_remove_songs())

    def _cmd_remove_cleared(self):
        """Remove cleared songs from in-game list"""
        asyncio.create_task(self.ctx.remove_songs())

    def _cmd_freeplay(self):
        """Toggle that restores or removes songs that aren't part of this AP run"""
        asyncio.create_task(self.ctx.freeplay_toggle())

    def _cmd_restore_songs(self):
        """Restore songs to their pre-Archipelago state, automatic on release or Client close
        Use as a failsafe for songs not appearing and play on the honor system"""
        logger.info("Restoring..")
        asyncio.create_task(self.ctx.restore_songs())
        logger.info("Base Game + Mod Packs Restored")

    def _cmd_deathlink(self, amnesty = ""):
        """Toggle Death Link on and off or provide a number >= 0 to change Amnesty.
        Lethality can be adjusted in the mod's config.toml"""
        asyncio.create_task(self.ctx.toggle_deathlink(amnesty))


class MegaMixContext(SuperContext):
    """MegaMix Game Context"""

    command_processor = DivaClientCommandProcessor
    tags = {"AP"}

    def __init__(self, server_address: Optional[str], password: Optional[str]) -> None:
        super().__init__(server_address, password)

        self.game = "Hatsune Miku Project Diva Mega Mix+"
        self.path = game_paths().get("mods")
        self.mod_name = "ArchipelagoMod"
        self.songResultsLocation = f"{self.path}/{self.mod_name}/results.json"
        self.deathLinkInLocation = f"{self.path}/{self.mod_name}/death_link_in"
        self.deathLinkOutLocation = f"{self.path}/{self.mod_name}/death_link_out"
        self.songListLocation = f"{self.path}/{self.mod_name}/song_list.txt"
        self.trapSuddenLocation = f"{self.path}/{self.mod_name}/sudden"
        self.trapHiddenLocation = f"{self.path}/{self.mod_name}/hidden"
        self.trapIconLocation = f"{self.path}/{self.mod_name}/icontrap"
        self.modData = None
        self.modded = False
        self.freeplay = False
        self.previous_received = []
        self.sent_unlock_message = False

        self.items_handling = 0b001 | 0b010 | 0b100  #Receive items from other worlds, starting inv, and own items
        self.location_ids = None
        self.location_name_to_ap_id = None
        self.location_ap_id_to_name = None
        self.item_name_to_ap_id = None
        self.item_ap_id_to_name = None
        self.checks_per_song = 2

        self.seed_name = None
        self.options = None
        self.remap = None

        self.goal_song = None
        self.goal_id = None
        self.autoRemove = False
        self.leeks_needed = 0
        self.leeks_obtained = 0
        self.leek_label = None
        self.grade_needed = None
        self.death_link = False
        self.death_link_amnesty = 0
        self.death_link_amnesty_count = 0

        self.watch_task = None
        if not self.watch_task:
            self.watch_task = asyncio.create_task(self.watch_json_file(self.songResultsLocation))

        self.watch_death_link_task = None

        self.obtained_items_queue = asyncio.Queue()
        self.critical_section_lock = asyncio.Lock()

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict):
        super().on_package(cmd, args) # Universal Tracker

        if cmd == "Connected":

            self.sent_unlock_message = False
            self.leeks_obtained = 0
            self.location_ids = set(args["missing_locations"] + args["checked_locations"])
            self.options = args["slot_data"]
            self.remap = self.options.get("modRemap", {})
            self.goal_song = self.options["victoryLocation"]
            self.goal_id = self.options["victoryID"]
            self.autoRemove = self.options["autoRemove"]
            self.leeks_needed = self.options["leekWinCount"]
            self.grade_needed = int(self.options["scoreGradeNeeded"])
            self.modData = self.options["modData"]
            if self.modData:
                self.modded = True
            asyncio.create_task(self.restore_songs()) # TODO: Remove, see function.
            asyncio.create_task(self.send_msgs([{"cmd": "GetDataPackage", "games": ["Hatsune Miku Project Diva Mega Mix+"]}]))

            self.death_link = self.options.get("deathLink", False)
            self.death_link_amnesty = self.options.get("deathLink_Amnesty", 0)
            self.death_link_amnesty_count = 0
            asyncio.create_task(self.update_death_link(self.death_link))

            if self.death_link and not self.watch_death_link_task:
                self.watch_death_link_task = asyncio.create_task(self.watch_death_link_out(self.deathLinkOutLocation))

            self.check_goal()

            # if we don't have the seed name from the RoomInfo packet, wait until we do.
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
            self.leeks_obtained = 0
            self.previous_received = []

            self.location_name_to_ap_id = args["data"]["games"]["Hatsune Miku Project Diva Mega Mix+"]["location_name_to_id"]
            self.location_name_to_ap_id = {
                name: loc_id for name, loc_id in
                self.location_name_to_ap_id.items() if loc_id in self.location_ids
            }
            self.location_ap_id_to_name = {v: k for k, v in self.location_name_to_ap_id.items()}
            self.item_name_to_ap_id = args["data"]["games"]["Hatsune Miku Project Diva Mega Mix+"]["item_name_to_id"]
            self.item_ap_id_to_name = {v: k for k, v in self.item_name_to_ap_id.items()}

            # If receiving data package, resync previous items
            asyncio.create_task(self.receive_item())

    async def receive_item(self):
        async with self.critical_section_lock:
            for network_item in self.items_received:
                if network_item not in self.previous_received:
                    self.previous_received.append(network_item)
                    if network_item.item == 1:
                        self.leeks_obtained += 1
                        self.check_goal()
                    elif network_item.item == 2:
                        # Maybe move static items out of MegaMixCollection instead of hard coding?
                        pass
                    elif network_item.item == 4:
                        if not os.path.isfile(self.trapHiddenLocation):
                            Path(self.trapHiddenLocation).touch()
                    elif network_item.item == 5:
                        if not os.path.isfile(self.trapSuddenLocation):
                            Path(self.trapSuddenLocation).touch()
                    elif network_item.item == 9:
                        if not os.path.isfile(self.trapIconLocation):
                            Path(self.trapIconLocation).touch()
            self.update_song_list()

    def update_song_list(self, remove = False):
        base_ids = {i.item // 10 for i in self.previous_received}
        song_list = {i for i in self.server_locations if i // 10 in base_ids}
        if self.leeks_obtained >= self.leeks_needed:
            song_list.add(self.goal_id)

        if self.freeplay:
            song_list = {location_id for location_id in self.location_ids if location_id not in song_list}
            if self.leeks_obtained < self.leeks_needed:
                song_list.add(self.goal_id)
            song_list.add(0)
        elif remove or self.autoRemove:
            song_list -= self.checked_locations

        song_list = {s // 10 for s in song_list}
        # TODO: Cache song_list, if same skip.
        song_unlock(self.songListLocation, song_list)

    def check_goal(self):
        if not self.leek_label:
            from kivymd.uix.label import MDLabel
            self.leek_label = MDLabel(halign="center", size_hint=(None, 1), width=100)
            self.ui.textinput.parent.add_widget(self.leek_label)
        self.leek_label.text = f"{self.leeks_obtained}/{self.leeks_needed} Leeks"

        if self.leeks_obtained >= self.leeks_needed:
            if not self.sent_unlock_message:
                self.sent_unlock_message = True
                logger.info(f"Got enough leeks! Unlocking goal song: {self.goal_song}")

            self.update_song_list()


    async def watch_json_file(self, file_name: str):
        """Watch a JSON file for changes and call the callback function."""
        file_path = os.path.join(os.path.dirname(__file__), file_name)
        last_modified = os.path.getmtime(file_path) if os.path.isfile(file_path) else 0.0
        try:
            while True:
                await asyncio.sleep(1)  # Wait for a short duration
                if os.path.isfile(file_path):
                    modified = os.path.getmtime(file_path)
                    if modified > last_modified:
                        last_modified = modified
                        try:
                            json_data = load_json_file(file_name)
                            await self.receive_location_check(json_data)
                        except (FileNotFoundError, json.JSONDecodeError) as e:
                            print(f"Error loading JSON file: {e}")
        except asyncio.CancelledError:
            print(f"Watch task for {file_name} was canceled.")


    async def watch_death_link_out(self, file_name: str):
        file_path = os.path.join(os.path.dirname(__file__), file_name)
        last_modified = os.path.getmtime(file_path) if os.path.isfile(file_path) else 0.0

        logger.debug(f"Watching {self.deathLinkOutLocation} ({last_modified})")

        while True:
            await asyncio.sleep(0.25)
            if os.path.isfile(file_path):
                modified = os.path.getmtime(file_path)
                if modified > last_modified:
                    last_modified = modified
                    await self.send_death()


    async def send_death(self, death_text: str = ""):
        if not self.death_link:
            return

        if not death_text:
            death_text = f"The Disappearance of {self.player_names[self.slot]}"

        self.death_link_amnesty_count += 1
        if self.death_link_amnesty_count > self.death_link_amnesty:
            self.death_link_amnesty_count = 0
            await super().send_death(death_text)


    def on_deathlink(self, data: dict[str, any]):
        super().on_deathlink(data)
        Path(self.deathLinkInLocation).touch()


    async def receive_location_check(self, song_data):
        logger.debug(song_data)

        if song_data.get('pvId') == 144: # Always available AP mod song
            logger.info("No checks to send at BK but seeing this means your Client is OK!")
            return

        # Check for remaps
        song_id = song_data.get('pvId')
        location_id = self.remap.get(str(song_id), song_id * 10)
        location_checks = set(range(location_id, location_id + self.checks_per_song))

        if not location_id == self.goal_id:
            if location_checks.issubset(set(self.checked_locations)):
                logger.info("No checks to send: Song checks previously sent or collected")
                return

            if not location_id in self.location_ids:
                logger.info("No checks to send: Song not in song pool")
                return

        if int(song_data.get('scoreGrade')) >= self.grade_needed:
            if location_id == self.goal_id:
                asyncio.create_task(self.end_goal())
                return

            logger.info("Cleared song with appropriate grade!")

            asyncio.create_task(self.send_checks(location_checks))
        else:
            logger.info(f"Song {song_data.get('pvName')} was not beaten with a high enough grade")

            if not song_data.get('deathLinked', False):
                await self.send_death()

    async def end_goal(self):
        message = [{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]

        if Permission.auto & Permission.from_text(self.permissions.get("release")) == Permission.auto:
            await self.restore_songs()
        elif self.autoRemove and not self.freeplay:
            await self.remove_songs()

        await self.send_msgs(message)

    async def send_checks(self, locations: set):
        await self.check_locations(locations)
        if self.autoRemove and not self.freeplay:
            await self.remove_songs()

    async def get_uncleared(self):
        prev_items = {i for item in self.previous_received for i in (item.item, item.item + 1)}
        missing_locations = {loc // 10 for loc in self.missing_locations if loc in prev_items}

        for location in sorted(missing_locations):
            location = self.remap.get(str(location), location * 10)
            logger.info(f"{self.item_ap_id_to_name[location]} is uncleared")

        if self.leeks_obtained >= self.leeks_needed:
            logger.info(f"Goal song: {self.goal_song} is unlocked.")

        if not missing_locations:
            logger.info("All available songs cleared")

    async def get_leek_info(self):
        logger.info(f"You have {self.leeks_obtained} Leeks")
        logger.info(f"You need {self.leeks_needed} Leeks total to unlock the goal song {self.goal_song}")

    async def toggle_remove_songs(self):
        self.autoRemove = not self.autoRemove

        if self.autoRemove:
            logger.info("Auto Remove Set to On")
            await self.remove_songs()
        else:
            logger.info("Auto Remove Set to Off")

    async def remove_songs(self):
        self.update_song_list(remove=True)
        logger.info("Removed songs!")

    async def freeplay_toggle(self):
        self.freeplay = not self.freeplay
        self.update_song_list()

        if self.freeplay:
            logger.info("Restored non-AP songs!")
        else:
            logger.info("Removed non-AP songs!")

    async def restore_songs(self):
        from .DataHandler import restore_originals, song_unlock
        mod_pv_dbs = [f"{self.path}/{pack}/rom/mod_pv_db.txt" for pack in os.listdir(".")]
        restore_originals(mod_pv_dbs)  # See function docstring

        song_unlock(self.songListLocation, {0})

    async def shutdown(self):
        await self.restore_songs()
        await super().shutdown()

    async def toggle_deathlink(self, amnesty: str = ""):
        if amnesty:
            if int(amnesty) > -1:
                self.death_link_amnesty = int(amnesty)
                logger.info(f"Death Link Amnesty is now {self.death_link_amnesty}")
            else:
                logger.info("Death Link Amnesty must be 0 or greater.")
        else:
            self.death_link = not self.death_link
            logger.info(f"Death Link is now {['off','on'][self.death_link]}")
            await self.update_death_link(self.death_link)

        # This is for when DL is disabled in the YAML and opted into with the Client.
        # TODO: The copy of this in on_package should be reworked.
        if self.death_link and not self.watch_death_link_task:
            self.watch_death_link_task = asyncio.create_task(self.watch_death_link_out(self.deathLinkOutLocation))

    def make_gui(self):
        ui = super().make_gui()
        ui.base_title = "Mega Mix Client"
        return ui

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
        if tracker_loaded:
            ctx.run_generator()
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
