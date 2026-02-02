# app/ingestion/validator.py

from app.core.constants import SUPPORTED_LANGUAGE, MAX_FILE_SIZE_KB
from app.core.exceptions import (
    UnsupportedLanguageError,
    FileSizeExceededError,
    InvalidCodeError
)

def validate_language(language: str) -> str:
    if not isinstance(language, str):
        raise UnsupportedLanguageError("Language must be a string")

    normalized = language.strip().lower()

    if normalized != SUPPORTED_LANGUAGE:
        raise UnsupportedLanguageError(
            f"Only {SUPPORTED_LANGUAGE} is supported"
        )

    return normalized



def validate_file_size(content: str):
    size_kb = len(content.encode("utf-8")) / 1024
    if size_kb > MAX_FILE_SIZE_KB:
        raise FileSizeExceededError(
            f"File exceeds {MAX_FILE_SIZE_KB} KB limit"
        )

def validate_not_empty(content: str):
    if not content.strip():
        raise InvalidCodeError("Empty file content")
