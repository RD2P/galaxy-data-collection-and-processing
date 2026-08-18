import json
from typing import Any


# Hard limits to prevent unusually large tools from dominating the LLM context.
MAX_DESCRIPTION_CHARS = 3000
MAX_HELP_CHARS = 5000
MAX_PARAMETER_HELP_CHARS = 800

MAX_OPTIONS = 30
MAX_OPTION_CHARS = 300

MAX_REQUIREMENTS = 30
MAX_CITATIONS = 10
MAX_XREFS_PER_TYPE = 20


def clean(value: Any) -> Any:
    """Recursively remove null and empty values."""

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
        return {
            k: v
            for k, v in cleaned.items()
            if v is not None
        }

    return value


def truncate(value: Any, max_chars: int) -> str | None:
    """Return a bounded string."""

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    if len(value) <= max_chars:
        return value

    return value[:max_chars].rstrip() + "..."


def extract_input(
    parameter: dict[str, Any],
    condition: str | None = None,
) -> list[dict[str, Any]]:
    """
    Extract semantic information from a Galaxy input.

    Conditional parameters are recursively flattened.
    Structural Galaxy parameters are ignored.
    """

    model_class = parameter.get("model_class")

    # Flatten Conditional inputs.
    if model_class == "Conditional":
        results = []

        name = parameter.get("name")

        for case in parameter.get("cases", []):
            if not isinstance(case, dict):
                continue

            case_value = case.get("value")

            if name and case_value is not None:
                nested_condition = f"{name}={case_value}"
            else:
                nested_condition = condition

            for nested_input in case.get("inputs", []):
                if isinstance(nested_input, dict):
                    results.extend(
                        extract_input(
                            nested_input,
                            nested_condition,
                        )
                    )

        return results

    # These are structural rather than semantic.
    if model_class in {
        "Section",
        "Repeat",
        "ConditionalWhen",
    }:
        return []

    result = {
        "name": parameter.get("name"),
        "label": truncate(
            parameter.get("label"),
            500,
        ),
        "type": parameter.get("type"),
        "help": truncate(
            parameter.get("help"),
            MAX_PARAMETER_HELP_CHARS,
        ),
        "optional": parameter.get("optional"),
        "extensions": parameter.get("extensions"),
        "edam": parameter.get("edam"),
        "condition": condition,
    }

    # Select/radio options.
    options = parameter.get("options")

    if isinstance(options, list) and options:
        extracted_options = []

        for option in options[:MAX_OPTIONS]:
            if not isinstance(option, list):
                continue

            if len(option) < 2:
                continue

            value = option[0]
            label = option[1]

            item = {
                "value": truncate(value, MAX_OPTION_CHARS),
                "label": truncate(label, MAX_OPTION_CHARS),
            }

            item = clean(item)

            if item:
                extracted_options.append(item)

        if extracted_options:
            result["options"] = extracted_options

    return [clean(result)]


def extract_inputs(details: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract semantic input information."""

    inputs = []

    for parameter in details.get("inputs", []):
        if isinstance(parameter, dict):
            inputs.extend(extract_input(parameter))

    return inputs


def extract_output(output: dict[str, Any]) -> dict[str, Any]:
    """Extract semantic output information."""

    result = {
        "name": output.get("name"),
        "label": truncate(
            output.get("label"),
            500,
        ),
        "type": output.get("output_type"),
        "format": output.get("format"),
        "default_format": output.get("default_format"),
        "edam_format": output.get("edam_format"),
        "edam_data": output.get("edam_data"),
    }

    # Extract discovered dataset formats without retaining
    # the complete dataset-discovery configuration.
    structure = output.get("structure")

    if isinstance(structure, dict):
        formats = []

        for dataset in structure.get("discover_datasets", []):
            if not isinstance(dataset, dict):
                continue

            fmt = dataset.get("format")

            if fmt and fmt not in formats:
                formats.append(fmt)

        if formats:
            result["discovered_formats"] = formats

    return clean(result)


def extract_outputs(details: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract semantic output information."""

    outputs = []

    for output in details.get("outputs", []):
        if isinstance(output, dict):
            outputs.append(extract_output(output))

    return outputs


def extract_requirements(details: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract software dependencies.

    Only the dependency identity is retained.
    """

    requirements = []

    for requirement in details.get("requirements", [])[:MAX_REQUIREMENTS]:
        if not isinstance(requirement, dict):
            continue

        result = {
            "name": requirement.get("name"),
            "version": requirement.get("version"),
        }

        result = clean(result)

        if result:
            requirements.append(result)

    return requirements


def extract_citations(details: dict[str, Any]) -> list[str]:
    """Extract a bounded list of citation identifiers/text."""

    citations = []

    for citation in details.get("citations", [])[:MAX_CITATIONS]:
        if isinstance(citation, str):
            value = citation.strip()

        elif isinstance(citation, dict):
            value = None

            for key in (
                "doi",
                "pmid",
                "citation",
                "text",
                "value",
            ):
                candidate = citation.get(key)

                if candidate:
                    value = str(candidate).strip()
                    break
        else:
            continue

        if value:
            citations.append(value)

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(citations))


def extract_xrefs(details: dict[str, Any]) -> dict[str, list[str]]:
    """Extract bounded external references."""

    xrefs: dict[str, list[str]] = {}

    for xref in details.get("xrefs", []):
        if not isinstance(xref, dict):
            continue

        xref_type = xref.get("type")
        value = xref.get("value")

        if not xref_type or not value:
            continue

        values = xrefs.setdefault(xref_type, [])

        if len(values) < MAX_XREFS_PER_TYPE:
            values.append(str(value))

    return xrefs


def preprocess_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a raw Galaxy tool record into a compact representation
    suitable for scientific metadata enrichment.

    No raw Galaxy XML, command templates, validators, test data,
    UI configuration, or other execution-specific structures are
    retained.
    """

    details = tool.get("details", {})

    if not isinstance(details, dict):
        details = {}

    tool_id = (
        tool.get("tool_id")
        or details.get("tool_id")
        or details.get("id")
    )

    result = {
        # Identity
        "tool_id": tool_id,
        "name": details.get("name"),
        "version": details.get("version"),

        # Scientific description
        "description": truncate(
            details.get("description"),
            MAX_DESCRIPTION_CHARS,
        ),
        "help": truncate(
            details.get("help"),
            MAX_HELP_CHARS,
        ),

        # Ontology metadata
        "edam_operations": details.get("edam_operations"),
        "edam_topics": details.get("edam_topics"),

        # External references
        "xrefs": extract_xrefs(details),
        "citations": extract_citations(details),

        # Interface semantics
        "inputs": extract_inputs(details),
        "outputs": extract_outputs(details),

        # Software context
        "requirements": extract_requirements(details),
    }

    return clean(result)


def process_jsonl(
    input_path: str,
    output_path: str,
) -> None:
    """Process Galaxy tools JSONL into compact enrichment JSONL."""

    processed = 0
    failed = 0

    with (
        open(input_path, "r", encoding="utf-8") as infile,
        open(output_path, "w", encoding="utf-8") as outfile,
    ):
        for line_number, line in enumerate(infile, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                tool = json.loads(line)

                processed_tool = preprocess_tool(tool)

                outfile.write(
                    json.dumps(
                        processed_tool,
                        ensure_ascii=False,
                        separators=(",", ":"),
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