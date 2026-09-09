"""
LLM Evaluation & Dynamic Benchmark Ingestor
Dynamically computes & matches model capability benchmarks for any API model.
"""
import re
from typing import List, Dict, Any

class LLMEvalsIngestor:
    """Dynamically produces benchmark capability evaluations for API-ingested models."""

    # Reference ELO & MMLU benchmarks for flagship families (ordered specific -> general)
    KNOWN_BENCHMARKS = {
        # Anthropic Generation 5 & 4
        "claude fable 5.1": {"mmlu_score": 96.8, "arena_elo": 1420, "tps": 75.0, "category": "Autonomous Agent & Frontier Leader"},
        "claude fable 5": {"mmlu_score": 95.9, "arena_elo": 1400, "tps": 80.0, "category": "Frontier Agent Leader"},
        "claude opus 5": {"mmlu_score": 95.5, "arena_elo": 1395, "tps": 70.0, "category": "Deep Reasoning & Frontier Synthesis"},
        "claude sonnet 5": {"mmlu_score": 93.8, "arena_elo": 1365, "tps": 115.0, "category": "Code & Agent Specialist"},
        "claude opus 4.8": {"mmlu_score": 93.2, "arena_elo": 1355, "tps": 75.0, "category": "Frontier Reasoning"},
        "claude opus 4.7": {"mmlu_score": 92.5, "arena_elo": 1345, "tps": 75.0, "category": "Frontier Reasoning"},
        "claude 3.7": {"mmlu_score": 91.2, "arena_elo": 1325, "tps": 85.0, "category": "Hybrid Reasoning Leader"},
        "claude 3.5": {"mmlu_score": 88.7, "arena_elo": 1282, "tps": 110.0, "category": "Code & Agent Specialist"},
        "claude haiku": {"mmlu_score": 84.5, "arena_elo": 1245, "tps": 140.0, "category": "High Speed Agent"},

        # OpenAI Generation 6, 5 & Reasoning
        "gpt-6 astra": {"mmlu_score": 96.4, "arena_elo": 1412, "tps": 65.0, "category": "Frontier State-of-the-Art Leader"},
        "gpt-6": {"mmlu_score": 96.2, "arena_elo": 1408, "tps": 65.0, "category": "Frontier State-of-the-Art Leader"},
        "gpt-5.6 luna": {"mmlu_score": 93.9, "arena_elo": 1370, "tps": 95.0, "category": "Frontier Multimodal"},
        "gpt-5.6 terra": {"mmlu_score": 94.4, "arena_elo": 1378, "tps": 85.0, "category": "Frontier Knowledge & Math"},
        "gpt-5.6 sol": {"mmlu_score": 93.6, "arena_elo": 1365, "tps": 90.0, "category": "Frontier Reasoning"},
        "gpt-5.6": {"mmlu_score": 93.8, "arena_elo": 1368, "tps": 92.0, "category": "Frontier Multimodal"},
        "gpt-4.5": {"mmlu_score": 92.1, "arena_elo": 1340, "tps": 65.0, "category": "Frontier Knowledge Leader"},
        "o3-mini": {"mmlu_score": 91.5, "arena_elo": 1318, "tps": 115.0, "category": "Reasoning Leader"},
        "o3": {"mmlu_score": 92.8, "arena_elo": 1345, "tps": 85.0, "category": "Advanced Reasoning Leader"},
        "o1": {"mmlu_score": 90.8, "arena_elo": 1312, "tps": 45.0, "category": "Reasoning Specialist"},
        "gpt-4o": {"mmlu_score": 88.6, "arena_elo": 1286, "tps": 82.1, "category": "Frontier Multimodal"},

        # Google Gemini Generation 3
        "gemini 3.8 flash": {"mmlu_score": 95.4, "arena_elo": 1390, "tps": 150.0, "category": "Ultra Fast Frontier Leader"},
        "gemini 3.8": {"mmlu_score": 95.2, "arena_elo": 1388, "tps": 145.0, "category": "Ultra Fast Frontier Leader"},
        "gemini 3.7 flash": {"mmlu_score": 94.2, "arena_elo": 1370, "tps": 135.0, "category": "Frontier Multimodal Flash"},
        "gemini 3.7": {"mmlu_score": 94.0, "arena_elo": 1368, "tps": 130.0, "category": "Frontier Multimodal Flash"},
        "gemini 3.6 flash": {"mmlu_score": 93.5, "arena_elo": 1360, "tps": 125.0, "category": "Frontier Flash Leader"},
        "gemini 3.5 flash": {"mmlu_score": 92.0, "arena_elo": 1335, "tps": 130.0, "category": "High Speed Flash"},
        "gemini 3": {"mmlu_score": 93.8, "arena_elo": 1355, "tps": 95.0, "category": "Frontier Multimodal"},
        "gemini 2.0": {"mmlu_score": 89.8, "arena_elo": 1305, "tps": 185.0, "category": "Ultra Fast Frontier"},

        # xAI Grok Generation 4
        "grok 4.6": {"mmlu_score": 93.8, "arena_elo": 1365, "tps": 85.0, "category": "Frontier Reasoning & Real-Time Search"},
        "grok 4.5": {"mmlu_score": 93.0, "arena_elo": 1350, "tps": 85.0, "category": "Frontier Reasoning & Real-Time Search"},
        "grok 4.3": {"mmlu_score": 91.5, "arena_elo": 1328, "tps": 90.0, "category": "Multi-Modal Agent"},
        "grok 4.20": {"mmlu_score": 90.8, "arena_elo": 1315, "tps": 95.0, "category": "Multi-Agent Specialist"},
        "grok": {"mmlu_score": 89.5, "arena_elo": 1295, "tps": 85.0, "category": "Reasoning & Search"},

        # Meta Llama & Muse
        "llama 4 maverick": {"mmlu_score": 92.4, "arena_elo": 1345, "tps": 110.0, "category": "Open Weights Frontier"},
        "llama 4 scout": {"mmlu_score": 89.6, "arena_elo": 1305, "tps": 160.0, "category": "Ultra Efficient Open Weights"},
        "llama 4": {"mmlu_score": 91.5, "arena_elo": 1330, "tps": 110.0, "category": "Open Weights Frontier"},
        "llama 3.3 70b": {"mmlu_score": 86.0, "arena_elo": 1265, "tps": 90.0, "category": "Open Weights Leader"},
        "llama 3 8b": {"mmlu_score": 68.5, "arena_elo": 1140, "tps": 120.0, "category": "Lightweight Open Model"},
        "muse spark": {"mmlu_score": 88.0, "arena_elo": 1280, "tps": 120.0, "category": "Efficient Open Architecture"},

        # DeepSeek Generation 4 & 3
        "deepseek v4 pro": {"mmlu_score": 93.2, "arena_elo": 1355, "tps": 90.0, "category": "Next-Gen Open Reasoning Leader"},
        "deepseek v4 flash": {"mmlu_score": 90.5, "arena_elo": 1315, "tps": 165.0, "category": "Ultra Low Cost High Speed"},
        "deepseek v4": {"mmlu_score": 92.5, "arena_elo": 1345, "tps": 90.0, "category": "Next-Gen Open Reasoning"},
        "deepseek v3.2": {"mmlu_score": 89.8, "arena_elo": 1298, "tps": 100.0, "category": "Cost Efficiency Leader"},
        "deepseek r1": {"mmlu_score": 90.8, "arena_elo": 1310, "tps": 48.0, "category": "Open Reasoning Leader"},
        "deepseek v3": {"mmlu_score": 88.5, "arena_elo": 1278, "tps": 95.0, "category": "Cost Efficiency Leader"},

        # Mistral
        "mistral large 3": {"mmlu_score": 90.8, "arena_elo": 1320, "tps": 95.0, "category": "Enterprise Multilingual"},
        "mistral-large-2512": {"mmlu_score": 90.8, "arena_elo": 1320, "tps": 95.0, "category": "Enterprise Multilingual"},
        "mistral medium 3": {"mmlu_score": 87.5, "arena_elo": 1275, "tps": 110.0, "category": "Mid-Tier Specialist"},
        "mistral small 4": {"mmlu_score": 84.8, "arena_elo": 1240, "tps": 140.0, "category": "High Speed Small Model"},
        "codestral": {"mmlu_score": 86.5, "arena_elo": 1260, "tps": 115.0, "category": "Code Specialist"},

        # Qwen
        "qwen3.8 max": {"mmlu_score": 91.8, "arena_elo": 1335, "tps": 95.0, "category": "High-Efficiency Coding Frontier"},
        "qwen3.8 flash": {"mmlu_score": 87.8, "arena_elo": 1275, "tps": 170.0, "category": "Ultra Fast Coding Model"},
        "qwen3.8": {"mmlu_score": 91.0, "arena_elo": 1320, "tps": 105.0, "category": "High-Efficiency Coding Frontier"},
        "qwen3.7 max": {"mmlu_score": 90.2, "arena_elo": 1310, "tps": 100.0, "category": "Multilingual Coding Leader"},
        "qwen3.7": {"mmlu_score": 88.5, "arena_elo": 1285, "tps": 110.0, "category": "Coding & Reasoning"},
        "qwen": {"mmlu_score": 85.5, "arena_elo": 1255, "tps": 105.0, "category": "Coding Specialist"}
    }

    def get_benchmarks_for_models(self, dynamic_models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dynamically matches or estimates benchmarks for API models using word boundaries."""
        benchmarks = []
        
        for item in dynamic_models:
            name_raw = item["model"].lower()
            id_raw = item.get("model_id", "").lower()
            target_text = f"{name_raw} {id_raw}".replace("-", " ").replace(":", " ").replace("/", " ")
            
            matched = False
            for key, val in self.KNOWN_BENCHMARKS.items():
                pattern = r'\b' + re.escape(key.replace("-", " ")) + r'\b'
                if re.search(pattern, target_text):
                    benchmarks.append({
                        "model": item["model"],
                        "mmlu_score": val["mmlu_score"],
                        "arena_elo": val["arena_elo"],
                        "avg_throughput_tps": val["tps"],
                        "category": val["category"]
                    })
                    matched = True
                    break

            if not matched:
                # Dynamic fallback estimation based on model characteristics
                ctx = item.get("context_window", 128000)
                # If small model (8b/7b/mini) vs large model
                if any(sm in target_text for sm in ["8b", "7b", "3b", "1b", "nano", "mini", "small"]):
                    base_mmlu = 72.0
                    elo_base = 1180
                else:
                    base_mmlu = 82.0
                    elo_base = 1250

                estimated_mmlu = round(base_mmlu + min((ctx / 200000.0) * 4.0, 8.0), 1)
                benchmarks.append({
                    "model": item["model"],
                    "mmlu_score": estimated_mmlu,
                    "arena_elo": elo_base + int(estimated_mmlu * 1.0),
                    "avg_throughput_tps": 85.0,
                    "category": "API AI Model"
                })

        return benchmarks

    def get_benchmarks(self) -> List[Dict[str, Any]]:
        """Legacy default fallback interface."""
        return list(self.KNOWN_BENCHMARKS.values())

if __name__ == "__main__":
    ingestor = LLMEvalsIngestor()
    test_models = [
        {"model": "Claude Fable 5.1", "model_id": "anthropic/claude-fable-5.1", "context_window": 1000000},
        {"model": "Claude Opus 5", "model_id": "anthropic/claude-opus-5", "context_window": 1000000},
        {"model": "Gemini 3.8 Flash", "model_id": "google/gemini-3.8-flash", "context_window": 1048576},
        {"model": "GPT-6 Astra", "model_id": "openai/gpt-6-astra", "context_window": 1050000},
        {"model": "Sao10K: Llama 3 8B Lunaris", "model_id": "sao10k/l3-8b-lunaris", "context_window": 8192}
    ]
    results = ingestor.get_benchmarks_for_models(test_models)
    for r in results:
        print(f"Matched: {r['model']} -> MMLU: {r['mmlu_score']}, ELO: {r['arena_elo']}, Category: {r['category']}")
