from src.analytics.finops_engine import FinOpsEngine
from src.quality.data_contracts import DataContractsEngine
from src.rag.vector_finops import VectorFinOpsEngine

PRICES = [
    {"provider": "A", "model": "cheap", "input_cost_per_1m": 0.10, "output_cost_per_1m": 0.30},
    {"provider": "B", "model": "smart", "input_cost_per_1m": 10.0, "output_cost_per_1m": 50.0},
    {"provider": "C", "model": "unscored", "input_cost_per_1m": 1.0, "output_cost_per_1m": 2.0},
]
BENCH = [
    {"model": "cheap", "mmlu_score": 80.0},
    {"model": "smart", "mmlu_score": 95.0},
]


def test_blended_price_and_value_score():
    rows = FinOpsEngine(":memory:").process_analytics(PRICES, BENCH)
    by = {r["model"]: r for r in rows}
    assert by["cheap"]["blended_cost_per_1m"] == 0.15  # 0.75 * 0.10 + 0.25 * 0.30
    assert by["smart"]["blended_cost_per_1m"] == 20.0
    assert by["cheap"]["efficiency_score"] == round(80 / 0.15, 2)
    assert by["cheap"]["tokens_per_dollar"] == 6_666_666
    assert by["cheap"]["tokens_per_dollar_formatted"] == "6,666,666"


def test_models_without_benchmarks_are_dropped_and_ranked():
    rows = FinOpsEngine(":memory:").process_analytics(PRICES, BENCH)
    assert [r["model"] for r in rows] == ["cheap", "smart"]


def test_contract_rejects_negative_price_and_bad_mmlu():
    c = DataContractsEngine()
    assert c.validate_pricing_data(PRICES)
    assert not c.validate_pricing_data([{**PRICES[0], "input_cost_per_1m": -1}])
    assert not c.validate_pricing_data([])
    assert not c.validate_benchmark_data([{"model": "x", "mmlu_score": 120}])


def test_summary_names_the_picks():
    rows = FinOpsEngine(":memory:").process_analytics(PRICES, BENCH)
    s = VectorFinOpsEngine().generate_rag_brief(rows)
    assert s["best_efficiency"] == "cheap"
    assert s["top_frontier"] == "smart"
    assert "cheap" in s["markdown_brief"]
