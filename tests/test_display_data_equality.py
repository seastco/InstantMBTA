"""Tests for DisplayData equality comparison."""

import unittest
from instantmbta.display_modes import DisplayData, DisplayLine


class TestDisplayDataEquality(unittest.TestCase):
    """Test DisplayData __eq__ implementation."""
    
    def test_equal_display_data(self):
        """Test that identical DisplayData objects are equal."""
        data1 = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[
                DisplayLine("OL In: 10:15 AM", is_route=True),
                DisplayLine("OL In: 10:23 AM", indent=True)
            ],
            refresh_seconds=60
        )
        
        data2 = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[
                DisplayLine("OL In: 10:15 AM", is_route=True),
                DisplayLine("OL In: 10:23 AM", indent=True)
            ],
            refresh_seconds=60
        )
        
        self.assertEqual(data1, data2)
        self.assertFalse(data1 != data2)
    
    def test_not_equal_different_title(self):
        """Test inequality when titles differ."""
        data1 = DisplayData(title="Oak Grove", date="07/06/25")
        data2 = DisplayData(title="Wellington", date="07/06/25")
        
        self.assertNotEqual(data1, data2)
        self.assertTrue(data1 != data2)
    
    def test_not_equal_different_date(self):
        """Test inequality when dates differ."""
        data1 = DisplayData(title="Oak Grove", date="07/06/25")
        data2 = DisplayData(title="Oak Grove", date="07/07/25")
        
        self.assertNotEqual(data1, data2)
    
    def test_not_equal_different_lines(self):
        """Test inequality when lines differ."""
        data1 = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[DisplayLine("OL In: 10:15 AM")]
        )
        
        data2 = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[DisplayLine("OL In: 10:23 AM")]  # Different time
        )
        
        self.assertNotEqual(data1, data2)
    
    def test_not_equal_different_refresh(self):
        """Test inequality when refresh seconds differ."""
        data1 = DisplayData(title="Test", date="07/06/25", refresh_seconds=60)
        data2 = DisplayData(title="Test", date="07/06/25", refresh_seconds=120)
        
        self.assertNotEqual(data1, data2)
    
    def test_not_equal_different_line_count(self):
        """Test inequality when number of lines differs."""
        data1 = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[
                DisplayLine("Line 1"),
                DisplayLine("Line 2")
            ]
        )
        
        data2 = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[DisplayLine("Line 1")]
        )
        
        self.assertNotEqual(data1, data2)
    
    def test_not_equal_non_displaydata(self):
        """Test inequality with non-DisplayData objects."""
        data = DisplayData(title="Test", date="07/06/25")
        
        self.assertNotEqual(data, "not a DisplayData")
        self.assertNotEqual(data, 123)
        self.assertNotEqual(data, None)
        self.assertNotEqual(data, {"title": "Test", "date": "07/06/25"})
    
    def test_display_line_equality(self):
        """Test DisplayLine equality (uses default dataclass eq)."""
        line1 = DisplayLine("Test", is_header=True, indent=False)
        line2 = DisplayLine("Test", is_header=True, indent=False)
        line3 = DisplayLine("Test", is_header=False, indent=False)
        
        self.assertEqual(line1, line2)
        self.assertNotEqual(line1, line3)
    
    def test_empty_display_data(self):
        """Test equality of empty DisplayData objects."""
        data1 = DisplayData(title="", date="", lines=[], refresh_seconds=60)
        data2 = DisplayData(title="", date="", lines=[], refresh_seconds=60)
        
        self.assertEqual(data1, data2)
    
    def test_display_update_logic(self):
        """Test the actual update logic from main loop."""
        # Simulate the logic from run_display_loop
        last_display_data = None
        display_data = DisplayData(title="Test", date="07/06/25")
        
        # First update - should update
        should_update = last_display_data is None or display_data != last_display_data
        self.assertTrue(should_update)
        
        # Same data - should not update
        last_display_data = display_data
        should_update = last_display_data is None or display_data != last_display_data
        self.assertFalse(should_update)
        
        # Changed data - should update
        new_display_data = DisplayData(title="Test", date="07/06/25", lines=[DisplayLine("New")])
        should_update = last_display_data is None or new_display_data != last_display_data
        self.assertTrue(should_update)


if __name__ == '__main__':
    unittest.main()