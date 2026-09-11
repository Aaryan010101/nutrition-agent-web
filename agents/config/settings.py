"""
Thali & Pulse — configuration & environment settings.

All sensitive values are read from environment variables.
Copy .env.example to .env and fill in your credentials before running.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WatsonxConfig:
    """IBM watsonx.ai credentials and model settings."""

    api_key: str = field(default_factory=lambda: os.environ["WATSONX_API_KEY"])
    project_id: str = field(default_factory=lambda: os.environ["WATSONX_PROJECT_ID"])
    url: str = field(
        default_factory=lambda: os.getenv(
            "WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
        )
    )

    # Primary reasoning model — Granite 3.3 8B Instruct (128k context)
    reasoning_model: str = field(
        default_factory=lambda: os.getenv(
            "WATSONX_REASONING_MODEL", "ibm/granite-3-3-8b-instruct"
        )
    )

    # Faster / cheaper model for simple lookup tasks
    fast_model: str = field(
        default_factory=lambda: os.getenv(
            "WATSONX_FAST_MODEL", "ibm/granite-3-3-2b-instruct"
        )
    )

    # Embedding model for RAG document ingestion
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "WATSONX_EMBEDDING_MODEL", "ibm/slate-125m-english-rtrvr"
        )
    )

    # Generation parameters
    max_new_tokens: int = 1024
    temperature: float = 0.2
    top_p: float = 0.9


@dataclass
class MilvusConfig:
    """Milvus vector-store connection for RAG food knowledge base."""

    host: str = field(default_factory=lambda: os.getenv("MILVUS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("MILVUS_PORT", "19530")))
    collection_name: str = field(
        default_factory=lambda: os.getenv(
            "MILVUS_COLLECTION", "indian_food_nutrition"
        )
    )
    # Dimension must match the embedding model output
    embedding_dim: int = 768


@dataclass
class AgentConfig:
    """Top-level agent runtime settings."""

    # Maximum number of tool-call iterations per agent turn
    max_iterations: int = 10

    # Default city when user hasn't provided one
    default_city: str = "Mumbai"

    # INR per 1000 kcal ceiling used as a sanity check on meal costs
    max_cost_per_1000_kcal_inr: float = 150.0

    # Disclaimer appended to every response
    disclaimer: str = (
        "⚠️ Disclaimer: Thali & Pulse provides general nutrition information only. "
        "It is not a substitute for personalised medical or dietary advice. "
        "Please consult a registered dietitian or physician before making significant "
        "changes to your diet, especially if you have a medical condition."
    )


# Singletons used throughout the application
watsonx = WatsonxConfig()
milvus = MilvusConfig()
agent = AgentConfig()
