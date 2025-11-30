import json
from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()

client = OpenAI()

def generate_questions(prompt):
    """
    Calls GPT-5-mini and returns parsed JSON list.
    """

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content

    try:
        return json.loads(raw)
    except:
        # fallback: return as raw text
        return [{"question": raw, "answer": "Parsing failed"}]

