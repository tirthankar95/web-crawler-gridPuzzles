from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)


def parse_puzzle_page(html: str) -> dict:
    """
    Parse the puzzle page HTML and extract:
        - puzzle id / title
        - categories and their items (the grid axes)
        - clues list
        - solution grid (if visible on page)
    """
    soup = BeautifulSoup(html, "html.parser")
    puzzle: dict = {}

    # --- Title / puzzle number ---
    title_el = soup.find("h1") or soup.find("h2")
    puzzle["title"] = title_el.get_text(strip=True) if title_el else "Unknown"

    # Try to grab puzzle number from title or URL hints in the page
    num_match = re.search(r"#(\d+)", puzzle["title"])
    if num_match:
        puzzle["id"] = int(num_match.group(1))

    # --- Categories / items (grid axes) ---
    # The site renders category labels in a header row of the grid table
    categories: list[dict] = []

    # Look for the logic grid table – usually has class "lp-table" or similar
    grid_table = soup.find(
        "table", class_=re.compile(r"grid|logic|puzzle", re.I)
    ) or soup.find("table")
    if grid_table:
        puzzle["grid_html"] = str(grid_table)
        # Extract header rows to get category names and items
        header_rows = grid_table.find_all("tr")
        # Collect all unique text cells
        all_cells = []
        for row in header_rows:
            for cell in row.find_all(["td", "th"]):
                txt = cell.get_text(strip=True)
                if txt:
                    all_cells.append(txt)
        puzzle["grid_cells_sample"] = all_cells[:50]  # keep first 50 for inspection

    # --- Clues ---
    clues: list[str] = []

    # Clues are often in an ordered list or a div with class containing "clue"
    clue_container = (
        soup.find(class_=re.compile(r"clue", re.I))
        or soup.find("ol")
        or soup.find("ul")
    )
    if clue_container:
        items = clue_container.find_all("li")
        clues = [li.get_text(strip=True) for li in items if li.get_text(strip=True)]

    # Fallback: grab all <li> text site-wide if nothing found yet
    if not clues:
        all_li = soup.find_all("li")
        for li in all_li:
            txt = li.get_text(strip=True)
            # Clues tend to be full sentences with commas
            if len(txt) > 20 and "," in txt:
                clues.append(txt)

    puzzle["clues"] = clues

    # --- Narrative / intro text ---
    # Usually a <p> or <div> above the grid describing the scenario
    intro_candidates = soup.find_all("p")
    intro_texts = [
        p.get_text(strip=True)
        for p in intro_candidates
        if len(p.get_text(strip=True)) > 60
    ]
    if intro_texts:
        puzzle["intro"] = intro_texts[0]

    # --- Raw text dump for manual inspection ---
    puzzle["page_text_excerpt"] = soup.get_text(separator="\n")[:3000]
    return puzzle
