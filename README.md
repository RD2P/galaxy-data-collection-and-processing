# Data Collection for SciComposer

This repository contains the Galaxy data collection, normalization, enrichment, and embedding pipelines used by SciComposer for retrieval and workflow/tool recommendation.

The project currently includes two main data streams:
- Galaxy tool metadata collection, preprocessing, LLM enrichment, and FAISS indexing.
- Galaxy workflow metadata collection, semantic structuring, and FAISS indexing.

## Data Sources

### WorkflowHub (workflows)

- All workflows catalog: https://www.workflowhub.eu/workflows.json
- Galaxy-only catalog: https://www.workflowhub.eu/workflows.json?filter[workflow_type]=galaxy
- Individual workflow record: https://workflowhub.eu/workflows/<id>.json
- Example workflow: https://workflowhub.eu/workflows/1713.json

### UseGalaxy (tools)

- Base URL: https://usegalaxy.org
- Tool details endpoint: https://usegalaxy.org/api/tools/{tool_id}
- Common query parameters:
  - `io_details=true`
  - `link_details=true`
  - `tool_version=<version>`

## Repository Structure

- `tools/`: Galaxy tool metadata collection, enrichment, and embedding pipeline.
- `workflows/`: Galaxy workflow collection, structuring, and embedding pipeline.

## Tools Pipeline Summary

The tools pipeline follows a full retrieval-prep workflow:

1. Collect raw tool metadata from the Galaxy API into `tools/tools_with_detail.jsonl`.
2. Preprocess the raw records with `tools/enrichment_pipeline/scripts/preprocess_raw_tool_details.py` to remove noisy metadata and keep only semantically useful fields.
3. Enrich the preprocessed tools with scientific metadata using `tools/enrichment_pipeline/scripts/enrichment.py`, which calls Ollama with the `qwen3.5:9b` model at `http://localhost:4378`.
4. Validate enriched records with `tools/enrichment_pipeline/scripts/validate_enriched_tools.py`.
5. Convert enriched records into embedding documents using `tools/embedding_pipeline/generate_embedding_documents.py`.
6. Build a FAISS index with `tools/embedding_pipeline/build_faiss_index.py` using `sentence-transformers/all-MiniLM-L6-v2` and normalized embeddings.

### Tools pipeline outputs

- `tools/tools_with_detail.jsonl`: raw API results for all fetched tools.
- `tools/tools_with_detail.json`: JSON-array export of the raw tool records.
- `tools/tool_summary.json`: compact catalog summary.
- `tools/enrichment_pipeline/data/tools_preprocessed.jsonl`: cleaned tool metadata for model enrichment.
- `tools/enrichment_pipeline/data/tools_enriched.jsonl`: LLM-enriched tool records.
- `tools/enrichment_pipeline/metrics_and_errors/tools_enrichment_metrics.jsonl`: timing and token metrics per tool.
- `tools/enrichment_pipeline/metrics_and_errors/tools_enrichment_errors.jsonl`: failed tool records.
- `tools/embedding_pipeline/data/tools_embedding_documents.jsonl`: text documents used for embedding.
- `tools/embedding_pipeline/data/tools.faiss`: FAISS search index.
- `tools/embedding_pipeline/data/tools_embedding_metadata.jsonl`: FAISS metadata map.

### Tools snapshot metrics

- 87 top-level catalog items
- 79 `ToolSection` and 8 `ToolSectionLabel`
- 2318 tools excluding labels
- 28 distinct model classes observed
- 2340 processed enriched records in the latest run
- 2198 valid enriched records
- 142 invalid records after validation (mostly missing description values in source metadata)
- 753 workflow records in the workflow embedding index

## Workflows Pipeline Summary

The workflows pipeline prepares Galaxy workflows for semantic retrieval in a similar way:

1. Discover Galaxy workflow IDs from the WorkflowHub catalog.
2. Fetch each workflow detail record from `https://workflowhub.eu/workflows/<id>.json`.
3. Write raw workflow JSON objects to `workflows/data/galaxy_workflows.jsonl`.
4. Structure the raw workflow records with `workflows/scripts/preprocess_workflows_for_embedding.py` by extracting inputs, outputs, step descriptions, connections, major operations, and a semantic `embedding_text` field.
5. Build a workflow FAISS index with `workflows/scripts/embed_workflows.py` using `sentence-transformers/all-MiniLM-L6-v2` and cosine-equivalent normalized embeddings.

### Workflow pipeline outputs

- `workflows/data/galaxy_workflows.jsonl`: raw workflow JSONL fetched from WorkflowHub.
- `workflows/data/workflows_structured.jsonl`: structured workflow records with metadata and `embedding_text`.
- `workflows/data/workflows.faiss`: workflow FAISS index.
- `workflows/data/workflows_index_metadata.json`: mapping from FAISS vector positions back to workflow IDs and titles.

### Workflow snapshot metrics

- 753 workflow records indexed
- 384 embedding dimension
- cosine similarity via normalized embeddings and `IndexFlatIP`

## Typical Data Flow

1. Discover relevant objects from API listing endpoints.
2. Fetch individual records as JSON.
3. Write JSONL for streaming, resume-friendly processing.
4. Normalize fields into model-friendly representations.
5. Enrich tool records with domain and scientific metadata.
6. Convert structured records into embedding documents.
7. Build FAISS indexes for retrieval.

## Quick Start

Prerequisites:
- Python 3.10+
- Optional local Ollama service for tool enrichment

Workflow structure and embedding:

```bash
cd workflows
python scripts/preprocess_workflows_for_embedding.py
python scripts/embed_workflows.py
```

Tool collection and enrichment:

```bash
cd tools
python collection_scripts/collect_galaxy_tools_with_detail.py
python enrichment_pipeline/scripts/preprocess_raw_tool_details.py
python enrichment_pipeline/scripts/enrichment.py
python embedding_pipeline/generate_embedding_documents.py
python embedding_pipeline/build_faiss_index.py
```

## Notes

- JSONL remains the main archival format for robust incremental processing and resume behavior.
- Tool enrichment treats missing scientific metadata fields as acceptable when the source data lacks coverage, while still flagging malformed or missing core information.
- The workflow and tool retrieval indexes are built from semantic text representations and optimized for cosine-style similarity search with FAISS.
- The more detailed pipeline documentation lives in the README files under the `tools/` and `workflows/` directories.
