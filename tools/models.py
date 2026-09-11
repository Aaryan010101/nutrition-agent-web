"""
Shared data models and types used across all Thali & Pulse agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Goal(str, Enum):
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"


@dataclass
class UserProfile:
    """Captured during the onboarding conversation."""

    age: int
    goal: Goal
    city: str
    monthly_budget_inr: float
    is_vegetarian: bool = True
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None

    @property
    def daily_budget_inr(self) -> float:
        return round(self.monthly_budget_inr / 30, 2)

    @property
    def target_calories(self) -> int:
        """
        Rough TDEE estimate (sedentary baseline + goal offset).
        For production use, capture activity level and use Mifflin–St Jeor.
        """
        if self.weight_kg and self.height_cm:
            # Mifflin–St Jeor for average adult (mixed-sex approximation)
            bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age
        else:
            # Generic fallback by age bracket
            bmr = 1800 if self.age < 40 else 1650

        tdee = bmr * 1.4  # light activity multiplier
        offsets = {
            Goal.WEIGHT_LOSS: -400,
            Goal.MUSCLE_GAIN: +300,
            Goal.MAINTENANCE: 0,
        }
        return int(tdee + offsets[self.goal])

    @property
    def target_protein_g(self) -> float:
        """1.2–2.0 g/kg; use 1.6 g/kg for muscle gain, 1.2 for others."""
        kg = self.weight_kg or 60.0
        factor = 1.6 if self.goal == Goal.MUSCLE_GAIN else 1.2
        return round(kg * factor, 1)


@dataclass
class NutritionSummary:
    """Nutritional totals for a meal or day."""

    calories_kcal: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sodium_mg: float = 0.0
    cost_inr: float = 0.0

    def __add__(self, other: "NutritionSummary") -> "NutritionSummary":
        return NutritionSummary(
            calories_kcal=self.calories_kcal + other.calories_kcal,
            protein_g=self.protein_g + other.protein_g,
            carbs_g=self.carbs_g + other.carbs_g,
            fat_g=self.fat_g + other.fat_g,
            fiber_g=self.fiber_g + other.fiber_g,
            sodium_mg=self.sodium_mg + other.sodium_mg,
            cost_inr=self.cost_inr + other.cost_inr,
        )


@dataclass
class MealSlot:
    """A single meal in a day plan."""

    slot: str          # "breakfast" | "lunch" | "snack" | "dinner"
    items: list[str]   # food item names
    nutrition: NutritionSummary = field(default_factory=NutritionSummary)
    description: str = ""


@dataclass
class DayPlan:
    """A full day's meal plan."""

    meals: list[MealSlot] = field(default_factory=list)

    @property
    def totals(self) -> NutritionSummary:
        total = NutritionSummary()
        for meal in self.meals:
            total = total + meal.nutrition
        return total

    @property
    def grocery_list(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for meal in self.meals:
            for item in meal.items:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
        return result
