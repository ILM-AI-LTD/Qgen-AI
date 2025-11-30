import pandas as pd
from pathlib import Path
import json

BASE_DIR = Path("curated_excels/Physics")
OUTPUT_FILE = Path("static_data/physics_topics_gcse.json")

data = {}

for file_path in BASE_DIR.glob("*.xlsx"):
    if file_path.name.startswith("~$"):  # skip temporary files
        continue

    chapter_name = file_path.stem.replace("Physics Chapter ", "").strip()
    subtopics_set = set()
    qtypes_set = set()

    try:
        xls = pd.ExcelFile(file_path, engine="openpyxl")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        continue

    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            # Find row containing headers
            header_row_idx = None
            for i, row in df.iterrows():
                if row.str.contains("Subtopic", case=False, na=False).any() and \
                   row.str.contains("Question type", case=False, na=False).any():
                    header_row_idx = i
                    break
            if header_row_idx is None:
                print(f"⚠️ Could not find proper header in sheet '{sheet_name}' of {file_path}")
                continue

            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row_idx)
            cols = [str(c).strip() for c in df.columns]

            if "Subtopic" not in cols or "Question type" not in cols:
                print(f"⚠️ Missing required columns in sheet '{sheet_name}' of {file_path}")
                continue

            subtopics_set.update(df["Subtopic"].dropna().astype(str).str.strip().tolist())
            qtypes_set.update(df["Question type"].dropna().astype(str).str.strip().tolist())

        except Exception as e:
            print(f"Error processing sheet '{sheet_name}' of {file_path}: {e}")
            continue

    if subtopics_set and qtypes_set:
        data[chapter_name] = {
            "topics": list(subtopics_set),
            "question_types": list(qtypes_set)
        }

# Save JSON
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f"Physics topics JSON saved to {OUTPUT_FILE}")
