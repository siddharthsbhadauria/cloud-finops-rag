"""
Master Data Orchestrator
Executes full ingestion, validation contracts, DuckDB transformations, RAG brief generation, and JSON web dataset export.
"""
import os
import json
from datetime import datetime, timezone

from src.ingest.cloud_pricing import CloudPricingIngestor
from src.ingest.llm_evals import LLMEvalsIngestor
from src.quality.data_contracts import DataContractsEngine
from src.analytics.finops_engine import FinOpsEngine
from src.rag.vector_finops import VectorFinOpsEngine

def run_pipeline():
    print("[INFO] Starting Cloud-FinOps-RAG Data Pipeline Execution...")

    # 1. Dynamic API Ingestion across all providers (Google, Anthropic, OpenAI, DeepSeek, Meta, Qwen)
    pricing_data = CloudPricingIngestor().get_all_llm_pricing(top_n=40)
    evals_data = LLMEvalsIngestor().get_benchmarks_for_models(pricing_data)

    # 2. Data Quality Contracts Gate
    validator = DataContractsEngine()
    if not validator.validate_pricing_data(pricing_data) or not validator.validate_benchmark_data(evals_data):
        raise ValueError("Data Quality Contract verification failed! Halting pipeline execution.")

    # 3. Analytics Engine
    analytics_engine = FinOpsEngine(db_path="data/finops.duckdb")
    analyzed_models = analytics_engine.process_analytics(pricing_data, evals_data)

    # 4. RAG Brief & Insights Generation
    rag_engine = VectorFinOpsEngine()
    rag_summary = rag_engine.generate_rag_brief(analyzed_models)

    # 5. Export JSON Dataset for GitHub Pages Frontend
    dataset = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_models_tracked": len(analyzed_models),
        "providers": list(set(m["provider"] for m in analyzed_models)),
        "summary": rag_summary,
        "models": analyzed_models
    }

    os.makedirs("data", exist_ok=True)
    out_json = os.path.join("data", "finops_dataset.json")
    out_js = os.path.join("data", "finops_dataset.js")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    with open(out_js, "w", encoding="utf-8") as f:
        f.write("window.FINOPS_DATA = " + json.dumps(dataset, indent=2, ensure_ascii=False) + ";\n")

    print(f"[SUCCESS] Exported {out_json} and {out_js} with {len(analyzed_models)} benchmarked models.")

if __name__ == "__main__":
    run_pipeline()
