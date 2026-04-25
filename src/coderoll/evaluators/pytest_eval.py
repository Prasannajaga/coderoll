from ..result import ExecutionResult, Score
from ..scoring import compute_score


class PytestEvaluator:
    def score(self, execution: ExecutionResult) -> Score:
        breakdown = compute_score(execution)
        return Score(
            value=breakdown.value,
            passed=breakdown.passed,
            details=breakdown.details,
        )
