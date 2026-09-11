"""
RAG retrieval utilities shared by all Thali & Pulse agents.

`FoodKnowledgeRetriever` wraps a Milvus collection and the watsonx embedding
model to answer semantic food-nutrition queries at runtime.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from pymilvus import Collection, connections

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.settings import milvus as milvus_cfg, watsonx as wx_cfg


class FoodKnowledgeRetriever:
    """
    Retrieve the most semantically similar food records from the Milvus
    vector store.  Results include the raw text chunk (for LLM context) and
    key nutrition scalars for downstream processing.
    """

    _instance: "FoodKnowledgeRetriever | None" = None

    def __new__(cls) -> "FoodKnowledgeRetriever":
        """Singleton — open Milvus connection once per process."""
        if cls._instance is None:
            obj = super().__new__(cls)
            obj._ready = False
            cls._instance = obj
        return cls._instance

    def _ensure_connected(self) -> None:
        if self._ready:
            return
        connections.connect(host=milvus_cfg.host, port=milvus_cfg.port)
        self._collection = Collection(milvus_cfg.collection_name)
        self._collection.load()
        self._ready = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        category_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Embed *query* and return the *top_k* most similar food items.

        Parameters
        ----------
        query:
            Free-text question, e.g. "high protein vegetarian lunch option
            under ₹40".
        top_k:
            Number of results to return.
        category_filter:
            Optional Milvus scalar filter, e.g. ``"category == 'Legume'"``.

        Returns
        -------
        list of dicts, each containing:
            ``id``, ``food_name``, ``category``, ``text_chunk``,
            ``calories_kcal``, ``protein_g``, ``carbs_g``, ``fat_g``,
            ``cost_inr``.
        """
        self._ensure_connected()

        query_vec = self._embed_query(query)

        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
        results = self._collection.search(
            data=[query_vec],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=category_filter,
            output_fields=[
                "id",
                "food_name",
                "category",
                "text_chunk",
                "calories_kcal",
                "protein_g",
                "carbs_g",
                "fat_g",
                "cost_inr",
            ],
        )

        hits: list[dict[str, Any]] = []
        for hit in results[0]:
            entity = hit.entity
            hits.append(
                {
                    "id": entity.get("id"),
                    "food_name": entity.get("food_name"),
                    "category": entity.get("category"),
                    "text_chunk": entity.get("text_chunk"),
                    "calories_kcal": entity.get("calories_kcal"),
                    "protein_g": entity.get("protein_g"),
                    "carbs_g": entity.get("carbs_g"),
                    "fat_g": entity.get("fat_g"),
                    "cost_inr": entity.get("cost_inr"),
                    "similarity_score": hit.score,
                }
            )
        return hits

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _embed_query(text: str) -> list[float]:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import Embeddings

        creds = Credentials(url=wx_cfg.url, api_key=wx_cfg.api_key)
        model = Embeddings(
            model_id=wx_cfg.embedding_model,
            credentials=creds,
            project_id=wx_cfg.project_id,
        )
        return model.embed_documents([text])[0]
