import re

# Function to replace symbols in song names
def replace_symbols(song_name):
    # Replace × with "x"
    song_name = song_name.replace("×", "x")
    # Replace 　 with regular space
    song_name = song_name.replace("　", " ")
    # Replace ～ with "~"
    song_name = song_name.replace("～", "~")
    # Replace ∞ with "∞" (you can change this to any character or space as required)
    song_name = song_name.replace("∞", " ")
    # Replace symbols between two words (no spaces) with space
    song_name = re.sub(r'([◎★♣＊☆])', ' ', song_name)
    # Remove symbols that should be removed
    song_name = song_name.replace("♪", "")
    # Clean up extra spaces created by replacement
    song_name = re.sub(r'\s+', ' ', song_name).strip()
    return song_name



# List of offending song names
offending_songs = [
    "Beware of the Miku Miku Germs♪",
    "I'll Miku-Miku You♪ (For Reals)",
    "Colorful × Melody",
    "VOiCE -DIVA　MIX-",
    "Clover♣Club",
    "Colorful × Sexy",
    "Luka Luka ★ Night Fever",
    "Piano × Forte × Scandal",
    "Nightmare ☆ Party Night",
    "Starlite★Lydian",
    "So Much Loving You★ -DIVA Edit-",
    "Gothic and Loneliness ～I'm the very DIVA～",
    "Monochrome∞Blue Sky",
    "Fire◎Flower",
    "Sadistic.Music∞Factory",
    "Negaposi＊Continues",
    "Black★Rock Shooter"
]

# Function to fix song names if they are in the offending songs list
def fix_song_name(song_name):
    if song_name in offending_songs:
        return replace_symbols(song_name)
    return song_name