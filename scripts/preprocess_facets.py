"""
Preprocess the raw Facets Assignment CSV.
- Clean facet names (remove trailing colons, numbering prefixes, whitespace)
- Categorize facets into domains
- Add description and score anchor columns
- Output: data/facets_cleaned.csv
"""

import csv
import re
import os

# ─── Category classification keywords ───
CATEGORY_KEYWORDS = {
    "emotion": [
        "emotion", "happiness", "sadness", "joy", "anger", "fear", "merriness",
        "blissful", "morose", "contentment", "irritabil", "hostil", "affect",
        "mood", "discontent", "cheerful", "vivacity", "peacefulness", "hateful",
        "joyful", "desperat", "enthusias", "high-spirit", "affection", "warmhearted",
        "cordiality", "genial", "droll", "ardency", "compassion fatigue",
    ],
    "safety": [
        "safety", "harmful", "violence", "drug", "risk", "danger", "crisis",
        "hostility", "hate", "disrespect", "dishonest", "impudence", "brazen",
        "rebellious", "coarse", "harmful", "physical-violence", "servil",
    ],
    "linguistic_quality": [
        "sentence structure", "spelling", "brevity", "language use",
        "storytelling", "comprehension", "information retention", "vocabulary",
        "grammar", "concreteness", "reliance on context", "verbal",
        "alphabetical", "numeric filing", "mental arithmetic", "analogies",
    ],
    "cognitive": [
        "reasoning", "intelligence", "memory", "cognitive", "attention",
        "decision", "critical", "logical", "spatial", "synthesis", "analysis",
        "perception", "processing", "problem", "estimating", "mathematical",
        "numerical", "data analysis", "troubleshooting", "economic reasoning",
        "statistical", "sequence", "working memory", "iq",
    ],
    "personality": [
        "openness", "conscientiousness", "neuroticism", "extraversion",
        "agreeableness", "hexaco", "big five", "enneagram", "assertive",
        "introvert", "judging", "perceiving", "conformity", "independent",
        "orderliness", "self-control", "self-directed", "psychoticism",
        "impulsiv", "perseveran", "determinedness", "dogged", "patience",
        "curious", "conventional", "conservatism", "liberalism", "quirkiness",
    ],
    "social": [
        "social", "leadership", "collaboration", "teamwork", "communication",
        "delegation", "trust", "relationship", "participation", "community",
        "feedback", "cooperation", "contribution", "peer", "network",
        "eye-contact", "non-verbal", "listening", "encourage", "volunteer",
        "civility", "dignity", "sportsmanship", "ethical leadership",
    ],
    "behavioral": [
        "behavior", "habit", "lifestyle", "sleep", "diet", "exercise",
        "travel", "cooking", "snacking", "caffeine", "breakfast", "commute",
        "subscription", "blog", "open-source", "pet", "museum", "choir",
        "dance", "music", "graffiti", "eco-tourism", "passport", "robotic",
        "gaming", "cloud-backup", "home-security",
    ],
    "health": [
        "health", "medical", "hormone", "metabolic", "immune", "sleep apnea",
        "chronic pain", "polygenic", "basophil", "serotonin", "chromatin",
        "parathyroid", "fsh level", "vision-check", "macronutrient",
        "caffeine sensitivity", "processed-food", "wake-time",
    ],
    "spiritual": [
        "spiritual", "religion", "prayer", "meditation", "faith", "holy",
        "pilgrim", "scripture", "quran", "bible", "sufi", "buddhist",
        "hindu", "jewish", "sikh", "bahá'í", "kabbalah", "gnostic",
        "i ching", "astrology", "aura", "reiki", "chakra", "yoga",
        "mantra", "dhikr", "kirtan", "new-age", "channeling",
    ],
    "professional": [
        "work style", "meeting deadline", "computer skill", "specialist",
        "training", "soft-skill", "skill-endorsement", "initiative",
        "desire for excellence", "achievement motivation", "innovation",
        "creativity component", "safety compliance", "patient care",
    ],
    "pragmatics": [
        "pragmatic", "context", "intent", "implicature", "turn-taking",
        "politeness", "indirect", "speech act", "presupposition",
        "common-sense", "input", "structure", "evaluating solutions",
    ],
    "self_and_identity": [
        "self-esteem", "self-efficacy", "self-improvement", "self-perspective",
        "identity", "alignment with societal", "individuality", "exemplar",
        "self-righteousness", "self-effacement", "cultural identity",
        "attachment", "ego", "martyrdom",
    ],
    "motivation": [
        "motivation", "intrinsic", "achievement", "affiliation", "pure challenge",
        "desire to influence", "activator", "goal-directed", "significance",
    ],
}

