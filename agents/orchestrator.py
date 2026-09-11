"""
Thali & Pulse — Orchestrator Agent

This is the top-level supervisor agent that:
1. Collects the user profile (onboarding)
2. Routes tasks to the four specialist sub-agents
3. Assembles a coherent, warm response with cost + nutrition info
4. Always appends the medical disclaimer

In watsonx Orchestrate, this file is registered as the primary agent.
The four specialist agents are registered as collaborator agents that the
orchestrator can call via tool invocations.

For local testing / standalone use, the orchestrator is also directly
runnable as a Python script.

Usage (local):
    python agents/orchestrator.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import agent as agent_cfg, watsonx as wx_cfg

# ---------------------------------------------------------------------------
# Orchestrator system prompt
# ---------------------------------------------------------------------------

ORCHESTRATOR_SYSTEM_PROMPT = """
You are **Thali & Pulse** — a warm, practical, and knowledgeable Indian nutrition assistant.

Your job is to help users eat well every day using foods that are familiar, affordable,
and actually available in their city — just like a balanced, home-cooked thali.

## Your personality
- Warm and local: you talk like a helpful local nutritionist, not a diet app.
- Practical: you always show cost (in ₹) alongside nutrition.
- Honest: you ground every recommendation in the retrieved food database — never invent values.
- Empathetic: you respect the user's budget, regional food preferences, and habits.

## Your capabilities
You can delegate tasks to four specialist agents:

1. **Nutrition Knowledge Agent** — looks up calorie and macro data for Indian foods,
   compares two foods, or searches by criteria (e.g. "high-iron breakfast under ₹30").

2. **Diet Recommendation Agent** — builds a full personalised day plan (breakfast,
   lunch, snack, dinner) within the user's calorie target and daily budget. Can also
   swap individual meals and generate grocery lists.

3. **Food Log & Feedback Agent** — analyses a meal the user describes (text or photo
   description) and gives an honest nutritional read vs. their daily balance.

4. **Health Advisory Agent** — reviews the day's accumulated nutrition and flags
   concerns (high sodium, low iron, low fibre) with practical Indian food solutions.

## Onboarding (collect on first interaction)
Before you can personalise advice, collect:
- Age
- Health / fitness goal (weight loss, muscle gain, or maintenance)
- City (for regional food availability)
- Monthly food budget in ₹
- Dietary preference (vegetarian / non-vegetarian)

Ask these in a single friendly message. Do not start planning until you have all five.

## Rules
- ALWAYS show cost alongside nutrition in every response.
- NEVER recommend imported superfoods (quinoa, kale, açaí, etc.) unless the user
  explicitly asks for them.
- ALWAYS end every substantive response with the disclaimer:
  {DISCLAIMER}
- If you cannot find a food in the knowledge base, say so honestly.
- For health flags, use the advisory agent's grounded output — do not improvise
  medical guidance.
""".format(DISCLAIMER=agent_cfg.disclaimer)


# ---------------------------------------------------------------------------
# Specialist sub-agent wrappers
# In watsonx Orchestrate these become "collaborator agent" tool calls.
# Locally they import and call the tool functions directly.
# ---------------------------------------------------------------------------

def _call_nutrition_agent(task: str, **kwargs: Any) -> dict[str, Any]:
    """Route to the Nutrition Knowledge Agent."""
    from tools.nutrition_knowledge_tools import (
        compare_foods,
        look_up_food_nutrition,
        search_foods_by_criteria,
    )
    if task == "look_up":
        return look_up_food_nutrition(**kwargs)
    elif task == "compare":
        return compare_foods(**kwargs)
    elif task == "search":
        return search_foods_by_criteria(**kwargs)
    return {"error": f"Unknown nutrition task: {task}"}


def _call_diet_agent(task: str, **kwargs: Any) -> dict[str, Any]:
    """Route to the Diet Recommendation Agent."""
    from tools.diet_recommendation_tools import (
        estimate_weekly_cost,
        generate_day_plan,
        generate_grocery_list,
        swap_meal,
    )
    if task == "day_plan":
        return generate_day_plan(**kwargs)
    elif task == "swap":
        return swap_meal(**kwargs)
    elif task == "grocery":
        return generate_grocery_list(**kwargs)
    elif task == "weekly_cost":
        return estimate_weekly_cost(**kwargs)
    return {"error": f"Unknown diet task: {task}"}


def _call_food_log_agent(task: str, **kwargs: Any) -> dict[str, Any]:
    """Route to the Food Log & Feedback Agent."""
    from tools.food_log_tools import (
        analyze_meal_text,
        check_daily_balance,
        log_meal,
    )
    if task == "analyze":
        return analyze_meal_text(**kwargs)
    elif task == "balance":
        return check_daily_balance(**kwargs)
    elif task == "log":
        return log_meal(**kwargs)
    return {"error": f"Unknown food-log task: {task}"}


def _call_health_agent(task: str, **kwargs: Any) -> dict[str, Any]:
    """Route to the Health Advisory Agent."""
    from tools.health_advisory_tools import (
        flag_health_concerns,
        generate_weekly_health_summary,
        get_rda_guidance,
    )
    if task == "flag":
        return flag_health_concerns(**kwargs)
    elif task == "rda":
        return get_rda_guidance(**kwargs)
    elif task == "weekly":
        return generate_weekly_health_summary(**kwargs)
    return {"error": f"Unknown health task: {task}"}


# ---------------------------------------------------------------------------
# ReAct-style orchestrator loop (local / standalone)
# ---------------------------------------------------------------------------

_TOOL_REGISTRY = {
    "nutrition_look_up":     lambda kw: _call_nutrition_agent("look_up", **kw),
    "nutrition_compare":     lambda kw: _call_nutrition_agent("compare", **kw),
    "nutrition_search":      lambda kw: _call_nutrition_agent("search", **kw),
    "diet_day_plan":         lambda kw: _call_diet_agent("day_plan", **kw),
    "diet_swap":             lambda kw: _call_diet_agent("swap", **kw),
    "diet_grocery":          lambda kw: _call_diet_agent("grocery", **kw),
    "diet_weekly_cost":      lambda kw: _call_diet_agent("weekly_cost", **kw),
    "log_analyze":           lambda kw: _call_food_log_agent("analyze", **kw),
    "log_balance":           lambda kw: _call_food_log_agent("balance", **kw),
    "log_meal":              lambda kw: _call_food_log_agent("log", **kw),
    "health_flag":           lambda kw: _call_health_agent("flag", **kw),
    "health_rda":            lambda kw: _call_health_agent("rda", **kw),
    "health_weekly":         lambda kw: _call_health_agent("weekly", **kw),
}

_TOOL_DESCRIPTIONS = """
Available tools (call with JSON arguments):
  nutrition_look_up     - Look up nutrition for a food. Args: food_name, servings
  nutrition_compare     - Compare two foods for a goal. Args: food_a, food_b, goal
  nutrition_search      - Search by criteria. Args: query, max_cost_inr, min_protein_g
  diet_day_plan         - Generate full day plan. Args: age, goal, city, daily_budget_inr,
                          is_vegetarian, weight_kg, height_cm
  diet_swap             - Swap one meal. Args: slot, current_items, goal, city,
                          calorie_allowance, budget_allowance_inr, reason
  diet_grocery          - Grocery list from meals_json. Args: meals_json, servings, days
  diet_weekly_cost      - Project weekly/monthly cost. Args: daily_cost_inr,
                          monthly_budget_inr
  log_analyze           - Analyse meal text. Args: meal_description, goal
  log_balance           - Check daily balance. Args: logged_calories, logged_protein_g,
                          logged_carbs_g, logged_fat_g, target_calories, target_protein_g
  log_meal              - Log a meal. Args: slot, meal_description, goal
  health_flag           - Flag health concerns from daily totals. Args: calories_kcal,
                          protein_g, carbs_g, fat_g, fiber_g, sodium_mg, iron_mg,
                          calcium_mg, age, is_female, goal
  health_rda            - Get RDA guidance. Args: nutrient, age, is_female
  health_weekly         - Weekly summary. Args: avg_calories, avg_protein_g,
                          avg_sodium_mg, avg_fiber_g, avg_iron_mg, days_on_plan, goal
