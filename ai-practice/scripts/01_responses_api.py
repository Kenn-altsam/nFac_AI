# File: scripts/01_qna_assistant.py

import os
import json
import time
import sys
from openai import OpenAI
from dotenv import load_dotenv

# 1) Load environment & config.json
load_dotenv()
if "OPENAI_API_KEY" not in os.environ:
    raise RuntimeError("Please set OPENAI_API_KEY in .env or environment")

if not os.path.isfile("config.json"):
    raise FileNotFoundError("config.json not found. Please run 00_bootstrap.py first.")

with open("config.json", "r") as cf:
    cfg = json.load(cf)
assistant_id = cfg.get("assistant_id")
if assistant_id is None:
    raise KeyError("config.json does not contain 'assistant_id'")

client = OpenAI()

# 2) Determine which question to ask:
#    - If passed on the command line, use that entire string.
#    - Otherwise, prompt interactively.
if len(sys.argv) > 1:
    question = " ".join(sys.argv[1:])
else:
    question = input("🔎 Enter your study question: ").strip()

if not question:
    print("No question provided. Exiting.")
    sys.exit(1)

print(f"\n⏳ Asking the assistant: “{question}”\n")

# 3) STEP 1: Create a new Thread containing that single user message.
thread = client.beta.threads.create(
    messages=[{"role": "user", "content": question}]
)

# 4) STEP 2: Kick off a Run (non‐streamed) against our assistant_id.
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant_id,
    stream=False
)

print(f"Run ID: {run.id}")
print("⏳ Waiting for run to finish…\n")

# 5) Poll until the Run’s status becomes either "completed" or "error"
while run.status not in ("completed", "error"):
    print(f"  • Current status: {run.status}")
    time.sleep(1)
    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

if run.status == "error":
    print("❌ Run failed with error object:")
    print(run.error)
    raise RuntimeError("Run ended with an error.")

print(f"✅ Run completed! Final status: {run.status}\n")

# 6) STEP 3: Fetch all messages in this thread and print the assistant’s reply.
messages = client.beta.threads.messages.list(thread_id=thread.id).data

for msg in messages:
    if msg.role == "assistant":
        # msg.content is a list of blocks. Each block has a `.text` attribute,
        # which is a Text object with `.value` (the string) and `.annotations`.
        full_answer = ""
        for block in msg.content:
            # Use block.text.value to get the plain string
            full_answer += block.text.value

        print("🤖 Assistant says:\n")
        print(full_answer.strip())
        print("\n— end of answer —\n")

        # 7) Check for any file citations in block.text.annotations
        citations = []
        for block in msg.content:
            if hasattr(block.text, "annotations") and block.text.annotations:
                for ann in block.text.annotations:
                    if getattr(ann, "file_citation", None):
                        file_id = ann.file_citation.file_id
                        # Retrieve the file’s metadata to show its filename
                        file_meta = client.files.retrieve(file_id)
                        citations.append(
                            f"• Cited file: {file_meta.filename} (file_id={file_id})"
                        )

        if citations:
            print("Citations used:")
            for c in citations:
                print("  " + c)
            print()  # extra newline

        break
else:
    print("No assistant message found in thread – something went wrong.")
