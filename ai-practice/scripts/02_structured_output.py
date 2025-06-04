# File: scripts/02_generate_notes.py

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

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

# 2) Define the Pydantic schema for each Note
class Note(BaseModel):
    id: int = Field(..., ge=1, le=10)
    heading: str
    summary: str = Field(..., max_length=150)
    page_ref: Optional[int] = Field(None, description="Page number in source PDF")

# 3) Build the system prompt
system_prompt = (
    "You are a study summarizer. "
    "Return exactly 10 unique notes that will help prepare for the exam. "
    "Respond *only* with valid JSON matching the Note[] schema.\n\n"
    "Each note must be an object with the keys: "
    "`id` (1–10), `heading` (string), `summary` (≤150 characters), `page_ref` (optional integer). "
    "Do NOT include any additional keys or text. "
)

print("⏳ Asking the assistant to generate 10 exam notes…\n")

# 4) Send the chat request with response_format=json_object
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": system_prompt}],
    response_format={"type": "json_object"},
)

raw_json = resp.choices[0].message.content
try:
    parsed = json.loads(raw_json)
except json.JSONDecodeError as e:
    print("❌ Failed to parse JSON returned by the model:")
    print(raw_json)
    raise e

# 5) We expect {"notes": [ { ... }, { ... }, … ] }
notes_list = parsed.get("notes")
if not isinstance(notes_list, list):
    raise ValueError("Expected a top-level 'notes' array in the JSON output")

validated_notes: List[Note] = []
errors = []
for idx, item in enumerate(notes_list):
    try:
        note = Note(**item)
        validated_notes.append(note)
    except ValidationError as ve:
        errors.append(f"Error parsing note at index {idx}:\n{ve.json()}\n")

if errors:
    print("❌ Validation errors occurred while parsing notes:\n")
    for err in errors:
        print(err)
    raise SystemExit("Exiting due to invalid schema.")

# 6) Print all ten notes
print("✅ Successfully validated 10 notes. Here they are:\n")
for note in validated_notes:
    print(f"Note {note.id}: {note.heading}")
    print(f"  Summary: {note.summary}")
    print(f"  Page Ref: {note.page_ref}\n")
