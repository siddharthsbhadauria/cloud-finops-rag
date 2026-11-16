"""
Daily summary: picks the best-value, cheapest and highest-scoring models and writes a short
Markdown brief from a template. No LLM or vector search is involved; the repo name predates this.
"""
import datetime
from typing import Any


class VectorFinOpsEngine:
    """Builds the daily Markdown summary from ranked model metrics."""

    def generate_rag_brief(self, analyzed_models: list[dict[str, Any]]) -> dict[str, Any]:
        if not analyzed_models:
            return {"markdown_brief": "No data available."}

        best_value = max(analyzed_models, key=lambda x: x.get("efficiency_score", 0))
        cheapest = min(analyzed_models, key=lambda x: x.get("blended_cost_per_1m", float("inf")))
        top = max(analyzed_models, key=lambda x: x.get("mmlu_score", 0))
        stamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")

        brief = f"""
### Daily LLM price summary
*{stamp}*

1. **Best value**: {best_value['model']} ({best_value['provider']}), value score {best_value['efficiency_score']} (MMLU {best_value['mmlu_score']} at ${best_value['blended_cost_per_1m']:.3f} per 1M tokens).
2. **Cheapest**: {cheapest['model']} ({cheapest['provider']}) at ${cheapest['blended_cost_per_1m']:.3f} per 1M blended tokens.
3. **Highest MMLU**: {top['model']} at {top['mmlu_score']}.
""".strip()

        return {
            "timestamp": stamp,
            "best_efficiency": best_value["model"],
            "lowest_cost": cheapest["model"],
            "top_frontier": top["model"],
            "markdown_brief": brief,
        }
