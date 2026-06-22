"""
Pydantic data models for the Conversation Evaluation Benchmark System.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """A single turn in a conversation."""
    role: str = Field(..., description="Speaker role: 'user' or 'assistant'")
    content: str = Field(..., description="The text content of this turn")


class Conversation(BaseModel):
    """A full multi-turn conversation to evaluate."""
    conversation_id: Optional[str] = Field(None, description="Unique conversation ID")
    turns: List[ConversationTurn] = Field(..., description="Ordered list of conversation turns")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Optional metadata")


class FacetDefinition(BaseModel):
    """Definition of a single evaluation facet loaded from CSV."""
    facet_id: int
    raw_name: str
    clean_name: str
    category: str
    description: str
    score_1_anchor: str
    score_5_anchor: str


class FacetScore(BaseModel):
    """Score result for a single facet on a single conversation turn."""
    facet_id: int
    facet_name: str
    category: str
    score: int = Field(..., ge=1, le=5, description="Score from 1 to 5")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence 0.0-1.0")
    reasoning: str = Field("", description="Brief reasoning for the score")


class TurnEvaluation(BaseModel):
    """Evaluation results for a single conversation turn."""
    turn_index: int
    role: str
    content_preview: str = Field("", description="First 100 chars of the turn content")
    facet_scores: List[FacetScore] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    """API request to evaluate a conversation."""
    conversation: Conversation
    facet_ids: Optional[List[int]] = Field(
        None, description="Specific facet IDs to evaluate. None = all facets."
    )


class EvaluationResult(BaseModel):
    """Complete evaluation result for a conversation."""
    conversation_id: str
    total_facets: int
    total_turns: int
    turn_evaluations: List[TurnEvaluation]
    category_averages: Dict[str, float] = Field(
        default_factory=dict,
        description="Average score per category across all turns"
    )


class FacetListResponse(BaseModel):
    """Response for the GET /api/facets endpoint."""
    total: int
    categories: Dict[str, int]
    facets: List[FacetDefinition]
