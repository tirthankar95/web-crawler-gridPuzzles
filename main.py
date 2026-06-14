"""
Logic Puzzle Baron Crawler
==========================
Collects grid logic puzzles from https://logic.puzzlebaron.com/init.php

Usage:
    python puzzle_crawler.py [options]

Options:
    --grid          Grid size to select (default: 4x4)
                    Choices: 3x4, 3x5, 4x4, 4x5, 4x6, 4x7
    --difficulty    Difficulty level (default: Easy)
                    Choices: Easy, Moderate, Challenging
    --count         Number of puzzles to collect (default: 5)
    --output        Output JSON file (default: puzzles.json)
    --headless      Run browser in headless mode (default: True)
    --delay         Seconds to wait between puzzles (default: 2)

Requirements:
    pip install playwright beautifulsoup4
    python -m playwright install chromium

Example:
    python puzzle_crawler.py --grid 4x4 --difficulty Easy --count 10
    python puzzle_crawler.py --grid 4x6 --difficulty Challenging --count 3 --headless false
"""

import json
import logging
import time
import re
import sys
from datetime import datetime
from pathlib import Path

from omegaconf import OmegaConf, DictConfig

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    logging.critical("playwright is not installed. Run: pip install playwright && python -m playwright install chromium")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    logging.critical("beautifulsoup4 is not installed. Run: pip install beautifulsoup4")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://logic.puzzlebaron.com/init.php"

GRID_SIZES = ["3x4", "3x5", "4x4", "4x5", "4x6", "4x7"]
DIFFICULTIES = ["Easy", "Moderate", "Challenging"]

