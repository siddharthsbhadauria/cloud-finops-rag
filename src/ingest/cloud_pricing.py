"""
Multi-Cloud & AI Model Dynamic API Ingestor
Dynamically fetches live AI models & tokenomics from public APIs with balanced provider coverage.
"""
import requests
import json
import os
import re
from typing import List, Dict, Any

class CloudPricingIngestor:
    """Dynamically ingests AI model pricing and specs from OpenRouter & Cloud APIs."""

    OPENROUTER_API = "https://openrouter.ai/api/v1/models"

    # Priority flagship & frontier models across all major AI providers
    PRIORITY_PATTERNS = [
        # Anthropic Next-Gen
        r"claude-fable-5\.1", r"claude-fable-5", r"claude-opus-5", r"claude-sonnet-5", r"claude-opus-4\.8", r"claude-haiku-4\.5",
        # Google Frontier
        r"gemini-3\.8", r"gemini-3\.7", r"gemini-3\.6", r"gemini-3\.5", r"gemini-3-pro", r"gemini-2\.5",
        # OpenAI Frontier
        r"gpt-6", r"gpt-5\.6", r"gpt-4\.5", r"o3", r"o1", r"gpt-4o",
        # DeepSeek
        r"deepseek-v4", r"deepseek-v3\.2", r"deepseek-r1", r"deepseek-v3",
        # Meta AI
        r"llama-4", r"llama-3\.3", r"muse-spark",
        # xAI / Grok
        r"grok-4\.6", r"grok-4\.5", r"grok-4\.3", r"grok-4\.20",
        # Mistral
        r"mistral-large-2512", r"mistral-medium-3", r"mistral-small-2603", r"codestral",
        # Qwen / Alibaba
        r"qwen3\.8", r"qwen3\.7", r"qwen-2\.5-coder"
    ]

    def _get_priority_score(self, model_id: str, name: str) -> int:
        """Scores models so that latest generation flagships rank highest."""
        combined = f"{model_id} {name}".lower()
        score = 0
        for idx, pattern in enumerate(self.PRIORITY_PATTERNS):
            if re.search(pattern, combined):
                # Earlier patterns have higher priority
                score += (len(self.PRIORITY_PATTERNS) - idx) * 10
                break
        
        # Boost newer version numbers in general
        if "5.1" in combined or "5.0" in combined or "-5" in combined:
            score += 25
        elif "4.8" in combined or "4.6" in combined or "4.5" in combined or "3.8" in combined or "3.7" in combined:
            score += 20
        elif "3.6" in combined or "3.5" in combined or "v4" in combined or "llama-4" in combined:
            score += 15

        return score

    def fetch_dynamic_llm_prices(self, top_n: int = 60) -> List[Dict[str, Any]]:
        """Queries OpenRouter public API, balancing model coverage across all 8 top providers."""
        try:
            res = requests.get(self.OPENROUTER_API, timeout=15)
            res.raise_for_status()
            data = res.json().get('data', [])

            models_by_provider: Dict[str, List[Dict[str, Any]]] = {}

            for item in data:
                model_id = item.get("id", "")
                name = item.get("name", model_id)
                pricing = item.get("pricing", {})

                # Skip batch, free-tier, internal, or test endpoints
                if ":batch" in model_id or ":free" in model_id or model_id.startswith("openrouter/"):
                    continue

                # Strip leading tilde or alias symbols
                clean_model_id = model_id.lstrip("~")

                # Convert price per token string to price per 1M tokens float
                try:
                    input_per_1m = float(pricing.get("prompt", 0)) * 1_000_000
                    output_per_1m = float(pricing.get("completion", 0)) * 1_000_000
                except (ValueError, TypeError):
                    input_per_1m = 0.0
                    output_per_1m = 0.0

                context_len = int(item.get("context_length", 128000))

                # Categorize provider
                lower_id = clean_model_id.lower()
                provider = "Other Provider"
                if "anthropic" in lower_id or "claude" in lower_id:
                    provider = "Anthropic / AWS"
                elif "google" in lower_id or "gemma" in lower_id:
                    provider = "Google / GCP"
                elif "openai" in lower_id or "/gpt" in lower_id or "/o1" in lower_id or "/o3" in lower_id:
                    provider = "OpenAI / Azure"
                elif "deepseek" in lower_id:
                    provider = "DeepSeek API"
                elif "meta" in lower_id or "llama" in lower_id:
                    provider = "Meta AI"
                elif "x-ai" in lower_id or "grok" in lower_id:
                    provider = "xAI / Grok"
                elif "mistral" in lower_id:
                    provider = "Mistral AI"
                elif "qwen" in lower_id or "alibaba" in lower_id:
                    provider = "Qwen / Alibaba"

                # Clean model display name
                clean_name = name
                prefixes = [
                    "Anthropic: ", "Google: ", "OpenAI: ", "DeepSeek: ", "Meta: ", 
                    "SpaceXAI: ", "xAI: ", "Mistral: ", "Qwen: ", "AionLabs: "
                ]
                for pfx in prefixes:
                    clean_name = clean_name.replace(pfx, "")
                clean_name = clean_name.strip()

                priority = self._get_priority_score(clean_model_id, clean_name)

                # Exclude unverified community endpoints / fine-tunes
                if provider == "Other Provider":
                    continue

                # Filter out invalid entries
                if input_per_1m >= 0 and output_per_1m >= 0 and clean_name:
                    model_rec = {
                        "provider": provider,
                        "model": clean_name,
                        "model_id": clean_model_id,
                        "input_cost_per_1m": round(input_per_1m, 4),
                        "output_cost_per_1m": round(output_per_1m, 4),
                        "context_window": context_len,
                        "region": "global",
                        "priority_score": priority,
                        "is_featured": (priority > 0)
                    }

                    if provider not in models_by_provider:
                        models_by_provider[provider] = []
                    models_by_provider[provider].append(model_rec)

            selected_models = []

            # 1. Round-robin: Pick top 7 models from EACH major provider
            target_per_provider = max(6, top_n // max(1, len(models_by_provider)))
            for prov, items in models_by_provider.items():
                # Sort by priority score desc, non-zero price first, then context window
                items.sort(key=lambda x: (
                    -x["priority_score"],
                    x["input_cost_per_1m"] == 0,
                    -x["context_window"]
                ))
                selected_models.extend(items[:target_per_provider])

            # 2. Add remaining high priority models across all providers
            for prov, items in models_by_provider.items():
                selected_models.extend(items[target_per_provider:])

            # Deduplicate by model clean name & model_id
            unique_models = []
            seen_ids = set()
            seen_names = set()
            for m in selected_models:
                if m["model_id"] not in seen_ids and m["model"] not in seen_names:
                    seen_ids.add(m["model_id"])
                    seen_names.add(m["model"])
                    unique_models.append(m)

            print(f"[API SUCCESS] Dynamically loaded {len(unique_models)} API models spanning {len(models_by_provider)} providers.")
            return unique_models[:top_n]
        except Exception as e:
            print(f"[API ERROR] Failed to query dynamic OpenRouter API: {e}")
            return []

    def get_all_llm_pricing(self, top_n: int = 60) -> List[Dict[str, Any]]:
        """Returns dynamic API pricing data."""
        return self.fetch_dynamic_llm_prices(top_n=top_n)

if __name__ == "__main__":
    ingestor = CloudPricingIngestor()
    prices = ingestor.get_all_llm_pricing(top_n=30)
    print(f"\nIngested {len(prices)} balanced dynamic models:")
    for p in prices:
        print(f" -> [{p['provider']}] {p['model']} (${p['input_cost_per_1m']}/1M in, ${p['output_cost_per_1m']}/1M out, Prio: {p['priority_score']})")
