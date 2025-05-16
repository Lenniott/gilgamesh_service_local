class DownloadError(Exception):
    """Raised when a media download fails."""
    pass

class UnsupportedURLError(Exception):
    """Raised when the provided URL is not supported."""
    pass

class ProcessingError(Exception):
    """Raised when media processing fails."""
    pass

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass 