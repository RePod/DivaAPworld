from typing import ClassVar

from test.param import classvar_matrix
from . import MegaMixTestBase


class TestOptionIncludes(MegaMixTestBase):
    """Set include_songs and test the multiworld item pool for their inclusion."""
    options = {
        "allow_megamix_dlc_songs": True,
        "duplicate_song_percentage": 0,
        "include_songs": ["Love is War [1]", "Packaged [10]", "Senbonzakura [216]", "Teo [271]"],
        "starting_song_count": 3,
        "additional_song_count": 15,
    }

    def test_included(self):
        world = self.get_world()
        pool = {song.name for song in world.multiworld.itempool if song.code >= 10}

        self.assertTrue(set(world.options.include_songs).issubset(pool))


class TestOptionExcludes(MegaMixTestBase):
    """Set exclude_songs and test the multiworld item pool for their absence."""
    options = {
        "allow_megamix_dlc_songs": True,
        "duplicate_song_percentage": 0,
        "exclude_songs": ["Love is War [1]", "Packaged [10]", "Senbonzakura [216]", "Teo [271]"],
        "starting_song_count": 10,
        "additional_song_count": 251,
    }

    def test_excluded(self):
        world = self.get_world()
        pool = {song.name for song in world.multiworld.itempool if song.code >= 10}

        self.assertFalse(set(world.options.exclude_songs).issubset(pool))


# Can also supply combinations.
@classvar_matrix(singer=[{'Hatsune Miku'}, {'Kagamine Rin'}, {'Kagamine Len'}, {'Megurine Luka'}, {'KAITO'}, {'MEIKO'}])
class TestOptionExcludeSinger(MegaMixTestBase):
    """Set exclude_singers and test the multiworld item pool for their absence."""
    auto_construct = False
    singer: ClassVar[set[str]]
    options = {
        "allow_megamix_dlc_songs": True,
        "additional_song_count": 251,
    }

    def test_exclude_singer(self):
        self.options["exclude_singers"] = self.singer
        self.world_setup()

        world = self.get_world()
        # WARNING: mm_collection.song_items is subject to available megamix_mod_data
        singer_songs = [song for song, prop in self.world.mm_collection.song_items.items() if set(prop.singers).intersection(world.options.exclude_singers)]
        pool = {song.name for song in self.world.multiworld.itempool if song.code >= 10}
        pool.update(world.starting_songs)

        intersect = pool.intersection(singer_songs)
        self.assertEqual(intersect, set(), f"0 songs expected from excluded {world.options.exclude_singers}, found {len(intersect)}: {intersect}")
        self.assertEqual(len(singer_songs) + len(pool) + 1, len(self.world.mm_collection.song_items))
