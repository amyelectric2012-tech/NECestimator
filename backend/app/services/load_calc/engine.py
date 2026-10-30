"""
Load Calculation Engine – Full Orchestrator
"""

from app.services.load_calc.optional_82 import calculate_optional_82
from app.services.load_calc.optional_83 import calculate_optional_83
from app.services.load_calc.optional_84 import calculate_optional_84
from app.services.load_calc.schemas import LoadCalcRequest, LoadCalcResult
from app.services.load_calc.standard import calculate_standard


class LoadCalcEngine:
    def calculate(self, data: LoadCalcRequest) -> list[LoadCalcResult]:
        results: list[LoadCalcResult] = []

        results.append(calculate_standard(data))

        if data.include_both_methods and data.project_type in ["single_family", "adu", "duplex"] and data.num_units == 1:
            results.append(calculate_optional_82(data))
            results.append(calculate_optional_83(data))

        if data.include_both_methods and data.project_type == "multi_family" and data.num_units >= 3:
            results.append(calculate_optional_84(data))

        return results
