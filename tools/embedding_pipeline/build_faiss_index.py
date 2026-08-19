import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


INPUT_FILE = Path("data/tools_embedding_documents.jsonl")
INDEX_FILE = Path("data/tools.faiss")
METADATA_FILE = Path("data/tools_index_metadata.json")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 64


def load_documents() -> tuple[list[str], list[dict]]:
    documents = []
    metadata = []

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {e}"
                ) from e

            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected JSON object on line {line_number}"
                )

            tool_id = record.get("tool_id")
            document = record.get("document")

            if not tool_id:
                raise ValueError(
                    f"Missing tool_id on line {line_number}"
                )

            if not document:
                raise ValueError(
                    f"Missing document on line {line_number}"
                )

            documents.append(document)

            metadata.append({
                "index": len(metadata),
                "tool_id": tool_id,
                "name": record.get("name", ""),
                "version": record.get("version", ""),
            })

    return documents, metadata


def build_index(
    documents: list[str],
) -> tuple[faiss.Index, np.ndarray]:
    print(f"Loading embedding model: {MODEL_NAME}")

    model = SentenceTransformer(MODEL_NAME)

    print(f"Embedding {len(documents)} documents...")

    embeddings = model.encode(
        documents,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(embeddings, dtype=np.float32)

    dimension = embeddings.shape[1]

    print(f"Embedding dimension: {dimension}")
    print(f"Embedding shape:     {embeddings.shape}")

    # Inner product on normalized vectors = cosine similarity.
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    return index, embeddings


def save_metadata(
    metadata: list[dict],
    dimension: int,
) -> None:
    metadata_record = {
        "model": MODEL_NAME,
        "dimension": dimension,
        "metric": "cosine_similarity",
        "index_type": "IndexFlatIP",
        "count": len(metadata),
        "tools": metadata,
    }

    with METADATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            metadata_record,
            f,
            ensure_ascii=False,
            indent=2,
        )


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("FAISS Index Builder")
    print("=" * 60)

    documents, metadata = load_documents()

    print(f"Documents loaded: {len(documents)}")

    index, embeddings = build_index(documents)

    if index.ntotal != len(metadata):
        raise RuntimeError(
            f"Index/metadata mismatch: "
            f"{index.ntotal} vectors vs {len(metadata)} metadata records"
        )

    print(f"\nSaving FAISS index: {INDEX_FILE}")

    faiss.write_index(index, str(INDEX_FILE))

    print(f"Saving metadata: {METADATA_FILE}")

    save_metadata(metadata, int(embeddings.shape[1]))

    print("\n" + "=" * 60)
    print("Index build complete")
    print("=" * 60)
    print(f"Vectors:       {index.ntotal}")
    print(f"Dimension:     {embeddings.shape[1]}")
    print(f"Index:         {INDEX_FILE}")
    print(f"Metadata:      {METADATA_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()