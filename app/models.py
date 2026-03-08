from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

class Issue(BaseModel):
    category: str
    severity: str
    line: Optional[int] = None
    suggestion: str

class LLMReview(BaseModel):
    summary: str = "LLM error: invalid JSON"
    confidence: float = 0.0
    issues: List[Issue] = []

class RefactorResult(BaseModel):
    refactored_code: str
    diff: str

class DocResult(BaseModel):
    documented_code: str
    issues: List[Issue] = []
