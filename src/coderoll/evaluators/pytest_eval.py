from ..result import ExecutionResult, Score


class PytestEvaluator:
    def score(self, execution: ExecutionResult) -> Score:
        passed = execution.exit_code == 0 and not execution.timed_out
        value = 1.0 if passed else 0.0
        return Score(
            value=value,
            passed=passed,
            details={
                "exit_code": execution.exit_code,
                "timed_out": execution.timed_out,
            },
        )
