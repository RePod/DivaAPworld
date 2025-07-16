from typing import ClassVar

from test.param import classvar_matrix
from . import MegaMixTestBase

# WARNING: mm_collection.song_items is subject to available megamix_mod_data from Players YAMLs during all tests.
# When testing locally this may affect length checks.

class TestOptionIncludes(MegaMixTestBase):
    """Set include_songs and test the multiworld item pool for their inclusion."""
    options = {
        "allow_megamix_dlc_songs": True,
        "duplicate_song_percentage": 0,
        "starting_song_count": 3,
        "additional_song_count": 15,
        "include_songs": ["Love is War [1]", "Packaged [10]", "Senbonzakura [216]", "Teo [271]"],
    }

    def test_included(self):
        world = self.get_world()
        pool = {song.name for song in world.multiworld.itempool if song.code >= 10}
        pool.update(world.starting_songs)
        pool.add(world.victory_song_name)

        self.assertTrue(world.options.include_songs.value.issubset(pool))

class TestOptionIncludesExact(MegaMixTestBase):
    """Set include_songs to the match the minimum required and verify the entire pool consists of them."""
    options = {
        "allow_megamix_dlc_songs": True,
        "duplicate_song_percentage": 0,
        "starting_song_count": 3,
        "additional_song_count": 15,
        "include_songs": [ # 19 songs for a 19 song seed (3+15+goal)
            "Love is War [1]", "The World is Mine [2]", "That One Second in Slow Motion [3]", "Jaded [4]", "Melt [5]",
            "Far Away [6]", "Strobo Nights [7]", "Star Story [8]", "Last Night, Good Night [9]", "Packaged [10]",
            "Rain With A Chance of Sweet*Drops [11]", "Marginal [12]", "Grumpy Waltz [13]", "Miracle Paint [14]",
            "Dreaming Leaf [15]", "VOC@LOID in Love [16]", "A Song of Wastelands, Forests, and Magic [17]",
            "Song of Life [18]", "moon [20]"
        ],
    }

    def test_include_exact(self):
        world = self.get_world()
        pool = {item.name for item in world.multiworld.itempool if item.code >= 10}
        pool.update(world.starting_songs)
        pool.add(world.victory_song_name)

        self.assertTrue(pool.issubset(set(world.options.include_songs)))

class TestOptionIncludesOverflow(MegaMixTestBase):
    """Set include_songs to more than the itempool can handle and verify the entire pool consists of them."""
    options = {
        "allow_megamix_dlc_songs": True,
        "duplicate_song_percentage": 0,
        "starting_song_count": 3,
        "additional_song_count": 15,
        "include_songs": [ # 20 songs for a 19 song seed (3+15+goal)
            "Love is War [1]", "The World is Mine [2]", "That One Second in Slow Motion [3]", "Jaded [4]", "Melt [5]",
            "Far Away [6]", "Strobo Nights [7]", "Star Story [8]", "Last Night, Good Night [9]", "Packaged [10]",
            "Rain With A Chance of Sweet*Drops [11]", "Marginal [12]", "Grumpy Waltz [13]", "Miracle Paint [14]",
            "Dreaming Leaf [15]", "VOC@LOID in Love [16]", "A Song of Wastelands, Forests, and Magic [17]",
            "Song of Life [18]", "moon [20]", "Beware of the Miku Miku Germs [21]"
        ]
    }

    def test_include_overflow(self):
        world = self.get_world()
        pool = {item.name for item in world.multiworld.itempool if item.code >= 10}
        pool.update(world.starting_songs)
        pool.add(world.victory_song_name)

        self.assertTrue(pool.issubset(world.options.include_songs.value))


class TestOptionExcludes(MegaMixTestBase):
    """Set exclude_songs and test the multiworld item pool for their absence."""
    options = {
        "allow_megamix_dlc_songs": True,
        "duplicate_song_percentage": 0,
        "starting_song_count": 10,
        "additional_song_count": 251,
        "exclude_songs": ["Love is War [1]", "Packaged [10]", "Senbonzakura [216]", "Teo [271]"],
    }

    def test_excluded(self):
        world = self.get_world()
        pool = {song.name for song in world.multiworld.itempool if song.code >= 10}
        pool.update(world.starting_songs)
        pool.add(world.victory_song_name)

        self.assertEqual(len(pool), len(world.mm_collection.song_items) - len(world.options.exclude_songs.value))
        self.assertFalse(world.options.exclude_songs.value.issubset(pool))


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
        singer_songs = [song for song, prop in self.world.mm_collection.song_items.items() if set(prop.singers).intersection(world.options.exclude_singers)]
        pool = {song.name for song in self.world.multiworld.itempool if song.code >= 10}
        pool.update(world.starting_songs)
        pool.add(world.victory_song_name)

        intersect = pool.intersection(singer_songs)
        self.assertEqual(0, len(intersect), f"0 songs from {world.options.exclude_singers} expected, got {len(intersect)}: {intersect}")
        self.assertEqual(len(singer_songs) + len(pool), len(self.world.mm_collection.song_items))
