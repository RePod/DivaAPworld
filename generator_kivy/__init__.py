import re

from kvui import (App, ScrollBox, Button, MainLayout, ContainerLayout, dp, Widget, BoxLayout, TooltipLabel, ToolTip,
                  Label)
from kivy.core.clipboard import Clipboard
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput
import Utils

import os
import settings
from .TextFilter import filter_important_lines

class AssociatedLabel(Label):
    def __init__(self, text, associate):
        Label.__init__(self)
        self.text = text
        self.associate = associate
        self.valign = 'center'

    def on_touch_down(self, touch):
        Label.on_touch_down(self, touch)
        if self.collide_point(touch.pos[0], touch.pos[1]):
            self.associate.active = not self.associate.active

class DivaJSONGenerator(App):
    container: ContainerLayout
    main_layout: MainLayout
    scrollbox: ScrollBox
    scrollbox_container: MainLayout
    main_panel: MainLayout
    quick_match_input: TextInput

    mods_folder = ""
    checkboxes = []


    def create_pack_list(self):
        for folder_name in os.listdir(self.mods_folder):
            if folder_name == "ArchipelagoMod":
                continue

            folder_path = os.path.join(self.mods_folder, folder_name)

            if os.path.isdir(folder_path):
                for root, dirs, files in os.walk(folder_path):
                    if 'mod_pv_db.txt' in files:
                        self.scrollbox.layout.add_widget(self.create_pack_line(folder_name))
                        break


    def create_pack_line(self, name: str):
        box = BoxLayout(size_hint_y=None, height=40)

        checkbox = CheckBox(size_hint=(None, None), width=50, height=40)
        self.checkboxes.append(checkbox)

        label = AssociatedLabel(name, checkbox)
        label.bind(size=label.setter('text_size'))

        box.add_widget(checkbox)
        box.add_widget(label)

        return box


    def create_pack_buttons(self):
        def toggle_checkbox(active: bool = True, search: str = ""):
            for i in self.checkboxes:
                if search:
                    label = i.parent.children[0].text
                    if "/" == search[0] == search[-1]:
                        if not re.search(search[1:-1], label):
                            continue
                    elif search not in label:
                        continue
                i.active = active

        quick_container = BoxLayout(orientation='vertical', size_hint_x=0.20)
        quick_all_button = Button(text="All", height=40)
        quick_all_button.bind(on_release=toggle_checkbox)
        quick_container.add_widget(quick_all_button)

        quick_none_button = Button(text="None", height=40)
        quick_none_button.bind(on_release=lambda button: toggle_checkbox(False))
        quick_container.add_widget(quick_none_button)

        quick_match_button = Button(text="Match", height=40)
        quick_match_button.bind(on_release=lambda button: toggle_checkbox(True, self.quick_match_input.text))
        quick_container.add_widget(quick_match_button)

        self.quick_match_input = TextInput(multiline=False, size_hint_y=None, height=40)
        self.quick_match_input.bind(on_text_validate=lambda i: toggle_checkbox(True, i.text))
        quick_container.add_widget(self.quick_match_input)

        quick_unmatch_button = Button(text="Unmatch", height=40)
        quick_unmatch_button.bind(on_release=lambda button: toggle_checkbox(False, self.quick_match_input.text))
        quick_container.add_widget(quick_unmatch_button)

        return quick_container


    def process_mods(self, folders):
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
                                          content=Label(text=f"Failed to read {file_path}: {e}"),
                                          size_hint=(None, None), size=(400, 200))
                            popup.open()

        return processed_text

    def build(self):
        self.title = "Hatsune Miku Project Diva Mega Mix+ JSON Generator"
        self.mods_folder = settings.get_settings()["megamix_options"]["mod_path"]

        self.options = {}
        self.container = ContainerLayout()

        self.main_layout = MainLayout(rows=3)
        self.container.add_widget(self.main_layout)

        def to_clipboard(button):
            checked_packs=[]
            for i, v in enumerate(self.checkboxes):
                if v.active is True:
                    checked_packs.append(str(os.path.join(self.mods_folder, self.scrollbox.children[0].children[-(i+1)].children[0].text)))

            combined_mod_pv_db = self.process_mods(checked_packs)
            mod_pv_db_json = filter_important_lines(combined_mod_pv_db, self.mods_folder)

            Clipboard.copy(mod_pv_db_json)

            box = BoxLayout(orientation="vertical")
            box.add_widget(Label(text=f"Generated {len(checked_packs)} packs ({len(mod_pv_db_json)} bytes)"))
            #box.add_widget(TextInput(text=mod_pv_db_json, multiline=False, readonly=True, size_hint_y=None, height=32))

            popup = Popup(title='Copied to clipboard',
                          content=box,
                          size_hint=(None, None), size=(400,200))
            popup.open()

        self.scrollbox_container = MainLayout(cols=2)

        self.scrollbox = ScrollBox(size_hint_y=1)
        self.scrollbox.layout.orientation = "vertical"
        self.create_pack_list()

        self.scrollbox_container.add_widget(self.scrollbox)
        self.scrollbox_container.add_widget(self.create_pack_buttons())

        bottom_box = BoxLayout(size_hint_y=None, height=40)
        process_button = Button(text="Generate Mod String")
        process_button.bind(on_release=to_clipboard)
        bottom_box.add_widget(process_button)
        bottom_box.add_widget(Button(text="Restore Song Packs", size_hint_x=0.5))
        open_mods = Button(text=self.mods_folder, size_hint_y=None, height=40)
        open_mods.bind(on_release=lambda button: Utils.open_file(self.mods_folder))

        self.main_layout.add_widget(open_mods)
        self.main_layout.add_widget(self.scrollbox_container)
        self.main_layout.add_widget(bottom_box)

        #self.main_layout.add_widget(self.main_panel)

        return self.container


def launch():
    DivaJSONGenerator().run()
