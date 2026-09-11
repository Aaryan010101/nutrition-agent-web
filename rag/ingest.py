"""
RAG ingestion pipeline for the Indian Food Composition knowledge base.

Reads data/indian_food_db.jsonl, creates rich text chunks for each food item,
embeds them with the watsonx slate embedding model, and upserts into a Milvus
collection called `indian_food_nutrition`.

Usage:
    python rag/ingest.py [--data-path data/indian_food_db.jsonl] [--recreate]

Dependencies:
    pip install pymilvus ibm-watsonx-ai
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
    connections,
    utility,
)

# Add project root to path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import milvus as milvus_cfg
from config.settings import watsonx as wx_cfg

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _food_to_text(item: dict[str, Any]) -> str:
    """
    Convert a food item dict to a rich natural-language chunk suitable for
    embedding and semantic retrieval.
    """
    vitamins_str = ", ".join(
        f"{k}={v}" for k, v in item.get("vitamins", {}).items()
    ) or "not listed"

    avail = ", ".join(item.get("availability", []))
    tags = ", ".join(item.get("tags", []))

    return (
        f"Food: {item['name']} (also called {item.get('regional_name', item['name'])}).\n"
        f"Category: {item['category']}. Serving: {item['serving_unit']}.\n"
        f"Nutrition per serving — Calories: {item['calories_kcal']} kcal, "
        f"Protein: {item['protein_g']}g, Carbs: {item['carbs_g']}g, "
        f"Fat: {item['fat_g']}g, Fiber: {item['fiber_g']}g, "
        f"Sodium: {item['sodium_mg']}mg, Iron: {item['iron_mg']}mg, "
        f"Calcium: {item['calcium_mg']}mg.\n"
        f"Vitamins: {vitamins_str}.\n"
        f"Estimated cost: ₹{item['cost_per_serving_inr']} per serving.\n"
        f"Available in: {avail}. Season: {item.get('season', 'year-round')}.\n"
        f"Tags: {tags}."
    )


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts using the watsonx slate embedding model via the
    ibm-watsonx-ai SDK.
    """
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import Embeddings

    creds = Credentials(url=wx_cfg.url, api_key=wx_cfg.api_key)
    model = Embeddings(
        model_id=wx_cfg.embedding_model,
        credentials=creds,
        project_id=wx_cfg.project_id,
    )
    result = model.embed_documents(texts)
    return result


# ---------------------------------------------------------------------------
# Milvus collection management
# ---------------------------------------------------------------------------

def _get_or_create_collection(recreate: bool = False) -> Collection:
    """Return a Milvus Collection, creating it fresh if requested."""
    connections.connect(host=milvus_cfg.host, port=milvus_cfg.port)

    col_name = milvus_cfg.collection_name

    if utility.has_collection(col_name):
        if recreate:
            log.info("Dropping existing collection '%s' …", col_name)
            utility.drop_collection(col_name)
        else:
            log.info("Reusing existing collection '%s'.", col_name)
            col = Collection(col_name)
            col.load()
            return col

    log.info("Creating collection '%s' …", col_name)
    fields = [
        FieldSchema("id", DataType.VARCHAR, max_length=128, is_primary=True),
        FieldSchema("food_name", DataType.VARCHAR, max_length=256),
        FieldSchema("category", DataType.VARCHAR, max_length=64),
        FieldSchema("text_chunk", DataType.VARCHAR, max_length=4096),
        FieldSchema(
            "embedding",
            DataType.FLOAT_VECTOR,
            dim=milvus_cfg.embedding_dim,
        ),
        # Scalar fields used for metadata filtering
        FieldSchema("calories_kcal", DataType.FLOAT),
        FieldSchema("protein_g", DataType.FLOAT),
        FieldSchema("carbs_g", DataType.FLOAT),
        FieldSchema("fat_g", DataType.FLOAT),
        FieldSchema("cost_inr", DataType.FLOAT),
    ]
    schema = CollectionSchema(fields, description="Indian food nutrition knowledge base")
    col = Collection(col_name, schema)

    # IVF_FLAT index — good balance of speed vs accuracy for <50k vectors
    col.create_index(
        "embedding",
        {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        },
    )
    col.load()
    return col


# ---------------------------------------------------------------------------
# Main ingestion logic
# ---------------------------------------------------------------------------

def ingest(data_path: Path, recreate: bool = False) -> int:
    """
    Load food items from *data_path*, embed them, and upsert into Milvus.
    Returns the number of items ingested.
    """
    items: list[dict[str, Any]] = []
    with data_path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    log.info("Loaded %d food items from %s.", len(items), data_path)

    texts = [_food_to_text(item) for item in items]
    log.info("Embedding %d text chunks …", len(texts))
    embeddings = _embed_texts(texts)

    col = _get_or_create_collection(recreate=recreate)

    rows = {
        "id": [item["id"] for item in items],
        "food_name": [item["name"] for item in items],
        "category": [item["category"] for item in items],
        "text_chunk": texts,
        "embedding": embeddings,
        "calories_kcal": [float(item["calories_kcal"]) for item in items],
        "protein_g": [float(item["protein_g"]) for item in items],
        "carbs_g": [float(item["carbs_g"]) for item in items],
        "fat_g": [float(item["fat_g"]) for item in items],
        "cost_inr": [float(item["cost_per_serving_inr"]) for item in items],
    }

    col.insert(list(rows.values()))
    col.flush()
    log.info("Ingested %d items into '%s'.", len(items), milvus_cfg.collection_name)
    return len(items)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Indian food DB into Milvus.")
    parser.add_argument(
        "--data-path",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "indian_food_db.jsonl",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the Milvus collection before ingestion.",
    )
    args = parser.parse_args()

    ingest(args.data_path, recreate=args.recreate)


if __name__ == "__main__":
    main()
