"""
    Structure Galaxy WorkflowHub workflow JSONL for embedding.

    Input:
        data/galaxy_workflows.jsonl

    Output:
        data/workflows_structured.jsonl

    Each output line contains:

    {
        "id": "...",
        "title": "...",
        "embedding_text": "...",
        "metadata": {...},
        "inputs": [...],
        "outputs": [...],
        "steps": [...],
        "connections": [...],
        "major_operations": [...],
        "graph": [...]
    }

    The embedding_text is the semantic representation used by the
    sentence-transformer model.

    The remaining fields preserve structured workflow information
    for use after retrieval.
"""

import json
import re
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

INPUT_FILE = DATA_DIR / "galaxy_workflows.jsonl"
OUTPUT_FILE = DATA_DIR / "workflows_structured.jsonl"


# ============================================================
# GENERAL UTILITIES
# ============================================================

def clean_text(value):
    """Normalize whitespace in text."""

    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def clean_description(value):
    """Keep the workflow purpose while removing catalog boilerplate."""

    description = clean_text(value)

    if not description:
        return ""

    description = re.split(
        r"\s+##\s+(?:Associated Tutorial|Features)|"
        r"\s+\*\*Workflow Author\(s\):",
        description,
        maxsplit=1,
    )[0]

    description = re.sub(r"!\[[^]]*\]\([^)]*\)", "", description)
    description = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", description)
    description = re.sub(r"https?://\S+", "", description)

    return clean_text(description)


def format_type(value):
    """Convert nested Galaxy type definitions into readable text."""

    if isinstance(value, dict):
        type_name = clean_text(value.get("type"))
        items = value.get("items")

        if items:
            item_types = ", ".join(
                format_type(item)
                for item in items
            )
            return f"{type_name}<{item_types}>" if type_name else item_types

        return type_name

    return clean_text(value)


def extract_tool_id(description):
    """
    Extract a Galaxy ToolShed identifier from a step description.

    Example:
        toolshed.g2.bx.psu.org/repos/.../tool/1.0

    Returns:
        Tool ID or None.
    """

    if not description:
        return None

    match = re.search(
        r"toolshed\.[^\s]+",
        description,
    )

    if not match:
        return None

    return match.group(0).rstrip(".,;")


def remove_tool_id(description):
    """
    Remove embedded ToolShed identifiers from descriptions.

    Tool IDs are retained separately in structured step data.
    """

    if not description:
        return ""

    description = re.sub(
        r"toolshed\.[^\s]+",
        "",
        description,
    )

    return clean_text(description)


# ============================================================
# INPUTS
# ============================================================

def structure_inputs(inputs):
    structured = []

    for inp in inputs:
        structured.append(
            {
                "name": clean_text(inp.get("name")),
                "description": clean_text(
                    inp.get("description")
                ),
                "type": [
                    format_type(t)
                    for t in (inp.get("type") or [])
                ],
            }
        )

    return structured


# ============================================================
# OUTPUTS
# ============================================================

def structure_outputs(outputs):
    structured = []

    for output in outputs:
        structured.append(
            {
                "name": clean_text(output.get("name")),
                "description": clean_text(
                    output.get("description")
                ),
                "type": [
                    format_type(t)
                    for t in (output.get("type") or [])
                ],
                "source_ids": [
                    clean_text(source)
                    for source in (
                        output.get("source_ids") or []
                    )
                ],
            }
        )

    return structured


# ============================================================
# STEPS
# ============================================================

def structure_steps(steps):
    structured = []

    for step in steps:
        name = clean_text(step.get("name"))
        description = clean_text(
            step.get("description")
        )

        tool_id = extract_tool_id(description)

        # Remove ToolShed ID from the semantic description.
        semantic_description = remove_tool_id(
            description
        )

        structured.append(
            {
                "id": str(step.get("id")),
                "name": name,
                "description": description,
                "semantic_description": semantic_description,
                "tool_id": tool_id,
            }
        )

    return structured


# ============================================================
# CONNECTIONS
# ============================================================

def structure_connections(links):
    structured = []

    for link in links:
        source = clean_text(
            link.get("source_id")
        )

        destination = clean_text(
            link.get("sink_id")
        )

        if not source or not destination:
            continue

        structured.append(
            {
                "source": source,
                "destination": destination,
            }
        )

    return structured


# ============================================================
# MAJOR OPERATIONS
# ============================================================

