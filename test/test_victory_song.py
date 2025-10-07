from . import MegaMixTestBase

class TestVictorySong(MegaMixTestBase):

    def test_victory_song_id(self):
        """Match the Victory Song ID back to its MMC self by name"""
        world = self.get_world()

        id_victory = world.item_name_to_id.get(world.victory_song_name)
        id_mmc = world.mm_collection.song_items.get(world.victory_song_name).code

        self.assertEqual(id_victory, id_mmc, "Victory Song code and MMC song code do not match")

    def test_victory_song_name(self):
        """Match the Victory Song name back to its MMC self by ID"""
        world = self.get_world()

        song_items = world.mm_collection.song_items
        name_victory = world.item_id_to_name.get(world.victory_song_id)
        name_mmc = [song for song in song_items if song_items[song].code == world.victory_song_id].pop()

        self.assertEqual(name_victory, name_mmc, "Victory Song name and MMC song name do not match")

class TestGoalSong(MegaMixTestBase):
    """Test the goal_song option despite not being in test_options or test_plando."""

    options = {
        "goal_song": "Love is War [1]",
        "exclude_songs": "Love is War [1]", # So it can't appear otherwise. It must be the Goal Song and not in the pool.
        "allow_megamix_dlc_songs": True,
        "additional_song_count": 300, # Consume all base+DLC songs
    }

    def test_goal_song(self):
        """Verify the specified Goal Song is, in fact, the goal song."""
        world = self.get_world()

        self.assertEqual(self.options.get("goal_song"), world.victory_song_name)

    def test_goal_song_not_in_pool(self):
        """Verify the specified Goal Song is not also in the item pool."""
        world = self.get_world()

        # There might be a helper function I missed.
        self.assertFalse(self.options.get("goal_song") in [item.name for item in world.multiworld.itempool
                                                           if item.player == self.player])
