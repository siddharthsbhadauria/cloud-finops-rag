"""
Multi-Cloud & AI Model Dynamic API Ingestor
Dynamically fetches live AI models & tokenomics from public APIs with balanced provider coverage.
"""
import requests
import json
import os
from typing import List, Dict, Any

class CloudPricingIngestor:
    """Dynamically ingests AI model pricing and specs from OpenRouter & Cloud APIs."""

    OPENROUTER_API = "https://openrouter.ai/api/v1/models"

    # Featured model slugs to prioritize across providers
    FEATURED_SLUGS = [
        "google/gemini-3.6-flash", "google/gemini-3.5-flash", "google/gemini-2.5-pro", "google/gemini-2.5-flash",
        "anthropic/claude-sonnet-4.6", "anthropic/claude-haiku-4.5", "anthropic/claude-3-haiku", "anthropic/claude-opus-4",
        "openai/gpt-4o", "openai/o3-mini", "openai/o1", "openai/gpt-4o-mini",
        "deepseek/deepseek-r1", "deepseek/deepseek-chat", "deepseek/deepseek-v3",
        "meta-llama/llama-3.3-70b-instruct", "qwen/qwen-2.5-coder-32b-instruct", "mistralai/mistral-large-2411"
    ]

    def fetch_dynamic_llm_prices(self, top_n: int = 40) -> List[Dict[str, Any]]:
        """Queries OpenRouter public API, balancing model coverage across Anthropic, Google, OpenAI, DeepSeek, and Meta."""
        try:
            res = requests.get(self.OPENROUTER_API, timeout=12)
            res.raise_for_status()
            data = res.json().get('data', [])

            models_by_provider: Dict[str, List[Dict[str, Any]]] = {}

            for item in data:
                model_id = item.get("id", "")
                name = item.get("name", model_id)
                pricing = item.get("pricing", {})

                # Skip batch endpoints
                if ":batch" in model_id:
                    continue
                
                # Convert price per token string to price per 1M tokens float
                try:
                    input_per_1m = float(pricing.get("prompt", 0)) * 1_000_000
                    output_per_1m = float(pricing.get("completion", 0)) * 1_000_000
                except (ValueError, TypeError):
                    input_per_1m = 0.0
                    output_per_1m = 0.0

                context_len = item.get("context_length", 128000)

                # Identify Provider
                provider = "Other Provider"
                if "google" in model_id or "gemma" in model_id:
                    provider = "Google / GCP"
                elif "anthropic" in model_id or "claude" in model_id:
                    provider = "Anthropic / AWS"
                elif "openai" in model_id or "/gpt" in model_id or "/o1" in model_id or "/o3" in model_id:
                    provider = "OpenAI / Azure"
                elif "deepseek" in model_id:
                    provider = "DeepSeek API"
                elif "meta" in model_id or "llama" in model_id:
                    provider = "Meta AI"
                elif "mistral" in model_id:
                    provider = "Mistral AI"
                elif "qwen" in model_id or "alibaba" in model_id:
                    provider = "Qwen / Alibaba"

                clean_name = name.replace("Anthropic: ", "").replace("Google: ", "").replace("OpenAI: ", "").replace("DeepSeek: ", "").replace("Meta: ", "")

                # Filter out negative pricing models, test endpoints, or invalid names
                if input_per_1m >= 0 and output_per_1m >= 0 and name and not model_id.startswith("openrouter/"):
                    model_rec = {
                        "provider": provider,
                        "model": clean_name,
                        "model_id": model_id,
                        "input_cost_per_1m": round(input_per_1m, 4),
                        "output_cost_per_1m": round(output_per_1m, 4),
                        "context_window": context_len,
                        "region": "global",
                        "is_featured": any(f in model_id for f in self.FEATURED_SLUGS)
                    }

                    if provider not in models_by_provider:
                        models_by_provider[provider] = []
                    models_by_provider[provider].append(model_rec)

            selected_models = []
            
            # 1. Round-robin: Pick top 4 models from EACH provider to ensure Google, Anthropic, OpenAI, etc. all get equal slots
            for prov, items in models_by_provider.items():
                items.sort(key=lambda x: (not x["is_featured"], x["input_cost_per_1m"] == 0, -x["context_window"]))
                selected_models.extend(items[:4])

            # 2. Add remaining models
            for prov, items in models_by_provider.items():
                selected_models.extend(items[4:])

            # Deduplicate by model_id
            unique_models = []
            seen = set()
            for m in selected_models:
                if m["model_id"] not in seen:
                    seen.add(m["model_id"])
                    unique_models.append(m)

            print(f"[API SUCCESS] Dynamically loaded {len(unique_models)} API models spanning {len(models_by_provider)} providers.")
            return unique_models[:top_n]
        except Exception as e:
            print(f"[API ERROR] Failed to query dynamic OpenRouter API: {e}")
            return []

    def get_all_llm_pricing(self, top_n: int = 40) -> List[Dict[str, Any]]:
        """Returns dynamic API pricing data."""
        return self.fetch_dynamic_llm_prices(top_n=top_n)

if __name__ == "__main__":
    ingestor = CloudPricingIngestor()
    prices = ingestor.get_all_llm_pricing(top_n=20)
    print(f"\nIngested {len(prices)} balanced dynamic models:")
    for p in prices:
        print(f" -> [{p['provider']}] {p['model']} (${p['input_cost_per_1m']}/1M in, ${p['output_cost_per_1m']}/1M out)")
