from . import MegaMixTestBase
from ..MegaMixCollection import MegaMixCollections
from ..Options import IncludeSongs, ExcludeSongs

class TestPlando(MegaMixTestBase):
    MMC = MegaMixCollections()
    song_items = MMC.song_items

    def _test_plando(self, exclude: bool = False):
        # Shuffle song_items, pick out 60, allocate 30 to include/exclude, verify they're not returned.

        world = self.get_world()
        self.world_setup()
        self.assertTrue(len(self.song_items) >= 60,f"Minimum 60 MMC song_items expected, got {len(self.song_items)}")

        items = list(self.song_items)
        world.random.shuffle(items)
        items = items[0:60]
        extras = items[-30:]
        candidates = items[0:30]

        self.assertTrue(len(candidates) == 30,f"30 candidates expected, got {len(candidates)}")
        self.assertTrue(len(extras) == 30,f"30 extras expected, got {len(extras)}")

        if exclude:
            world.options.exclude_songs = ExcludeSongs(candidates)
        else:
            world.options.include_songs = IncludeSongs(candidates)

        song_pool = world.handle_plando(items)
        overlap = [song for song in candidates if song in song_pool]
        self.world_setup()

        self.assertTrue(len(overlap) == 0, f"0 overlap expected, got {len(overlap)}")
        self.assertTrue(len(song_pool) == len(extras), f"{len(extras)} remaining in song pool expected, got {len(song_pool)}")

    def test_plando_include(self):
        self._test_plando()

    def test_plando_exclude(self):
        self._test_plando(True)
