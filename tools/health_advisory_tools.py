"""
Health Advisory Agent — Tools

Analyses aggregated daily nutrition data and flags preventive health
notes — e.g. excessive sodium, inadequate fibre, low iron for women.

These are NOT medical diagnoses; they are general wellness flags grounded
in the Indian Council of Medical Research (ICMR) Recommended Dietary
Allowances (RDA) and WHO guidelines.

Public tools:
  - flag_health_concerns
  - get_rda_guidance
  - generate_weekly_health_summary
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import agent as agent_cfg, watsonx as wx_cfg


# ---------------------------------------------------------------------------
# ICMR RDA reference ranges (adult, sedentary–moderate activity)
# Source: ICMR NIN Nutrient Requirements 2020
# ---------------------------------------------------------------------------

_RDA = {
    "calories_kcal": {"min": 1600, "max": 2800},
    "protein_g":     {"min": 40.0, "max": 120.0},     # per day
    "fat_g":         {"min": 20.0, "max": 100.0},
    "fiber_g":       {"min": 25.0, "max": 40.0},
    "sodium_mg":     {"min": 0.0,  "max": 2000.0},    # WHO limit 2000 mg
    "iron_mg":       {"min": 17.0, "max": 45.0},      # higher for women
    "calcium_mg":    {"min": 600.0, "max": 2000.0},
}

# Flags — threshold multipliers relative to max
_HIGH_SODIUM_THRESHOLD_MG = 1800     # approaching WHO 2g limit
_LOW_FIBER_THRESHOLD_G    = 20.0
_LOW_IRON_THRESHOLD_MG    = 12.0
_LOW_PROTEIN_THRESHOLD_G  = 40.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _granite_generate(prompt: str, max_tokens: int = 400) -> str:
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    creds = Credentials(url=wx_cfg.url, api_key=wx_cfg.api_key)
    model = ModelInference(
        model_id=wx_cfg.reasoning_model,
        credentials=creds,
        project_id=wx_cfg.project_id,
        params={
            "max_new_tokens": max_tokens,
            "temperature": 0.1,   # conservative for health advice
            "top_p": wx_cfg.top_p,
        },
    )
    return model.generate_text(prompt=prompt).strip()


# ---------------------------------------------------------------------------
# Tool 1 — flag_health_concerns
# ---------------------------------------------------------------------------

def flag_health_concerns(
    calories_kcal: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    fiber_g: float,
    sodium_mg: float,
    iron_mg: float,
    calcium_mg: float,
    age: int = 30,
    is_female: bool = False,
    goal: str = "maintenance",
) -> dict[str, Any]:
    """
    Scan a day's nutrition totals for preventive health concerns based on
    ICMR/WHO reference values.

    Parameters
    ----------
    calories_kcal : float  Total daily calories consumed.
    protein_g     : float  Total daily protein in grams.
    carbs_g       : float  Total daily carbohydrates in grams.
    fat_g         : float  Total daily fat in grams.
    fiber_g       : float  Total daily dietary fibre in grams.
    sodium_mg     : float  Total daily sodium in milligrams.
    iron_mg       : float  Total daily iron in milligrams.
    calcium_mg    : float  Total daily calcium in milligrams.
    age           : int    User's age (affects RDA thresholds).
    is_female     : bool   Female users have higher iron RDA.
    goal          : str    User's goal string.

    Returns
    -------
    dict with a list of flags (severity + message) and a Granite-generated
    advisory paragraph.
    """
    flags: list[dict[str, str]] = []

    # Sodium
    if sodium_mg > _HIGH_SODIUM_THRESHOLD_MG:
        flags.append({
            "nutrient": "Sodium",
            "severity": "⚠️ Warning",
            "value": f"{sodium_mg:.0f} mg",
            "note": (
                f"Your sodium intake ({sodium_mg:.0f} mg) is approaching the "
                f"WHO recommended limit of 2000 mg/day. Consider reducing "
                f"pickles, papad, and packaged snacks."
            ),
        })

    # Fibre
    if fiber_g < _LOW_FIBER_THRESHOLD_G:
        flags.append({
            "nutrient": "Fibre",
            "severity": "ℹ️ Note",
            "value": f"{fiber_g:.1f} g",
            "note": (
                f"Fibre intake ({fiber_g:.1f} g) is below 25 g/day. "
                f"Add a katori of dal or sabzi, or choose whole wheat roti "
                f"over maida products."
            ),
        })

    # Protein
    protein_min = 50.0 if age < 60 else 45.0
    if protein_g < _LOW_PROTEIN_THRESHOLD_G:
        flags.append({
            "nutrient": "Protein",
            "severity": "⚠️ Warning",
            "value": f"{protein_g:.1f} g",
            "note": (
                f"Protein intake ({protein_g:.1f} g) is below the minimum "
                f"recommended {protein_min} g/day. Include a serving of dal, "
                f"eggs, paneer, or sprouts in your next meal."
            ),
        })

    # Iron (women have higher RDA: ~21 mg/day pre-menopause)
    iron_rda = 21.0 if is_female and age < 50 else 17.0
    if iron_mg < _LOW_IRON_THRESHOLD_MG:
        flags.append({
            "nutrient": "Iron",
            "severity": "ℹ️ Note",
            "value": f"{iron_mg:.1f} mg",
            "note": (
                f"Iron intake ({iron_mg:.1f} mg) is low. "
                f"Add iron-rich foods like poha with peanuts, rajma, or "
                f"spinach (palak). Pair with a vitamin C source (lemon, amla) "
                f"to enhance absorption."
            ),
        })

    # Calcium
    if calcium_mg < 500:
        flags.append({
            "nutrient": "Calcium",
            "severity": "ℹ️ Note",
            "value": f"{calcium_mg:.0f} mg",
            "note": (
                f"Calcium intake ({calcium_mg:.0f} mg) is below 600 mg/day. "
                f"Add a glass of milk, a katori of dahi, or some ragi to your "
                f"daily plan."
            ),
        })

    # Calorie surplus for weight loss goal
    if goal == "weight_loss" and calories_kcal > 2400:
        flags.append({
            "nutrient": "Calories",
            "severity": "⚠️ Warning",
            "value": f"{calories_kcal:.0f} kcal",
            "note": (
                f"Calorie intake ({calories_kcal:.0f} kcal) may be too high "
                f"for a weight-loss goal. Consider smaller portions or replacing "
                f"one rice serving with more dal and sabzi."
            ),
        })

    # Build Granite advisory if there are flags
    if flags:
        flag_lines = "\n".join(
            f"  - {f['severity']} {f['nutrient']}: {f['note']}" for f in flags
        )
        prompt = (
            f"You are a careful, warm Indian health advisor (NOT a doctor).\n"
            f"Based on the following nutritional flags for today's diet, write a "
            f"3-4 sentence advisory paragraph using common Indian foods as solutions. "
            f"Use a reassuring tone. Always end with the reminder that this is "
            f"general guidance and not a substitute for professional medical advice.\n\n"
            f"FLAGS:\n{flag_lines}\n\n"
            f"ADVISORY:"
        )
        advisory = _granite_generate(prompt, max_tokens=300)
    else:
        advisory = (
            "Great job! Your nutrition today looks well-balanced. "
            "Keep up the variety and stay hydrated."
        )

    return {
        "flags": flags,
        "flag_count": len(flags),
        "advisory": advisory,
        "summary": {
            "calories_kcal": round(calories_kcal, 1),
            "protein_g": round(protein_g, 1),
            "fiber_g": round(fiber_g, 1),
            "sodium_mg": round(sodium_mg, 1),
            "iron_mg": round(iron_mg, 1),
            "calcium_mg": round(calcium_mg, 1),
        },
        "disclaimer": agent_cfg.disclaimer,
    }


# ---------------------------------------------------------------------------
# Tool 2 — get_rda_guidance
# ---------------------------------------------------------------------------

def get_rda_guidance(
    nutrient: str,
    age: int = 30,
    is_female: bool = False,
) -> dict[str, Any]:
    """
    Return ICMR/WHO reference dietary allowance for a specific nutrient.

    Parameters
    ----------
    nutrient  : str  Nutrient name, e.g. "protein", "iron", "calcium",
                     "sodium", "fiber", "calories".
    age       : int  User's age.
    is_female : bool True for female users.

    Returns
    -------
    dict with recommended range, Indian food sources, and a brief explanation.
    """
    nutrient_lower = nutrient.lower().replace(" ", "_")

    # Indian food sources per nutrient
    _SOURCES: dict[str, list[str]] = {
        "protein_g":    ["dal", "paneer", "eggs", "chana", "rajma", "sprouted moong"],
        "iron_mg":      ["poha", "rajma", "spinach", "ragi", "horse gram"],
        "calcium_mg":   ["milk", "dahi", "paneer", "ragi", "sesame seeds"],
        "fiber_g":      ["whole wheat roti", "dal", "sabzi", "fruits", "oats"],
        "sodium_mg":    ["limit pickles, papad, salted snacks, processed foods"],
        "calories_kcal":["balanced across dal, roti/rice, sabzi, dairy/protein"],
        "fat_g":        ["ghee (1 tsp/day), peanuts, sesame", "limit fried foods"],
    }

    # Normalise key
    key = next((k for k in _RDA if nutrient_lower in k), None)
    if not key:
        return {
            "error": f"Nutrient '{nutrient}' not found. Try: protein, iron, calcium, "
                     "sodium, fiber, calories, fat.",
            "disclaimer": agent_cfg.disclaimer,
        }

    rda = _RDA[key]

    # Adjust iron for females
    if key == "iron_mg" and is_female and age < 50:
        rda = {"min": 21.0, "max": 45.0}

    return {
        "nutrient": key,
        "recommended_range": rda,
        "unit": key.split("_")[-1],
        "age": age,
        "is_female": is_female,
        "indian_food_sources": _SOURCES.get(key, ["See a registered dietitian"]),
        "reference": "ICMR NIN Nutrient Requirements 2020 / WHO Guidelines",
        "disclaimer": agent_cfg.disclaimer,
    }


# ---------------------------------------------------------------------------
# Tool 3 — generate_weekly_health_summary
# ---------------------------------------------------------------------------

def generate_weekly_health_summary(
    avg_calories: float,
    avg_protein_g: float,
    avg_sodium_mg: float,
    avg_fiber_g: float,
    avg_iron_mg: float,
    days_on_plan: int,
    goal: str = "maintenance",
) -> dict[str, Any]:
    """
    Produce a weekly health summary from averaged daily nutrition values.

    Parameters
    ----------
    avg_calories  : float  Average daily calories over the week.
    avg_protein_g : float  Average daily protein in grams.
    avg_sodium_mg : float  Average daily sodium in milligrams.
    avg_fiber_g   : float  Average daily fibre in grams.
    avg_iron_mg   : float  Average daily iron in milligrams.
    days_on_plan  : int    Number of days the user followed the plan.
    goal          : str    User's goal string.

    Returns
    -------
    dict with trend commentary and Granite-generated weekly summary paragraph.
    """
    trends: list[str] = []

    if avg_sodium_mg > 1600:
        trends.append(f"Average sodium ({avg_sodium_mg:.0f} mg/day) is trending high.")
    if avg_fiber_g < 22:
        trends.append(f"Average fibre ({avg_fiber_g:.1f} g/day) needs improvement.")
    if avg_protein_g < 45:
        trends.append(f"Average protein ({avg_protein_g:.1f} g/day) is on the lower side.")

    if not trends:
        trends.append("All key nutrients are within healthy ranges — keep it up!")

    trend_text = "\n".join(f"  - {t}" for t in trends)

    prompt = (
        f"You are a warm Indian health advisor reviewing a user's week on the "
        f"Thali & Pulse nutrition plan.\n"
        f"They followed the plan for {days_on_plan} out of 7 days. Goal: {goal}.\n"
        f"Weekly averages: {avg_calories:.0f} kcal/day, {avg_protein_g:.1f}g protein/day, "
        f"{avg_sodium_mg:.0f}mg sodium/day, {avg_fiber_g:.1f}g fibre/day.\n\n"
        f"KEY OBSERVATIONS:\n{trend_text}\n\n"
        f"Write a 4-5 sentence encouraging weekly summary. Acknowledge what went well, "
        f"suggest one specific improvement using Indian food, and motivate them for "
        f"the coming week. Always end with the disclaimer.\n\n"
        f"SUMMARY:"
    )
    summary_text = _granite_generate(prompt, max_tokens=350)

    return {
        "days_on_plan": days_on_plan,
        "weekly_averages": {
            "calories_kcal": round(avg_calories, 1),
            "protein_g": round(avg_protein_g, 1),
            "sodium_mg": round(avg_sodium_mg, 1),
            "fiber_g": round(avg_fiber_g, 1),
            "iron_mg": round(avg_iron_mg, 1),
        },
        "trend_observations": trends,
        "summary": summary_text,
        "disclaimer": agent_cfg.disclaimer,
    }
