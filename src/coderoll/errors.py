class CoderollError(Exception):
    """Base error for coderoll."""


class TaskError(CoderollError):
    """Raised when loading or validating a task fails."""


class CandidateError(CoderollError):
    """Raised when loading or validating candidates fails."""


class SandboxError(CoderollError):
    """Raised when sandbox execution fails."""


class DockerError(SandboxError):
    """Raised for Docker-specific failures."""


class StoreError(CoderollError):
    """Raised when reading or writing run records fails."""
