class PipelineError(Exception):
    """Base class for pipeline errors."""


class ValidationError(PipelineError):
    """Raised when contract validation fails."""


class StageError(PipelineError):
    """Raised when a stage execution fails."""

