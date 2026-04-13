"""
init_chromadb.py

Ingest a large CSV of leads into a local ChromaDB persistent collection named 'employee_db'.

- Reads CSV in chunks to avoid OOM.
- Deduplicates IDs within each chunk (keeps last occurrence).
- Splits upserts into safe sub-batches to avoid ChromaDB max-batch errors.
- Uses chromadb.PersistentClient(path="./hr_chroma_db").
- Upserts using 'email' as unique id. Documents are empty strings.
- Skips rows with missing/empty email.
- Progress logging via tqdm and logging.
"""
from __future__ import annotations
import argparse
import logging
import os
from typing import List, Dict

import pandas as pd
from tqdm import tqdm

try:
    from chromadb import PersistentClient
except Exception as exc:
    raise ImportError("chromadb is required. Install with `pip install chromadb`.") from exc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("init_chromadb")

EXPECTED_METADATA_COLUMNS = [
    "firstName",
    "lastName",
    "title",
    "companyName",
    "department",
    "level",
    "industry",
    "country",
    "state",
    "email",
]

# safe upsert sub-batch size (below observed max from chroma errors)
DEFAULT_MAX_UPSERT_BATCH = 5000


def ensure_collection(client: PersistentClient, name: str):
    try:
        collection = client.get_collection(name)
        LOGGER.info("Using existing collection '%s'.", name)
    except Exception:
        collection = client.create_collection(name)
        LOGGER.info("Created collection '%s'.", name)
    return collection


def process_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    # Ensure email column exists
    if "email" not in chunk.columns:
        chunk["email"] = None

    # Normalize email: strip + lower; coerce obvious 'nan' strings to empty
    chunk["email"] = chunk["email"].astype(str).str.strip().str.lower()
    chunk.loc[chunk["email"].isin({"nan", "None"}), "email"] = ""

    # Filter out empty emails
    filtered = chunk[chunk["email"].notna() & (chunk["email"] != "")]
    return filtered


def build_upsert_payload(df: pd.DataFrame):
    ids: List[str] = []
    metadatas: List[Dict] = []
    documents: List[str] = []

    for _, row in df.iterrows():
        email = str(row.get("email", "")).strip().lower()
        if not email:
            continue
        ids.append(email)
        metadata = {col: (row.get(col, "") if pd.notna(row.get(col, "")) else "") for col in EXPECTED_METADATA_COLUMNS}
        metadatas.append(metadata)
        documents.append("")  # per spec: empty document
    return ids, metadatas, documents


def _upsert_in_sublots(collection, ids, metadatas, documents, max_batch):
    """Split arrays into sub-batches of size <= max_batch and upsert each."""
    total = len(ids)
    for start in range(0, total, max_batch):
        end = min(start + max_batch, total)
        sub_ids = ids[start:end]
        sub_mds = metadatas[start:end]
        sub_docs = documents[start:end]
        LOGGER.info("Upserting sub-batch %d:%d (size=%d)", start, end, len(sub_ids))
        collection.upsert(ids=sub_ids, metadatas=sub_mds, documents=sub_docs)


def ingest(csv_path: str, chunk_size: int = 10000, client_path: str = "./hr_chroma_db", max_upsert_batch: int = DEFAULT_MAX_UPSERT_BATCH):
    if not os.path.exists(csv_path):
        LOGGER.error("CSV file not found: %s", csv_path)
        raise FileNotFoundError(csv_path)

    client = PersistentClient(path=client_path)
    collection = ensure_collection(client, "employee_db")

    total_rows = 0
    total_upserted = 0
    LOGGER.info("Starting ingestion from %s with chunk_size=%d and max_upsert_batch=%d", csv_path, chunk_size, max_upsert_batch)

    reader = pd.read_csv(csv_path, chunksize=chunk_size, dtype=str, low_memory=False)
    for chunk in tqdm(reader, desc="Chunks processed"):
        total_rows += len(chunk)
        processed = process_chunk(chunk)
        if processed.empty:
            continue
        ids, metadatas, documents = build_upsert_payload(processed)
        if not ids:
            continue

        # Deduplicate IDs within this batch; keep last occurrence
        unique_map = {}
        duplicates = 0
        for i, _id in enumerate(ids):
            if _id in unique_map:
                duplicates += 1
            unique_map[_id] = (metadatas[i], documents[i])

        if duplicates:
            LOGGER.info("Found %d duplicate ids in current batch; keeping last occurrence.", duplicates)

        ids = list(unique_map.keys())
        metadatas = [v[0] for v in unique_map.values()]
        documents = [v[1] for v in unique_map.values()]

        try:
            _upsert_in_sublots(collection, ids, metadatas, documents, max_upsert_batch)
            total_upserted += len(ids)
        except Exception as exc:
            LOGGER.exception("Failed to upsert a batch/sub-batch: %s", exc)
            raise

    LOGGER.info("Ingestion complete. Rows read=%d, records upserted=%d", total_rows, total_upserted)


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest leads CSV into ChromaDB (employee_db).")
    parser.add_argument("--csv", "-c", required=False, default="leads.csv", help="Path to leads CSV (default: leads.csv)")
    parser.add_argument("--chunksize", "-s", required=False, type=int, default=10000, help="Pandas read_csv chunksize (default: 10000)")
    parser.add_argument("--dbpath", "-d", required=False, default="./hr_chroma_db", help="PersistentClient path (default: ./hr_chroma_db)")
    parser.add_argument("--max-upsert-batch", "-m", required=False, type=int, default=DEFAULT_MAX_UPSERT_BATCH, help="Max upsert sub-batch size (default: 5000)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ingest(csv_path=args.csv, chunk_size=args.chunksize, client_path=args.dbpath, max_upsert_batch=args.max_upsert_batch)
