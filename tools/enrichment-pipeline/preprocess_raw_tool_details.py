import json
from typing import Any


def clean(value: Any) -> Any:
    """Remove empty/null values recursively."""
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    if isinstance(value, list):
        cleaned = [clean(v) for v in value]
        return [v for v in cleaned if v is not None]

    if isinstance(value, dict):
        cleaned = {k: clean(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v is not None}

    return value


def extract_input(parameter: dict[str, Any], condition: str | None = None) -> list[dict]:
    """
    Extract useful semantic information from a Galaxy input parameter.

    Handles normal inputs and nested Conditional parameters.
    """

    model_class = parameter.get("model_class")

    # Conditional input
    if model_class == "Conditional":
        results = []

        for case in parameter.get("cases", []):
            case_value = case.get("value")

            for nested_input in case.get("inputs", []):
                results.extend(
                    extract_input(
                        nested_input,
                        condition=f"{parameter.get('name')}={case_value}",
                    )
                )

        return results

    # Ignore non-useful parameter types
    if model_class in {
        "Section",
        "Repeat",
        "ConditionalWhen",
    }:
        return []

    result = {
        "name": parameter.get("name"),
        "label": parameter.get("label"),
        "type": parameter.get("type"),
        "help": parameter.get("help"),
        "optional": parameter.get("optional"),
        "extensions": parameter.get("extensions"),
        "edam": parameter.get("edam"),
        "condition": condition,
    }

    # Extract select/radio options
    options = parameter.get("options")

    if options:
        extracted_options = []

        for option in options:
            if isinstance(option, list) and len(option) >= 2:
                extracted_options.append(option[0])

        if extracted_options:
            result["options"] = extracted_options

    return [clean(result)]


def extract_inputs(details: dict[str, Any]) -> list[dict]:
    """Extract all useful input information."""
    inputs = []

    for parameter in details.get("inputs", []):
        inputs.extend(extract_input(parameter))

    return inputs


def extract_output(output: dict[str, Any]) -> dict:
    """Extract useful semantic information from a Galaxy output."""

    result = {
        "name": output.get("name"),
        "label": output.get("label"),
        "type": output.get("output_type"),
        "format": output.get("format"),
        "default_format": output.get("default_format"),
        "edam_format": output.get("edam_format"),
        "edam_data": output.get("edam_data"),
    }

    # ToolOutputCollection may specify formats through
    # dataset discovery rules.
    structure = output.get("structure", {})

    discovered_formats = []

    for dataset in structure.get("discover_datasets", []):
        fmt = dataset.get("format")

        if fmt and fmt not in discovered_formats:
            discovered_formats.append(fmt)

    if discovered_formats:
        result["discovered_formats"] = discovered_formats

    return clean(result)


def extract_outputs(details: dict[str, Any]) -> list[dict]:
    """Extract all useful output information."""

    return [
        extract_output(output)
        for output in details.get("outputs", [])
    ]


def preprocess_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a raw Galaxy tool record into a compact representation
    suitable for LLM enrichment.
    """

    details = tool.get("details", {})

    tool_id = tool.get("tool_id") or details.get("tool_id") or details.get("id")

    result = {
        "tool_id": tool_id,

        "name": details.get("name"),

        "version": details.get("version"),

        "description": details.get("description"),

        "panel_section": details.get("panel_section_name"),

        "workflow_compatible": details.get("is_workflow_compatible"),

        "edam_operations": details.get("edam_operations"),

        "edam_topics": details.get("edam_topics"),

        "bio_tools": [
            x.get("value")
            for x in details.get("xrefs", [])
            if x.get("type") == "bio.tools"
        ],

        "inputs": extract_inputs(details),

        "outputs": extract_outputs(details),
    }

    return clean(result)


def process_jsonl(input_path: str, output_path: str) -> None:
    """
    Process a JSONL file containing Galaxy tools.
    """

    processed = 0
    failed = 0

    with open(input_path,"r", encoding="utf-8") as infile, \
         open(output_path, "w", encoding="utf-8") as outfile:

        for line_number, line in enumerate(infile, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                tool = json.loads(line)

                enriched_input = preprocess_tool(tool)

                outfile.write(
                    json.dumps(
                        enriched_input,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

                processed += 1

            except Exception as e:
                failed += 1

                print(
                    f"Failed to process line {line_number}: {e}"
                )

    print(f"Processed: {processed}")
    print(f"Failed:    {failed}")
    print(f"Output:    {output_path}")


if __name__ == "__main__":
    process_jsonl(
        input_path="../tools_with_detail.jsonl",
        output_path="data/tools_preprocessed.jsonl",
    )