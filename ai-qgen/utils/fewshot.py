# fewshot.py
import pandas as pd
import random
from pathlib import Path

# at top of fewshot.py
import time
from pathlib import Path

_df_cache = {}  # { (path_str, mtime) : df }

def _read_excel_cached(path: Path, sheet_name=None):
    key = (str(path.resolve()), None if sheet_name is None else sheet_name, path.stat().st_mtime)
    if key in _df_cache:
        return _df_cache[key]
    # read
    if sheet_name is None:
        df = pd.read_excel(path, engine="openpyxl")
    else:
        df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    _df_cache[key] = df
    return df

# use _read_excel_cached inside load_excel / load_alevel_sheet:
def load_excel(chapter_num:int):
    file_path = Path("curated_excels") / f"Math Chapter {chapter_num}.xlsx"
    if not file_path.exists():
        raise FileNotFoundError(...)
    return _read_excel_cached(file_path)

def load_alevel_sheet(sheet_name: str):
    file_path = Path("curated_excels") / "A Level Math.xlsx"
    if not file_path.exists():
        raise FileNotFoundError(...)
    return _read_excel_cached(file_path, sheet_name=sheet_name)

def _safe_str(x):
    import pandas as pd
    if pd.isna(x):
        return ""
    return str(x).strip()


def _select_fewshots_from_df(df: pd.DataFrame, topic: str, difficulty: str, k: int = 10):
    """
    Core selection routine - filters by 'Topic Name' and 'Difficulty Level' columns.
    Returns list of dicts: {question, hint, answer, difficulty}
    """
    if "Topic Name" not in df.columns:
        raise KeyError(f"Expected column 'Topic Name'. Found: {df.columns.tolist()}")

    # filter by topic - exact match (case-insensitive) or contains fallback
    subset = df[df["Topic Name"].astype(str).str.lower() == topic.lower()]
    if subset.empty:
        subset = df[df["Topic Name"].astype(str).str.contains(topic, case=False, na=False)]

    if subset.empty:
        return []

    if "Difficulty Level" not in subset.columns:
        raise KeyError("Expected column 'Difficulty Level' in curated Excel")

    # try exact difficulty
    subset_exact = subset[subset["Difficulty Level"].astype(str).str.lower() == difficulty.lower()]

    if not subset_exact.empty:
        subset = subset_exact
    else:
        # fallback: use other difficulties from the subset
        subset = subset[subset["Difficulty Level"].astype(str).str.lower() != difficulty.lower()]

    # sample up to k
    k = min(k, len(subset))
    sampled = subset.sample(k).to_dict(orient="records")

    fewshots = []
    for row in sampled:
        fewshots.append({
            "question": _safe_str(row.get("Question")),
            "hint": _safe_str(row.get("Hint")),
            "answer": _safe_str(row.get("Answer")),
            "difficulty": _safe_str(row.get("Difficulty Level"))
        })
    return fewshots


def get_fewshot_examples(chapter_num: int, topic: str, difficulty: str, k: int = 10):
    """
    GCSE few-shot selection from per-chapter Excel file.
    """
    df = load_excel(chapter_num)
    return _select_fewshots_from_df(df, topic, difficulty, k=k)


def get_fewshot_examples_alevel(sheet_name: str, topic: str, difficulty: str, k: int = 10):
    """
    A-Level few-shot selection from a specific sheet in the A-Level workbook.
    """
    df = load_alevel_sheet(sheet_name)
    return _select_fewshots_from_df(df, topic, difficulty, k=k)
