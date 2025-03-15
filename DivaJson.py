import os
import tkinter as tk
from tkinter import Tk, filedialog, messagebox
from tkinter import ttk
from .TextFilter import filter_important_lines

import settings


class ModManagerApp:
    def __init__(self, master):
        self.Tk = Tk()
        self.master = master
        self.master.title("Diva Json Generator")

        self.mods_folder = settings.get_settings()["megamix_options"]["mod_path"]  # Load the mods folder from config
        self.folders = []

        self.button_frame = tk.Frame(self.master)
        self.button_frame.pack(pady=10)

        # Label for the current mods folder
        self.current_folder_label = tk.Label(self.button_frame,
                                             text=f"Current Mods Folder: {self.mods_folder or 'Not selected'}")
        self.current_folder_label.grid(row=0, column=0, columnspan=2, padx=5, pady=5)

        # Button for selecting mods folder
        self.select_mods_button = self.create_button("Select Mods Folder", self.select_folder, 1, 0)
        self.select_mods_button.grid(row=1, column=0, sticky='w')  # Align left

        self.scrollable_frame = None
        self.canvas = None
        self.scrollbar = None

        self.checkbox_frame = None

        self.generated_text_box = tk.Text(self.master, height=10, width=50, wrap='word', state='disabled')
        self.generated_text_box.pack_forget()  # Initially hidden

        # Label above the copy button
        self.paste_label = tk.Label(self.master, text="Paste to Mod Data section in your YAML")
        self.copy_button = tk.Button(self.master, text="Copy to Clipboard", command=self.copy_to_clipboard)
        self.copy_button.pack_forget()  # Initially hidden

        self.setup_scrollable_frame()

        self.process_button = tk.Button(self.master, text="Process Mods", command=self.process_mods)
        self.process_button.pack_forget()  # Initially hidden

        # Right-side frame for the button and status label
        self.right_frame = tk.Frame(self.master)
        self.right_frame.pack(side='right', padx=20, pady=20, anchor='e')

        # Fix Song Packs button
        self.fix_button = tk.Button(self.right_frame, text="Fix Song Packs", command=self.fix_song_packs)
        self.fix_button.pack(pady=10)

        # Status label for showing messages (initially hidden)
        self.status_label = tk.Label(self.right_frame, text="", fg="green")
        self.status_label.pack(pady=10)

        # Check if a mods folder was loaded and populate the folder list if it exists
        if self.mods_folder:
            self.list_folders()  # Populate the folders if a folder was previously set
            self.process_button.pack(pady=10)  # Show the process button
            self.fix_button.pack(pady=10)  # Show the fix button

    def create_button(self, text, command, row, column):
        button = tk.Button(self.button_frame, text=text, command=command)
        button.grid(row=row, column=column, padx=5)
        return button

    def setup_scrollable_frame(self):
        self.scrollable_frame = ttk.Frame(self.master)
        self.canvas = tk.Canvas(self.scrollable_frame)
        self.scrollbar = ttk.Scrollbar(self.scrollable_frame, orient="vertical", command=self.canvas.yview)

        self.checkbox_frame = ttk.Frame(self.canvas)
        self.checkbox_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window((0, 0), window=self.checkbox_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollable_frame.pack(fill="both", expand=True)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_mods_folder(self):
        try:
            with open('config.txt', 'r') as file:
                folder = file.read().strip()  # Load folder from config
                if os.path.exists(folder) and os.path.isdir(folder):  # Check if it's a valid directory
                    return folder
                else:
                    return ""  # Invalid path
        except FileNotFoundError:
            return ""

    def save_mods_folder(self, folder_path):
        with open('config.txt', 'w') as file:
            file.write(folder_path)  # Save the folder path to config

    def select_folder(self):
        self.mods_folder = filedialog.askdirectory()
        if self.mods_folder:
            self.save_mods_folder(self.mods_folder)  # Save selected folder
            self.current_folder_label.config(text=f"Current Mods Folder: {self.mods_folder}")  # Update label
            self.list_folders()
            self.process_button.pack(pady=10)  # Show the process button

    def list_folders(self):
        # Clear the checkbox frame first
        for widget in self.checkbox_frame.winfo_children():
            widget.destroy()

        self.folders = []

        # Loop through each folder in mods_folder
        for folder_name in os.listdir(self.mods_folder):
            folder_path = os.path.join(self.mods_folder, folder_name)

            # Check if it's a directory
            if os.path.isdir(folder_path):
                # Recursively search for mod_pv_db.txt using os.walk
                for root, dirs, files in os.walk(folder_path):
                    if 'mod_pv_db.txt' in files:
                        # If found, create a checkbox
                        var = tk.BooleanVar()
                        chk = tk.Checkbutton(self.checkbox_frame, text=folder_name, variable=var)
                        chk.pack(anchor='w')
                        self.folders.append((folder_path, var))
                        break  # No need to search further in this directory

    def process_mods(self):
        output_file_path = os.path.join(os.getcwd(), "combined_mod_pv_db.txt")
        with open(output_file_path, "w", encoding='utf-8', errors='ignore') as output_file:
            for folder_path, var in self.folders:
                if var.get():
                    folder_name = os.path.basename(folder_path)
                    output_file.write(f"song_pack={folder_name}\n")
                    for master, dirs, files in os.walk(folder_path):
                        for file in files:
                            if file == "mod_pv_db.txt":
                                file_path = os.path.join(master, file)
                                try:
                                    with open(file_path, "r", encoding='utf-8', errors='ignore') as input_file:
                                        output_file.write(input_file.read() + "\n")
                                except Exception as e:
                                    messagebox.showerror("Error", f"Failed to read {file_path}: {e}")

        # Now pass the player name to the filter function
        self.display_generated_text(
            filter_important_lines("combined_mod_pv_db.txt", "filtered_file.txt", self.mods_folder))

    def display_generated_text(self, text):
        self.generated_text_box.config(state='normal')
        self.generated_text_box.delete(1.0, tk.END)  # Clear the box
        self.generated_text_box.insert(tk.END, text)
        self.generated_text_box.config(state='disabled')
        self.generated_text_box.pack(pady=10)  # Show the text box
        self.paste_label.pack(pady=10)  # Show the label
        self.copy_button.pack(pady=10)  # Show the copy button

    def copy_to_clipboard(self):
        text = self.generated_text_box.get(1.0, tk.END).strip()  # Get text from the text box
        self.Tk.clipboard_clear()
        self.Tk.clipboard_append(text)
        self.Tk.withdraw()
        messagebox.showinfo("Copied", "Text copied to clipboard!")  # Notify user

    def fix_song_packs(self):

        for folder_path, var in self.folders:
            mod_copy_found = False
            for root, dirs, files in os.walk(folder_path):
                if 'mod_pv_dbCOPY.txt' in files and 'mod_pv_db.txt' in files:
                    copy_file_path = os.path.join(root, 'mod_pv_dbCOPY.txt')
                    original_file_path = os.path.join(root, 'mod_pv_db.txt')

                    try:
                        # Read the contents of mod_pv_dbCOPY.txt
                        with open(copy_file_path, 'r', encoding='utf-8', errors='ignore') as copy_file:
                            copy_content = copy_file.read()

                        # Overwrite mod_pv_db.txt with the contents from mod_pv_dbCOPY.txt
                        with open(original_file_path, 'w', encoding='utf-8', errors='ignore') as original_file:
                            original_file.write(copy_content)

                        mod_copy_found = True
                        break  # Stop searching further in this folder once the file is processed
                    except Exception as e:
                        # Display an error message in red on the status label
                        self.status_label.config(text=f"Error fixing {original_file_path}: {e}", fg="red")
                        mod_copy_found = True  # Stop further searching for this folder

            if not mod_copy_found:
                # If no mod_pv_dbCOPY.txt was found, display a warning
                self.status_label.config(text=f"mod_pv_dbCOPY.txt not found in {folder_path}", fg="orange")

        self.status_label.config(text="Song Packs fixed", fg="green")


def launch():
    master = tk.Tk()
    app = ModManagerApp(master)
    master.mainloop()
