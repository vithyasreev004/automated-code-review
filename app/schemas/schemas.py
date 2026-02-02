from pydantic import BaseModel
from typing import List, Optional

# -------------------------------
# LLM output for each file
# -------------------------------
class LLMReview(BaseModel):
    explanation: Optional[str] = None
    generated_docstrings: Optional[str] = None
    refactor_suggestions: Optional[str] = None

# -------------------------------
# Response model for review/refactor
# -------------------------------
class ReviewResult(BaseModel):
    filename: str
    ast_summary: Optional[dict] = None
    static_analysis_issues: Optional[List[dict]] = []
    llm_review: LLMReview

class ReviewResponse(BaseModel):
    summary: dict
    issues: List[dict]
    documentation: dict
    llm_results: List[ReviewResult]
