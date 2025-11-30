# scripts/generate_topics.py
import json
from pathlib import Path
import pandas as pd

CURATED = Path("curated_excels")
OUT_DIR = Path("static_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "topics.json"

def get_topics_for_chapter(chapter_num: int):
    path = CURATED / f"Math Chapter {chapter_num}.xlsx"
    if not path.exists():
        return []
    # Try to read; if headers not on first row this will still often work because we know your files are consistent
    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        print(f"Failed to read {path}: {e}")
        return []
        
    if "Topic Name" not in df.columns:
        df.columns = [str(c).strip() for c in df.columns]

    if "Topic Name" not in df.columns:
        print(f"Warning: 'Topic Name' not found in {path}. Columns: {df.columns.tolist()}")
        return []

    # fillna BEFORE astype to avoid 'nan' string
    topics_series = df["Topic Name"].fillna("").astype(str).map(lambda s: s.strip())

    # filter out empty and literal 'nan' (if someone wrote 'nan' as text)
    cleaned = []
    seen = set()
    for t in topics_series:
        if not t:
            continue
        low = t.lower()
        if low == "nan":
            continue
        if t not in seen:
            seen.add(t)
            cleaned.append(t)
    return cleaned

def main(chapters=(1,2,3,4,5)):
    data = {}
    for c in chapters:
        data[str(c)] = get_topics_for_chapter(c)
    OUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote topics to", OUT_FILE)
    print(OUT_FILE.read_text(encoding='utf-8'))

if __name__ == "__main__":
    # edit this tuple if you have different chapter numbers
    main(chapters=(1,2,3,4,5))
