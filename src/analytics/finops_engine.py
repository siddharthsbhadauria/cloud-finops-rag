"""
FinOps analytics: joins prices with benchmark scores and ranks models in DuckDB.

blended price  = 75% input price + 25% output price (per million tokens)
value score    = MMLU / blended price
"""
import os
from typing import Any

import duckdb

RANK_SQL = """
    SELECT
        p.provider,
        p.model,
        p.input_cost_per_1m,
        p.output_cost_per_1m,
        p.context_window,
        p.region,
        b.mmlu_score,
        b.arena_elo,
        b.avg_throughput_tps,
        b.category,
        ROUND(p.input_cost_per_1m * 0.75 + p.output_cost_per_1m * 0.25, 4) AS blended_cost_per_1m
    FROM prices p
    JOIN benchmarks b USING (model)
"""


class FinOpsEngine:
    """Computes blended price, tokens per dollar and value score for each model."""

    def __init__(self, db_path: str = "data/finops.duckdb"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    def process_analytics(self, pricing_records: list[dict[str, Any]], benchmark_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        con = duckdb.connect(self.db_path)
        try:
            con.execute("""
                CREATE OR REPLACE TABLE prices (
                    provider VARCHAR, model VARCHAR, input_cost_per_1m DOUBLE, output_cost_per_1m DOUBLE,
                    context_window BIGINT, region VARCHAR)
            """)
            con.executemany("INSERT INTO prices VALUES (?, ?, ?, ?, ?, ?)", [
                (p["provider"], p["model"], float(p["input_cost_per_1m"]), float(p["output_cost_per_1m"]),
                 int(p.get("context_window", 128000)), p.get("region", "global"))
                for p in pricing_records
            ])
            con.execute("""
                CREATE OR REPLACE TABLE benchmarks (
                    model VARCHAR, mmlu_score DOUBLE, arena_elo BIGINT, avg_throughput_tps DOUBLE, category VARCHAR)
            """)
            seen = set()
            rows = []
            for b in benchmark_records:
                if b["model"] in seen:
                    continue
                seen.add(b["model"])
                rows.append((b["model"], float(b["mmlu_score"]), int(b.get("arena_elo", 1200)),
                             float(b.get("avg_throughput_tps", 50.0)), b.get("category", "LLM")))
            con.executemany("INSERT INTO benchmarks VALUES (?, ?, ?, ?, ?)", rows)

            con.execute(f"""
                CREATE OR REPLACE TABLE finops_models AS
                SELECT *,
                    CASE WHEN blended_cost_per_1m > 0 THEN CAST(FLOOR(1000000 / blended_cost_per_1m) AS BIGINT) ELSE 0 END AS tokens_per_dollar,
                    CASE WHEN blended_cost_per_1m > 0 THEN ROUND(mmlu_score / blended_cost_per_1m, 2) ELSE 0 END AS efficiency_score
                FROM ({RANK_SQL})
                ORDER BY efficiency_score DESC, model
            """)
            cur = con.execute("SELECT * FROM finops_models ORDER BY efficiency_score DESC, model")
            cols = [c[0] for c in cur.description]
            results = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
        finally:
            con.close()

        for r in results:
            r["tokens_per_dollar_formatted"] = f"{r['tokens_per_dollar']:,}"
        print(f"[OK] Ranked {len(results)} models in DuckDB ({self.db_path}).")
        return results
