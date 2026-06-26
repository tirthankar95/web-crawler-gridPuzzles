"""
Tests for gridr.py
"""
import json
import pytest
import logging
from pathlib import Path
from omegaconf import DictConfig
from page_parser.grid_parser import parse_puzzle_page
from page_parser.parse_elements import (
    puzzle_components,
    parse_puzzle
)
    

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 2. Create a FileHandler to write logs to a file
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.INFO)

# 3. Create a Formatter to format log lines
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# 4. Attach the Handler to the Logger
logger.addHandler(file_handler)

@pytest.fixture
def puzzle_html():
    """Load the sample HTML puzzle page."""
    html_file = Path(__file__).parent.parent / "webpages" / "Logic Puzzles _ Solve a Puzzle_p3.html"
    if not html_file.exists():
        pytest.skip(f"HTML file not found: {html_file}")
    return html_file.read_text(encoding="utf-8")


@pytest.mark.verified
def test_parsed_puzzle(puzzle_html):
    """Test that title is extracted correctly."""
    result = parse_puzzle_page(puzzle_html, cfg=DictConfig({"grid": "3x4"}))
    story, clues, table, options = puzzle_components(result)
    
    assert story.startswith("Minnetonka Manatee Company sent out a number of different boats today on manatee")

    assert clues.strip() == """1.The Foxy Roxy saw 3 manatees.
2.The vessel that saw 5 manatees is either the Samantha or Captain Espinoza's vessel.
3.The boat that saw 4 manatees was led by Captain Armstrong.
4.Captain Preston's vessel saw 1  fewer manatees than the Benny II.
5.The Watery Pete saw 2  more manatees than the Foxy Roxy."""
    
    assert table == """+------------+---------+------------+
|   Manatees | Boats   | Captains   |
+============+=========+============+
|          3 |         |            |
+------------+---------+------------+
|          4 |         |            |
+------------+---------+------------+
|          5 |         |            |
+------------+---------+------------+
|          6 |         |            |
+------------+---------+------------+"""


@pytest.mark.verified
def test_get_puzzle():
    '''Checks if we are correctly getting data from a parsed puzzle page.'''
    with open("tests/data/puzzles.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        x, xx, xxx, options = puzzle_components(data['puzzles'][0])
    assert options == """Oyster: Bluepoint, Fanneuil, Katamaka, Thatcher
Origins: Appleton, CT, Charlestown, CT, Nesketucket, MA, Willapa, RI"""


@pytest.mark.verified
def test_final_puzzle():
    with open("tests/data/puzzles.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        puzzle = parse_puzzle(data['puzzles'][0])
    assert puzzle == """
Story:
James runs Raw 642, an oyster bar in the coastal town of Shelshank, Rhode Island.  Help him sort out today's menu by matching each oyster to its price and place of origin, and determine the descriptive "tasting finish" associated with each. Remember, as with all grid-based logic puzzles, no option in any category will ever be used more than once.  If you get stuck or run into problems, try the "Clear Errors" button to remove any mistakes that might be present on the grid, or the "Hint" button to see the next logical step in the puzzle.

Clues:
1.The oyster from Appleton, CT costs 10 cents more than the Fanneuil oyster.
2.The Thatcher oyster costs 10 cents more than the Bluepoint oyster.
3.The oyster from Charlestown, CT costs somewhat less than the Bluepoint oyster.
4.The one from Charlestown, CT costs 10 cents more than the oyster from Nesketucket, MA.

Solve the grid puzzle by filling the table:
+----------+----------+-----------+
| Prices   | Oyster   | Origins   |
+==========+==========+===========+
| $2.00    |          |           |
+----------+----------+-----------+
| $2.10    |          |           |
+----------+----------+-----------+
| $2.20    |          |           |
+----------+----------+-----------+
| $2.30    |          |           |
+----------+----------+-----------+

Use the clues to fill the table with the following categories:
Oyster: Bluepoint, Fanneuil, Katamaka, Thatcher
Origins: Appleton, CT, Charlestown, CT, Nesketucket, MA, Willapa, RI"""