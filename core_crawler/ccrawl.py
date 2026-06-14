import time
import json
import logging
from pathlib import Path
from omegaconf import DictConfig
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from page_parser.grid_parser import parse_puzzle_page

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://logic.puzzlebaron.com/init.php"
# <select name="sg"> option values
GRID_VALUE_MAP = {
    "3x4": "1",
    "3x5": "2",
    "4x4": "3",
    "4x5": "4",
    "4x6": "5",
    "4x7": "6",
}

# <select name="sd"> option values
DIFFICULTY_VALUE_MAP = {
    "Easy":        "1",
    "Moderate":    "2",
    "Challenging": "3",
}


def crawl_puzzles(
    grid_size: str,
    difficulty: str,
    count: int,
    output_file: str,
    headless: bool,
    delay: float,
    cfg: DictConfig = None,
):
    grid_value       = GRID_VALUE_MAP[grid_size]
    difficulty_value = DIFFICULTY_VALUE_MAP[difficulty]
    
    results: list[dict] = []
    errors: list[str] = []

    logger.info(
        f"Starting crawler: grid={grid_size}, difficulty={difficulty}, count={count}"
    )
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

                # ── Step 2: Select Grid Size ──────────────────────────────
                page.select_option("select[name='sg']", value=grid_value)
                logger.info(f"  Grid size set  → option value={grid_value} ({grid_size})")

                page.select_option("select[name='sd']", value=difficulty_value)
                logger.info(f"  Difficulty set → option value={difficulty_value} ({difficulty})")

                logger.info("  Clicking 'Create Puzzle' …")
                page.click("input[name='CreatePuzzle']")
                
                time.sleep(cfg.sleep_time_fast)
                logger.info("  Clicking 'Start this puzzle' …")
                page.click("input[name='submit']")
                
                time.sleep(cfg.sleep_time_fast)
                html = page.content()
                puzzle = parse_puzzle_page(html)
                puzzle["url"]          = page.url
                puzzle["grid_size"]    = grid_size
                puzzle["difficulty"]   = difficulty
                puzzle["collected_at"] = datetime.utcnow().isoformat() + "Z"
                puzzle["index"]        = i
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
    logger.info(
        f"Done! Collected {len(results)}/{count} puzzles. Saved to: {path.resolve()}"
    )
    if errors:
        logger.warning(f"Errors ({len(errors)}):")
        for e in errors:
            logger.warning(f"  • {e}")
    return output