# Score anchors per category
SCORE_ANCHORS = {
    "emotion": ("No emotional expression detected", "Dominant emotional expression throughout"),
    "safety": ("No safety concerns", "Severe safety concerns present"),
    "linguistic_quality": ("Very poor linguistic quality", "Excellent linguistic quality"),
    "cognitive": ("No cognitive engagement", "Deep cognitive engagement"),
    "personality": ("Trait not exhibited", "Trait strongly exhibited"),
    "social": ("No social engagement", "Highly collaborative/social"),
    "behavioral": ("Behavior absent", "Behavior strongly present"),
    "health": ("Not relevant/mentioned", "Strongly relevant/mentioned"),
    "spiritual": ("Not relevant/mentioned", "Strongly relevant/mentioned"),
    "professional": ("Not exhibited", "Strongly exhibited"),
    "pragmatics": ("Poor pragmatic quality", "Excellent pragmatic quality"),
    "self_and_identity": ("Not exhibited", "Strongly exhibited"),
    "motivation": ("No motivational signals", "Strong motivational signals"),
}

DEFAULT_ANCHORS = ("Not present/exhibited", "Strongly present/exhibited")


def clean_facet_name(raw_name: str) -> str:
    """Clean a raw facet name."""
    name = raw_name.strip()
    # Remove leading number + dot pattern like "800. " or "644. "
    name = re.sub(r"^\d+\.\s*", "", name)
    # Remove trailing colon
    name = name.rstrip(":")
    # Remove common prefixes
    prefixes_to_strip = [
        "Psychological construct: ",
        "Psychological construct:",
        "Character strength: ",
        "Character strength:",
        "Social-cognition variable: ",
        "Social-cognition variable:",
        "Cognitive measure: ",
        "Cognitive measure:",
        "Emotional-intelligence measure: ",
        "Emotional-intelligence measure:",
        "Defense-mechanism tendency: ",
        "Defense-mechanism tendency:",
        "Well-being component: ",
        "Well-being component:",
        "Value orientation: ",
        "Value orientation:",
        "Big Five facet Openness – ",
        "Big Five facet Openness –",
        "Mindfulness facet: ",
        "Mindfulness facet:",
        "HEXACO domain: ",
        "HEXACO domain:",
    ]
    for prefix in prefixes_to_strip:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    # Strip again
    name = name.strip()
    # Remove category-like suffixes that are just headers
    # e.g., "Conscientiousness Facets" → skip these
    return name


def categorize_facet(clean_name: str) -> str:
    """Classify a facet into a category based on keyword matching."""
    name_lower = clean_name.lower()
    best_category = "personality"  # default
    best_score = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in name_lower)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category


def generate_description(clean_name: str, category: str) -> str:
    """Generate a brief evaluator description for a facet."""
    return (
        f"Evaluate the degree to which '{clean_name}' is expressed or "
        f"relevant in this conversation turn. Consider both explicit "
        f"statements and implicit signals."
    )


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base_dir, "data", "facets_raw.csv")
    output_path = os.path.join(base_dir, "data", "facets_cleaned.csv")

    facets = []
    with open(input_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header "Facets"
        for row in reader:
            if row and row[0].strip():
                facets.append(row[0].strip())

    print(f"Read {len(facets)} raw facets")

    cleaned = []
    seen = set()
    for raw in facets:
        clean = clean_facet_name(raw)
        if not clean or len(clean) < 2:
            print(f"  SKIPPED (empty after cleaning): '{raw}'")
            continue
        # Skip header-like entries
        if clean.endswith("Subcomponents") or clean.endswith("End Points"):
            print(f"  SKIPPED (header-like): '{raw}' → '{clean}'")
            continue

        # Deduplicate
        key = clean.lower().replace(" ", "").replace("-", "")
        if key in seen:
            print(f"  SKIPPED (duplicate): '{raw}' → '{clean}'")
            continue
        seen.add(key)

        category = categorize_facet(clean)
        description = generate_description(clean, category)
        anchors = SCORE_ANCHORS.get(category, DEFAULT_ANCHORS)

        cleaned.append({
            "facet_id": len(cleaned) + 1,
            "raw_name": raw,
            "clean_name": clean,
            "category": category,
            "description": description,
            "score_1_anchor": anchors[0],
            "score_5_anchor": anchors[1],
        })

    print(f"\nCleaned to {len(cleaned)} unique facets")

    # Print category distribution
    from collections import Counter
    cats = Counter(f["category"] for f in cleaned)
    print("\nCategory distribution:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "facet_id", "raw_name", "clean_name", "category",
            "description", "score_1_anchor", "score_5_anchor",
        ])
        writer.writeheader()
        writer.writerows(cleaned)

    print(f"\nWrote cleaned facets to {output_path}")


if __name__ == "__main__":
    main()
