# Logic Puzzle Baron Crawler

A Python web crawler that automates collecting grid logic puzzles from [logic.puzzlebaron.com](https://logic.puzzlebaron.com/init.php) using **Playwright** (a headless browser).

---

## Setup

**1. Install dependencies**

```bash
pip install playwright beautifulsoup4
python -m playwright install chromium
```

---

## Usage

```bash
python puzzle_crawler.py [options]
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--grid` | `4x4` | Grid size: `3x4`, `3x5`, `4x4`, `4x5`, `4x6`, `4x7` |
| `--difficulty` | `Easy` | Difficulty: `Easy`, `Moderate`, `Challenging` |
| `--count` | `5` | Number of puzzles to collect |
| `--output` | `puzzles.json` | Output JSON file path |
| `--headless` | `true` | `false` to watch the browser in action |
| `--delay` | `2.0` | Seconds to pause between requests |

### Examples

```bash
# Collect 5 Easy 4x4 puzzles (default)
python puzzle_crawler.py

# Collect 10 Challenging 4x6 puzzles
python puzzle_crawler.py --grid 4x6 --difficulty Challenging --count 10

# Watch the browser work (non-headless)
python puzzle_crawler.py --count 3 --headless false

# Save to a custom file
python puzzle_crawler.py --count 20 --output my_puzzles.json
```

---

## What the Crawler Does

```
init.php (selection page)
   │
   ├─ Selects Grid Size radio button    (e.g. "4x4 Grid")
   ├─ Selects Difficulty radio button   (e.g. "Easy")
   └─ Clicks "Create Puzzle" button
            │
            ▼
   Intermediate page (puzzle preview)
   └─ Clicks "Start Puzzle" button
            │
            ▼
   Puzzle page  ──► HTML parsed ──► JSON saved
```

---

## Output Format

The output `puzzles.json` has this structure:

```json
{
  "meta": {
    "grid_size": "4x4",
    "difficulty": "Easy",
    "requested": 5,
    "collected": 5,
    "errors": 0,
    "generated_at": "2026-06-14T10:00:00Z"
  },
  "errors": [],
  "puzzles": [
    {
      "index": 1,
      "url": "https://logic.puzzlebaron.com/play.php?...",
      "title": "Logic Puzzle #12345",
      "id": 12345,
      "grid_size": "4x4",
      "difficulty": "Easy",
      "collected_at": "2026-06-14T10:00:01Z",
      "intro": "Four friends each ordered a different meal...",
      "clues": [
        "The person who ordered pasta is not Alice.",
        "Bob sat directly next to the person who ordered soup.",
        ...
      ],
      "grid_cells_sample": ["Names", "Alice", "Bob", "Carol", "Dan", ...],
      "grid_html": "<table>...</table>",
      "page_text_excerpt": "..."
    },
    ...
  ]
}
```

---

## Notes

- **Be polite**: the default 2-second delay between requests avoids hammering the server. Don't set it below 1 second.
- **No login required**: the site allows anonymous puzzle access.
- **Headless mode**: set `--headless false` to visually debug if puzzles aren't being collected correctly.
- **Site changes**: if the crawler stops working, the site's HTML structure may have changed. Open `--headless false` to inspect what's on screen at each step.