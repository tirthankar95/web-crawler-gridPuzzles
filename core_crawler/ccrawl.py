import logging 
from playwright.sync_api import (
    sync_playwright, 
    TimeoutError as PlaywrightTimeout
)
logger = logging.getLogger(__name__)  

GRID_LABEL_MAP = {
    "3x4": "3x4 Grid",
    "3x5": "3x5 Grid",
    "4x4": "4x4 Grid",
    "4x5": "4x5 Grid",
    "4x6": "4x6 Grid",
    "4x7": "4x7 Grid",
}

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