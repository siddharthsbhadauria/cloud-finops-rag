"""
Cloud FinOps & Analytics Processing Engine
Calculates tokenomics efficiency metrics, cost ratios, and persists analytical models.
"""
import os
from typing import List, Dict, Any

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

class FinOpsEngine:
    """Computes cost-to-intelligence ratios and token efficiency scores."""

    def __init__(self, db_path: str = "data/finops.duckdb"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def process_analytics(self, pricing_records: List[Dict[str, Any]], benchmark_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Joins pricing with benchmarks and computes tokenomics metrics."""
        
        bench_map = {b["model"]: b for b in benchmark_records}
        results = []

        for p in pricing_records:
            model_name = p["model"]
            if model_name not in bench_map:
                continue
            b = bench_map[model_name]

            in_cost = float(p["input_cost_per_1m"])
            out_cost = float(p["output_cost_per_1m"])
            blended = round((in_cost * 0.75) + (out_cost * 0.25), 4)
            tokens_per_dollar = int(1_000_000 / blended) if blended > 0 else 0
            mmlu = float(b["mmlu_score"])
            efficiency = round(mmlu / blended, 2) if blended > 0 else 0

            results.append({
                "provider": p["provider"],
                "model": model_name,
                "input_cost_per_1m": in_cost,
                "output_cost_per_1m": out_cost,
                "context_window": int(p.get("context_window", 128000)),
                "region": p.get("region", "us-east-1"),
                "mmlu_score": mmlu,
                "arena_elo": int(b.get("arena_elo", 1200)),
                "avg_throughput_tps": float(b.get("avg_throughput_tps", 50.0)),
                "category": b.get("category", "LLM"),
                "blended_cost_per_1m": blended,
                "tokens_per_dollar": tokens_per_dollar,
                "tokens_per_dollar_formatted": f"{tokens_per_dollar:,}",
                "efficiency_score": efficiency
            })

        # Sort by efficiency score descending
        results.sort(key=lambda x: x["efficiency_score"], reverse=True)

        if HAS_DUCKDB:
            try:
                conn = duckdb.connect(self.db_path)
                conn.execute("CREATE TEMP TABLE raw_results AS SELECT * FROM results")
                conn.execute("DROP TABLE IF EXISTS finops_models")
                conn.execute("CREATE TABLE finops_models AS SELECT * FROM raw_results")
                conn.close()
                print("Saved analytical tables to DuckDB database.")
            except Exception as e:
                print(f"DuckDB Notice: {e}")

        print(f"[OK] FinOps Analytics Engine processed {len(results)} model benchmarks successfully.")
        return results

if __name__ == "__main__":
    from src.ingest.cloud_pricing import CloudPricingIngestor
    from src.ingest.llm_evals import LLMEvalsIngestor

    pricing = CloudPricingIngestor().get_all_llm_pricing()
    evals = LLMEvalsIngestor().get_benchmarks()
    
    engine = FinOpsEngine()
    processed = engine.process_analytics(pricing, evals)
    print("Top Model:", processed[0]["model"], "Efficiency:", processed[0]["efficiency_score"])
