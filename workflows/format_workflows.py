"""
    Convert WorkflowHub workflow JSONL into structured text suitable for embedding.

    Input:
        workflows.jsonl

    Output:
        workflows_structured.jsonl

    Each output line:
    {
        "id": "workflow id",
        "text": "structured workflow text summary"
    }
"""

import json
from pathlib import Path


INPUT_FILE = "galaxy_workflows.jsonl"
OUTPUT_FILE = "workflows_structured.jsonl"


def clean(value):
    '''Normalize values: trim strings, flatten lists and dicts'''
    if value is None:
        return "None"

    if isinstance(value, str):
        value = value.strip()
        return value if value else "None"

    if isinstance(value, list):
        return ", ".join(clean(v) for v in value)

    if isinstance(value, dict):
        if "type" in value:
            return clean(value["type"])
        return json.dumps(value, ensure_ascii=False)

    return str(value)


def format_types(type_list):
    '''convert I/O type lists to comma-separated string'''
    if not type_list:
        return "None"

    values = []
    for t in type_list:
        if isinstance(t, dict):
            values.append(t.get("type", "Unknown"))
        else:
            values.append(str(t))

    return ", ".join(values)


def format_workflow(workflow):
    '''Build multiline string representing workflow'''

    data = workflow.get("data", {})
    attr = data.get("attributes", {})
    internals = attr.get("internals", {})

    lines = []

    # ==========================================================
    # HEADER
    # ==========================================================

    lines.append("WORKFLOW")
    lines.append("")

    lines.append(f"Name: {clean(attr.get('title'))}")
    lines.append(f"Platform: {clean(attr.get('workflow_class', {}).get('title'))}")
    lines.append(f"Description: {clean(attr.get('description'))}")
    lines.append(f"License: {clean(attr.get('license'))}")
    lines.append(f"Version: {clean(attr.get('version'))}")
    lines.append(f"Workflow Class: {clean(attr.get('workflow_class', {}).get('title'))}")

    tags = attr.get("tags", [])
    lines.append(f"Tags: {', '.join(tags) if tags else 'None'}")

    lines.append(f"Created: {clean(attr.get('created_at'))}")
    lines.append(f"Updated: {clean(attr.get('updated_at'))}")

    # ==========================================================
    # INPUTS
    # ==========================================================

    lines.append("")
    lines.append("----------------------------------------")
    lines.append("INPUTS")
    lines.append("")

    inputs = internals.get("inputs", [])

    if not inputs:
        lines.append("None")
    else:
        for inp in inputs:
            lines.append("Input:")
            lines.append(f"  Name: {clean(inp.get('name'))}")
            lines.append(f"  Description: {clean(inp.get('description'))}")
            lines.append(f"  Type: {format_types(inp.get('type'))}")
            lines.append("")

    # ==========================================================
    # OUTPUTS
    # ==========================================================

    lines.append("----------------------------------------")
    lines.append("OUTPUTS")
    lines.append("")

    outputs = internals.get("outputs", [])

    if not outputs:
        lines.append("None")
    else:
        for out in outputs:
            lines.append("Output:")
            lines.append(f"  Name: {clean(out.get('name'))}")
            lines.append(f"  Description: {clean(out.get('description'))}")
            lines.append(f"  Type: {format_types(out.get('type'))}")

            source = out.get("source_ids", [])
            if source:
                lines.append(f"  Produced By: {', '.join(source)}")
            else:
                lines.append("  Produced By: None")

            lines.append("")

    # ==========================================================
    # STEPS
    # ==========================================================

    lines.append("----------------------------------------")
    lines.append("ANALYSIS STEPS")
    lines.append("")

    steps = internals.get("steps", [])

    if not steps:
        lines.append("None")
    else:
        for step in steps:
            lines.append(f"Step {step.get('id')}")
            lines.append(f"  Name: {clean(step.get('name'))}")
            lines.append(f"  Description: {clean(step.get('description'))}")
            lines.append("")

    # ==========================================================
    # CONNECTIONS
    # ==========================================================

    lines.append("----------------------------------------")
    lines.append("WORKFLOW CONNECTIONS")
    lines.append("")

    links = internals.get("links", [])

    if not links:
        lines.append("None")
    else:
        for link in links:
            lines.append(f"Source: {clean(link.get('source_id'))}")
            lines.append(f"Destination: {clean(link.get('sink_id'))}")
            lines.append("")

    # ==========================================================
    # SUMMARY
    # ==========================================================

    lines.append("----------------------------------------")
    lines.append("PIPELINE SUMMARY")
    lines.append("")

    lines.append(
        "Inputs: " +
        (", ".join(i.get("name") or "Unnamed" for i in inputs) if inputs else "None")
    )

    lines.append(
        "Outputs: " +
        (", ".join(o.get("name") or "Unnamed" for o in outputs) if outputs else "None")
    )

    lines.append(f"Number of Inputs: {len(inputs)}")
    lines.append(f"Number of Outputs: {len(outputs)}")
    lines.append(f"Number of Steps: {len(steps)}")
    lines.append(f"Number of Connections: {len(links)}")

    return "\n".join(lines)


def main():
    '''Stream input file line by line and formats the workflow in that line'''
    
    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    count = 0

    with input_path.open("r", encoding="utf-8") as infile, \
         output_path.open("w", encoding="utf-8") as outfile:

        for line in infile:
            line = line.strip()
            if not line:
                continue

            workflow = json.loads(line)

            text = format_workflow(workflow)

            record = {
                "id": workflow.get("data", {}).get("id"),
                "text": text
            }

            outfile.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    print(f"Processed {count} workflows.")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()