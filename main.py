import hydra
import logging
import pandas as pd
from omegaconf import DictConfig
from core_crawler.ccrawl import crawl_puzzles
from page_parser.parse_elements import parse_puzzle, puzzle_components

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

def save_data(result: dict, output_file: str):
    df = pd.read_csv(output_file)
    new_entry = pd.DataFrame([result])
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(output_file, index=False)


@hydra.main(version_base=None, config_path=".", config_name="config")
def main(cfg: DictConfig):
    output = crawl_puzzles(
        grid_size=cfg.grid,
        difficulty=cfg.difficulty,
        count=cfg.count,
        output_file=cfg.output,
        headless=cfg.headless,
        delay=cfg.delay,
        cfg=cfg
    )
    result = parse_puzzle(output['puzzles'][0]) # Parses puzzle
    story, clues, table, options = puzzle_components(output['puzzles'][0]) # Extracts components
    save_data({
        "Grid": cfg.grid,
        "Difficulty": cfg.difficulty,
        "Story": story,
        "Clues": clues,
        "Table": table,
        "Options": options,
        "Puzzle": result
    }, cfg.excel_output)

if __name__ == "__main__":
    main()
