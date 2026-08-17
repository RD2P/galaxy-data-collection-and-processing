# Galaxy Tools Data Collection

This directory contains scripts and artifacts for collecting and structuring Galaxy tool metadata for SciComposer.

## Source API

Base URL:
- https://usegalaxy.org

Primary endpoint:
- https://usegalaxy.org/api/tools/{tool_id}

Common query parameters:
- `io_details=true`: include tool inputs/outputs and parameter details
- `link_details=true`: include links for tool resources
- `tool_version=<version>`: request a specific version when available

Related endpoint:
- `/tools/<tool_id>/input` (tool input schema/details route)

## Directory Contents

- `ids.txt`: list of tool IDs to fetch (one ID per line)
- `collect_galaxy_tools_with_detail.py.py`: fetches details for each tool ID and writes JSONL
- `tools_with_detail.jsonl`: raw line-delimited collection output (append-only)
- `convert_jsonl_to_json.py`: converts JSONL output to a JSON array file
- `tools_with_detail.json`: array-format export of collected tool records
- `tool.py`: reduces a tool catalog (`tools.json`) to a compact summary
- `tool_summary.json`: simplified hierarchy output from `tool.py`
- `tool_examples.json`: example records

## Quick Start

Collect tool details:

```bash
python collect_galaxy_tools_with_detail.py.py
```

Convert JSONL to JSON array:

```bash
python convert_jsonl_to_json.py
```

Build compact catalog summary from `tools.json`:

```bash
python tool.py
```

## Output Record Shape

Successful fetch lines in `tools_with_detail.jsonl`:

```json
{
  "tool_id": "<id>",
  "details": {"...": "tool payload from /api/tools/{tool_id}"}
}
```

Failed fetch lines:

```json
{
  "tool_id": "<id>",
  "error": "<request error message>"
}
```

## Captured Catalog Stats

From the current summary snapshot:
- Total top-level items: 87
- `ToolSection`: 79
- `ToolSectionLabel`: 8
- Total tool count (excluding labels): 2318
- Distinct model classes observed: 28

## Model Classes Observed

- ToolSection
- Tool
- DataSourceTool
- ToolSectionLabel
- BuildListCollectionTool
- DuplicateFileToCollectionTool
- ConvertSampleSheetTool
- FlattenTool
- NestTool
- MergeCollectionTool
- SplitPairedAndUnpairedTool
- FilterFailedDatasetsTool
- FilterEmptyDatasetsTool
- FilterNullTool
- KeepSuccessDatasetsTool
- FilterFromFileTool
- ZipCollectionTool
- UnzipCollectionTool
- CrossProductFlatCollectionTool
- CrossProductNestedCollectionTool
- HarmonizeTool
- SortTool
- TagFromFileTool
- RelabelFromFileTool
- ExtractDatasetCollectionTool
- ApplyRulesTool
- ExpressionTool
- InteractiveTool

## Tool Section Counts (Snapshot)

The snapshot includes section-level counts such as:
- QIIME2: 161
- ChemicalToolBox: 153
- Metagenomic Analysis: 134
- Mothur: 131
- Imaging: 130
- EMBOSS: 107
- Annotation: 106
- Single-cell: 75
- RNA-seq: 73

## Notes

- `collect_galaxy_tools_with_detail.py` appends to `tools_with_detail.jsonl`; reruns will add more lines unless the file is reset.
- Requests are throttled with a short delay between calls.
- Keep raw JSONL as the source of truth; generate derived JSON views in separate files.