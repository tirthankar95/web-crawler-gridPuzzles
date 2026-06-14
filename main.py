import logging
import hydra
from omegaconf import DictConfig
from core_crawler.ccrawl import crawl_puzzles

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path=".", config_name="config")
def main(cfg: DictConfig):
    crawl_puzzles(
        grid_size=cfg.grid,
        difficulty=cfg.difficulty,
        count=cfg.count,
        output_file=cfg.output,
        headless=cfg.headless,
        delay=cfg.delay,
        cfg=cfg
    )


if __name__ == "__main__":
    main()
