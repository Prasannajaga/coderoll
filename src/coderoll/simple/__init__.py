from ..config import SandboxConfig
from ..simple_exec import SimpleExecutionResult, execute_simple

# Friendly alias for users who prefer a shorter verb.
run_code = execute_simple

__all__ = [
    "SandboxConfig",
    "SimpleExecutionResult",
    "execute_simple",
    "run_code",
]
