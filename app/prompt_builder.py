"""
Prompt Builder — constructs multi-step evaluation prompts.
Uses structured templates to avoid one-shot solutions.
"""

from typing import List
from app.models import FacetDefinition, ConversationTurn


def format_conversation(turns: List[ConversationTurn]) -> str:
    """Format conversation turns into a readable string."""
    lines = []
    for i, turn in enumerate(turns):
        role_label = turn.role.upper()
        lines.append(f"[Turn {i+1}] {role_label}: {turn.content}")
    return "\n".join(lines)


def build_step1_prompt(
    turns: List[ConversationTurn],
    target_turn_index: int,
    facets: List[FacetDefinition],
) -> str:
    """
    Step 1: Analyze the conversation and provide reasoning for each facet.
    This is the 'think' step — no scores yet.
    """
    conversation_text = format_conversation(turns)
    target_turn = turns[target_turn_index]

    facet_list = "\n".join(
        f"  {i+1}. **{f.clean_name}** (Category: {f.category})\n"
        f"     Description: {f.description}\n"
        f"     Scale: 1 = {f.score_1_anchor} → 5 = {f.score_5_anchor}"
        for i, f in enumerate(facets)
    )

    prompt = f"""You are an expert conversation analyst evaluating the quality and characteristics of a conversation.

## Conversation
{conversation_text}

## Target Turn for Evaluation
Turn {target_turn_index + 1} ({target_turn.role.upper()}): "{target_turn.content[:500]}"

## Facets to Analyze
{facet_list}

## Task — Step 1: Analysis
For each facet listed above, provide a brief analysis (1-2 sentences) of how much this facet is expressed or relevant in the **target turn**, considering the full conversation context.

Respond in this exact JSON format:
```json
{{
  "analyses": [
    {{
      "facet_name": "<facet name>",
      "reasoning": "<1-2 sentence analysis>"
    }}
  ]
}}
```

Provide analysis for ALL {len(facets)} facets listed above."""

    return prompt


def build_step2_prompt(
    turns: List[ConversationTurn],
    target_turn_index: int,
    facets: List[FacetDefinition],
    step1_analyses: str,
) -> str:
    """
    Step 2: Based on the reasoning from Step 1, assign scores and confidence.
    This satisfies the 'no one-shot' constraint.
    """
    target_turn = turns[target_turn_index]

    facet_names = ", ".join(f.clean_name for f in facets)

    prompt = f"""You are an expert conversation analyst. You previously analyzed a conversation turn for the following facets: {facet_names}.

## Target Turn
Turn {target_turn_index + 1} ({target_turn.role.upper()}): "{target_turn.content[:500]}"

## Your Previous Analysis
{step1_analyses}

## Task — Step 2: Scoring
Based on your analysis above, assign a score and confidence for EACH facet.

- **Score**: Integer from 1 to 5
  - 1 = Not present / Very low
  - 2 = Slightly present / Low
  - 3 = Moderately present / Medium
  - 4 = Clearly present / High
  - 5 = Dominant / Very high
- **Confidence**: Float from 0.0 to 1.0 (how confident you are in your score)

Respond in this exact JSON format:
```json
{{
  "scores": [
    {{
      "facet_name": "<facet name>",
      "score": <1-5>,
      "confidence": <0.0-1.0>,
      "reasoning": "<brief justification>"
    }}
  ]
}}
```

You MUST score ALL {len(facets)} facets. Do not skip any."""

    return prompt
