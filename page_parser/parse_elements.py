from tabulate import tabulate
import re

def extract(grid_data) -> str:
    result, _iter = [], 0
    for k, v in grid_data.items():
        if len(v) > 0:
            dim = []
            for x in v:
                if x:
                    dim.append(x.strip())
            _iter += 1
            if dim:
                result.append(f'Category {_iter}: ' + ", ".join(dim))
    return "\n".join(result)


def puzzle_components(result: dict):
    clues = ""
    story = result.get("story", "")
    for clue in result["clues"]:
        clues += clue['text'] + "\n"
    matrix = result.get("answer_grid", "")
    table = tabulate(matrix[1:], headers=matrix[0], tablefmt="grid")
    options = extract(result.get("all_options", []))
    return story, clues.strip(), table, options


def parse_puzzle(result: dict):
    story, clues, table, options = puzzle_components(result)
    puzzle = f"""\nStory:\n{story}\n\nClues:\n{clues}\n\nSolve the grid puzzle by filling the table:\n{table}\n\nUse the clues to fill the table with the following categories:\n{options}"""
    print(puzzle)
    return puzzle

