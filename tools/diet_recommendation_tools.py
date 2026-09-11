"""
Diet Recommendation Agent — Tools

Builds personalised, budget-constrained Indian meal plans using:
  1. RAG retrieval to find region- and goal-appropriate foods
  2. Granite LLM to compose natural-language meal descriptions
  3. Deterministic budget / calorie balancing logic

Public tools exposed as watsonx Orchestrate skills:
  - generate_day_plan
  - swap_meal
  - generate_grocery_list
  - estimate_weekly_cost
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import agent as agent_cfg, watsonx as wx_cfg
from rag.retriever import FoodKnowledgeRetriever
from tools.models import Goal, MealSlot, NutritionSummary

_retriever = FoodKnowledgeRetriever()

# Macronutrient distribution targets per goal
_MACRO_TARGETS: dict[str, dict[str, float]] = {
    Goal.WEIGHT_LOSS: {"protein_pct": 0.35, "carbs_pct": 0.40, "fat_pct": 0.25},
    Goal.MUSCLE_GAIN: {"protein_pct": 0.35, "carbs_pct": 0.45, "fat_pct": 0.20},
    Goal.MAINTENANCE: {"protein_pct": 0.25, "carbs_pct": 0.50, "fat_pct": 0.25},
}


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


def _slot_query(slot: str, goal: str, city: str) -> str:
    """Build a semantic query string for a meal slot."""
    slot_hints = {
        "breakfast": "light energising breakfast",
        "lunch":     "filling satisfying lunch",
        "snack":     "healthy affordable snack",
        "dinner":    "light easy-to-digest dinner",
    }
    goal_hints = {
        Goal.WEIGHT_LOSS: "low calorie high fiber",
        Goal.MUSCLE_GAIN: "high protein",
        Goal.MAINTENANCE: "balanced",
    }
    return (
        f"{slot_hints.get(slot, slot)} "
        f"{goal_hints.get(goal, 'balanced')} "
        f"Indian food typical in {city}"
    )


def _build_meal_slot(
    slot: str,
    goal: str,
    city: str,
    budget_inr: float,
    calorie_target: int,
    exclude_ids: set[str] | None = None,
) -> MealSlot:
    """
    Retrieve candidates and greedily pick items to fill a meal slot within
    the per-slot calorie and budget allocation.
    """
    exclude_ids = exclude_ids or set()
    calorie_fractions = {
        "breakfast": 0.25,
        "lunch":     0.35,
        "snack":     0.10,
        "dinner":    0.30,
    }
    slot_cal_target = calorie_target * calorie_fractions.get(slot, 0.25)
    slot_budget = budget_inr * calorie_fractions.get(slot, 0.25)

    query = _slot_query(slot, goal, city)
    candidates = _retriever.retrieve(query=query, top_k=10)
    candidates = [c for c in candidates if c["id"] not in exclude_ids]

    chosen: list[dict] = []
    running_cal = 0.0
    running_cost = 0.0

    for c in candidates:
        if running_cal >= slot_cal_target * 0.90:
            break
        if running_cost + c["cost_inr"] > slot_budget * 1.10:
            continue
        chosen.append(c)
        running_cal += c["calories_kcal"]
        running_cost += c["cost_inr"]
        if len(chosen) >= 3:  # cap items per meal
            break

    if not chosen and candidates:
        chosen = [candidates[0]]  # fallback: at least one item

    nutrition = NutritionSummary(
        calories_kcal=sum(c["calories_kcal"] for c in chosen),
        protein_g=sum(c["protein_g"] for c in chosen),
        carbs_g=sum(c["carbs_g"] for c in chosen),
        fat_g=sum(c["fat_g"] for c in chosen),
        cost_inr=sum(c["cost_inr"] for c in chosen),
    )

    return MealSlot(
        slot=slot,
        items=[c["food_name"] for c in chosen],
        nutrition=nutrition,
    )


# ---------------------------------------------------------------------------
# Tool 1 — generate_day_plan
# ---------------------------------------------------------------------------

def generate_day_plan(
    age: int,
    goal: str,
    city: str,
    daily_budget_inr: float,
    is_vegetarian: bool = True,
    weight_kg: float = 60.0,
    height_cm: float = 165.0,
) -> dict[str, Any]:
    """
    Generate a personalised full-day Indian meal plan.

    Parameters
    ----------
    age             : int   User's age in years.
    goal            : str   "weight_loss", "muscle_gain", or "maintenance".
    city            : str   User's city (influences regional food selection).
    daily_budget_inr: float Daily food budget in INR.
    is_vegetarian   : bool  Exclude non-vegetarian items (default True).
    weight_kg       : float Body weight in kg (default 60.0).
    height_cm       : float Height in cm (default 165.0).

    Returns
    -------
    dict with:
      - meals: list of {slot, items, nutrition} dicts
      - daily_totals: aggregate nutrition
      - grocery_list: list of ingredients
      - narrative: Granite-generated warm description of the plan
      - disclaimer
    """
    from tools.models import Goal as GoalEnum, UserProfile

    try:
        goal_enum = GoalEnum(goal)
    except ValueError:
        goal_enum = GoalEnum.MAINTENANCE

    profile = UserProfile(
        age=age,
        goal=goal_enum,
        city=city,
        monthly_budget_inr=daily_budget_inr * 30,
        is_vegetarian=is_vegetarian,
        weight_kg=weight_kg,
        height_cm=height_cm,
    )

    slots = ["breakfast", "lunch", "snack", "dinner"]
    meals: list[dict] = []
    used_ids: set[str] = set()

    for slot in slots:
        meal_slot = _build_meal_slot(
            slot=slot,
            goal=goal,
            city=city,
            budget_inr=profile.daily_budget_inr,
            calorie_target=profile.target_calories,
            exclude_ids=used_ids,
        )
        # Track used items to promote variety
        used_ids.update(meal_slot.items)
        meals.append(
            {
                "slot": meal_slot.slot,
                "items": meal_slot.items,
                "nutrition": {
                    "calories_kcal": meal_slot.nutrition.calories_kcal,
                    "protein_g": meal_slot.nutrition.protein_g,
                    "carbs_g": meal_slot.nutrition.carbs_g,
                    "fat_g": meal_slot.nutrition.fat_g,
                    "cost_inr": meal_slot.nutrition.cost_inr,
                },
            }
        )

    # Aggregate totals
    total_cal = sum(m["nutrition"]["calories_kcal"] for m in meals)
    total_protein = sum(m["nutrition"]["protein_g"] for m in meals)
    total_carbs = sum(m["nutrition"]["carbs_g"] for m in meals)
    total_fat = sum(m["nutrition"]["fat_g"] for m in meals)
    total_cost = sum(m["nutrition"]["cost_inr"] for m in meals)

    # Grocery list — unique items across all meals
    seen: set[str] = set()
    grocery_list: list[str] = []
    for m in meals:
        for item in m["items"]:
            if item not in seen:
                seen.add(item)
                grocery_list.append(item)

    # Granite narrative
    meal_summary = "\n".join(
        f"  {m['slot'].title()}: {', '.join(m['items'])} "
        f"({m['nutrition']['calories_kcal']:.0f} kcal, ₹{m['nutrition']['cost_inr']:.0f})"
        for m in meals
    )
    prompt = (
        f"You are a warm, practical Indian nutritionist.\n"
        f"Write a 4-5 sentence friendly introduction to the following day's meal plan "
        f"for a {age}-year-old with goal '{goal}' living in {city}. "
        f"Mention WHY the foods are chosen, reference cost-efficiency, and use "
        f"a warm, local tone. Do NOT add nutritional claims not supported by the plan.\n\n"
        f"MEAL PLAN:\n{meal_summary}\n\n"
        f"Total: {total_cal:.0f} kcal | Protein: {total_protein:.0f}g | "
        f"Cost: ₹{total_cost:.0f}\n\n"
        f"NARRATIVE:"
    )
    narrative = _granite_generate(prompt, max_tokens=300)

    return {
        "meals": meals,
        "daily_totals": {
            "calories_kcal": round(total_cal, 1),
            "protein_g": round(total_protein, 1),
            "carbs_g": round(total_carbs, 1),
            "fat_g": round(total_fat, 1),
            "total_cost_inr": round(total_cost, 1),
            "budget_inr": round(daily_budget_inr, 1),
            "within_budget": total_cost <= daily_budget_inr,
        },
        "grocery_list": grocery_list,
        "narrative": narrative,
        "disclaimer": agent_cfg.disclaimer,
    }


# ---------------------------------------------------------------------------
# Tool 2 — swap_meal
# ---------------------------------------------------------------------------

def swap_meal(
    slot: str,
    current_items: str,
    goal: str,
    city: str,
    calorie_allowance: float,
    budget_allowance_inr: float,
    reason: str = "",
) -> dict[str, Any]:
    """
    Suggest an alternative for a single meal slot that fits the same
    calorie and budget constraints.

    Parameters
    ----------
    slot               : str   Meal slot to replace: "breakfast", "lunch",
                               "snack", or "dinner".
    current_items      : str   Comma-separated list of current meal items.
    goal               : str   User's goal string.
    city               : str   User's city.
    calorie_allowance  : float Maximum calories for this slot.
    budget_allowance_inr: float Maximum spend for this slot in INR.
    reason             : str   Optional reason for swap (e.g. "don't like paneer").

    Returns
    -------
    dict with suggested alternative items and their nutrition, plus a
    Granite explanation of why the swap is nutritionally equivalent.
    """
    exclude_names = {s.strip().lower() for s in current_items.split(",")}

    query = (
        f"alternative {slot} option {goal.replace('_', ' ')} "
        f"Indian {city} {reason}"
    )
    candidates = _retriever.retrieve(query=query, top_k=10)
    candidates = [
        c for c in candidates
        if c["food_name"].lower() not in exclude_names
        and c["calories_kcal"] <= calorie_allowance
        and c["cost_inr"] <= budget_allowance_inr
    ]

    if not candidates:
        return {
            "message": "No valid swap found within your calorie and budget limits.",
            "disclaimer": agent_cfg.disclaimer,
        }

    # Greedy fill up to calorie_allowance
    chosen: list[dict] = []
    used_cal = 0.0
    used_cost = 0.0
    for c in candidates:
        if used_cal + c["calories_kcal"] > calorie_allowance * 1.10:
            continue
        if used_cost + c["cost_inr"] > budget_allowance_inr * 1.10:
            continue
        chosen.append(c)
        used_cal += c["calories_kcal"]
        used_cost += c["cost_inr"]
        if len(chosen) >= 3:
            break

    if not chosen:
        chosen = [candidates[0]]

    swap_names = ", ".join(c["food_name"] for c in chosen)
    context = "\n".join(c["text_chunk"] for c in chosen)

    prompt = (
        f"You are a helpful Indian nutritionist.\n"
        f"A user wants to swap their {slot} ({current_items}) "
        f"for something else. You are suggesting: {swap_names}.\n"
        f"Using ONLY the data below, write 2-3 sentences explaining why this "
        f"swap is a good nutritional alternative for their '{goal}' goal. "
        f"Mention cost if relevant.\n\n"
        f"DATA:\n{context}\n\n"
        f"EXPLANATION:"
    )
    explanation = _granite_generate(prompt, max_tokens=200)

    return {
        "slot": slot,
        "original_items": current_items,
        "suggested_items": [c["food_name"] for c in chosen],
        "nutrition": {
            "calories_kcal": round(sum(c["calories_kcal"] for c in chosen), 1),
            "protein_g": round(sum(c["protein_g"] for c in chosen), 1),
            "carbs_g": round(sum(c["carbs_g"] for c in chosen), 1),
            "fat_g": round(sum(c["fat_g"] for c in chosen), 1),
            "cost_inr": round(sum(c["cost_inr"] for c in chosen), 1),
        },
        "explanation": explanation,
        "disclaimer": agent_cfg.disclaimer,
    }


# ---------------------------------------------------------------------------
# Tool 3 — generate_grocery_list
# ---------------------------------------------------------------------------

def generate_grocery_list(
    meals_json: str,
    servings: int = 1,
    days: int = 1,
) -> dict[str, Any]:
    """
    Generate a consolidated grocery list from a meals plan.

    Parameters
    ----------
    meals_json : str  JSON string — list of meal dicts with 'items' key.
    servings   : int  Number of people to cater for (default 1).
    days       : int  Number of days this plan covers (default 1).

    Returns
    -------
    dict with a grocery list, estimated total cost, and shopping tips.
    """
    import json as _json

    try:
        meals = _json.loads(meals_json)
    except Exception:
        return {"error": "Invalid meals_json. Pass a valid JSON list.", "disclaimer": agent_cfg.disclaimer}

    item_counts: dict[str, int] = {}
    for meal in meals:
        for item in meal.get("items", []):
            item_counts[item] = item_counts.get(item, 0) + (servings * days)

    # Estimate cost per item from the retriever
    cost_estimates: dict[str, float] = {}
    for item_name in item_counts:
        hits = _retriever.retrieve(query=item_name, top_k=1)
        if hits:
            cost_estimates[item_name] = hits[0]["cost_inr"]

    grocery = [
        {
            "item": item,
            "quantity": f"{count} serving(s)",
            "estimated_cost_inr": round(cost_estimates.get(item, 0.0) * count, 1),
        }
        for item, count in item_counts.items()
    ]

    total_cost = sum(g["estimated_cost_inr"] for g in grocery)

    return {
        "grocery_list": grocery,
        "estimated_total_cost_inr": round(total_cost, 1),
        "tip": (
            "Buy dals, grains, and spices in bulk from your local kirana store "
            "for best value. Fresh vegetables should ideally be bought daily or "
            "every other day."
        ),
        "disclaimer": agent_cfg.disclaimer,
    }


# ---------------------------------------------------------------------------
# Tool 4 — estimate_weekly_cost
# ---------------------------------------------------------------------------

def estimate_weekly_cost(
    daily_cost_inr: float,
    monthly_budget_inr: float,
) -> dict[str, Any]:
    """
    Project weekly and monthly food costs and check against the user's budget.

    Parameters
    ----------
    daily_cost_inr      : float Estimated cost for one day's plan in INR.
    monthly_budget_inr  : float User's stated monthly food budget in INR.

    Returns
    -------
    dict with weekly and monthly cost projections and budget status.
    """
    weekly = daily_cost_inr * 7
    monthly = daily_cost_inr * 30
    remaining = monthly_budget_inr - monthly
    pct_used = (monthly / monthly_budget_inr * 100) if monthly_budget_inr > 0 else 0

    status = "✅ Within budget" if remaining >= 0 else "⚠️ Over budget"

    return {
        "daily_cost_inr": round(daily_cost_inr, 1),
        "weekly_cost_inr": round(weekly, 1),
        "monthly_cost_inr": round(monthly, 1),
        "monthly_budget_inr": round(monthly_budget_inr, 1),
        "remaining_inr": round(remaining, 1),
        "budget_utilisation_pct": round(pct_used, 1),
        "status": status,
        "tip": (
            "If you're over budget, try replacing one paneer or non-veg meal "
            "per day with dal or eggs — you can save ₹30–₹60 per day without "
            "sacrificing protein."
        ) if remaining < 0 else (
            "You have budget headroom — consider adding a glass of milk or a "
            "seasonal fruit as an afternoon snack for extra micronutrients."
        ),
        "disclaimer": agent_cfg.disclaimer,
    }
