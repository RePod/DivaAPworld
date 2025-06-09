from kvui import ThemedApp, ScrollBox, MDTextField, MDBoxLayout, MDLabel
from kivy.metrics import dp
from kivy.properties import ObjectProperty
from kivy.core.clipboard import Clipboard
from kivy.uix.checkbox import CheckBox
from kivymd.uix.behaviors import HoverBehavior
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
from kivymd.uix.dialog import MDDialog, MDDialogHeadlineText, MDDialogContentContainer, MDDialogIcon, MDDialogSupportingText

from kivy.lang.builder import Builder
import pkgutil

import re
import os
import Utils
import settings
from .TextFilter import filter_important_lines
from .TxTToJSON import ConflictException
from .. import MegaMixWorld
from ..DataHandler import restore_originals

class AssociatedMDLabel(MDLabel):
    def __init__(self, text, associate):
        MDLabel.__init__(self)
        self.text = text
        self.associate = associate
        self.valign = 'center'

    def on_touch_down(self, touch):
        MDLabel.on_touch_down(self, touch)
        if self.collide_point(touch.pos[0], touch.pos[1]):
            self.associate.active = not self.associate.active

class MDBoxLayoutHover(MDBoxLayout, HoverBehavior):
    pass

class DivaJSONGenerator(ThemedApp):
    container: MDBoxLayout = ObjectProperty(None)
    pack_list_scroll: ScrollBox = ObjectProperty(None)
    filter_input: MDTextField = ObjectProperty(None)

    mods_folder = settings.get_settings()["megamix_options"]["mod_path"]
    self_mod_name = "ArchipelagoMod" # Hardcoded. Fetch from Client or something.
    checkboxes = []
    labels = []

    def create_pack_list(self):
        for folder_name in os.listdir(self.mods_folder):
            if folder_name == self.self_mod_name:
                continue

            if os.path.isfile(os.path.join(self.mods_folder, folder_name, "rom/mod_pv_db.txt")):
                self.pack_list_scroll.layout.add_widget(self.create_pack_line(folder_name))

    def create_pack_line(self, name: str):
        box = MDBoxLayoutHover(size_hint_y=None, height=40)

        checkbox = CheckBox(size_hint=(None, None), width=50, height=40)
        self.checkboxes.append(checkbox)

        label = AssociatedMDLabel(name, checkbox)
        self.labels.append(name)

        box.add_widget(checkbox)
        box.add_widget(label)

        return box

    def toggle_checkbox(self, active: bool = True, search: str = "", import_dml: bool = False):
        dml_config = ""
        if import_dml:
            dml_path = os.path.join(os.path.dirname(self.mods_folder), "config.toml")
            try:
                with open(dml_path, "r", encoding='utf-8', errors='ignore') as DMLConfig:
                    dml_config = DMLConfig.read()
                self.show_snackbar("Imported from DML")
            except Exception as e:
                MDDialog(
                    MDDialogIcon(icon="alert"),
                    MDDialogHeadlineText(text="Could not locate or read DML config"),
                    MDDialogContentContainer(MDDialogSupportingText(text=f"{e}")),
                ).open()

        # Look away
        for cb in [box.children[1] for box in self.pack_list_scroll.layout.children]:
            label = cb.parent.children[0].text
            if import_dml and label not in dml_config:
                continue
            elif search:
                if "/" == search[0] == search[-1]:
                    if not re.search(search[1:-1], label):
                        continue
                elif search.lower() not in label.lower():
                    continue
            cb.active = active

    def toggle_checkbox_from_input(self, active: bool = False):
        if self.filter_input.text:
            self.toggle_checkbox(active=active, search=self.filter_input.text)

    def filter_pack_list(self, instance: MDTextField, search: str):
        self.pack_list_scroll.layout.clear_widgets()

        # Almost definitely a better way to do this.
        for i in self.checkboxes:
            label = i.parent.children[0].text
            if search:
                if "/" == search[0] == search[-1]:
                    if not re.search(search[1:-1], label):
                        continue
                elif search.lower() not in label.lower():
                    continue
            self.pack_list_scroll.layout.add_widget(i.parent)

    @staticmethod
    def process_mods(folders: list[str]):
        processed_text = ""
        trim_pv_db = re.compile(r'^pv_\d+\.(song_name|difficulty\.)')

        for folder_path in folders:
            folder_name = os.path.basename(folder_path)
            processed_text += f"\nsong_pack={folder_name}\n"
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file == "mod_pv_db.txt":
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r", encoding='utf-8', errors='ignore') as input_file:
                                processed_text += "\n".join([line for line in input_file.read().splitlines() if re.search(trim_pv_db, line)])
                        except Exception as e:
                            MDDialog(
                                MDDialogIcon(icon="alert"),
                                MDDialogHeadlineText(text=f"Pack: {folder_name}"),
                                MDDialogContentContainer(
                                    MDDialogSupportingText(text=f"Failed to read {file_path}: {e}")),
                            ).open()

        return processed_text

    def process_to_clipboard(self):
        checked_packs = []

        for i, cb in enumerate(self.checkboxes):
            if cb.active is True:
                checked_packs.append(str(os.path.join(self.mods_folder, self.labels[i])))

        combined_mod_pv_db = self.process_mods(checked_packs)
        try:
            mod_pv_db_json = filter_important_lines(combined_mod_pv_db, self.mods_folder)
        except ConflictException as e:
            MDDialog(
                MDDialogIcon(icon="alert"),
                MDDialogHeadlineText(text=f"Conflicting IDs prevent generating"),
                MDDialogSupportingText(text=str(e))
            ).open()
            return

        if mod_pv_db_json:
            json_length = round(len(mod_pv_db_json) / 1024, 2)
            Clipboard.copy(mod_pv_db_json)

            MDDialog(
                MDDialogHeadlineText(text="Copied mod string to clipboard"),
                MDDialogSupportingText(text=f"{len(checked_packs)} pack(s) ({json_length} KiB)"),
            ).open()
        else:
            self.show_snackbar("No song packs selected")

    def open_mods_folder(self):
        Utils.open_file(self.mods_folder)

    @staticmethod
    def show_snackbar(message: str = "ooeeoo"):
        MDSnackbar(MDSnackbarText(text=message), y=dp(24), pos_hint={"center_x": 0.5}, size_hint_x=0.5).open()

    def process_restore_originals(self):
        mod_pv_dbs = [f"{self.mods_folder}/{pack}/rom/mod_pv_db.txt" for pack in self.labels + [self.self_mod_name]]
        try:
            restore_originals(mod_pv_dbs)
            self.show_snackbar("Song packs restored")
        except Exception as e:
            self.show_snackbar(str(e))

    def build(self):
        self.title = "Hatsune Miku Project Diva Mega Mix+ JSON Generator"

        data = pkgutil.get_data(MegaMixWorld.__module__, "generator_megamix/generator.kv").decode()
        self.container = Builder.load_string(data)
        self.pack_list_scroll = self.container.ids.pack_list_scroll
        self.filter_input = self.container.ids.filter_input
        self.create_pack_list()

        self.set_colors()
        self.container.md_bg_color = self.theme_cls.backgroundColor

        return self.container


def launch():
    DivaJSONGenerator().run()
