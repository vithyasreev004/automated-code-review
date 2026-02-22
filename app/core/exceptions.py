class CodeReviewException(Exception):
    """Base exception for code review system"""

class UnsupportedLanguageError(CodeReviewException):
    pass

class InvalidCodeError(CodeReviewException):
    pass

class FileSizeExceededError(CodeReviewException):
    pass