"""


def _granite_orchestrate(messages: list[dict], max_tokens: int = 1024) -> str:
    """
    Call Granite via the chat/messages API for multi-turn orchestration.
    """
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
    # Build a single prompt from messages for models that don't support chat API
    prompt_parts = []
    for m in messages:
        role = m["role"].upper()
        prompt_parts.append(f"[{role}]: {m['content']}")
    prompt_parts.append("[ASSISTANT]:")
    prompt = "\n\n".join(prompt_parts)
    return model.generate_text(prompt=prompt).strip()


def run_orchestrator_turn(
    user_message: str,
    conversation_history: list[dict],
    user_profile: dict | None = None,
) -> dict[str, Any]:
    """
    Process a single user turn through the Thali & Pulse orchestrator.

    Parameters
    ----------
    user_message         : str   The user's latest message.
    conversation_history : list  Prior messages in [{"role": ..., "content": ...}] format.
    user_profile         : dict  Collected user profile (may be None during onboarding).

    Returns
    -------
    dict with:
      - response: str   Assistant's reply to the user.
      - tool_calls: list  Any sub-agent calls made (for transparency / logging).
      - updated_history: list  Updated conversation history.
    """
    tool_calls_made: list[dict] = []

    # Build system message with tool list
    system_content = (
        ORCHESTRATOR_SYSTEM_PROMPT
        + "\n\n"
        + _TOOL_DESCRIPTIONS
        + "\n\nWhen you need to call a tool, output EXACTLY:\n"
        + 'TOOL_CALL: {"tool": "<name>", "args": {<json args>}}\n'
        + "Then wait for the tool result before continuing.\n"
        + "When you have enough information, write your final response to the user."
    )

    if user_profile:
        profile_str = json.dumps(user_profile, indent=2)
        system_content += f"\n\nCURRENT USER PROFILE:\n{profile_str}"

    messages = [{"role": "system", "content": system_content}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # ReAct loop — up to max_iterations tool calls
    for iteration in range(agent_cfg.max_iterations):
        raw_response = _granite_orchestrate(messages, max_tokens=1024)

        # Check for tool call
        if "TOOL_CALL:" in raw_response:
            # Extract tool call JSON
            try:
                call_json_str = raw_response.split("TOOL_CALL:", 1)[1].strip()
                # Handle potential trailing text after the JSON object
                brace_count = 0
                end_idx = 0
                for i, ch in enumerate(call_json_str):
                    if ch == "{":
                        brace_count += 1
                    elif ch == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                call_json = json.loads(call_json_str[:end_idx])
                tool_name = call_json["tool"]
                tool_args = call_json.get("args", {})
            except (json.JSONDecodeError, KeyError) as exc:
                # Malformed tool call — break the loop and return what we have
                break

            # Execute the tool
            if tool_name in _TOOL_REGISTRY:
                tool_result = _TOOL_REGISTRY[tool_name](tool_args)
            else:
                tool_result = {"error": f"Unknown tool: {tool_name}"}

            tool_calls_made.append(
                {"tool": tool_name, "args": tool_args, "result": tool_result}
            )

            # Feed result back into the conversation
            messages.append({"role": "assistant", "content": raw_response})
            messages.append(
                {
                    "role": "user",
                    "content": f"TOOL_RESULT: {json.dumps(tool_result)}",
                }
            )
        else:
            # No tool call — this is the final response
            final_response = raw_response
            conversation_history = messages[1:]  # drop system message
            conversation_history.append(
                {"role": "assistant", "content": final_response}
            )
            return {
                "response": final_response,
                "tool_calls": tool_calls_made,
                "updated_history": conversation_history,
            }

    # Fallback if max iterations hit
    fallback = (
        "I'm sorry, I couldn't complete your request in the allowed number of steps. "
        "Please try rephrasing your question or breaking it into smaller parts.\n\n"
        + agent_cfg.disclaimer
    )
    return {
        "response": fallback,
        "tool_calls": tool_calls_made,
        "updated_history": conversation_history,
    }


# ---------------------------------------------------------------------------
# CLI entry point for local testing
# ---------------------------------------------------------------------------

def main() -> None:
    """Simple interactive REPL for local testing."""
    print("\n🍽️  Thali & Pulse — Personalised Indian Nutrition Agent")
    print("=" * 60)
    print("Type your message and press Enter. Type 'quit' to exit.\n")

    history: list[dict] = []
    profile: dict | None = None

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! Eat well! 🙏")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "bye"}:
            print("Goodbye! Eat well! 🙏")
            break

        result = run_orchestrator_turn(
            user_message=user_input,
            conversation_history=history,
            user_profile=profile,
        )

        print(f"\nThali & Pulse: {result['response']}\n")
        history = result["updated_history"]

        if result["tool_calls"]:
            print(f"  [Sub-agents called: {[tc['tool'] for tc in result['tool_calls']]}]\n")


if __name__ == "__main__":
    main()
