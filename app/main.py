"""
FastAPI application — serves the evaluation API and the web UI.
"""

import logging
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    EvaluationRequest,
    EvaluationResult,
    FacetListResponse,
    Conversation,
    ConversationTurn,
)
from app.facet_registry import registry
from app.scorer import ConversationScorer
from app.llm_engine import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Conversation Evaluation Benchmark",
    description=(
        "A production-ready benchmark system that scores conversation turns "
        "on 300+ facets covering linguistic quality, pragmatics, safety and emotion."
    ),
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global scorer
scorer = ConversationScorer()


# ── API Routes ──

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "total_facets": registry.total,
        "categories": registry.categories,
    }


@app.get("/api/facets", response_model=FacetListResponse)
async def get_facets():
    """Return all registered facets with their metadata."""
    return FacetListResponse(
        total=registry.total,
        categories=registry.categories,
        facets=registry.get_all(),
    )


@app.post("/api/evaluate", response_model=EvaluationResult)
async def evaluate_conversation(request: EvaluationRequest):
    """
    Evaluate a conversation across all (or selected) facets.
    Uses multi-step prompting — NOT one-shot.
    """
    try:
        if not request.conversation.turns:
            raise HTTPException(400, "Conversation must have at least one turn")

        if not request.conversation.conversation_id:
            request.conversation.conversation_id = str(uuid.uuid4())[:8]

        result = await scorer.evaluate(
            request.conversation,
            facet_ids=request.facet_ids,
        )
        return result

    except Exception as e:
        logger.error(f"Evaluation error: {e}", exc_info=True)
        raise HTTPException(500, f"Evaluation failed: {str(e)}")





@app.get("/api/facets/categories")
async def get_categories():
    """Get facet categories with counts."""
    return registry.categories


@app.post("/api/facets/reload")
async def reload_facets():
    """Hot-reload facets from CSV (useful after adding new facets)."""
    try:
        registry.reload()
        return {
            "status": "reloaded",
            "total_facets": registry.total,
            "categories": registry.categories,
        }
    except Exception as e:
        raise HTTPException(500, f"Reload failed: {str(e)}")


# ── Static File Serving ──

@app.get("/")
async def serve_ui():
    return FileResponse("static/index.html")


# Mount static files AFTER routes
import os
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
