# Data Collection for SciComposer

This repository contains data collection and preprocessing pipelines for **SciComposer**, a multi-agent framework for Galaxy workflow design.

The project currently includes:
- Galaxy **workflow** data collection and text structuring for downstream retrieval/embedding.
- Galaxy **tool** metadata collection and simplification.

## Data Sources

### WorkflowHub (workflows)

- All workflows: https://www.workflowhub.eu/workflows.json
- Galaxy workflows only: https://www.workflowhub.eu/workflows.json?filter[workflow_type]=galaxy
- Individual workflow by ID: https://workflowhub.eu/workflows/<id>.json
- Example individual workflow: https://workflowhub.eu/workflows/1713.json

### UseGalaxy (tools)

- Base URL: https://usegalaxy.org
- Tool details endpoint: https://usegalaxy.org/api/tools/{tool_id}
- Common query parameters:
	- `io_details=true`
	- `link_details=true`
	- `tool_version=<version>`

## Repository Structure

- `workflows/`: Collection and processing for Galaxy workflows.
- `tools/`: Collection and processing for Galaxy tool metadata.

## Tools Pipeline Outputs

The `tools/` directory produces:
- `tools_with_detail.jsonl`: raw line-delimited API results (success and error records).
- `tools_with_detail.json`: JSON-array export converted from JSONL.
- `tool_summary.json`: compact tool catalog summary generated from `tools.json`.

Current snapshot metrics from `tools/README.md`:
- 87 top-level catalog items
- 79 `ToolSection` and 8 `ToolSectionLabel`
- 2318 tools (excluding labels)
- 28 model classes observed

## Typical Data Flow

1. Discover relevant objects from API listing endpoints.
2. Fetch individual records as JSON.
3. Store records as JSONL for streaming-friendly processing.
4. Convert raw records into structured text or compact summaries for model use.

## Quick Start

Prerequisites:
- Python 3.10+

Workflow structuring example:

```bash
cd workflows
python format_workflows.py
```

Tool-detail collection example:

```bash
cd tools
python collect_galaxy_tools_with_detail.py.py
```

Tool JSONL to JSON conversion example:

```bash
cd tools
python convert_jsonl_to_json.py
```

## Notes

- JSONL files are intended for incremental processing and easier resume behavior.
- The `workflows/` pipeline is documented in more detail in `workflows/README.md`.
- The `tools/` pipeline is documented in more detail in `tools/README.md`.
