from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)


def parse_puzzle_page(html: str) -> dict:
    """
    Parse the puzzle page HTML and extract:
        - puzzle id / title
        - active clues
        - backstory/narrative
        - puzzle grid (main playable grid)
        - answer grid (solution table)
    """
    soup = BeautifulSoup(html, "html.parser")
    puzzle: dict = {}

    # --- Title ---
    title_el = soup.find("h1") or soup.find("h2")
    puzzle["title"] = title_el.get_text(strip=True) if title_el else "Unknown"

    # Try to grab puzzle number from title
    num_match = re.search(r"#(\d+)", puzzle["title"])
    if num_match:
        puzzle["id"] = int(num_match.group(1))

    # --- Active Clues ---
    # Clues are in divs with class "clue" inside clue_holder
    clues: list[dict] = []
    clue_divs = soup.find_all("div", class_="clue")
    for clue_div in clue_divs:
        clue_text = clue_div.get_text(strip=True)
        clue_id = clue_div.get("id", "")
        if clue_text:
            clues.append({"id": clue_id, "text": clue_text})
    puzzle["clues"] = clues
    logger.info(f"Extracted {len(clues)} active clues")

    # --- Backstory / Story ---
    # Story is usually in tabs-2 section with "Backstory and Goal" heading
    story = None
    tabs2 = soup.find("div", id="tabs-2")
    if tabs2:
        # Find all paragraphs in this tab
        story_parts = []
        for p in tabs2.find_all("p"):
            txt = p.get_text(strip=True)
            if txt and len(txt) > 20:
                story_parts.append(txt)
        if story_parts:
            story = " ".join(story_parts)
    puzzle["story"] = story
    logger.info(f"Extracted story: {len(story) if story else 0} chars")

    # --- Main Puzzle Grid ---
    # The playable grid has id="puzzletable"
    puzzle_grid_table = soup.find("table", id="puzzletable")
    if puzzle_grid_table:
        puzzle["grid_html"] = str(puzzle_grid_table)
        # Extract grid structure
        rows = puzzle_grid_table.find_all("tr")
        grid_data = []
        for row in rows:
            cells = row.find_all(["td", "th"])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if row_data:
                grid_data.append(row_data)
        puzzle["grid_data"] = grid_data
        logger.info(f"Extracted puzzle grid with {len(grid_data)} rows")

    # --- Answer Grid ---
    # The answer/solution grid has id="answergrid"
    answer_grid_table = soup.find("table", id="answergrid")
    answer_grid = None
    if answer_grid_table:
        answer_grid = []
        rows = answer_grid_table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if row_data:
                answer_grid.append(row_data)
        puzzle["answer_grid"] = answer_grid
        logger.info(f"Extracted answer grid with {len(answer_grid)} rows")

    # --- Raw text excerpt for fallback ---
    puzzle["page_text_excerpt"] = soup.get_text(separator="\n")[:3000]
    return puzzle
