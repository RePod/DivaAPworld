# Hatsune Miku Project DIVA Mega Mix+ Setup Guide

## Requirements
- [Hatsune Miku Project DIVA Mega Mix+](https://store.steampowered.com/app/1761390/Hatsune_Miku_Project_DIVA_Mega_Mix/) (Steam)
  - [Extra Song Pack](https://store.steampowered.com/app/1887030/Hatsune_Miku_Project_DIVA_Mega_Mix_Extra_Song_Pack/) (optional, recommended, cheaper bundled)
  - The game can be played in Archipelago without the Extra Song Pack DLC.
- [DivaModLoader](https://github.com/blueskythlikesclouds/DivaModLoader?tab=readme-ov-file#installation)
- [[GB]](https://gamebanana.com/mods/514140) Archipelago Mod

## First Time Setup
This is a minimal setup to get started. Mod managers exist that may make certain steps easier, but you use them at your discretion.

1. If not already installed, [follow DivaModLoader's installation steps.](https://github.com/blueskythlikesclouds/DivaModLoader?tab=readme-ov-file#installation)
   - See 3 for locating `DivaMegaMix.exe`
2. Install the Archipelago Mod listed under [Requirements.](#requirements)
3. Upon starting the **Mega Mix Client** you will be prompted to select `DivaMegaMix.exe`:
   - Right-click the game entry in Steam, **Manage > Browse local files**
   - `DivaMegaMix.exe` (extension may be hidden) is what you will need to navigate to and select
   - You may be able to ***Ctrl+C*** the game EXE and paste its path into the original prompt's text input
4. Play! (requires a [YAML and generation](tutorial/Archipelago/setup_en))

### Resulting basic file structure
```
Hatsune Miku Project DIVA Mega Mix Plus\
├ DivaMegaMix.exe <─ game, select when prompted by Client/JSON generator
├ dinput8.dll <─ mod loader
├ config.toml <─ mod loader config (no need to edit)
└ mods\
  └ ArchipelagoMod\ <─ AP mod, currently required to be this name
    └ config.toml <─ AP mod config
```

## Optional Quality of Life Mods
- [[GB]](https://gamebanana.com/mods/388083) ExPatch
- [[GB]](https://gamebanana.com/mods/380955) High Frame Rate
- [[GB]](https://gamebanana.com/mods/449088) [[DMA]](https://divamodarchive.com/post/193) IntroPatch
- [[GB]](https://gamebanana.com/mods/427425) KeepFocus
- [[GB]](https://gamebanana.com/mods/414252) Mega Mix Thumbnail Manager

## Mod Songs
**Note: Currently, using mod songs requires the seed to be [generated locally](/tutorial/Archipelago/setup_en#generating-a-multiplayer-game), not on the website. Hosting on the website afterwards is fine.**

Open the **Mega Mix JSON Generator** from the Archipelago Launcher.

Checked song packs will be included in the song selection pool and have their visibility in-game controlled when using the **Mega Mix Client**. *Enabled* but unchecked packs will not be included in the pool and may remain visible in-game. Disable these manually.

### Adding the output to your YAML
On the line for `megamix_mod_data` paste and format it as such:
```YAML
megamix_mod_data: '{"MyFirstSongPack":[["MyFirstSong",144,224]]}'
```

It is recommended to regenerate the mod string when adding or updating packs. Individual songs can be excluded from the pool in the YAML's `exclude_songs` section.

## Troubleshooting

### Checks are not sending
Make sure the **Mega Mix Client** is open and connected to a room.

Try playing the BK song. If a success message does not appear on completion try restarting the **Mega Mix Client**.

### There are songs outside my specified difficulty settings
To increase the success of seed generation the difficulty settings are conservatively expanded *until* a minimally viable song pool is found.

If you do not like the results of the difficulty expansion consider less restrictive settings.

Starting (`start_inventory`) and Included songs (`include_songs`) will *always* ignore difficulty settings.

### My settings are too long or difficult
**Note: You can play any available difficulty for the same checks.**

In the [AP mod folder](#Resulting-basic-file-structure) open `results.json` with a text editor. If it does not exist play a song first.

Given `Song I Want To Beat [5678]`:
- Change the number after `pvId` to `5678` 
- Change the number after `scoreGrade` to `5` (Perfect).

Save the file while the **Mega Mix Client** is open and connected.

### Newly received songs are not appearing in game
While on the song list press ***F7*** or the defined `reload` key in the [mod's config](#Resulting-basic-file-structure) to reload the game. 

### Modded songs are not appearing in game
Install [ExPatch](#Optional-Quality-of-Life-Mods). Extreme/Extra Extreme only modded songs are common.

Similar to the [mod's config](#Resulting-basic-file-structure), ensure `enabled = true` in a pack's `config.toml`.

### Songs still aren't appearing
Run `/restore_songs` in the **Mega Mix Client**, reload, and play manually (honor system).
