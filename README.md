# 🍽️ Thali & Pulse

**A personalised Indian nutrition agent built on watsonx Orchestrate + IBM Granite.**

Thali & Pulse plans your daily food intake like a balanced home-cooked thali — rooted
in what's actually available in your city, constrained to your real budget, and backed
by verified Indian food composition data rather than generic international "superfoods."

> ⚠️ **Disclaimer:** Thali & Pulse provides general nutrition information only.
> It is not a substitute for personalised medical or dietary advice. Please consult
> a registered dietitian or physician before making significant changes to your diet.

---

## Architecture

```
User
 │
 ▼
┌─────────────────────────────────────────────────────┐
│          Thali & Pulse Orchestrator                  │  ← IBM Granite 3.3 8B
│  (watsonx Orchestrate supervisor agent)              │    via watsonx.ai
└────────────┬──────────────────────────────┬──────────┘
             │  routes via collaborator calls│
    ┌────────┴────────┐            ┌─────────┴─────────┐
    │  Nutrition       │            │  Diet              │
    │  Knowledge       │            │  Recommendation    │
    │  Agent           │            │  Agent             │
    │  (RAG lookup,    │            │  (day plan, swap,  │
    │   comparison)    │            │   grocery list)    │
    └────────┬─────────┘            └──────────┬────────┘
             │                                  │
    ┌────────┴─────────┐            ┌──────────┴────────┐
    │  Food Log &      │            │  Health Advisory   │
    │  Feedback Agent  │            │  Agent             │
    │  (meal analysis, │            │  (ICMR/WHO flags,  │
    │   daily balance) │            │   weekly summary)  │
    └──────────────────┘            └────────────────────┘
             │                                  │
             └──────────────┬───────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  Milvus Vector Store        │
              │  indian_food_nutrition      │
              │  (25+ Indian foods, JSONL   │
              │   → embedded with           │
              │   ibm/slate-125m-english)   │
              └─────────────────────────────┘
```

### Component summary

| Component | File | Role |
|---|---|---|
| **Orchestrator** | `agents/orchestrator.py` | Supervisor — collects profile, routes to sub-agents |
| **Nutrition Knowledge Agent** | `tools/nutrition_knowledge_tools.py` | RAG food lookup, comparisons, criteria search |
| **Diet Recommendation Agent** | `tools/diet_recommendation_tools.py` | Day plan, meal swap, grocery list, cost projection |
| **Food Log & Feedback Agent** | `tools/food_log_tools.py` | Meal text analysis, daily balance check |
| **Health Advisory Agent** | `tools/health_advisory_tools.py` | ICMR/WHO flag checking, RDA guidance, weekly summary |
| **RAG Ingestion** | `rag/ingest.py` | Builds Milvus collection from `data/indian_food_db.jsonl` |
| **RAG Retriever** | `rag/retriever.py` | Singleton retrieval client used by all agents |
| **Food DB** | `data/indian_food_db.jsonl` | 26 Indian foods with full nutrition + cost metadata |
| **Agent YAML** | `config/agents.yaml` | watsonx Orchestrate import definition for all 5 agents |
| **Settings** | `config/settings.py` | Centralised env-based configuration |

---

## Setup

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10+ |
| Milvus | 2.4+ (local Docker or IBM Cloud Databases for Milvus) |
| IBM Cloud account | watsonx.ai project required |

### 1 — Clone and install

```bash
git clone <repo-url> && cd thali-pulse
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2 — Configure credentials

```bash
cp .env.example .env
# Edit .env with your real watsonx API key and project ID
```

### 3 — Start Milvus (local Docker)

```bash
docker run -d \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:v2.4.0 \
  milvus run standalone
