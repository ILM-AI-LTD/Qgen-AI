import os
import json
from pathlib import Path
import pandas as pd

INPUT_DIR = "curated_excels/Chemistry"
OUT_DIR = Path("static_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "Chemistry_topics_gcse.json"

def extract_metadata():
    chapter_data = {}

    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            chapter_name = os.path.splitext(filename)[0].replace("Chemistry Chapter ", "").strip()
            file_path = os.path.join(INPUT_DIR, filename)

            try:
                df = pd.read_excel(file_path)

                topics = sorted(df["Subtopic"].dropna().astype(str).unique())
                qtypes = sorted(df["Question type"].dropna().astype(str).unique())

                chapter_data[chapter_name] = {
                    "topics": topics,
                    "question_types": qtypes
                }

            except Exception as e:
                print(f"Error processing {filename}: {e}")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(chapter_data, f, indent=4, ensure_ascii=False)

    print(f"Physics metadata written to {OUT_FILE}")

if __name__ == "__main__":
    extract_metadata()
