class RepositoryError(Exception):
    """Base exception for repository operations."""


class RepositoryNotFoundError(RepositoryError):
    """Raised when the local repository is not found."""


class CloneError(RepositoryError):
    """Raised when cloning fails."""


class PullError(RepositoryError):
    """Raised when pulling fails."""
