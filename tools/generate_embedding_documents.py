import json
from pathlib import Path
from typing import Any


INPUT_FILE = Path("data/tools_enriched.jsonl")
OUTPUT_FILE = Path("data/tools_embedding_documents.jsonl")


def format_list(value: Any) -> str:
    """Convert a list into a compact comma-separated string."""
    if not isinstance(value, list):
        return ""

    return ", ".join(str(item).strip() for item in value if str(item).strip())


def build_document(tool: dict[str, Any]) -> str:
    """Build the text used for semantic embedding."""
    enrichment = tool.get("enrichment", {})

    sections = [
        f"Tool: {tool.get('name', '')}",
        f"Version: {tool.get('version', '')}",
        f"Purpose: {enrichment.get('purpose', '')}",
        f"Scientific domains: {format_list(enrichment.get('scientific_domains'))}",
        f"Operations: {format_list(enrichment.get('operations'))}",
        f"Input concepts: {format_list(enrichment.get('input_concepts'))}",
        f"Output concepts: {format_list(enrichment.get('output_concepts'))}",
        f"Workflow roles: {format_list(enrichment.get('workflow_roles'))}",
        f"Use cases: {format_list(enrichment.get('use_cases'))}",
        f"Keywords: {format_list(enrichment.get('keywords'))}",
        f"Synonyms: {format_list(enrichment.get('synonyms'))}",
        f"Description: {enrichment.get('enriched_description', '')}",
    ]

    return "\n".join(
        section for section in sections
        if section.split(":", 1)[1].strip()
    )


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    total = 0

    with (
        INPUT_FILE.open("r", encoding="utf-8") as input_file,
        OUTPUT_FILE.open("w", encoding="utf-8") as output_file,
    ):
        for line_number, line in enumerate(input_file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                tool = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {e}"
                ) from e

            if not isinstance(tool, dict):
                raise ValueError(
                    f"Expected JSON object on line {line_number}"
                )

            tool_id = tool.get("tool_id")

            if not tool_id:
                raise ValueError(
                    f"Missing tool_id on line {line_number}"
                )

            document = {
                "tool_id": tool_id,
                "name": tool.get("name", ""),
                "version": tool.get("version", ""),
                "document": build_document(tool),
            }

            output_file.write(
                json.dumps(document, ensure_ascii=False) + "\n"
            )

            total += 1

    print("=" * 60)
    print("Embedding Document Generation")
    print("=" * 60)
    print(f"Input:            {INPUT_FILE}")
    print(f"Output:           {OUTPUT_FILE}")
    print(f"Documents:        {total}")
    print("=" * 60)


if __name__ == "__main__":
    main()