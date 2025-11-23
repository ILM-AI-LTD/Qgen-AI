# scripts/generate_alevel_topics.py
import json
from pathlib import Path
import pandas as pd

# Adjust this path if your A-Level workbook has a different filename
ALEVEL_XLSX = Path("curated_excels") / "A Level Math.xlsx"
OUT_DIR = Path("static_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "alevel_topics.json"

def normalize_cols(df):
    df.columns = [str(c).strip() for c in df.columns]
    return df

def topics_from_sheet(sheet_name: str):
    try:
        df = pd.read_excel(ALEVEL_XLSX, sheet_name=sheet_name, engine="openpyxl")
    except Exception as e:
        print(f"Failed to read sheet '{sheet_name}': {e}")
        return []
    df = normalize_cols(df)
    if "Topic Name" not in df.columns:
        print(f"Warning: sheet '{sheet_name}' has no 'Topic Name' column. Columns: {df.columns.tolist()}")
        return []
    series = df["Topic Name"].fillna("").astype(str).map(lambda s: s.strip())
    seen = set()
    out = []
    for t in series:
        if not t:
            continue
        if t.lower() == "nan":
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out

def main():
    if not ALEVEL_XLSX.exists():
        print("A-Level workbook not found at:", ALEVEL_XLSX)
        OUT_FILE.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    xls = pd.ExcelFile(ALEVEL_XLSX, engine="openpyxl")
    sheets = xls.sheet_names

    result = {}
    for s in sheets:
        topics = topics_from_sheet(s)
        result[s] = topics

    OUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(result)} sheets -> {OUT_FILE}")

if __name__ == "__main__":
    main()
