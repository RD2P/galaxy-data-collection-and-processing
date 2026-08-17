from __future__ import annotations

import json
from pathlib import Path

INPUT_FILE = Path("tools_with_detail.jsonl")
OUTPUT_FILE = Path("tools_with_detail.json")


def main() -> None:
    first_record = True

    with INPUT_FILE.open("r", encoding="utf-8") as input_handle, OUTPUT_FILE.open("w", encoding="utf-8") as output_handle:
        output_handle.write("[")

        for line_number, line in enumerate(input_handle, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc

            if first_record:
                first_record = False
            else:
                output_handle.write(",")

            output_handle.write("\n")
            json.dump(record, output_handle, ensure_ascii=False)

        if not first_record:
            output_handle.write("\n")
        output_handle.write("]\n")


if __name__ == "__main__":
    main()