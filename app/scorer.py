"""
Scorer — the main orchestrator that ties everything together.
Processes conversations through the multi-step evaluation pipeline.
"""

import uuid
import asyncio
import logging
from typing import Dict, List, Optional
from collections import defaultdict

from app.models import (
    Conversation,
    EvaluationResult,
    FacetScore,
    TurnEvaluation,
    FacetDefinition,
)
from app.facet_registry import registry
from app.prompt_builder import build_step1_prompt, build_step2_prompt
from app.config import settings
from app.output_parser import parse_step1_response, parse_step2_response
from app.llm_engine import BaseLLMEngine, get_engine

logger = logging.getLogger(__name__)


class ConversationScorer:
    """
    Orchestrates the multi-step evaluation of conversations.

    Pipeline per turn:
    1. Get facet batches from registry
    2. For each batch:
       a. Step 1: Generate reasoning (analysis)
       b. Step 2: Assign scores + confidence
    3. Aggregate results
    """

    def __init__(self, engine: Optional[BaseLLMEngine] = None):
        self.engine = engine or get_engine()
        self.registry = registry

    async def evaluate(
        self,
        conversation: Conversation,
        facet_ids: Optional[List[int]] = None,
    ) -> EvaluationResult:
        """
        Evaluate all turns in a conversation across all (or selected) facets.
        """
        conv_id = conversation.conversation_id or str(uuid.uuid4())[:8]
        turn_evaluations: List[TurnEvaluation] = []

        for turn_idx, turn in enumerate(conversation.turns):
            logger.info(f"Evaluating turn {turn_idx+1}/{len(conversation.turns)}")

            turn_scores = await self._evaluate_turn(
                conversation.turns,
                turn_idx,
                facet_ids,
            )

            turn_eval = TurnEvaluation(
                turn_index=turn_idx,
                role=turn.role,
                content_preview=turn.content[:100],
                facet_scores=turn_scores,
            )
            turn_evaluations.append(turn_eval)

        # Compute category averages
        category_averages = self._compute_category_averages(turn_evaluations)

        return EvaluationResult(
            conversation_id=conv_id,
            total_facets=self.registry.total,
            total_turns=len(conversation.turns),
            turn_evaluations=turn_evaluations,
            category_averages=category_averages,
        )

        return all_scores
    
    async def _evaluate_turn(
        self,
        turns: list,
        target_turn_index: int,
        facet_ids: Optional[List[int]] = None,
    ) -> List[FacetScore]:
        """Evaluate a single turn across all facet batches concurrently."""
        all_scores: List[FacetScore] = []
        batches = list(self.registry.get_batches(facet_ids=facet_ids))
        
        # Limit concurrency to avoid 429/402 errors on free tier
        sem = asyncio.Semaphore(2)  # 2 concurrent batches

        async def process_batch(idx, batch):
            async with sem:
                logger.info(f"  Batch {idx+1}/{len(batches)} ({len(batch)} facets)")
                return await self._evaluate_batch(turns, target_turn_index, batch)

        tasks = [process_batch(i, batch) for i, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks)
        
        for res in results:
            all_scores.extend(res)

        return all_scores

    async def _evaluate_batch(
        self,
        turns: list,
        target_turn_index: int,
        facets: List[FacetDefinition],
    ) -> List[FacetScore]:
        """
        Run the two-step evaluation for a batch of facets on one turn.
        """
        facet_names = [f.clean_name for f in facets]
        facet_lookup = {f.clean_name.lower(): f for f in facets}

        # ── Step 1: Analysis ──
        step1_prompt = build_step1_prompt(turns, target_turn_index, facets)
        try:
            step1_response = await self.engine.generate(step1_prompt)
            step1_analyses = parse_step1_response(step1_response, facet_names)
        except Exception as e:
            logger.error(f"Step 1 failed: {e}")
            step1_analyses = "\n".join(
                f"- **{name}**: Analysis unavailable" for name in facet_names
            )

        # ── Step 2: Scoring ──
        step2_prompt = build_step2_prompt(
            turns, target_turn_index, facets, step1_analyses
        )
        try:
            step2_response = await self.engine.generate(step2_prompt)
            raw_scores = parse_step2_response(step2_response, facet_names)
        except Exception as e:
            logger.error(f"Step 2 failed: {e}")
            # Return default scores
            raw_scores = [
                {
                    "facet_name": name,
                    "score": 3,
                    "confidence": 0.1,
                    "reasoning": f"Scoring failed: {e}",
                }
                for name in facet_names
            ]

        # ── Convert to FacetScore models ──
        result: List[FacetScore] = []
        for raw in raw_scores:
            fname = raw["facet_name"]
            facet_def = facet_lookup.get(fname.lower())
            if not facet_def:
                # Try fuzzy match
                facet_def = self._fuzzy_match_facet(fname, facet_lookup)

            if facet_def:
                result.append(
                    FacetScore(
                        facet_id=facet_def.facet_id,
                        facet_name=facet_def.clean_name,
                        category=facet_def.category,
                        score=raw["score"],
                        confidence=raw["confidence"],
                        reasoning=raw.get("reasoning", ""),
                    )
                )

        return result

    def _fuzzy_match_facet(
        self, name: str, lookup: Dict[str, FacetDefinition]
    ) -> Optional[FacetDefinition]:
        """Try to match a facet name that doesn't exactly match."""
        name_lower = name.lower().strip()

        # Try partial match
        for key, facet in lookup.items():
            if name_lower in key or key in name_lower:
                return facet

        return None

    def _compute_category_averages(
        self, turn_evals: List[TurnEvaluation]
    ) -> Dict[str, float]:
        """Compute average score per category across all turns."""
        category_scores: Dict[str, List[float]] = defaultdict(list)

        for turn_eval in turn_evals:
            for fs in turn_eval.facet_scores:
                category_scores[fs.category].append(fs.score)

        return {
            cat: round(sum(scores) / len(scores), 2)
            for cat, scores in sorted(category_scores.items())
            if scores
        }
