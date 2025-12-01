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

def detect_header_row(raw_df, expected_keywords=None, max_search_rows=8):
    """
    try to detect which row index contains the "real" header by searching for
    expected keywords (case-insensitive).
    Returns header_row index (0-based) or None if not found.
    """
    if expected_keywords is None:
        expected_keywords = {"subtopic", "question", "question type", "answer"}

    for r in range(min(max_search_rows, len(raw_df))):
        # collect non-empty values in the row
        row_vals = [str(x).strip().lower() for x in raw_df.iloc[r].tolist()]
        # count matches of expected keywords
        matches = 0
        for kv in expected_keywords:
            for val in row_vals:
                # exact or contains match (loose)
                if kv in val:
                    matches += 1
                    break
        # Heuristic: if at least 1-2 expected keywords appear in that row, consider it header
        if matches >= 1:
            return r
    return None

# use _read_excel_cached inside load_excel / load_alevel_sheet:
def load_excel(chapter_num:int):
    file_path = Path("curated_excels") / "Math" / f"Math Chapter {chapter_num}.xlsx"
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    return _read_excel_cached(file_path)

def load_alevel_sheet(sheet_name: str):
    file_path = Path("curated_excels") / "Math" / f"A Level Math.xlsx"
    if not file_path.exists():
        raise FileNotFoundError(...)
    return _read_excel_cached(file_path, sheet_name=sheet_name)

def _safe_str(x):
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

def _select_fewshots_science(df: pd.DataFrame, qtype: str, topic: str = None, k: int = 10):
    # determine question-type column name
    if "Question type" in df.columns:
        qcol = "Question type"
    else:
        raise KeyError(f"Expected column 'Question type'. Found: {df.columns.tolist()}")

    # filter by question type (exact then contains)
    subset = df[df[qcol].astype(str).str.lower() == (qtype or "").lower()]
    if subset.empty:
        subset = df[df[qcol].astype(str).str.contains(str(qtype), case=False, na=False)]

    if subset.empty:
        return []

    # If Subtopic column exists, filter by Subtopic (exact then contains)
    if "Subtopic" in subset.columns:
        sub_exact = subset[subset["Subtopic"].astype(str).str.lower() == topic.lower()]
        if not sub_exact.empty:
            subset = sub_exact
        else:
            sub_contains = subset[subset["Subtopic"].astype(str).str.contains(str(topic), case=False, na=False)]
            if not sub_contains.empty:
                subset = sub_contains

    k = min(k, len(subset))
    sampled = subset.sample(k).to_dict(orient="records")

    def _safe_str(x):
        if pd.isna(x):
            return ""
        return str(x).strip()

    fewshots = []
    for s in sampled:
        fewshots.append({
            "question": _safe_str(s.get("Question")),
            "answer": _safe_str(s.get("Answer")),
            "question_type": _safe_str(s.get(qcol)),
            "subtopic": _safe_str(s.get("Subtopic")) if "Subtopic" in s else ""
        })
    return fewshots

def load_science_excel(subject: str, chapter_name: str):
    """
    Robust loader for science (Physics/Chemistry) chapter files.
    - Finds the appropriate file in curated_excels/<Subject>/
    - Iterates sheets, detects header row per sheet, reads sheet with that header,
      then concatenates sheets that contain expected columns.
    Returns a single pandas.DataFrame containing concatenated rows from readable sheets.
    """
    folder = Path("curated_excels") / subject
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")

    # Candidate exact filename patterns
    candidates = [
        folder / f"{subject} Chapter {chapter_name}.xlsx",
        folder / f"{subject} Chapter {chapter_name}.xls",
        folder / f"{chapter_name}.xlsx",
        folder / f"{chapter_name}.xls"
    ]

    found = None
    for c in candidates:
        if c.exists():
            found = c
            break

    # Fallback: match any file whose *stem* contains chapter_name
    if not found:
        for p in folder.iterdir():
            if p.suffix.lower() in (".xlsx", ".xls") and chapter_name.lower() in p.stem.lower():
                found = p
                break

    if not found:
        raise FileNotFoundError(f"Excel not found for chapter '{chapter_name}' in {folder}")

    # Use ExcelFile to iterate sheets
    xls = pd.ExcelFile(found, engine="openpyxl")
    sheet_names = xls.sheet_names

    dfs = []
    expected_keywords = {"subtopic", "question", "question type", "answer"}

    for sheet in sheet_names:
        try:
            # read sheet *without* headers (header=None) so we can inspect top rows
            raw = pd.read_excel(found, sheet_name=sheet, header=None, engine="openpyxl")
            if raw.empty:
                continue

            header_row = detect_header_row(raw, expected_keywords=expected_keywords, max_search_rows=8)
            if header_row is None:
                # couldn't detect header in this sheet; skip it with a diagnostic print
                print(f"⚠️ Could not find proper header in sheet '{sheet}' of {found.name}")
                continue

            # Now read sheet again using detected header_row
            df_sheet = pd.read_excel(found, sheet_name=sheet, header=header_row, engine="openpyxl")
            # Normalize columns
            df_sheet.columns = [str(c).strip() for c in df_sheet.columns]

            # Check sheet has at least one of required columns (Subtopic or Question type or Question)
            cols_lower = [c.lower() for c in df_sheet.columns]
            if not any(k in cols_lower for k in ("subtopic", "question", "question type")):
                # not a usable sheet
                print(f"⚠️ Sheet '{sheet}' in {found.name} doesn't contain target columns; skipping.")
                continue

            dfs.append(df_sheet)

        except Exception as e:
            print(f"Error reading sheet '{sheet}' in {found.name}: {e}")
            continue

    if not dfs:
        raise ValueError(f"No usable sheets found in {found} for chapter_name='{chapter_name}'")

    # Concatenate all found usable sheets
    combined = pd.concat(dfs, ignore_index=True, sort=False)
    # final normalization of column names
    combined.columns = [str(c).strip() for c in combined.columns]
    return combined

def get_fewshot_examples_science(subject: str, chapter_name: str, qtype: str, topic: str, k: int = 10):
    df = load_science_excel(subject, chapter_name)
    return _select_fewshots_science(df, qtype, topic=topic, k=k)


