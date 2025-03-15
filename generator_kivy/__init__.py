from kvui import (App, ScrollBox, Button, MainLayout, ContainerLayout, dp, Widget, BoxLayout, TooltipLabel, ToolTip,
                  Label)
from kivy.core.clipboard import Clipboard
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput
import Utils

import os
import settings

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
    main_panel: MainLayout
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


    def build(self):
        self.mods_folder = settings.get_settings()["megamix_options"]["mod_path"]

        self.options = {}
        self.container = ContainerLayout()

        self.main_layout = MainLayout(rows=3)
        self.container.add_widget(self.main_layout)

        def to_clipboard(button):
            for i, v in enumerate(self.checkboxes):
                if v.active is True:
                    print(v.active, self.scrollbox.children[0].children[-(i+1)].children[0].text)

            generated_string = "THISISWHEREI'DPUTTHEJSONOUTPUT,IFIHADANY"
            Clipboard.copy(generated_string)
            popup = Popup(title='Copied to clipboard',
                          content=TextInput(text=generated_string, multiline=False, readonly=True, size_hint_y=None, height=32),
                          size_hint=(None, None), size=(400,200))
            popup.open()

        self.scrollbox = ScrollBox(size_hint_y=1)
        self.scrollbox.layout.orientation = "vertical"
        self.create_pack_list()

        bottom_box = BoxLayout(size_hint_y=None, height=40)

        process_button = Button(text="Generate Mod String")
        process_button.bind(on_release=to_clipboard)
        bottom_box.add_widget(process_button)

        bottom_box.add_widget(Button(text="Restore Song Packs", size_hint_x=0.5))

        #self.main_panel = MainLayout()
        open_mods = Button(text=self.mods_folder, size_hint_y=None, height=40)
        open_mods.bind(on_release=lambda button: Utils.open_file(self.mods_folder))

        self.main_layout.add_widget(open_mods)
        self.main_layout.add_widget(self.scrollbox)
        self.main_layout.add_widget(bottom_box)

        #self.main_layout.add_widget(self.main_panel)

        return self.container


def launch():
    DivaJSONGenerator().run()
