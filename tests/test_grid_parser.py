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


# Load test data from external file
def _load_test_cases():
    """Load test cases from JSON file."""
    test_data_file = Path(__file__).parent / "data" / "test_parsed_puzzle_data.json"
    with open(test_data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    test_cases = []
    for case in data["test_cases"]:
        html_file = Path(__file__).parent.parent / "webpages" / case["filename"]
        test_cases.append((
            html_file,
            case['grid'],
            case["story"],
            case["clues"],
            case["table"],
            case["options"]
        ))
    return test_cases


@pytest.mark.parametrize(
    "html_file,grid,story,clues,table,options",
    [(tc[0], tc[1], tc[2], tc[3], tc[4], tc[5]) for tc in _load_test_cases()]
)
@pytest.mark.verified
def test_puzzle_components(html_file, grid, story, clues, table, options):
    """Test that title is extracted correctly."""
    if not html_file.exists():
        pytest.skip(f"HTML file not found: {html_file}")
    puzzle_html = html_file.read_text(encoding="utf-8")
    result = parse_puzzle_page(puzzle_html, cfg=DictConfig({"grid": grid}))
    parsed_story, parsed_clues, parsed_table, parsed_options = puzzle_components(result)
    assert parsed_story.strip() == story
    assert parsed_clues.strip() == clues
    assert parsed_table == table
    assert parsed_options == options


@pytest.mark.parametrize(
    "html_file,grid,story,clues,table,options",
    [(tc[0], tc[1], tc[2], tc[3], tc[4], tc[5]) for tc in _load_test_cases()]
)
@pytest.mark.verified
def test_final_puzzle(html_file, grid, story, clues, table, options):
    if not html_file.exists():
        pytest.skip(f"HTML file not found: {html_file}")
    puzzle_html = html_file.read_text(encoding="utf-8")
    result = parse_puzzle_page(puzzle_html, cfg=DictConfig({"grid": grid}))
    puzzle = parse_puzzle(result)
    expected_puzzle = f"""\nStory:\n{story}\n\nClues:\n{clues}\n\nSolve the grid puzzle by filling the table:\n{table}\n\nUse the clues to fill the table with the following categories:\n{options}"""
    assert puzzle == expected_puzzle