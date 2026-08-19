"""
    Structure Galaxy WorkflowHub workflow JSONL for embedding.

    Input:
        workflows/data/galaxy_workflows.jsonl

    Output:
        workflows/data/workflows_structured.jsonl

    Each output line contains:
    {
        "id": "...",
        "title": "...",
        "embedding_text": "...",
        "metadata": {...},
        "inputs": [...],
        "outputs": [...],
        "steps": [...],
        "connections": [...]
    }
"""

import json
import re
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUT_FILE = DATA_DIR / "galaxy_workflows.jsonl"
OUTPUT_FILE = DATA_DIR / "workflows_structured.jsonl"


# ------------------------------------------------------------
# General utilities
# ------------------------------------------------------------

def clean_text(value):
    """Normalize whitespace in text."""
    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_tool_id(description):
    """Extract Galaxy ToolShed identifier from a step description."""

    if not description:
        return None

    match = re.search(
        r"toolshed\.[^\s]+",
        description,
    )

    if not match:
        return None

    return match.group(0).rstrip(".,;")


# ------------------------------------------------------------
# Inputs
# ------------------------------------------------------------

def structure_inputs(inputs):
    structured = []

    for inp in inputs:
        structured.append({
            "name": clean_text(inp.get("name")),
            "description": clean_text(inp.get("description")),
            "type": [
                clean_text(t.get("type"))
                if isinstance(t, dict)
                else clean_text(t)
                for t in (inp.get("type") or [])
            ],
        })

    return structured


# ------------------------------------------------------------
# Outputs
# ------------------------------------------------------------

def structure_outputs(outputs):
    structured = []

    for output in outputs:
        structured.append({
            "name": clean_text(output.get("name")),
            "description": clean_text(output.get("description")),
            "type": [
                clean_text(t.get("type"))
                if isinstance(t, dict)
                else clean_text(t)
                for t in (output.get("type") or [])
            ],
            "source_ids": [
                clean_text(source)
                for source in (output.get("source_ids") or [])
            ],
        })

    return structured


# ------------------------------------------------------------
# Steps
# ------------------------------------------------------------

def structure_steps(steps):
    structured = []

    for step in steps:
        name = clean_text(step.get("name"))
        description = clean_text(step.get("description"))

        tool_id = extract_tool_id(description)

        structured.append({
            "id": str(step.get("id")),
            "name": name,
            "description": description,
            "tool_id": tool_id,
        })

    return structured


# ------------------------------------------------------------
# Connections
# ------------------------------------------------------------

def structure_connections(links):
    structured = []

    for link in links:
        source = clean_text(link.get("source_id"))
        destination = clean_text(link.get("sink_id"))

        if not source or not destination:
            continue

        structured.append({
            "source": source,
            "destination": destination,
        })

    return structured


# ------------------------------------------------------------
# Major operations
# ------------------------------------------------------------

def select_major_operations(steps):
    """
    Remove generic Galaxy/data-manipulation operations from the
    semantic description.

    They remain available in the structured `steps` field.
    """

    generic_operations = {
        "paste",
        "cut",
        "extract",
        "compute",
        "text transformation",
        "show image info",
        "width extraction",
        "height extraction",
        "header extraction",
        "extract element identifiers",
        "collapse collection",
        "collapse collection into one file",
        "concatenate datasets",
        "sample id",
        "header for total area",
    }

    operations = []

    for step in steps:
        name = step["name"]

        if name.lower() in generic_operations:
            continue

        operation = {
            "name": name,
            "description": step["description"],
        }

        if step["tool_id"]:
            operation["tool_id"] = step["tool_id"]

        operations.append(operation)

    return operations


# ------------------------------------------------------------
# Simplified workflow graph
# ------------------------------------------------------------

def build_graph_description(steps, connections):
    """
    Convert low-level Galaxy connections into a simplified
    human-readable graph.

    Example:

        Input Image -> Color Deconvolution
        Color Deconvolution -> Split Image Channels
        Split Image Channels -> Extract Stain Channel
    """

    step_names = {
        step["id"]: step["name"]
        for step in steps
    }

    edges = []
    seen = set()

    for connection in connections:
        source = connection["source"]
        destination = connection["destination"]

        source_step = source.split("/")[0]
        destination_step = destination.split("/")[0]

        source_name = step_names.get(source_step, source_step)
        destination_name = step_names.get(
            destination_step,
            destination_step,
        )

        edge = (source_name, destination_name)

        if edge in seen:
            continue

        seen.add(edge)
        edges.append(edge)

    return [
        {
            "source": source,
            "destination": destination,
        }
        for source, destination in edges
    ]