GENERIC_OPERATIONS = {
    "paste",
    "cut",
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


def is_generic_operation(step):
    """
    Determine whether a step is primarily a generic
    Galaxy/data-manipulation operation.

    These steps remain in the structured workflow but are
    excluded from the semantic operation summary.
    """

    name = step["name"].lower()

    if name in GENERIC_OPERATIONS:
        return True

    description = step["semantic_description"].lower()

    generic_descriptions = {
        "grep1",
        "paste1",
        "cut1",
        "show tail1",
        "show beginning1",
        "cat1",
    }

    if description in generic_descriptions:
        return True

    return False


def select_major_operations(steps):
    """
    Select scientifically meaningful workflow operations.

    Full step information remains in `steps`.
    """

    operations = []

    for step in steps:

        if is_generic_operation(step):
            continue

        operation = {
            "name": step["name"],
        }

        if step["semantic_description"]:
            operation["description"] = (
                step["semantic_description"]
            )

        if step["tool_id"]:
            operation["tool_id"] = step["tool_id"]

        operations.append(operation)

    return operations


# ============================================================
# WORKFLOW GRAPH
# ============================================================

def build_graph(steps, connections, inputs):
    """
    Convert Galaxy's low-level connection representation
    into a simplified workflow graph.

    Galaxy connections may look like:

        "Color Deconvolution"
        "Split Image Channels for Staining Detection"

    or:

        "3/out_file1"
        "5/input"

    Only the step identifiers are used to construct the
    simplified graph.

    Returns:
        [
            {
                "source": "Color Deconvolution",
                "destination": "Split Image Channels..."
            }
        ]
    """

    step_names = {
        step["id"]: step["name"]
        for step in steps
    }
    step_ids = set(step_names)
    input_names = {
        input_data["name"]
        for input_data in inputs
        if input_data["name"]
    }

    def resolve_endpoint(endpoint):
        endpoint = endpoint.strip()

        if endpoint in step_names:
            return step_names[endpoint]

        name_matches = [
            step_name
            for step_name in step_names.values()
            if (
                endpoint == step_name
                or endpoint.endswith(f"/{step_name}")
                or endpoint.startswith(f"{step_name}/")
            )
        ]

        if name_matches:
            return max(name_matches, key=len)

        for part in endpoint.split("/"):
            if part in step_ids:
                return step_names[part]

        for input_name in input_names:
            if endpoint == input_name or endpoint.endswith(f"/{input_name}"):
                return input_name

        return endpoint.removeprefix("#main/")

    edges = []
    seen = set()

    for connection in connections:

        source = connection["source"]
        destination = connection["destination"]

        source_name = resolve_endpoint(source)
        destination_name = resolve_endpoint(destination)

        edge = (
            source_name,
            destination_name,
        )

        if edge in seen:
            continue

        seen.add(edge)

        edges.append(
            {
                "source": source_name,
                "destination": destination_name,
            }
        )

    return edges


def build_semantic_graph(graph):
    """
    Remove obvious low-level Galaxy/data-manipulation nodes
    from the graph used for embedding.

    The full graph remains available in `graph`.
    """

    generic_names = {
        name.lower()
        for name in GENERIC_OPERATIONS
    }

    semantic_graph = []

    for edge in graph:

        source = edge["source"]
        destination = edge["destination"]

        source_generic = (
            source.lower() in generic_names
        )

        destination_generic = (
            destination.lower() in generic_names
        )

        if source_generic or destination_generic:
            continue

        semantic_graph.append(edge)

    return semantic_graph


# ============================================================
# EMBEDDING TEXT
# ============================================================

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
    Build the semantic representation passed to the
    sentence-transformer model.

    This intentionally excludes:
        - timestamps
        - license
        - authors
        - version information
        - URLs
        - raw ToolShed identifiers
        - low-level Galaxy ports
        - generic metadata
    """

    sections = []

    # --------------------------------------------------------
    # Workflow identity
    # --------------------------------------------------------

    if title:
        sections.append(
            f"Workflow: {title}"
        )

    # --------------------------------------------------------
    # Scientific purpose
    # --------------------------------------------------------

    if description:
        sections.append(
            f"Purpose: {description}"
        )

    # --------------------------------------------------------
    # Platform
    # --------------------------------------------------------

    if workflow_class:
        sections.append(
            f"Platform: {workflow_class}"
        )

    # --------------------------------------------------------
    # Inputs
    # --------------------------------------------------------

    if inputs:

        input_lines = []

        for inp in inputs:

            line = inp["name"]

            if inp["description"]:
                line += (
                    f": {inp['description']}"
                )

            if inp["type"]:
                line += (
                    f" "
                    f"(type: "
                    f"{', '.join(inp['type'])})"
                )

            input_lines.append(
                f"- {line}"
            )

        sections.append(
            "Inputs:\n"
            + "\n".join(input_lines)
        )

    # --------------------------------------------------------
    # Major scientific operations
    # --------------------------------------------------------

    if operations:

        operation_lines = []

        for operation in operations:

            line = operation["name"]

            if operation.get("description"):
                line += (
                    f": "
                    f"{operation['description']}"
                )

            operation_lines.append(
                f"- {line}"
            )

        sections.append(
            "Major operations:\n"
            + "\n".join(operation_lines)
        )

    # --------------------------------------------------------
    # Workflow structure
    # --------------------------------------------------------

    if graph:

        graph_lines = [
            (
                f"- {edge['source']} "
                f"-> {edge['destination']}"
            )
            for edge in graph
        ]

        sections.append(
            "Workflow structure:\n"
            + "\n".join(graph_lines)
        )

    # --------------------------------------------------------
    # Outputs
    # --------------------------------------------------------

    if outputs:

        output_lines = []

        for output in outputs:

            line = output["name"]

            if output["description"]:
                line += (
                    f": "
                    f"{output['description']}"
                )

            if output["type"]:
                line += (
                    f" "
                    f"(type: "
                    f"{', '.join(output['type'])})"
                )

            output_lines.append(
                f"- {line}"
            )

        sections.append(
            "Outputs:\n"
            + "\n".join(output_lines)
        )

    return "\n\n".join(sections)


# ============================================================
# WORKFLOW
# ============================================================

def structure_workflow(workflow):

    data = workflow.get("data", {})
    attributes = data.get("attributes", {})
    internals = attributes.get("internals", {})

    workflow_id = clean_text(
        data.get("id")
    )

    title = clean_text(
        attributes.get("title")
    )

    description = clean_description(
        attributes.get("description")
    )

    workflow_class_data = (
        attributes.get("workflow_class") or {}
    )

    workflow_class = clean_text(
        workflow_class_data.get("title")
    )

    # --------------------------------------------------------
    # Structured components
    # --------------------------------------------------------

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

    major_operations = select_major_operations(
        steps
    )

    # Full workflow graph.
    graph = build_graph(
        steps,
        connections,
        inputs,
    )

    # Simplified graph for embedding.
    semantic_graph = build_semantic_graph(
        graph
    )

    # --------------------------------------------------------
    # Embedding representation
    # --------------------------------------------------------

    embedding_text = build_embedding_text(
        title=title,
        description=description,
        workflow_class=workflow_class,
        inputs=inputs,
        outputs=outputs,
        operations=major_operations,
        graph=semantic_graph,
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    data_links = data.get("links") or {}

    metadata = {
        "platform": workflow_class,
        "version": attributes.get("version"),
        "latest_version": attributes.get(
            "latest_version"
        ),
        "license": clean_text(
            attributes.get("license")
        ),
        "tags": attributes.get("tags") or [],
        "description": description,
        "workflow_url": (
            data_links.get("self")
            if isinstance(data_links, dict)
            else None
        ),
    }

    # --------------------------------------------------------
    # Final structured record
    # --------------------------------------------------------

    return {
        "id": workflow_id,
        "title": title,

        # Text passed to the embedding model.
        "embedding_text": embedding_text,

        # Metadata retained for retrieval.
        "metadata": metadata,

        # Structured workflow information.
        "inputs": inputs,
        "outputs": outputs,
        "steps": steps,
        "connections": connections,
        "major_operations": major_operations,

        # Full simplified graph.
        "graph": graph,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    count = 0
    skipped = 0

    with (
        input_path.open(
            "r",
            encoding="utf-8",
        ) as infile,

        output_path.open(
            "w",
            encoding="utf-8",
        ) as outfile,
    ):

        for line in infile:

            line = line.strip()

            if not line:
                continue

            try:
                workflow = json.loads(line)

                structured = structure_workflow(
                    workflow
                )

                if not structured["id"]:
                    skipped += 1
                    continue

                if not structured["embedding_text"]:
                    skipped += 1
                    continue

                outfile.write(
                    json.dumps(
                        structured,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

                count += 1

            except Exception as exc:

                skipped += 1

                print(
                    f"Error processing workflow: {exc}"
                )

    print(
        f"Processed {count} workflows."
    )

    print(
        f"Skipped {skipped} workflows."
    )

    print(
        f"Wrote {output_path}"
    )


if __name__ == "__main__":
    main()