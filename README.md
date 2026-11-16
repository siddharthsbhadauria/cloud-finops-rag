# cloud-finops-rag

[![CI](https://github.com/siddharthsbhadauria/cloud-finops-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/siddharthsbhadauria/cloud-finops-rag/actions/workflows/ci.yml)
[![Daily pipeline](https://github.com/siddharthsbhadauria/cloud-finops-rag/actions/workflows/daily_finops_rag.yml/badge.svg)](https://github.com/siddharthsbhadauria/cloud-finops-rag/actions/workflows/daily_finops_rag.yml)

A daily benchmark of LLM API prices. Every day a GitHub Actions job pulls current prices for 60 models across 8 providers, checks them against a data contract, joins published MMLU scores and ranks each model in DuckDB by quality per dollar.

**Dashboard:** https://siddharthsbhadauria.github.io/cloud-finops-rag/

## How it works

```
GitHub Actions cron
  -> OpenRouter models API (prices)       src/ingest/cloud_pricing.py
  -> MMLU lookup table                    src/ingest/llm_evals.py
  -> data contract                        src/quality/data_contracts.py
  -> DuckDB join and ranking              src/analytics/finops_engine.py
  -> JSON for the dashboard               generate_dataset.py
  -> GitHub Pages                         index.html, app.js
```

- **Prices** come from the OpenRouter models API, which lists per-token prices for each provider's hosted models. The pipeline keeps the top models per provider, 60 in total.
- **Quality scores** come from a hand-maintained table of published MMLU results. Models that aren't in the table get an estimate based on size and context window. The dashboard marks those rows as estimates and leaves them out of the daily picks.
- **The data contract** is plain Python. It stops the run if any field is missing, a price is negative or an MMLU score falls outside 0 to 100.
- **DuckDB** loads prices and scores into tables, joins them and computes the scores in SQL. The result is kept in `data/finops.duckdb`.
- **The daily summary** is a short Markdown brief filled in from a template. No LLM or vector search is involved; the repo name comes from an earlier plan.

## The numbers

| Metric | Formula |
| :--- | :--- |
| Blended price | 75% of the input price + 25% of the output price, per million tokens |
| Tokens per dollar | 1,000,000 / blended price |
| Value score | MMLU / blended price |

The value score ignores latency, context length and task fit. Treat it as a first filter, not a verdict.

## Run it locally

```bash
pip install -r requirements.txt
python generate_dataset.py          # writes data/finops_dataset.json and .js
python -m http.server               # then open http://localhost:8000
```

Tests and lint:

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

## License

MIT
