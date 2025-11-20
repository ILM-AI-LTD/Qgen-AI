import json
from pathlib import Path
from openai import OpenAI
import os
import pandas as pd

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_markdown_prompt(json_data):
    prompt = f"""
You are a formatting engine.

You will receive a JSON list of question-answer pairs:

{json.dumps(json_data, indent=2)}

Your task:
1. Keep all textual instructions, words, and context **exactly as they appear**.
2. Wrap all mathematical expressions with:
   - Inline math and single line equation → $…$
   - Display any function names, formulas → $$…$$
   - Equations with multiple steps: chain fractions, factorization, etc. wrap each step with $…$
   - Lists of numbers, primes, or sets with $…$ as appropriate.
3. Multiple formulas in the same line should be individually wrapped with $…$
4. Avoid adding any extra text, headings, or numbers.
5. Do not generate any meaningless function name, formula or text. Strictly keep the contents
  of given json_data
6. Give proper spacing, make the texts appear clear and well-spaced.
7. For each item, produce JSON with keys: question_markdown, answer_markdown.
8. You must follow all the instructions given above. This step is compulsory.

Respond with a JSON list only, same length as input.
"""
    return prompt


def generate_markdown(json_data):
    """
    Calls GPT-5-mini to convert JSON Q/A to Markdown JSON list.
    """
    prompt = build_markdown_prompt(json_data)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content

    try:
        md_list = json.loads(raw)
        # Ensure each item has question_markdown and answer_markdown
        for item in md_list:
            if "question_markdown" not in item:
                item["question_markdown"] = item.get("question", "")
            if "answer_markdown" not in item:
                item["answer_markdown"] = item.get("answer", "")
        return md_list
    except Exception as e:
        # fallback: convert manually if parse fails
        md_list = []
        for idx, item in enumerate(json_data, 1):
            q = item.get("question", "")
            a = item.get("answer", "")
            md_list.append({
                "question_markdown": f"{q}",
                "answer_markdown": f"{a}"
            })
        return md_list


def save_markdown_as_excel(markdown_list, output_path: Path):
    """
    Save the Markdown list into Excel file.
    """
    df = pd.DataFrame(markdown_list)
    df.to_excel(output_path, index=False, engine='openpyxl')
    return output_path
