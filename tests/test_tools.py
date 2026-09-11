"""
Unit tests for Thali & Pulse tools.

These tests mock watsonx.ai and Milvus so they run without real credentials
or a running vector store.

Run with:
    pip install pytest pytest-mock
    pytest tests/ -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_HIT = {
    "id": "dal_toor_cooked",
    "food_name": "Toor Dal (Cooked)",
    "category": "Legume",
    "text_chunk": (
        "Food: Toor Dal (Cooked). Category: Legume. Serving: 1 katori (150g).\n"
        "Nutrition per serving — Calories: 173 kcal, Protein: 11.5g, Carbs: 29.0g, "
        "Fat: 0.6g, Fiber: 8.0g, Sodium: 8mg, Iron: 2.8mg, Calcium: 48mg.\n"
        "Cost: ₹12 per serving. Tags: high-protein, high-fiber, vegan."
    ),
    "calories_kcal": 173.0,
    "protein_g": 11.5,
    "carbs_g": 29.0,
    "fat_g": 0.6,
    "cost_inr": 12.0,
    "similarity_score": 0.95,
}

SAMPLE_HIT_B = {
    "id": "chana_kabuli_cooked",
    "food_name": "Chickpea (Cooked)",
    "category": "Legume",
    "text_chunk": "Food: Chickpea. Calories: 210 kcal, Protein: 12g, Cost: ₹18.",
    "calories_kcal": 210.0,
    "protein_g": 12.0,
    "carbs_g": 34.0,
    "fat_g": 3.5,
    "cost_inr": 18.0,
    "similarity_score": 0.88,
}


@pytest.fixture()
def mock_retriever(monkeypatch):
    """Patch FoodKnowledgeRetriever.retrieve to return deterministic results."""
    mock = MagicMock()
    mock.retrieve.return_value = [SAMPLE_HIT]
    # Patch at the module level where it is instantiated
    monkeypatch.setattr(
        "tools.nutrition_knowledge_tools._retriever", mock
    )
    monkeypatch.setattr(
        "tools.diet_recommendation_tools._retriever", mock
    )
    monkeypatch.setattr(
        "tools.food_log_tools._retriever", mock
    )
    return mock


@pytest.fixture()
def mock_granite(monkeypatch):
    """Patch all _granite_generate helpers to return a fixed string."""
    fixed_response = "This is a helpful nutritional explanation."

    for module in [
        "tools.nutrition_knowledge_tools",
        "tools.diet_recommendation_tools",
        "tools.food_log_tools",
        "tools.health_advisory_tools",
    ]:
        monkeypatch.setattr(f"{module}._granite_generate", lambda *a, **kw: fixed_response)

    return fixed_response


# ---------------------------------------------------------------------------
# Nutrition Knowledge Tools
# ---------------------------------------------------------------------------

class TestLookUpFoodNutrition:
    def test_returns_nutrition_for_known_food(self, mock_retriever, mock_granite):
        from tools.nutrition_knowledge_tools import look_up_food_nutrition

        result = look_up_food_nutrition("dal")

        assert result["food_name"] == "Toor Dal (Cooked)"
        assert result["calories_kcal"] == 173.0
        assert result["protein_g"] == 11.5
        assert "disclaimer" in result

    def test_scales_by_servings(self, mock_retriever, mock_granite):
        from tools.nutrition_knowledge_tools import look_up_food_nutrition

        result = look_up_food_nutrition("dal", servings=2.0)

        assert result["calories_kcal"] == pytest.approx(346.0)
        assert result["protein_g"] == pytest.approx(23.0)
        assert result["cost_inr"] == pytest.approx(24.0)

    def test_returns_error_when_no_hits(self, mock_retriever, mock_granite):
        mock_retriever.retrieve.return_value = []
        from tools.nutrition_knowledge_tools import look_up_food_nutrition

        result = look_up_food_nutrition("purple cauliflower from mars")

        assert "error" in result


class TestCompareFoods:
    def test_compares_two_foods(self, mock_retriever, mock_granite):
        from tools.nutrition_knowledge_tools import compare_foods

        mock_retriever.retrieve.side_effect = [[SAMPLE_HIT], [SAMPLE_HIT_B]]
        result = compare_foods("dal", "chana", goal="weight_loss")

        assert result["food_a"]["name"] == "Toor Dal (Cooked)"
        assert result["food_b"]["name"] == "Chickpea (Cooked)"
        assert "comparison" in result
        assert result["goal"] == "weight_loss"

    def test_returns_error_for_missing_food_a(self, mock_retriever, mock_granite):
        from tools.nutrition_knowledge_tools import compare_foods

        mock_retriever.retrieve.side_effect = [[], [SAMPLE_HIT_B]]
        result = compare_foods("xyz123", "chana")

        assert "error" in result


class TestSearchFoodsByCriteria:
    def test_filters_by_cost(self, mock_retriever, mock_granite):
        from tools.nutrition_knowledge_tools import search_foods_by_criteria

        mock_retriever.retrieve.return_value = [SAMPLE_HIT, SAMPLE_HIT_B]
        result = search_foods_by_criteria(query="high protein legume", max_cost_inr=15.0)

        # SAMPLE_HIT costs ₹12 (passes), SAMPLE_HIT_B costs ₹18 (filtered out)
        assert len(result["results"]) == 1
        assert result["results"][0]["food_name"] == "Toor Dal (Cooked)"


# ---------------------------------------------------------------------------
# Diet Recommendation Tools
# ---------------------------------------------------------------------------

class TestGenerateDayPlan:
    def test_returns_four_meals(self, mock_retriever, mock_granite):
        from tools.diet_recommendation_tools import generate_day_plan

        # Make retriever return a few results for slot queries
        mock_retriever.retrieve.return_value = [SAMPLE_HIT, SAMPLE_HIT_B]

        result = generate_day_plan(
            age=28,
            goal="maintenance",
            city="Mumbai",
            daily_budget_inr=150,
        )

        assert len(result["meals"]) == 4
        slots = {m["slot"] for m in result["meals"]}
        assert slots == {"breakfast", "lunch", "snack", "dinner"}

    def test_daily_totals_present(self, mock_retriever, mock_granite):
        from tools.diet_recommendation_tools import generate_day_plan

        mock_retriever.retrieve.return_value = [SAMPLE_HIT]

        result = generate_day_plan(
            age=35, goal="weight_loss", city="Chennai", daily_budget_inr=120
        )

        totals = result["daily_totals"]
        assert "calories_kcal" in totals
        assert "protein_g" in totals
        assert "total_cost_inr" in totals
        assert "within_budget" in totals

    def test_grocery_list_has_items(self, mock_retriever, mock_granite):
        from tools.diet_recommendation_tools import generate_day_plan

        mock_retriever.retrieve.return_value = [SAMPLE_HIT]
        result = generate_day_plan(
            age=25, goal="muscle_gain", city="Pune", daily_budget_inr=200
        )

        assert isinstance(result["grocery_list"], list)
        assert len(result["grocery_list"]) > 0


class TestEstimateWeeklyCost:
    def test_within_budget(self):
        from tools.diet_recommendation_tools import estimate_weekly_cost

        result = estimate_weekly_cost(
            daily_cost_inr=100, monthly_budget_inr=4000
        )

        assert result["monthly_cost_inr"] == pytest.approx(3000.0)
        assert result["remaining_inr"] == pytest.approx(1000.0)
        assert "✅" in result["status"]

    def test_over_budget(self):
        from tools.diet_recommendation_tools import estimate_weekly_cost

        result = estimate_weekly_cost(
            daily_cost_inr=200, monthly_budget_inr=3000
        )

        assert result["remaining_inr"] < 0
        assert "⚠️" in result["status"]


# ---------------------------------------------------------------------------
# Food Log Tools
# ---------------------------------------------------------------------------

class TestAnalyzeMealText:
    def test_returns_breakdown(self, mock_retriever, mock_granite):
        from tools.food_log_tools import analyze_meal_text

        # Patch the item extractor to return a known list
        with patch(
            "tools.food_log_tools._extract_food_items",
            return_value=["dal", "roti"],
        ):
            mock_retriever.retrieve.return_value = [SAMPLE_HIT]
            result = analyze_meal_text("2 rotis and dal fry", goal="maintenance")

        assert "item_breakdown" in result
        assert "meal_totals" in result
        assert result["meal_totals"]["calories_kcal"] > 0

    def test_disclaimer_present(self, mock_retriever, mock_granite):
        from tools.food_log_tools import analyze_meal_text

        with patch(
            "tools.food_log_tools._extract_food_items",
            return_value=["poha"],
        ):
            mock_retriever.retrieve.return_value = [SAMPLE_HIT]
            result = analyze_meal_text("poha breakfast")

        assert "disclaimer" in result


class TestCheckDailyBalance:
    def test_on_track(self):
        from tools.food_log_tools import check_daily_balance

        result = check_daily_balance(
            logged_calories=1600,
            logged_protein_g=55,
            logged_carbs_g=200,
            logged_fat_g=40,
            target_calories=1800,
            target_protein_g=60,
        )

        assert "✅" in result["calorie_status"] or "ℹ️" in result["calorie_status"]
        assert result["calories_remaining"] == pytest.approx(200.0)

    def test_over_calories(self):
        from tools.food_log_tools import check_daily_balance

        result = check_daily_balance(
            logged_calories=2000,
            logged_protein_g=70,
            logged_carbs_g=250,
            logged_fat_g=60,
            target_calories=1800,
            target_protein_g=60,
        )

        assert "⚠️" in result["calorie_status"]


# ---------------------------------------------------------------------------
# Health Advisory Tools
# ---------------------------------------------------------------------------

class TestFlagHealthConcerns:
    def test_high_sodium_flagged(self, mock_granite):
        from tools.health_advisory_tools import flag_health_concerns

        result = flag_health_concerns(
            calories_kcal=1800, protein_g=55, carbs_g=220, fat_g=50,
            fiber_g=25, sodium_mg=2100, iron_mg=18, calcium_mg=700,
        )

        nutrient_flags = [f["nutrient"] for f in result["flags"]]
        assert "Sodium" in nutrient_flags

    def test_low_fiber_flagged(self, mock_granite):
        from tools.health_advisory_tools import flag_health_concerns

        result = flag_health_concerns(
            calories_kcal=1800, protein_g=55, carbs_g=220, fat_g=50,
            fiber_g=10, sodium_mg=900, iron_mg=18, calcium_mg=700,
        )

        nutrient_flags = [f["nutrient"] for f in result["flags"]]
        assert "Fibre" in nutrient_flags

    def test_no_flags_for_healthy_day(self, mock_granite):
        from tools.health_advisory_tools import flag_health_concerns

        result = flag_health_concerns(
            calories_kcal=1800, protein_g=65, carbs_g=220, fat_g=50,
            fiber_g=28, sodium_mg=1200, iron_mg=18, calcium_mg=700,
        )

        assert result["flag_count"] == 0
        assert "disclaimer" in result


class TestGetRdaGuidance:
    def test_returns_protein_rda(self):
        from tools.health_advisory_tools import get_rda_guidance

        result = get_rda_guidance(nutrient="protein", age=30)

        assert "recommended_range" in result
        assert "indian_food_sources" in result
        assert "dal" in result["indian_food_sources"]

    def test_adjusts_iron_for_female(self):
        from tools.health_advisory_tools import get_rda_guidance

        female_result = get_rda_guidance(nutrient="iron", age=30, is_female=True)
        male_result = get_rda_guidance(nutrient="iron", age=30, is_female=False)

        assert female_result["recommended_range"]["min"] > male_result["recommended_range"]["min"]

    def test_unknown_nutrient(self):
        from tools.health_advisory_tools import get_rda_guidance

        result = get_rda_guidance(nutrient="pixie_dust")
        assert "error" in result


# ---------------------------------------------------------------------------
# User Profile model
# ---------------------------------------------------------------------------

class TestUserProfile:
    def test_daily_budget(self):
        from tools.models import Goal, UserProfile

        profile = UserProfile(age=30, goal=Goal.MAINTENANCE, city="Delhi", monthly_budget_inr=3000)
        assert profile.daily_budget_inr == pytest.approx(100.0)

    def test_target_calories_weight_loss(self):
        from tools.models import Goal, UserProfile

        profile = UserProfile(
            age=28, goal=Goal.WEIGHT_LOSS, city="Mumbai",
            monthly_budget_inr=3000, weight_kg=70, height_cm=170
        )
        # Should be TDEE - 400; value should be in a sane range
        assert 1200 < profile.target_calories < 2500

    def test_target_protein_muscle_gain(self):
        from tools.models import Goal, UserProfile

        profile = UserProfile(
            age=25, goal=Goal.MUSCLE_GAIN, city="Bengaluru",
            monthly_budget_inr=4000, weight_kg=65
        )
        # 1.6 g/kg × 65 kg = 104 g
        assert profile.target_protein_g == pytest.approx(104.0)
