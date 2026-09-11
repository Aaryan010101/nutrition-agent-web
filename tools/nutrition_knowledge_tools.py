"""
Nutrition Knowledge Agent — Tools

These functions are registered as watsonx Orchestrate skills for the
Nutrition Knowledge Agent. They retrieve food nutrition data from the Milvus
RAG store and summarise it using IBM Granite via watsonx.ai.

Each public function follows the watsonx Orchestrate tool signature pattern:
- typed parameters (primitives only, no complex objects)
- returns a plain dict or str so the agent can reason over the output
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import agent as agent_cfg, watsonx as wx_cfg
from rag.retriever import FoodKnowledgeRetriever

_retriever = FoodKnowledgeRetriever()


# ---------------------------------------------------------------------------
# Helpers — Granite inference
# ---------------------------------------------------------------------------

def _granite_generate(prompt: str, max_tokens: int = 512) -> str:
    """Send a prompt to Granite 3.3 8B Instruct and return the response text."""
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    creds = Credentials(url=wx_cfg.url, api_key=wx_cfg.api_key)
    model = ModelInference(
        model_id=wx_cfg.reasoning_model,
        credentials=creds,
        project_id=wx_cfg.project_id,
        params={
            "max_new_tokens": max_tokens,
            "temperature": wx_cfg.temperature,
            "top_p": wx_cfg.top_p,
        },
    )
    response = model.generate_text(prompt=prompt)
    return response.strip()


# ---------------------------------------------------------------------------
# Tool 1 — look_up_food_nutrition
# ---------------------------------------------------------------------------

def look_up_food_nutrition(food_name: str, servings: float = 1.0) -> dict[str, Any]:
    """
    Retrieve nutrition facts for a named Indian food item from the knowledge base.

    Parameters
    ----------
    food_name : str
        Common or regional name of the food (e.g. "dal makhani", "poha",
        "roti", "chana masala").
    servings : float
        Number of servings to scale nutrition values by (default 1.0).

    Returns
    -------
    dict with keys: food_name, serving_unit, calories_kcal, protein_g,
    carbs_g, fat_g, fiber_g, sodium_mg, cost_inr, explanation, disclaimer.
    """
    hits = _retriever.retrieve(query=food_name, top_k=3)
    if not hits:
        return {
            "error": f"No nutrition data found for '{food_name}'. "
                     "Please try a more specific Indian food name.",
            "disclaimer": agent_cfg.disclaimer,
        }

    # Use the top hit for the structured response
    top = hits[0]

    # Build a concise context block from all retrieved hits for the LLM
    context = "\n---\n".join(h["text_chunk"] for h in hits)

    prompt = (
        f"You are a warm Indian nutritionist helping a user understand {food_name}.\n"
        f"Using ONLY the following retrieved nutrition data, give a 2-3 sentence "
        f"explanation of this food's nutritional value and when it's a good choice. "
        f"Be specific, practical, and mention the cost. Do NOT invent values.\n\n"
        f"RETRIEVED DATA:\n{context}\n\n"
        f"EXPLANATION (2-3 sentences):"
    )

    explanation = _granite_generate(prompt, max_tokens=200)

    scale = servings
    return {
        "food_name": top["food_name"],
        "servings": servings,
        "calories_kcal": round(top["calories_kcal"] * scale, 1),
        "protein_g": round(top["protein_g"] * scale, 1),
        "carbs_g": round(top["carbs_g"] * scale, 1),
        "fat_g": round(top["fat_g"] * scale, 1),
        "cost_inr": round(top["cost_inr"] * scale, 1),
        "explanation": explanation,
        "disclaimer": agent_cfg.disclaimer,
    }


# ---------------------------------------------------------------------------
# Tool 2 — compare_foods
# ---------------------------------------------------------------------------

def compare_foods(food_a: str, food_b: str, goal: str = "general") -> dict[str, Any]:
    """
    Compare two Indian foods and explain which is better for a given goal.

    Parameters
    ----------
    food_a : str  First food to compare (e.g. "rajma").
    food_b : str  Second food to compare (e.g. "chana").
    goal   : str  User's goal: "weight_loss", "muscle_gain", or "maintenance".

    Returns
    -------
    dict with nutrition data for both foods, a winner recommendation, and a
    Granite-generated explanation grounded in retrieved data.
    """
    hits_a = _retriever.retrieve(query=food_a, top_k=1)
    hits_b = _retriever.retrieve(query=food_b, top_k=1)

    if not hits_a:
        return {"error": f"No data found for '{food_a}'.", "disclaimer": agent_cfg.disclaimer}
    if not hits_b:
        return {"error": f"No data found for '{food_b}'.", "disclaimer": agent_cfg.disclaimer}

    a, b = hits_a[0], hits_b[0]

    context = (
        f"Food A — {a['food_name']}:\n{a['text_chunk']}\n\n"
        f"Food B — {b['food_name']}:\n{b['text_chunk']}"
    )

    prompt = (
        f"You are a practical Indian nutritionist.\n"
        f"A user with the goal of '{goal}' wants to know which is better: "
        f"{food_a} or {food_b}.\n"
        f"Using ONLY the data below, give a clear 3-4 sentence comparison. "
        f"State which is better for this goal and WHY, mentioning key nutrients "
        f"and cost. Do NOT add information not present in the data.\n\n"
        f"DATA:\n{context}\n\n"
        f"COMPARISON:"
    )

    comparison = _granite_generate(prompt, max_tokens=300)

    return {
        "food_a": {
            "name": a["food_name"],
            "calories_kcal": a["calories_kcal"],
            "protein_g": a["protein_g"],
            "carbs_g": a["carbs_g"],
            "fat_g": a["fat_g"],
            "cost_inr": a["cost_inr"],
        },
        "food_b": {
            "name": b["food_name"],
            "calories_kcal": b["calories_kcal"],
            "protein_g": b["protein_g"],
            "carbs_g": b["carbs_g"],
            "fat_g": b["fat_g"],
            "cost_inr": b["cost_inr"],
        },
        "goal": goal,
        "comparison": comparison,
        "disclaimer": agent_cfg.disclaimer,
    }


# ---------------------------------------------------------------------------
# Tool 3 — search_foods_by_criteria
# ---------------------------------------------------------------------------

def search_foods_by_criteria(
    query: str,
    max_cost_inr: float = 100.0,
    min_protein_g: float = 0.0,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Search the food knowledge base for items matching free-text criteria with
    optional scalar filters.

    Parameters
    ----------
    query        : str   Natural language query (e.g. "high-iron breakfast",
                         "low-calorie snack", "protein for muscle gain").
    max_cost_inr : float Maximum cost per serving in INR (default 100).
    min_protein_g: float Minimum protein per serving in grams (default 0).
    top_k        : int   Number of results (1–10, default 5).

    Returns
    -------
    dict with a list of matching foods and their key nutrition facts.
    """
    top_k = max(1, min(top_k, 10))
    hits = _retriever.retrieve(query=query, top_k=top_k * 2)  # over-fetch for filter

    # Apply scalar filters (Milvus expression filter is done at retrieval time
    # for production; here we post-filter for simplicity)
    filtered = [
        h for h in hits
        if h["cost_inr"] <= max_cost_inr and h["protein_g"] >= min_protein_g
    ][:top_k]

    if not filtered:
        return {
            "message": "No foods matched your criteria. Try relaxing the filters.",
            "disclaimer": agent_cfg.disclaimer,
        }

    results = [
        {
            "food_name": h["food_name"],
            "category": h["category"],
            "calories_kcal": h["calories_kcal"],
            "protein_g": h["protein_g"],
            "cost_inr": h["cost_inr"],
            "snippet": h["text_chunk"][:200] + "…",
        }
        for h in filtered
    ]

    return {
        "query": query,
        "filters": {"max_cost_inr": max_cost_inr, "min_protein_g": min_protein_g},
        "results": results,
        "disclaimer": agent_cfg.disclaimer,
    }
