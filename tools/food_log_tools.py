"""
Food Log & Feedback Agent — Tools

Accepts a meal description (text or photo description) from the user,
looks up all mentioned foods in the RAG knowledge base, computes
nutritional totals, and compares them against the user's daily target.

Public tools:
  - analyze_meal_text
  - check_daily_balance
  - log_meal
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import agent as agent_cfg, watsonx as wx_cfg
from rag.retriever import FoodKnowledgeRetriever
from tools.models import Goal, NutritionSummary

_retriever = FoodKnowledgeRetriever()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _granite_generate(prompt: str, max_tokens: int = 512) -> str:
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
    return model.generate_text(prompt=prompt).strip()


def _extract_food_items(description: str) -> list[str]:
    """
    Ask Granite to extract individual food items mentioned in a
    meal description or photo description.
    Returns a list of food name strings.
    """
    prompt = (
        "You are a nutrition assistant. Extract all distinct food items "
        "mentioned in the following meal description. "
        "Return ONLY a JSON array of short food names (e.g. [\"dal\", \"roti\", \"dahi\"]). "
        "No explanation, no markdown, just the JSON array.\n\n"
        f"MEAL DESCRIPTION: {description}\n\n"
        "JSON ARRAY:"
    )
    raw = _granite_generate(prompt, max_tokens=150)

    # Parse the JSON array safely
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: treat the whole description as a single query
    return [description]


# ---------------------------------------------------------------------------
# Tool 1 — analyze_meal_text
# ---------------------------------------------------------------------------

def analyze_meal_text(
    meal_description: str,
    goal: str = "maintenance",
) -> dict[str, Any]:
    """
    Analyse a meal described in text (or as a photo description) and return
    detailed nutrition facts and feedback.

    Parameters
    ----------
    meal_description : str
        Free-text description of what the user ate, e.g.
        "2 rotis, dal fry, a small bowl of rice, and a glass of chaas"
        OR a photo description like "plate with idli, sambar, and coconut chutney".
    goal : str
        User's goal: "weight_loss", "muscle_gain", or "maintenance".

    Returns
    -------
    dict with individual item breakdown, meal totals, a fit assessment,
    and a Granite-generated feedback message.
    """
    food_items = _extract_food_items(meal_description)

    item_details: list[dict] = []
    total = NutritionSummary()

    for item_name in food_items:
        hits = _retriever.retrieve(query=item_name, top_k=1)
        if hits:
            h = hits[0]
            item_details.append(
                {
                    "item": h["food_name"],
                    "calories_kcal": h["calories_kcal"],
                    "protein_g": h["protein_g"],
                    "carbs_g": h["carbs_g"],
                    "fat_g": h["fat_g"],
                    "cost_inr": h["cost_inr"],
                }
            )
            total.calories_kcal += h["calories_kcal"]
            total.protein_g += h["protein_g"]
            total.carbs_g += h["carbs_g"]
            total.fat_g += h["fat_g"]
            total.cost_inr += h["cost_inr"]
        else:
            item_details.append(
                {
                    "item": item_name,
                    "note": "Not found in knowledge base — nutrition not counted.",
                }
            )

    # Build context for feedback generation
    context_lines = "\n".join(
        f"  - {d['item']}: {d.get('calories_kcal', '?')} kcal, "
        f"{d.get('protein_g', '?')}g protein"
        for d in item_details
    )

    goal_context = {
        Goal.WEIGHT_LOSS: "This meal should be low-calorie and high-fibre.",
        Goal.MUSCLE_GAIN: "This meal should be high in protein.",
        Goal.MAINTENANCE: "This meal should be balanced.",
    }.get(goal, "This meal should be balanced.")

    prompt = (
        f"You are a practical, warm Indian nutritionist reviewing a user's meal.\n"
        f"Goal: {goal} — {goal_context}\n\n"
        f"MEAL BREAKDOWN:\n{context_lines}\n"
        f"TOTAL: {total.calories_kcal:.0f} kcal, {total.protein_g:.0f}g protein, "
        f"{total.carbs_g:.0f}g carbs, {total.fat_g:.0f}g fat\n\n"
        f"Write 3-4 sentences of honest, friendly feedback. "
        f"Mention what's good, what could be improved, and one practical suggestion "
        f"using common Indian foods. Do NOT invent nutrition values.\n\n"
        f"FEEDBACK:"
    )
    feedback = _granite_generate(prompt, max_tokens=250)

    return {
        "meal_description": meal_description,
        "extracted_items": food_items,
        "item_breakdown": item_details,
        "meal_totals": {
            "calories_kcal": round(total.calories_kcal, 1),
            "protein_g": round(total.protein_g, 1),
            "carbs_g": round(total.carbs_g, 1),
            "fat_g": round(total.fat_g, 1),
            "cost_inr": round(total.cost_inr, 1),
        },
        "feedback": feedback,
        "disclaimer": agent_cfg.disclaimer,
    }


# ---------------------------------------------------------------------------
# Tool 2 — check_daily_balance
# ---------------------------------------------------------------------------

def check_daily_balance(
    logged_calories: float,
    logged_protein_g: float,
    logged_carbs_g: float,
    logged_fat_g: float,
    target_calories: int,
    target_protein_g: float,
    meals_logged: int = 3,
) -> dict[str, Any]:
    """
    Compare what the user has eaten so far today against their daily targets.

    Parameters
    ----------
    logged_calories   : float  Total kcal consumed so far today.
    logged_protein_g  : float  Total protein consumed so far (grams).
    logged_carbs_g    : float  Total carbs consumed so far (grams).
    logged_fat_g      : float  Total fat consumed so far (grams).
    target_calories   : int    User's daily calorie target.
    target_protein_g  : float  User's daily protein target (grams).
    meals_logged      : int    Number of meals logged so far today (default 3).

    Returns
    -------
    dict with remaining allowances, macro balance percentages, and a
    plain-language status message.
    """
    remaining_cal = target_calories - logged_calories
    remaining_protein = target_protein_g - logged_protein_g

    cal_pct = (logged_calories / target_calories * 100) if target_calories else 0
    protein_pct = (logged_protein_g / target_protein_g * 100) if target_protein_g else 0

    total_macro_g = logged_protein_g + logged_carbs_g + logged_fat_g
    macro_split = (
        {
            "protein_pct": round(logged_protein_g / total_macro_g * 100, 1),
            "carbs_pct": round(logged_carbs_g / total_macro_g * 100, 1),
            "fat_pct": round(logged_fat_g / total_macro_g * 100, 1),
        }
        if total_macro_g > 0
        else {"protein_pct": 0, "carbs_pct": 0, "fat_pct": 0}
    )

    # Simple heuristic status
    if cal_pct > 105:
        cal_status = "⚠️ You've exceeded your calorie target for today."
    elif cal_pct >= 85:
        cal_status = "✅ Calorie intake is on track."
    elif meals_logged >= 3:
        cal_status = "⬇️ You're under your calorie target — make sure dinner is filling."
    else:
        cal_status = f"ℹ️ {cal_pct:.0f}% of daily calories consumed ({meals_logged} meals logged)."

    protein_status = (
        "✅ Protein target nearly met."
        if protein_pct >= 80
        else f"⬇️ Protein is low — add a dal, egg, or paneer to your next meal."
    )

    return {
        "calories_consumed": round(logged_calories, 1),
        "calories_target": target_calories,
        "calories_remaining": round(remaining_cal, 1),
        "protein_consumed_g": round(logged_protein_g, 1),
        "protein_target_g": round(target_protein_g, 1),
        "protein_remaining_g": round(remaining_protein, 1),
        "macro_split_pct": macro_split,
        "calorie_status": cal_status,
        "protein_status": protein_status,
        "disclaimer": agent_cfg.disclaimer,
    }


# ---------------------------------------------------------------------------
# Tool 3 — log_meal (stateless summary for LLM session context)
# ---------------------------------------------------------------------------

def log_meal(
    slot: str,
    meal_description: str,
    goal: str = "maintenance",
) -> dict[str, Any]:
    """
    Log a single meal and return a concise nutrition summary suitable for
    accumulating across a session.

    Parameters
    ----------
    slot             : str  "breakfast", "lunch", "snack", or "dinner".
    meal_description : str  What the user ate.
    goal             : str  User's goal string.

    Returns
    -------
    dict with slot, nutrition totals, and a one-sentence status line.
    """
    analysis = analyze_meal_text(meal_description=meal_description, goal=goal)
    totals = analysis["meal_totals"]

    status = (
        f"{slot.title()} logged: {totals['calories_kcal']} kcal, "
        f"{totals['protein_g']}g protein, ₹{totals['cost_inr']:.0f}."
    )

    return {
        "slot": slot,
        "meal_description": meal_description,
        "nutrition": totals,
        "status": status,
        "disclaimer": agent_cfg.disclaimer,
    }
