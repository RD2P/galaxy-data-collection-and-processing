import json
from pathlib import Path
from collections import Counter
from typing import Any


INPUT_FILE = Path("data/tools_enriched.jsonl")


REQUIRED_TOP_LEVEL_FIELDS = {
    "tool_id",
    "name",
    "version",
    "description",
}

REQUIRED_ENRICHMENT_FIELDS = {
    "purpose",
    "scientific_domains",
    "operations",
    "input_concepts",
    "output_concepts",
    "workflow_roles",
    "use_cases",
    "keywords",
    "synonyms",
    "enriched_description",
}


def is_empty(value: Any) -> bool:
    """Return True for missing, null, or effectively empty values."""
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, (list, dict)):
        return len(value) == 0

    return False


def validate_tool(tool: dict[str, Any], line_number: int) -> list[str]:
    errors = []

    # Required top-level tool metadata
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in tool:
            errors.append(f"missing field: {field}")
        elif is_empty(tool[field]):
            errors.append(f"empty field: {field}")

    if "tool_id" in tool and not isinstance(tool["tool_id"], str):
        errors.append("tool_id is not a string")

    if "name" in tool and not isinstance(tool["name"], str):
        errors.append("name is not a string")

    if "version" in tool and not isinstance(tool["version"], str):
        errors.append("version is not a string")

    if "description" in tool and not isinstance(tool["description"], str):
        errors.append("description is not a string")

    enrichment = tool.get("enrichment")
    if "enrichment" not in tool:
        errors.append("missing field: enrichment")
    elif not isinstance(enrichment, dict):
        errors.append("enrichment is not an object")
    else:
        for field in REQUIRED_ENRICHMENT_FIELDS:
            if field not in enrichment:
                errors.append(f"missing field: enrichment.{field}")
            elif is_empty(enrichment[field]):
                errors.append(f"empty field: enrichment.{field}")

        if "purpose" in enrichment and not isinstance(enrichment["purpose"], str):
            errors.append("enrichment.purpose is not a string")

        for field in [
            "scientific_domains",
            "operations",
            "input_concepts",
            "output_concepts",
            "workflow_roles",
            "use_cases",
            "keywords",
            "synonyms",
        ]:
            if field in enrichment:
                if not isinstance(enrichment[field], list):
                    errors.append(f"enrichment.{field} is not a list")
                elif any(not isinstance(item, str) for item in enrichment[field]):
                    errors.append(f"enrichment.{field} contains non-string values")

        if "enriched_description" in enrichment and not isinstance(
            enrichment["enriched_description"], str
        ):
            errors.append("enrichment.enriched_description is not a string")

    return errors


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    total = 0
    valid = 0
    invalid = 0
    parse_errors = 0

    error_counts = Counter()
    invalid_tools = []
    ids = set()
    duplicate_ids = []

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            total += 1
            line = line.strip()

            if not line:
                parse_errors += 1
                error_counts["empty line"] += 1
                continue

            try:
                tool = json.loads(line)
            except json.JSONDecodeError as e:
                parse_errors += 1
                error = f"invalid JSON: {e.msg}"
                error_counts[error] += 1
                invalid_tools.append({
                    "line": line_number,
                    "errors": [error],
                })
                continue

            if not isinstance(tool, dict):
                invalid += 1
                error_counts["record is not an object"] += 1
                invalid_tools.append({
                    "line": line_number,
                    "errors": ["record is not an object"],
                })
                continue

            tool_errors = validate_tool(tool, line_number)

            # Duplicate ID check
            tool_id = tool.get("tool_id")
            if tool_id:
                if tool_id in ids:
                    duplicate_ids.append({
                        "line": line_number,
                        "id": tool_id,
                    })
                    tool_errors.append("duplicate tool_id")
                else:
                    ids.add(tool_id)

            if tool_errors:
                invalid += 1

                for error in tool_errors:
                    error_counts[error] += 1

                invalid_tools.append({
                    "line": line_number,
                    "id": tool.get("tool_id"),
                    "name": tool.get("name"),
                    "errors": tool_errors,
                })
            else:
                valid += 1

    print("=" * 60)
    print("Galaxy Tool Enrichment Validation")
    print("=" * 60)

    print(f"Input file:       {INPUT_FILE}")
    print(f"Total records:    {total}")
    print(f"Valid records:    {valid}")
    print(f"Invalid records:  {invalid}")
    print(f"Parse errors:     {parse_errors}")
    print(f"Unique IDs:       {len(ids)}")
    print(f"Duplicate IDs:    {len(duplicate_ids)}")

    print("\nError summary:")

    if not error_counts:
        print("  None")
    else:
        for error, count in error_counts.most_common():
            print(f"  {count:5d}  {error}")

    if invalid_tools:
        print("\nInvalid records:")

        for item in invalid_tools[:20]:
            print(f"\n  Line {item['line']}")
            print(f"  ID:   {item.get('id')}")
            print(f"  Name: {item.get('name')}")

            for error in item["errors"]:
                print(f"    - {error}")

        if len(invalid_tools) > 20:
            print(
                f"\n  ... {len(invalid_tools) - 20} additional invalid records"
            )

    print("\n" + "=" * 60)

    if invalid == 0 and parse_errors == 0 and not duplicate_ids:
        print("VALIDATION PASSED")
    else:
        print("VALIDATION FAILED")


if __name__ == "__main__":
    main()