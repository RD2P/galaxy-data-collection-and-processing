"""
    Embed structured Galaxy WorkflowHub workflows and build a FAISS index.

    Input:
        data/workflows_structured.jsonl

    Outputs:
        data/workflows.faiss
        data/workflows_index_metadata.json

    The JSONL file must contain one workflow per line with an
    `embedding_text` field.

    The FAISS index stores the normalized workflow embeddings.
    The metadata file maps FAISS vector positions back to workflow IDs.
"""

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# ============================================================
# Configuration
# ============================================================

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

INPUT_FILE = DATA_DIR / "workflows_structured.jsonl"
INDEX_FILE = DATA_DIR / "workflows.faiss"
METADATA_FILE = DATA_DIR / "workflows_index_metadata.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

BATCH_SIZE = 32


# ============================================================
# Load workflows
# ============================================================

def load_workflows(path):
    """
    Load structured workflow records from JSONL.

    Returns:
        list of workflow records
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Input path is not a file: {path}"
        )

    workflows = []
    workflow_ids = set()

    with path.open("r", encoding="utf-8") as infile:

        for line_number, line in enumerate(infile, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                workflow = json.loads(line)

            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

            if not isinstance(workflow, dict):
                raise ValueError(
                    f"Expected a JSON object on line {line_number}"
                )

            embedding_text = workflow.get(
                "embedding_text"
            )

            if not embedding_text:
                raise ValueError(
                    f"Missing embedding_text on line {line_number}"
                )

            workflow_id = workflow.get("id")

            if not workflow_id:
                raise ValueError(
                    f"Missing workflow id on line {line_number}"
                )

            if workflow_id in workflow_ids:
                raise ValueError(
                    f"Duplicate workflow id on line {line_number}: "
                    f"{workflow_id}"
                )

            workflow_ids.add(workflow_id)
            workflows.append(workflow)

    return workflows


# ============================================================
# Build embeddings
# ============================================================

def build_embeddings(model, texts):
    """
    Generate normalized embeddings for workflow text.

    Normalization allows cosine similarity to be represented
    using inner-product search in FAISS.
    """

    if not texts:
        raise ValueError("Cannot embed an empty text collection")

    token_lengths = [
        len(model.tokenize([text])["input_ids"][0])
        for text in texts
    ]
    max_length = model.max_seq_length
    truncated_count = sum(
        length > max_length
        for length in token_lengths
    )

    if truncated_count:
        print(
            f"Warning: {truncated_count} of {len(texts)} workflows "
            f"exceed the model limit of {max_length} tokens and will "
            "be truncated by the model."
        )

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(embeddings, dtype=np.float32)

    if embeddings.ndim != 2:
        raise RuntimeError(
            f"Expected a 2-D embedding matrix, got shape {embeddings.shape}"
        )

    if embeddings.shape[0] != len(texts):
        raise RuntimeError(
            f"Embedding count mismatch: {embeddings.shape[0]} vectors "
            f"for {len(texts)} texts"
        )

    if not np.isfinite(embeddings).all():
        raise RuntimeError("Embedding matrix contains non-finite values")

    return embeddings


# ============================================================
# Build FAISS index
# ============================================================

def build_faiss_index(embeddings):
    """
    Build an IndexFlatIP FAISS index.

    Because embeddings are normalized, inner product is
    equivalent to cosine similarity.
    """

    if embeddings.ndim != 2 or embeddings.shape[0] == 0:
        raise ValueError(
            f"Expected a non-empty 2-D embedding matrix, got {embeddings.shape}"
        )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(embeddings)

    if index.ntotal != embeddings.shape[0]:
        raise RuntimeError(
            f"FAISS count mismatch: {index.ntotal} vectors vs "
            f"{embeddings.shape[0]} embeddings"
        )

    return index


# ============================================================
# Build metadata
# ============================================================

def build_metadata(workflows):
    """
    Create the mapping between FAISS vector positions and
    workflow records.

    FAISS position 0 corresponds to workflows[0],
    position 1 corresponds to workflows[1], etc.
    """

    metadata = []

    for position, workflow in enumerate(workflows):
        metadata.append(
            {
                "index": position,
                "id": workflow.get("id"),
                "title": workflow.get("title"),
            }
        )

    return metadata


# ============================================================
# Main
# ============================================================

def main():

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Loading workflows from {INPUT_FILE}"
    )

    workflows = load_workflows(
        INPUT_FILE
    )

    if not workflows:
        raise RuntimeError(
            "No workflows with embedding_text found."
        )

    print(
        f"Loaded {len(workflows)} workflows."
    )

    # --------------------------------------------------------
    # Load embedding model
    # --------------------------------------------------------

    print(
        f"Loading model: {MODEL_NAME}"
    )

    model = SentenceTransformer(
        MODEL_NAME
    )

    # --------------------------------------------------------
    # Extract embedding text
    # --------------------------------------------------------

    texts = [
        workflow["embedding_text"]
        for workflow in workflows
    ]

    # --------------------------------------------------------
    # Generate embeddings
    # --------------------------------------------------------

    print(
        "Generating workflow embeddings..."
    )

    embeddings = build_embeddings(
        model,
        texts,
    )

    print(
        f"Embedding shape: {embeddings.shape}"
    )

    # --------------------------------------------------------
    # Build FAISS index
    # --------------------------------------------------------

    print(
        "Building FAISS index..."
    )

    index = build_faiss_index(
        embeddings
    )

    print(
        f"FAISS vectors: {index.ntotal}"
    )

    # --------------------------------------------------------
    # Save FAISS index
    # --------------------------------------------------------

    faiss.write_index(
        index,
        str(INDEX_FILE),
    )

    print(
        f"Wrote FAISS index: {INDEX_FILE}"
    )

    # --------------------------------------------------------
    # Save metadata mapping
    # --------------------------------------------------------

    metadata = build_metadata(
        workflows
    )

    if index.ntotal != len(metadata):
        raise RuntimeError(
            f"Index/metadata mismatch: {index.ntotal} vectors vs "
            f"{len(metadata)} metadata records"
        )

    metadata_record = {
        "model": MODEL_NAME,
        "dimension": int(
            embeddings.shape[1]
        ),
        "metric": "cosine_similarity",
        "index_type": "IndexFlatIP",
        "count": len(workflows),
        "workflows": metadata,
    }

    with METADATA_FILE.open(
        "w",
        encoding="utf-8",
    ) as outfile:

        json.dump(
            metadata_record,
            outfile,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Wrote metadata: {METADATA_FILE}"
    )

    print()
    print("Done.")
    print(
        f"Workflows indexed: {len(workflows)}"
    )
    print(
        f"Embedding dimension: "
        f"{embeddings.shape[1]}"
    )


if __name__ == "__main__":
    main()