# Maps our friendly names to what the page's radio button labels say
GRID_LABEL_MAP = {
    "3x4": "3x4 Grid",
    "3x5": "3x5 Grid",
    "4x4": "4x4 Grid",
    "4x5": "4x5 Grid",
    "4x6": "4x6 Grid",
    "4x7": "4x7 Grid",
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def select_radio_by_label(page, label_text: str) -> bool:
    """Click a radio button whose associated label contains label_text."""
    # Try label element approach first
    labels = page.query_selector_all("label")
    for lbl in labels:
        if label_text.lower() in lbl.inner_text().lower():
            lbl.click()
            return True
    # Fallback: find input[type=radio] near matching text
    radios = page.query_selector_all("input[type='radio']")
    for radio in radios:
        val = radio.get_attribute("value") or ""
        if label_text.lower() in val.lower():
            radio.click()
            return True
    return False


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
    grid_table = (
        soup.find("table", class_=re.compile(r"grid|logic|puzzle", re.I))
        or soup.find("table")
    )
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
    intro_texts = [p.get_text(strip=True) for p in intro_candidates if len(p.get_text(strip=True)) > 60]
    if intro_texts:
        puzzle["intro"] = intro_texts[0]

    # --- Raw text dump for manual inspection ---
    puzzle["page_text_excerpt"] = soup.get_text(separator="\n")[:3000]

    return puzzle


# ---------------------------------------------------------------------------
# Core crawler
# ---------------------------------------------------------------------------
def crawl_puzzles(
    grid_size: str,
    difficulty: str,
    count: int,
    output_file: str,
    headless: bool,
    delay: float,
):
    grid_label = GRID_LABEL_MAP[grid_size]
    results: list[dict] = []
    errors: list[str] = []

    logger.info(f"Starting crawler: grid={grid_size}, difficulty={difficulty}, count={count}")
    logger.info(f"Output file: {output_file}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )

        for i in range(1, count + 1):
            logger.info(f"─── Puzzle {i}/{count} ───────────────────────────")

            try:
                page = context.new_page()

                # ── Step 1: Load the selection page ──────────────────────
                logger.info("Loading init.php …")
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_load_state("networkidle", timeout=15_000)

                # ── Step 2: Select Grid Size ──────────────────────────────
                logger.info(f"Selecting grid size: {grid_label}")
                if not select_radio_by_label(page, grid_label):
                    # Try value-based approach
                    radios = page.query_selector_all("input[type='radio']")
                    logger.warning(f"Available radio values: {[r.get_attribute('value') for r in radios]}")
                    raise RuntimeError(f"Could not find radio for '{grid_label}'")

                # ── Step 3: Select Difficulty ─────────────────────────────
                logger.info(f"Selecting difficulty: {difficulty}")
                if not select_radio_by_label(page, difficulty):
                    raise RuntimeError(f"Could not find radio for difficulty '{difficulty}'")

                # ── Step 4: Click "Create Puzzle" ─────────────────────────
                logger.info("Clicking 'Create Puzzle' …")
                # Find the submit button – try common patterns
                submit_btn = (
                    page.query_selector("input[type='submit']")
                    or page.query_selector("button[type='submit']")
                    or page.query_selector("input[value*='Create']")
                    or page.query_selector("input[value*='Puzzle']")
                    or page.query_selector("button")
                )
                if not submit_btn:
                    raise RuntimeError("Could not find submit/create button")

                logger.info(f"Submit button text: '{submit_btn.get_attribute('value') or submit_btn.inner_text()}'")
                submit_btn.click()
                page.wait_for_load_state("domcontentloaded", timeout=20_000)
                page.wait_for_load_state("networkidle", timeout=15_000)

                intermediate_url = page.url
                logger.info(f"After create → {intermediate_url}")

                # ── Step 5: Click "Start Puzzle" ──────────────────────────
                # This page shows puzzle info and has a "Start Puzzle" button
                start_btn = None
                for selector in [
                    "a:has-text('Start Puzzle')",
                    "input[value*='Start']",
                    "button:has-text('Start')",
                    "a[href*='puzzle']",
                    "input[type='submit']",
                ]:
                    try:
                        start_btn = page.query_selector(selector)
                        if start_btn:
                            break
                    except Exception:
                        continue

                if start_btn:
                    btn_text = start_btn.inner_text() if hasattr(start_btn, "inner_text") else ""
                    logger.info(f"Clicking start button: '{btn_text or start_btn.get_attribute('value')}' …")
                    start_btn.click()
                    page.wait_for_load_state("domcontentloaded", timeout=20_000)
                    page.wait_for_load_state("networkidle", timeout=15_000)
                else:
                    logger.warning("No 'Start Puzzle' button found – parsing current page as puzzle page")

                puzzle_url = page.url
                logger.info(f"Puzzle URL: {puzzle_url}")

                # ── Step 6: Parse puzzle content ──────────────────────────
                html = page.content()
                puzzle = parse_puzzle_page(html)
                puzzle["url"] = puzzle_url
                puzzle["grid_size"] = grid_size
                puzzle["difficulty"] = difficulty
                puzzle["collected_at"] = datetime.utcnow().isoformat() + "Z"
                puzzle["index"] = i

                clue_count = len(puzzle.get("clues", []))
                logger.info(f"Collected: '{puzzle.get('title', 'N/A')}' with {clue_count} clues")
                results.append(puzzle)

            except PlaywrightTimeout as e:
                msg = f"Puzzle {i}: Timeout – {e}"
                logger.error(msg)
                errors.append(msg)
            except Exception as e:
                msg = f"Puzzle {i}: {type(e).__name__}: {e}"
                logger.error(msg)
                errors.append(msg)
            finally:
                try:
                    page.close()
                except Exception:
                    pass

            if i < count:
                logger.info(f"Waiting {delay}s before next puzzle …")
                time.sleep(delay)

        browser.close()

    # ── Save results ──────────────────────────────────────────────────────
    output = {
        "meta": {
            "grid_size": grid_size,
            "difficulty": difficulty,
            "requested": count,
            "collected": len(results),
            "errors": len(errors),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
        "errors": errors,
        "puzzles": results,
    }

    path = Path(output_file)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    logger.info(f"Done! Collected {len(results)}/{count} puzzles. Saved to: {path.resolve()}")
    if errors:
        logger.warning(f"Errors ({len(errors)}):")
        for e in errors:
            logger.warning(f"  • {e}")
    return output


@hydra.main(config_path="config.yaml")
def main(cfg: DictConfig):
    crawl_puzzles(
        grid_size=cfg.grid,
        difficulty=cfg.difficulty,
        count=cfg.count,
        output_file=cfg.output,
        headless=cfg.headless,
        delay=cfg.delay,
    )

if __name__ == "__main__":
    main()