# Galaxy Workflows Data Collection

This directory contains the workflow collection, semantic structuring, and embedding pipeline for Galaxy workflows used by SciComposer.

## Source endpoints

WorkflowHub APIs used in this pipeline:
- All workflows catalog:
  - https://www.workflowhub.eu/workflows.json
- Galaxy-only catalog:
  - https://www.workflowhub.eu/workflows.json?filter[workflow_type]=galaxy
- Individual workflow:
  - https://workflowhub.eu/workflows/<id>.json
- Example:
  - https://workflowhub.eu/workflows/1713.json

## Pipeline overview

The workflow pipeline has three main stages:

1. Collect raw workflow records from WorkflowHub.
2. Structure them into a semantic, retrieval-friendly representation.
3. Embed the structured text into a FAISS index for similarity search.

## Files in this directory

- `data/galaxy_workflows.jsonl`
  - Raw workflow JSONL downloaded from WorkflowHub.
  - One workflow object per line.
- `scripts/preprocess_workflows_for_embedding.py`
  - Cleans raw workflow JSON, extracts inputs, outputs, steps, links, and a semantic `embedding_text` field.
- `data/workflows_structured.jsonl`
  - Structured workflow records used for retrieval and downstream indexing.
- `scripts/embed_workflows.py`
  - Loads the structured workflow JSONL, encodes the `embedding_text` field, and builds a FAISS index.
- `data/workflows.faiss`
  - FAISS index for workflow search.
- `data/workflows_index_metadata.json`
  - Metadata mapping between FAISS positions and workflow IDs/titles.

## Collection stage

The collection process discovers Galaxy workflow IDs from the Galaxy-filtered catalog and then fetches each item from the individual workflow endpoint.

The raw records are stored as JSONL so that the pipeline can be resumed or reprocessed without re-fetching every workflow.

## Structuring stage

`preprocess_workflows_for_embedding.py` converts each raw workflow into a compact, semantically meaningful record with:

- `id`: workflow identity
- `title`: workflow title
- `embedding_text`: text passed to the embedding model
- `metadata`: workflow metadata such as platform, tags, description, and URL
- `inputs`: normalized input definitions
- `outputs`: normalized output definitions
- `steps`: step-level descriptions and tool IDs
- `connections`: workflow edge list
- `major_operations`: scientifically meaningful operations, excluding generic Galaxy/data-manipulation steps
- `graph`: simplified workflow graph for retrieval and interpretation

### Semantic filtering

The script intentionally strips boilerplate and low-value metadata before building the embedding text:

- timestamps and version metadata are excluded from the embedding text
- raw ToolShed identifiers are removed from semantic descriptions while being retained in step metadata
- generic operations like simple text manipulation or file concatenation are suppressed in the major-operation summary
- URLs, license strings, and catalog boilerplate are removed from the purpose description

This keeps the embedding text focused on scientific workflow intent and structure rather than platform noise.

## Embedding stage

The workflow embedding script uses `sentence-transformers/all-MiniLM-L6-v2` and normalizes the resulting embeddings before constructing a FAISS index.

Key implementation details:

- Input: `data/workflows_structured.jsonl`
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Embedding normalization: enabled
- FAISS index type: `IndexFlatIP`
- Similarity metric: cosine-equivalent via normalized inner product

Because the vectors are normalized, the FAISS inner-product search corresponds to cosine similarity.

### Run command

From this directory:

```bash
python scripts/preprocess_workflows_for_embedding.py
python scripts/embed_workflows.py
```

## Latest embedding result

```text
Embedding shape: (753, 384)
Building FAISS index...
FAISS vectors: 753
Wrote FAISS index: /student/gld141/ISE_2026/projects/data_collection/workflows/data/workflows.faiss
Wrote metadata: /student/gld141/ISE_2026/projects/data_collection/workflows/data/workflows_index_metadata.json

Done.
Workflows indexed: 753
Embedding dimension: 384
```

## Data quality notes

- Some workflow fields may be missing or empty.
- The structuring script normalizes missing values and removes low-value boilerplate.
- The embedding step validates that every workflow has a non-empty `embedding_text` and a unique ID.
- Keep raw JSONL immutable; write processed results to new files.

## Current workflow snapshot

- 753 workflow records indexed
- 384-dimensional embeddings
- 1 FAISS index built for semantic retrieval
- Metadata file exposes workflow ID and title mapping for each vector position
