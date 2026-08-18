"""Find the preprocessed tool record with the largest payload and print it."""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = BASE_DIR / "data" / "tools_preprocessed.jsonl"


def format_size(size_bytes: int) -> str:
    """Convert bytes to a human-readable size string."""
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size_bytes)
    unit_index = 0

    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    return f"{value:.2f} {units[unit_index]}"


def json_size_bytes(obj: object) -> int:
    """Return the byte length of the JSON-encoded object."""
    return len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def main() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Could not find input file: {DATA_FILE}")

    largest_tool = None
    largest_size = -1
    largest_line_number = 0

    with DATA_FILE.open("r", encoding="utf-8") as infile:
        for line_number, line in enumerate(infile, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                tool = json.loads(stripped)
            except json.JSONDecodeError as exc:
                print(f"Skipping invalid JSON on line {line_number}: {exc}")
                continue

            size = json_size_bytes(tool)
            if size > largest_size:
                largest_tool = tool
                largest_size = size
                largest_line_number = line_number

    if largest_tool is None:
        raise ValueError(f"No valid tool records were found in {DATA_FILE}")

    tool_name = largest_tool.get("name") or largest_tool.get("tool_id") or "unknown tool"
    tool_id = largest_tool.get("tool_id") or "unknown id"

    print(f"Largest tool: {tool_name} ({tool_id})")
    print(f"Data size: {format_size(largest_size)}")
    print(f"Source line: {largest_line_number}")

if __name__ == "__main__":
    main()
