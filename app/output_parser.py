"""
Output Parser — extracts structured JSON from LLM text output.
Handles markdown fences, partial JSON, and validation.
"""

import json
import re
import logging
from typing import Dict, List, Optional, Any

from app.config import settings

logger = logging.getLogger(__name__)


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM output text.
    Handles: raw JSON, markdown code fences, partial JSON.
    """
    # Try 1: Extract from markdown code fences
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try 2: Find JSON object directly
    brace_match = re.search(r'\{.*\}', text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    # Try 3: Find JSON array
    bracket_match = re.search(r'\[.*\]', text, re.DOTALL)
    if bracket_match:
        try:
            data = json.loads(bracket_match.group(0))
            return {"items": data}
        except json.JSONDecodeError:
            pass

    logger.warning(f"Could not extract JSON from text: {text[:200]}...")
    return None


def parse_step1_response(text: str, expected_facets: List[str]) -> str:
    """
    Parse Step 1 (analysis) response.
    Returns the raw analyses text to feed into Step 2.
    """
    data = extract_json(text)

    if data and "analyses" in data:
        # Format as readable text for Step 2
        lines = []
        for item in data["analyses"]:
            name = item.get("facet_name", "Unknown")
            reasoning = item.get("reasoning", "No analysis provided")
            lines.append(f"- **{name}**: {reasoning}")
        return "\n".join(lines)

    # Fallback: use the raw text as-is
    logger.warning("Couldn't parse Step 1 JSON, using raw text")
    return text


def parse_step2_response(
    text: str,
    expected_facets: List[str],
) -> List[Dict[str, Any]]:
    """
    Parse Step 2 (scoring) response.
    Returns list of {facet_name, score, confidence, reasoning}.
    """
    data = extract_json(text)

    if data and "scores" in data:
        return _validate_scores(data["scores"], expected_facets)

    # Fallback: try regex extraction
    logger.warning("Couldn't parse Step 2 JSON, trying regex fallback")
    return _regex_parse_scores(text, expected_facets)


def _validate_scores(
    scores: List[Dict], expected_facets: List[str]
) -> List[Dict[str, Any]]:
    """Validate and normalize parsed scores."""
    validated = []
    scored_names = set()

    for item in scores:
        name = item.get("facet_name", "")
        score = item.get("score", 3)
        confidence = item.get("confidence", 0.5)
        reasoning = item.get("reasoning", "")

        # Clamp score
        score = max(settings.SCORE_MIN, min(settings.SCORE_MAX, int(score)))
        # Clamp confidence
        confidence = max(0.0, min(1.0, float(confidence)))

        validated.append({
            "facet_name": name,
            "score": score,
            "confidence": round(confidence, 2),
            "reasoning": reasoning,
        })
        scored_names.add(name.lower())

    # Fill missing facets with defaults
    for facet_name in expected_facets:
        if facet_name.lower() not in scored_names:
            validated.append({
                "facet_name": facet_name,
                "score": 3,  # neutral default
                "confidence": 0.1,  # low confidence
                "reasoning": "Facet was not scored by the model",
            })

    return validated


def _regex_parse_scores(text: str, expected_facets: List[str]) -> List[Dict[str, Any]]:
    """
    Fallback: extract scores using regex patterns.
    Looks for patterns like: facet_name: score=3, confidence=0.8
    """
    results = []
    scored_names = set()

    # Pattern: "facet_name" ... score: N ... confidence: 0.X
    pattern = r'"?([^"]+?)"?\s*[:\-]\s*(?:score\s*[=:]\s*)?(\d)\s*.*?(?:confidence\s*[=:]\s*)?([\d.]+)?'
    for match in re.finditer(pattern, text, re.IGNORECASE):
        name = match.group(1).strip()
        score = int(match.group(2))
        conf = float(match.group(3)) if match.group(3) else 0.5

        score = max(settings.SCORE_MIN, min(settings.SCORE_MAX, score))
        conf = max(0.0, min(1.0, conf))

        results.append({
            "facet_name": name,
            "score": score,
            "confidence": round(conf, 2),
            "reasoning": "Parsed via regex fallback",
        })
        scored_names.add(name.lower())

    # Fill missing
    for facet_name in expected_facets:
        if facet_name.lower() not in scored_names:
            results.append({
                "facet_name": facet_name,
                "score": 3,
                "confidence": 0.1,
                "reasoning": "Could not parse score from model output",
            })

    return results
