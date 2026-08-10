"""
Multi-Cloud & AI Model Dynamic API Ingestor
Dynamically fetches live AI models & tokenomics from public APIs without hardcoding.
"""
import requests
import json
import os
from typing import List, Dict, Any

class CloudPricingIngestor:
    """Dynamically ingests AI model pricing and specs from OpenRouter & Cloud APIs."""

    OPENROUTER_API = "https://openrouter.ai/api/v1/models"
    AZURE_RETAIL_API = "https://prices.azure.com/api/retail/prices?$filter=serviceName eq 'Virtual Machines' and priceType eq 'Consumption'"

    def fetch_dynamic_llm_prices(self, top_n: int = 50) -> List[Dict[str, Any]]:
        """Queries OpenRouter public API to dynamically extract live models, pricing, and context windows."""
        try:
            res = requests.get(self.OPENROUTER_API, timeout=12)
            res.raise_for_status()
            data = res.json().get('data', [])

            models = []
            for item in data:
                model_id = item.get("id", "")
                name = item.get("name", model_id)
                pricing = item.get("pricing", {})
                
                # Convert price per token string to price per 1M tokens float
                try:
                    input_per_1m = float(pricing.get("prompt", 0)) * 1_000_000
                    output_per_1m = float(pricing.get("completion", 0)) * 1_000_000
                except (ValueError, TypeError):
                    input_per_1m = 0.0
                    output_per_1m = 0.0

                context_len = item.get("context_length", 128000)

                # Extract clean provider name
                provider = "Open Provider"
                if "/" in model_id:
                    prov_slug = model_id.split("/")[0].lower()
                    if "google" in prov_slug: provider = "Google / GCP"
                    elif "anthropic" in prov_slug: provider = "Anthropic / AWS"
                    elif "openai" in prov_slug: provider = "OpenAI / Azure"
                    elif "deepseek" in prov_slug: provider = "DeepSeek API"
                    elif "meta" in prov_slug or "llama" in prov_slug: provider = "Meta AI"
                    elif "mistral" in prov_slug: provider = "Mistral AI"
                    elif "qwen" in prov_slug or "alibaba" in prov_slug: provider = "Qwen / Alibaba"
                    elif "cohere" in prov_slug: provider = "Cohere"

                # Filter out models with invalid names or zero prices unless popular free models
                if input_per_1m >= 0 and name:
                    models.append({
                        "provider": provider,
                        "model": name,
                        "model_id": model_id,
                        "input_cost_per_1m": round(input_per_1m, 4),
                        "output_cost_per_1m": round(output_per_1m, 4),
                        "context_window": context_len,
                        "region": "global"
                    })

            # Sort by context length & filter top N relevant models
            models.sort(key=lambda x: (x["input_cost_per_1m"], -x["context_window"]))
            print(f"[API SUCCESS] Dynamically fetched {len(models)} live AI models from OpenRouter API.")
            return models[:top_n]
        except Exception as e:
            print(f"[API ERROR] Failed to query dynamic OpenRouter API: {e}")
            return []

    def get_all_llm_pricing(self, top_n: int = 50) -> List[Dict[str, Any]]:
        """Returns dynamic API pricing data."""
        return self.fetch_dynamic_llm_prices(top_n=top_n)

if __name__ == "__main__":
    ingestor = CloudPricingIngestor()
    prices = ingestor.get_all_llm_pricing(top_n=10)
    print(f"Ingested {len(prices)} dynamic models from public API.")
    for p in prices[:3]:
        print(f" -> {p['model']} ({p['provider']}): ${p['input_cost_per_1m']}/1M in, ${p['output_cost_per_1m']}/1M out")
