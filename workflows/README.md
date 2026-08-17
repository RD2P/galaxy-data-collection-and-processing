# Galaxy Workflows Data Collection

This directory contains the data collection and preprocessing pipeline for **Galaxy workflows** used by SciComposer.

## Source Endpoints

WorkflowHub APIs used in this pipeline:
- All workflows catalog:
	- https://www.workflowhub.eu/workflows.json
- Galaxy-only catalog:
	- https://www.workflowhub.eu/workflows.json?filter[workflow_type]=galaxy
- Individual workflow:
	- https://workflowhub.eu/workflows/<id>.json
- e.g.:
	- https://workflowhub.eu/workflows/1713.json

## Files in This Directory

- `galaxy_workflows.jsonl`
	- Input JSONL used by formatting scripts.
	- Expected: one workflow JSON object per line (typically from individual `<id>.json` fetches).
- `format_workflows.py`
	- Converts raw workflow JSONL into structured text records.
- `workflows_structured.jsonl`
	- Output JSONL where each line has:
		- `id`: workflow identifier
		- `text`: structured multi-section summary (metadata, inputs, outputs, steps, links, counts)
- `workflow_example.json`
	- Example raw workflow payload for schema inspection.
- `workflow_enrichment.md`
	- Notes for a later enrichment stage (summaries/tags/normalized fields).

## Processing Pipeline

1. Discover Galaxy workflow IDs from the Galaxy-filtered catalog endpoint.
2. Fetch each workflow from `https://workflowhub.eu/workflows/<id>.json`.
3. Write one JSON object per line into `galaxy_workflows.jsonl`.
4. Run `format_workflows.py` to produce `workflows_structured.jsonl`.

## Run the Formatter

From this directory:

```bash
python format_workflows.py
```

The script reads:
- `galaxy_workflows.jsonl`

And writes:
- `workflows_structured.jsonl`

## Data Quality Notes

- Some workflow fields may be missing or empty.
- `format_workflows.py` normalizes missing values to `None` in text output.
- Keep raw JSONL immutable; write processed results to new files.
