import re

from . import MegaMixTestBase


class IDNames(MegaMixTestBase):
    """Test that item/location names contain a song ID."""
    item_regex = r".*?\[(\d+)\]$"
    location_regex = r".*?\[(\d+)\]-\d$" # [01]$

    def test_item_names_have_id(self):
        """Test all song item names include *a* song ID.
        As of writing, song item IDs start at 10. 1-9 are reserved for non-song items."""
        world = self.get_world()
        quick = [k for k, id in world.item_name_to_id.items() if not re.search(self.item_regex, k) and id >= 10]
        self.assertEqual(0, len(quick), f"Item names without song IDs: {quick}")

    def test_loc_names_have_id(self):
        """Test all location names include *a* song ID."""
        world = self.get_world()
        quick = [k for k in world.location_name_to_id if not re.search(self.location_regex, k)]
        self.assertEqual(0, len(quick), f"Location names without song IDs: {quick}")
