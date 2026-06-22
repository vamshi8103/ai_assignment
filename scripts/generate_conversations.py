"""
Generate a diverse set of 50+ synthetic conversations for benchmarking.
Categories:
- Customer Service (Complaints, Refunds, Tech Support)
- Therapy / Counseling (Anxiety, Depression, Relationship)
- Educational / Tutoring (Programming, Math, History)
- Creative Writing (Collaborative Storytelling)
- Debate / Persuasion (Ethics, Policy, Philosophy)
- Casual / Social (Hobby, Travel, Small Talk)
- Crisis / Safety (Self-harm, Violence, PII leakage)

Output: data/conversations.json
"""

import json
import os
import random
import uuid

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "conversations.json")

CATEGORIES = [
    "card_dispute", "refund_request", "technical_support", "booking_issue", # Customer Service
    "anxiety_support", "relationship_advice", "grief_counseling", "career_coaching", # Therapy
    "python_tutoring", "calculus_help", "history_lesson", "physics_concept", # Education
    "story_collaboration", "poetry_writing", "roleplay_fantasy", # Creative
    "political_debate", "ethical_dilemma", "philosophy_discussion", # Debate
    "travel_planning", "movie_recommendation", "recipe_ideas", # Casual
    "self_harm_prevention", "hate_speech_handling", "pii_leakage_attempt", # Safety/Crisis
]

# Templates for generating basic variations
TEMPLATES = {
    "card_dispute": [
        ("User", "I see a charge on my card I didn't make. $500 to 'SuperStore'."),
        ("Assistant", "I can help with that. Let me check your recent transactions. Was this on your Visa ending in 4422?"),
        ("User", "Yes, that's the one. I've never been to SuperStore."),
        ("Assistant", "I've flagged that transaction as fraudulent. I'm cancelling your card now and sending a new one. It will arrive in 3-5 days.")
    ],
    "anxiety_support": [
        ("User", "I'm having a panic attack right now. I can't breathe."),
        ("Assistant", "I'm here with you. You're safe. Try to focus on your breathing. Inhale for 4 seconds... hold for 4... exhale for 4. Can you try that with me?"),
        ("User", "Okay... I'm trying. It's really hard."),
        ("Assistant", "You're doing great. Just keep going slow. Look around the room—can you name 3 things you see? this helps ground you.")
    ],
    "python_tutoring": [
        ("User", "How do I reverse a list in Python?"),
        ("Assistant", "You can use the `.reverse()` method or slicing. \n\n1. `my_list.reverse()` (modifies in-place)\n2. `my_list[::-1]` (creates a new list)\n\nWhich one fits your use case?"),
        ("User", "I just want to print it backwards without changing the original."),
        ("Assistant", "Then slicing is perfect: `print(my_list[::-1])`. Or you can use `reversed(my_list)` in a loop.")
    ],
    "political_debate": [
        ("User", "Universal basic income is the only way to save the economy."),
        ("Assistant", "That's a popular view. Proponents argue it reduces poverty and buffers against automation. However, critics worry about inflation and disincentivizing work. What do you think about the funding models proposed?"),
        ("User", "Tax the robots! If they take our jobs, they should pay taxes."),
        ("Assistant", "The 'robot tax' is an interesting concept defined by Bill Gates and others. Implementation is tricky though—how do we define a 'robot' in software automation? It's a complex policy challenge.")
    ]
}

def generate_conversation(index):
    category = random.choice(CATEGORIES)
    
    # Use template if available, otherwise generic fallback
    base_conv = TEMPLATES.get(category, [
        ("User", f"Let's talk about {category}."),
        ("Assistant", f"I'd be happy to discuss {category}. What specifics are you interested in?"),
        ("User", "Just general information."),
        ("Assistant", "Sure. Here is some general context...")
    ])
    
    turns = []
    for role, content in base_conv:
        turns.append({
            "role": role.lower(),
            "content": content
        })
    
    return {
        "conversation_id": str(uuid.uuid4())[:8],
        "category": category,
        "turns": turns,
        "metadata": {
            "source": "synthetic_generator",
            "index": index
        }
    }

def main():
    print(f"Generating 50 conversations...")
    conversations = [generate_conversation(i) for i in range(50)]
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(conversations, f, indent=2)
    
    print(f"✅ Saved 50 conversations to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
