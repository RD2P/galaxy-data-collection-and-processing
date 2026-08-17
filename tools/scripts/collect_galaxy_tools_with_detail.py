from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

BASE_URL = "https://usegalaxy.org"
INPUT_FILE = Path("ids.txt")
OUTPUT_FILE = Path("tools_with_detail.jsonl")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def load_tool_ids(path: Path) -> list[str]:
	if not path.exists():
		alternate = Path("idx.txt")
		if alternate.exists():
			path = alternate
		else:
			raise FileNotFoundError(f"Could not find {path} or {alternate}")

	return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fetch_tool_details(session: requests.Session, tool_id: str) -> dict:
	url = f"{BASE_URL}/api/tools/{tool_id}"
	response = session.get(
		url,
		params={"io_details": "true", "link_details": "true"},
		timeout=30,
	)
	response.raise_for_status()
	return response.json()


def main() -> None:
	tool_ids = load_tool_ids(INPUT_FILE)
	total_ids = len(tool_ids)
	success_count = 0
	error_count = 0
	LOGGER.info("Loaded %s tool ids", total_ids)
	LOGGER.info("Writing results to %s", OUTPUT_FILE)
	with requests.Session() as session, OUTPUT_FILE.open("a", encoding="utf-8") as output_handle:
		for index, tool_id in enumerate(tool_ids):
			current = index + 1
			LOGGER.info("Fetching %s/%s: %s", current, total_ids, tool_id)
			try:
				details = fetch_tool_details(session, tool_id)
				record = {"tool_id": tool_id, "details": details}
				success_count += 1
				LOGGER.info("Completed %s/%s: %s success=%s error=%s", current, total_ids, tool_id, success_count, error_count)
			except requests.RequestException as exc:
				record = {"tool_id": tool_id, "error": str(exc)}
				error_count += 1
				LOGGER.warning("Failed %s/%s: %s success=%s error=%s", current, total_ids, tool_id, success_count, error_count)

			output_handle.write(json.dumps(record, ensure_ascii=False))
			output_handle.write("\n")
			output_handle.flush()

			if index < len(tool_ids) - 1:
				time.sleep(0.25)

	LOGGER.info("Done. total=%s success=%s error=%s", total_ids, success_count, error_count)


if __name__ == "__main__":
	main()

