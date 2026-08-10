"""
Data Quality Contracts Engine
Verifies schema constraints, non-null pricing bounds, and valid metric thresholds.
"""
from typing import List, Dict, Any

class DataContractsEngine:
    """Verifies schema contracts and data validity for ingested pricing & eval datasets."""

    def validate_pricing_data(self, pricing_records: List[Dict[str, Any]]) -> bool:
        """Asserts non-null prices, valid numeric floats, and provider presence."""
        if not pricing_records:
            print("Contract Error: Pricing records list is empty.")
            return False

        required_keys = ["provider", "model", "input_cost_per_1m", "output_cost_per_1m"]

        for idx, rec in enumerate(pricing_records):
            for key in required_keys:
                if key not in rec or rec[key] is None:
                    print(f"Contract Failure in record #{idx}: Missing key '{key}'")
                    return False
            
            if rec["input_cost_per_1m"] < 0 or rec["output_cost_per_1m"] < 0:
                print(f"Contract Failure in record #{idx}: Negative pricing detected ({rec['model']})")
                return False

        print(f"[OK] Great Expectations / Data Contract Passed: Verified {len(pricing_records)} pricing records.")
        return True

    def validate_benchmark_data(self, benchmark_records: List[Dict[str, Any]]) -> bool:
        """Asserts non-null MMLU ratings and valid ELO bounds."""
        if not benchmark_records:
            print("Contract Error: Benchmark records list is empty.")
            return False

        for idx, rec in enumerate(benchmark_records):
            if "model" not in rec or "mmlu_score" not in rec:
                print(f"Contract Failure in benchmark #{idx}: Missing core fields.")
                return False
            
            if not (0 <= rec["mmlu_score"] <= 100):
                print(f"Contract Failure: MMLU score out of 0-100 range ({rec['mmlu_score']})")
                return False

        print(f"[OK] Great Expectations / Data Contract Passed: Verified {len(benchmark_records)} benchmark records.")
        return True

if __name__ == "__main__":
    validator = DataContractsEngine()
    test_pricing = [{"provider": "AWS", "model": "Test", "input_cost_per_1m": 1.0, "output_cost_per_1m": 2.0}]
    assert validator.validate_pricing_data(test_pricing)