```

### 4 — Ingest the food knowledge base

```bash
python rag/ingest.py
# Add --recreate to drop and rebuild the collection
```

### 5 — Run the local REPL

```bash
python agents/orchestrator.py
```

### 6 — Deploy to watsonx Orchestrate

1. Open your **watsonx Orchestrate** instance in IBM Cloud.
2. Navigate to **Agent Builder → Import agent**.
3. Upload `config/agents.yaml`.
4. In **Secrets Manager**, add `WATSONX_API_KEY` and `WATSONX_PROJECT_ID`.
5. Publish the `thali_pulse_orchestrator` agent as your primary interface.

---

## Usage examples

### Onboarding

```
User: Hi! I want help planning my meals.

Thali & Pulse: Namaste! 🙏 I'm Thali & Pulse — your personal Indian nutrition guide.
To build a plan that really works for you, I need just 5 quick details:
  1. How old are you?
  2. What's your goal — weight loss, muscle gain, or maintaining your current weight?
  3. Which city do you live in?
  4. What's your monthly food budget in ₹?
  5. Are you vegetarian or non-vegetarian?
```

### Ask about a food

```
User: How many calories are in 2 rotis and a katori of toor dal?

Thali & Pulse: Here's the breakdown:
  • 2 Whole Wheat Rotis (60g)    — 142 kcal | 5.4g protein | ₹6
  • 1 katori Toor Dal (150g)     — 173 kcal | 11.5g protein | ₹12
  ─────────────────────────────────────────────────────
  Total                           — 315 kcal | 16.9g protein | ₹18
...
```

### Log a meal

```
User: I just had poha with peanuts and a cutting chai for breakfast.

Thali & Pulse: Great start! 
  • Poha (200g)       — 250 kcal | 4.5g protein | ₹20
  • Roasted Peanuts (30g) — 176 kcal | 7.5g protein | ₹10
  Total breakfast     — 426 kcal | 12g protein | ₹30

  The poha gives you a solid iron boost (3.5 mg), and the peanuts
  add healthy fats and protein. You have ~1,374 kcal remaining for today. ✅
```

### Swap a meal

```
User: I don't want paneer today. Swap my lunch.

Thali & Pulse: No problem! Here's a swap for your lunch that stays within your
  ₹65 budget and ~500 kcal target:
  • Rajma (1 katori) + 3 Rotis + Mixed Veg Sabzi
  — 498 kcal | 18.5g protein | ₹47
  Rajma is an excellent protein source (13.5g per katori) and costs
  ₹18 less than the paneer option while hitting your muscle-gain targets.
```

---

## Food database

The knowledge base (`data/indian_food_db.jsonl`) currently includes 26 foods across
all major Indian categories. Each record has:

- Calories, protein, carbs, fat, fibre, sodium, iron, calcium per serving
- Regional name(s) and availability (pan-India / regional)
- Season availability
- Estimated cost per serving in ₹ (market prices, 2024)
- Tags (vegan, non-veg, high-protein, etc.)

**To add more foods:** Append a new JSON line to `data/indian_food_db.jsonl` following
the same schema, then re-run `python rag/ingest.py --recreate`.

---

## Running tests

```bash
pip install pytest pytest-mock
pytest tests/ -v
```

All tests mock watsonx.ai and Milvus — no credentials or running infrastructure needed.

---

## Extending the agent

| Goal | What to change |
|---|---|
| Add a new sub-agent (e.g. Exercise Agent) | Add tools in `tools/`, register in `agents/orchestrator.py`, add agent block to `config/agents.yaml` |
| Add more foods | Append to `data/indian_food_db.jsonl`, re-run `rag/ingest.py --recreate` |
| Change the reasoning model | Update `WATSONX_REASONING_MODEL` in `.env` |
| Switch from Milvus to Elasticsearch | Replace `rag/retriever.py` with an Elasticsearch client; update `requirements.txt` |
| Add session persistence | Wrap `run_orchestrator_turn()` with a database-backed session store (e.g. Redis) |

---

## Data sources & references

- **Indian Food Composition Tables (IFCT 2017)** — National Institute of Nutrition, ICMR
- **ICMR NIN Nutrient Requirements 2020** — RDA values used in the Health Advisory Agent
- **WHO Sodium Intake Guidelines** — 2g/day limit used for sodium flagging
- **USDA FoodData Central** — cross-reference for some items
