#!/usr/bin/env python3
"""
00 — Assistant Bootstrap Script

Creates or updates a reusable OpenAI assistant with file_search capabilities.
Stores the ASSISTANT_ID in a local config.json file for reuse across labs.

Usage: python scripts/00_bootstrap.py
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

def main():
    print("🚀 OpenAI Practice Lab - Assistant Bootstrap")
    print("=" * 50)

    load_dotenv()
    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("Please set OPENAI_API_KEY in a .env file or environment")

    client = OpenAI()
    print("✅ OpenAI client initialized")

    assistant = client.beta.assistants.create(
        name="Study Q&A Assistant",
        instructions=(
            "You are a helpful tutor. "
            "Use the knowledge in the attached files to answer study questions. "
            "Cite sources (file citations) where possible."
        ),
        model="gpt-4o-mini",
        tools=[{"type": "file_search"}],
    )
    assistant_id = assistant.id
    print(f"✅ Created Assistant: {assistant_id}")

    vector_store = client.vector_stores.create(name="Study Materials")
    vector_store_id = vector_store.id
    print(f"✅ Created Vector Store: {vector_store_id}")

    file_path = "/Users/kenn_/nfac/AI/ai-practice/data/attention.pdf"
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Could not find file: {file_path}")

    with open(file_path, "rb") as f:
        batch = client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store_id,
            files=[f],
        )
    print(f"✅ Uploaded {file_path} into Vector Store (status={batch.status})")

    client.beta.assistants.update(
        assistant_id=assistant_id,
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store_id]
            }
        },
    )
    print("✅ Attached Vector Store to assistant's file_search")

    config = {
        "assistant_id": assistant_id,
        "vector_store_id": vector_store_id
    }
    with open("config.json", "w") as cf:
        json.dump(config, cf, indent=2)

    print("✅ Wrote config.json with assistant_id & vector_store_id\n")
    print("You can now run `01_qna_assistant.py` and `02_generate_notes.py`.")

if __name__ == "__main__":
    main()