# ------------------------------------------------------------
# Embedding representation
# ------------------------------------------------------------

def build_embedding_text(
    title,
    description,
    workflow_class,
    inputs,
    outputs,
    operations,
    graph,
):
    """
    Construct only the information that should influence
    semantic similarity.
    """

    sections = []

    if title:
        sections.append(
            f"Workflow: {title}"
        )

    if description:
        sections.append(
            f"Purpose: {description}"
        )

    if workflow_class:
        sections.append(
            f"Platform: {workflow_class}"
        )

    if inputs:
        input_lines = []

        for inp in inputs:
            line = inp["name"]

            if inp["description"]:
                line += f": {inp['description']}"

            if inp["type"]:
                line += f" (type: {', '.join(inp['type'])})"

            input_lines.append(f"- {line}")

        sections.append(
            "Inputs:\n" +
            "\n".join(input_lines)
        )

    if operations:
        operation_lines = []

        for operation in operations:
            line = operation["name"]

            if operation["description"]:
                line += f": {operation['description']}"

            operation_lines.append(f"- {line}")

        sections.append(
            "Major scientific operations:\n" +
            "\n".join(operation_lines)
        )

    if graph:
        graph_lines = [
            f"- {edge['source']} -> {edge['destination']}"
            for edge in graph
        ]

        sections.append(
            "Workflow structure:\n" +
            "\n".join(graph_lines)
        )

    if outputs:
        output_lines = []

        for output in outputs:
            line = output["name"]

            if output["description"]:
                line += f": {output['description']}"

            output_lines.append(f"- {line}")

        sections.append(
            "Outputs:\n" +
            "\n".join(output_lines)
        )

    return "\n\n".join(sections)


# ------------------------------------------------------------
# Workflow
# ------------------------------------------------------------

def structure_workflow(workflow):
    data = workflow.get("data", {})
    attributes = data.get("attributes", {})
    internals = attributes.get("internals", {})

    workflow_id = clean_text(data.get("id"))
    title = clean_text(attributes.get("title"))
    description = clean_text(attributes.get("description"))

    workflow_class = attributes.get("workflow_class") or {}
    workflow_class = clean_text(
        workflow_class.get("title")
    )

    inputs = structure_inputs(
        internals.get("inputs") or []
    )

    outputs = structure_outputs(
        internals.get("outputs") or []
    )

    steps = structure_steps(
        internals.get("steps") or []
    )

    connections = structure_connections(
        internals.get("links") or []
    )

    operations = select_major_operations(steps)

    graph = build_graph_description(
        steps,
        connections,
    )

    embedding_text = build_embedding_text(
        title=title,
        description=description,
        workflow_class=workflow_class,
        inputs=inputs,
        outputs=outputs,
        operations=operations,
        graph=graph,
    )

    return {
        "id": workflow_id,
        "title": title,

        "embedding_text": embedding_text,

        "metadata": {
            "platform": workflow_class,
            "version": attributes.get("version"),
            "latest_version": attributes.get("latest_version"),
            "license": clean_text(attributes.get("license")),
            "tags": attributes.get("tags") or [],
            "description": description,
            "workflow_url": (
                attributes.get("links", {}).get("self")
                if isinstance(attributes.get("links"), dict)
                else None
            ),
        },

        "inputs": inputs,
        "outputs": outputs,

        # Full structured workflow information.
        "steps": steps,
        "connections": connections,

        # Reduced representation for semantic retrieval.
        "major_operations": operations,
        "graph": graph,
    }


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    count = 0

    with (
        input_path.open("r", encoding="utf-8") as infile,
        output_path.open("w", encoding="utf-8") as outfile,
    ):
        for line in infile:
            line = line.strip()

            if not line:
                continue

            workflow = json.loads(line)

            structured = structure_workflow(workflow)

            if not structured["id"]:
                continue

            outfile.write(
                json.dumps(
                    structured,
                    ensure_ascii=False,
                )
                + "\n"
            )

            count += 1

    print(f"Processed {count} workflows.")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()