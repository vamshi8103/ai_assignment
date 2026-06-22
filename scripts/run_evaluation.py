"""
Run evaluation on all conversations in data/conversations.json.
Uses the configured LLM backend (mock or API) to score them.
Outputs individual JSON results and a zipped archive.
"""

import asyncio
import json
import os
import zipfile
import time
from datetime import datetime

# Add project root to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scorer import ConversationScorer
from app.models import Conversation
from app.config import settings

INPUT_FILE = os.path.join(settings.BASE_DIR, "data", "conversations.json")
OUTPUT_DIR = os.path.join(settings.BASE_DIR, "output", f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

async def evaluate_all():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        print("Run 'python scripts/generate_conversations.py' first.")
        return

    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    print(f"🚀 Starting evaluation of {len(data)} conversations...")
    print(f"Backend: {settings.LLM_BACKEND}")
    print(f"Output: {OUTPUT_DIR}")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    scorer = ConversationScorer()
    results = []

    start_time = time.time()
    
    for i, item in enumerate(data):
        print(f"[{i+1}/{len(data)}] Processing {item['conversation_id']} ({item.get('category', 'unknown')})...")
        
        conv = Conversation(**item)
        
        # Run full evaluation on all facets
        
        try:
            result = await scorer.evaluate(conv)
            
            # Save individual JSON
            out_path = os.path.join(OUTPUT_DIR, f"{conv.conversation_id}.json")
            with open(out_path, "w") as f:
                f.write(result.model_dump_json(indent=2))
            
            results.append(out_path)
            
        except Exception as e:
            error_msg = f"❌ Failed to evaluate {conv.conversation_id}: {e}"
            print(error_msg)
            with open(os.path.join(settings.BASE_DIR, "output", "error_log.txt"), "a") as log:
                log.write(error_msg + "\n")

    duration = time.time() - start_time
    print(f"\n✅ Completed in {duration:.2f}s")
    
    # Zip results
    zip_path = os.path.join(settings.BASE_DIR, "output", "evaluation_results.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for json_file in results:
            zf.write(json_file, os.path.basename(json_file))
            
    print(f"📦 Results packaged: {zip_path}")

if __name__ == "__main__":
    asyncio.run(evaluate_all())
