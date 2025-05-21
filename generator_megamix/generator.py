from kvui import (ThemedApp, MDButton, MDButtonText, MDGridLayout, ScrollBox, MDTextField, MDBoxLayout, MDLabel)
from kivy.properties import ObjectProperty
from kivy.core.clipboard import Clipboard
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput

from kivy.lang.builder import Builder
import pkgutil

import re
import os
import Utils
import settings
from .TextFilter import filter_important_lines
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

class DivaJSONGenerator(ThemedApp):
    container: MDBoxLayout = ObjectProperty(None)
    packlist_scroll: ScrollBox = ObjectProperty(None)
    filter_input: MDTextField = ObjectProperty(None)

    mods_folder = ""
    checkboxes = []
    labels = []

    def create_pack_list(self):
        for folder_name in os.listdir(self.mods_folder):
            if folder_name == "ArchipelagoMod":
                continue

            folder_path = os.path.join(self.mods_folder, folder_name)

            if os.path.isdir(folder_path):
                for root, dirs, files in os.walk(folder_path):
                    if 'mod_pv_db.txt' in files:
                        self.packlist_scroll.layout.add_widget(self.create_pack_line(folder_name))
                        break


    def create_pack_line(self, name: str):
        box = MDBoxLayout(size_hint_y=None, height=40)

        checkbox = CheckBox(size_hint=(None, None), width=50, height=40)
        self.checkboxes.append(checkbox)

        label = AssociatedMDLabel(name, checkbox)
        label.bind(size=label.setter('text_size'))
        self.labels.append(name)

        box.add_widget(checkbox)
        box.add_widget(label)

        return box


    def toggle_checkbox(self, active: bool = True, search: str = "", import_dml: bool = False):
        dml_config = ""
        if import_dml:
            dml_path = os.path.split(self.mods_folder)[0] + "/config.toml"
            try:
                with open(dml_path, "r", encoding='utf-8',
                          errors='ignore') as DMLConfig:
                    dml_config = DMLConfig.read()
            except Exception as e:
                popup = Popup(title='Could not obtain DML config',
                              content=TextInput(text=f"{e}"),
                              size_hint=(None, None), size=(400, 200))
                popup.open()

        for i in self.checkboxes:
            label = i.parent.children[0].text
            if import_dml and label not in dml_config:
                continue
            elif search:
                if "/" == search[0] == search[-1]:
                    if not re.search(search[1:-1], label):
                        continue
                elif search not in label:
                    continue
            i.active = active


    def toggle_checkbox_from_input(self, active: bool = False):
        self.toggle_checkbox(active, self.filter_input.text)


    @staticmethod
    def process_mods(folders):
        processed_text = ""
        trim_pv_db = re.compile(r'^pv_\d+\.(song_name|difficulty\.)')

        for folder_path in folders:
            folder_name = os.path.basename(folder_path)
            processed_text += f"\nsong_pack={folder_name}\n"
            for master, dirs, files in os.walk(folder_path):
                for file in files:
                    if file == "mod_pv_db.txt":
                        file_path = os.path.join(master, file)
                        try:
                            with open(file_path, "r", encoding='utf-8', errors='ignore') as input_file:
                                processed_text += "\n".join([line for line in input_file.read().splitlines() if re.search(trim_pv_db, line)])
                        except Exception as e:
                            popup = Popup(title='Error',
                                          content=MDLabel(text=f"Failed to read {file_path}: {e}"),
                                          size_hint=(None, None), size=(400, 200))
                            popup.open()

        return processed_text


    def process_to_clipboard(self):
        checked_packs = []

        for i, cb in enumerate(self.checkboxes):
            if cb.active is True:
                checked_packs.append(
                    str(os.path.join(self.mods_folder, self.packlist_scroll.layout.children[-(i + 1)].children[0].text)))

        combined_mod_pv_db = self.process_mods(checked_packs)
        mod_pv_db_json = filter_important_lines(combined_mod_pv_db, self.mods_folder)

        Clipboard.copy(mod_pv_db_json)

        box = MDBoxLayout(orientation="vertical")
        box.add_widget(MDLabel(text=f"Generated {len(checked_packs)} pack(s) ({round(len(mod_pv_db_json) / 1024, 2)} KiB)"))

        popup = Popup(title='Copied to clipboard',
                      content=box,
                      size_hint=(None, None), size=(400, 200))
        popup.open()


    def open_mods_folder(self):
        Utils.open_file(self.mods_folder)


    def process_restore_originals(self):
            mod_pv_dbs = [f"{self.mods_folder}/{pack}/rom/mod_pv_db.txt" for pack in self.labels]
            restore_originals(mod_pv_dbs)


    def build(self):
        self.title = "Hatsune Miku Project Diva Mega Mix+ JSON Generator"
        self.mods_folder = settings.get_settings()["megamix_options"]["mod_path"]

        data = pkgutil.get_data(MegaMixWorld.__module__, "generator_megamix/generator.kv").decode()
        self.container = Builder.load_string(data)
        self.packlist_scroll = self.container.ids.packlist_scroll
        self.filter_input = self.container.ids.filter_input
        self.create_pack_list()

        self.set_colors()
        self.container.md_bg_color = self.theme_cls.backgroundColor

        return self.container


def launch():
    DivaJSONGenerator().run()
