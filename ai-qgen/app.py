# app.py
import sys
import os
import io
import random
import string
import datetime
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pydantic import BaseModel
from pathlib import Path
import json
import re

from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# allow importing from utils if needed
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../utils'))
sys.path.append(r"D:\Work\Question generator AI\ai-qgen\utils")
from fewshot import get_fewshot_examples, get_fewshot_examples_alevel
from prompt_builder import build_generation_prompt
from llm_engine import generate_with_gpt
from markdown_builder import generate_markdown, save_markdown_as_excel

# Ensure folders exist
Path("curated_excels").mkdir(parents=True, exist_ok=True)
Path("outputs").mkdir(parents=True, exist_ok=True)
Path("frontend").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="AI Question Generator Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class QuestionRequest(BaseModel):
    curriculum: str  # "GCSE" or "ALEVEL"
    chapter_num: Optional[int] = None
    chapter_name: Optional[str] = None
    topic: str
    difficulty: str
    num_questions: int

# static files mounts
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

@app.get("/", include_in_schema=False)
def serve_frontend():
    index_path = Path("frontend") / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Question Generator Backend is running! (no frontend/index.html found)"}

TOPICS_FILE = Path("static_data/topics.json")
ALEVEL_TOPICS_FILE = Path("static_data/alevel_topics.json")
ALEVEL_CHAPTERS_FILE = Path("static_data/alevel_chapters.json")


@app.get("/topics")
def topics_for_chapter(
    curriculum: str = Query("GCSE", description="GCSE or ALEVEL"),
    chapter_num: Optional[int] = Query(None, description="Chapter number for GCSE"),
    chapter_name: Optional[str] = Query(None, description="Chapter name (sheet) for A-LEVEL")
):
    # A-LEVEL static JSON branch
    if curriculum and curriculum.upper() == "ALEVEL":
        if not ALEVEL_TOPICS_FILE.exists():
            raise HTTPException(status_code=500, detail="A-level topics file not found; run scripts/generate_alevel_topics.py")
        data = json.loads(ALEVEL_TOPICS_FILE.read_text(encoding="utf-8"))
        if chapter_name is None:
            # return available chapter names (keys)
            return {"chapters": list(data.keys())}
        topics = data.get(chapter_name, [])
        return {"chapter": chapter_name, "topics": topics}

    # GCSE / default branch (static JSON)
    if not TOPICS_FILE.exists():
        raise HTTPException(status_code=500, detail="Topics file not found. Run scripts/generate_topics.py")
    if chapter_num is None:
        raise HTTPException(status_code=400, detail="chapter_num is required for GCSE")
    data = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))
    return {"chapter": chapter_num, "topics": data.get(str(chapter_num), [])}


@app.get("/alevel_chapters")
def alevel_chapters():
    if not ALEVEL_CHAPTERS_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail="A-level chapters file not found; create static_data/alevel_chapters.json"
        )
    try:
        data = json.loads(ALEVEL_CHAPTERS_FILE.read_text(encoding="utf-8"))
        if "chapters" not in data or not isinstance(data["chapters"], list):
            raise HTTPException(status_code=500, detail="alevel_chapters.json malformed; expected {\"chapters\": [...]}")

        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _safe_filename(s: str) -> str:
    """Sanitize for filenames - replace spaces and remove problematic chars."""
    s = str(s or "")
    s = re.sub(r"[\/\\\:\*\?\"\<\>\|]", "", s)  # remove invalid filename chars
    s = s.strip().replace(" ", "_")
    return s


@app.post("/generate")
def generate_questions(req: QuestionRequest):
    # Validate inputs
    if req.num_questions < 1 or req.num_questions > 40:
        raise HTTPException(status_code=400, detail="num_questions must be between 1 and 40")

    # GCSE flow
    if req.curriculum.upper() == "GCSE":
        if req.chapter_num is None:
            raise HTTPException(status_code=400, detail="chapter_num is required for GCSE")

        try:
            fewshots = get_fewshot_examples(
                chapter_num=req.chapter_num,
                topic=req.topic,
                difficulty=req.difficulty,
                k=min(10, req.num_questions)
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except KeyError as e:
            raise HTTPException(status_code=500, detail=str(e))

        print(f"[generate:GCSE] num_questions={req.num_questions}, chapter={req.chapter_num}, topic='{req.topic}', difficulty='{req.difficulty}'")
        print(f"[generate:GCSE] fewshots found: {len(fewshots)} examples")
        print(f"[generate] using_fallback={any(fs['difficulty'].lower() != req.difficulty.lower() for fs in fewshots)}")

        if not fewshots:
            return {"error": f"No few-shot examples found for topic '{req.topic}' and difficulty '{req.difficulty}' in chapter {req.chapter_num}"}

        # Build prompt -> LLM
        prompt = build_generation_prompt(req.topic, req.difficulty, fewshots, req.num_questions)
        generated = generate_with_gpt(prompt)

        # Convert to markdown (second LLM call inside generate_markdown)
        markdown_list = generate_markdown(generated)

        # Save markdown list into Excel (.xlsx)
        safe_topic = _safe_filename(req.topic)
        out_file_md = Path("outputs") / f"GCSE_Chapter{req.chapter_num}_{safe_topic}_{req.difficulty}_{len(markdown_list)}.xlsx"
        save_markdown_as_excel(markdown_list, out_file_md)

        return {
            "generated_questions": generated,
            "output_file": str(out_file_md),
            "fewshots_used": len(fewshots),
            "fewshots_preview": fewshots[:5]
        }

    # A-LEVEL flow
    elif req.curriculum.upper() == "ALEVEL":
        if not req.chapter_name:
            raise HTTPException(status_code=400, detail="chapter_name is required for ALEVEL")

        try:
            fewshots = get_fewshot_examples_alevel(
                sheet_name=req.chapter_name,
                topic=req.topic,
                difficulty=req.difficulty,
                k=min(10, req.num_questions)
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except KeyError as e:
            raise HTTPException(status_code=500, detail=str(e))

        print(f"[generate:ALEVEL] num_questions={req.num_questions}, sheet='{req.chapter_name}', topic='{req.topic}', difficulty='{req.difficulty}'")
        print(f"[generate:ALEVEL] fewshots found: {len(fewshots)} examples")
        print(f"[generate] using_fallback={any(fs['difficulty'].lower() != req.difficulty.lower() for fs in fewshots)}")

        if not fewshots:
            return {"error": f"No few-shot examples found for topic '{req.topic}' and difficulty '{req.difficulty}' in sheet '{req.chapter_name}'"}

        # Build prompt -> LLM
        prompt = build_generation_prompt(req.topic, req.difficulty, fewshots, req.num_questions)
        generated = generate_with_gpt(prompt)

        # Convert to markdown
        markdown_list = generate_markdown(generated)

        # Save markdown list into Excel (.xlsx)
        safe_topic = _safe_filename(req.topic)
        safe_sheet = _safe_filename(req.chapter_name)
        out_file_md = Path("outputs") / f"ALEvel_{safe_sheet}_{safe_topic}_{req.difficulty}_{len(markdown_list)}.xlsx"
        save_markdown_as_excel(markdown_list, out_file_md)

        return {
            "generated_questions": generated,
            "output_file": str(out_file_md),
            "fewshots_used": len(fewshots),
            "fewshots_preview": fewshots[:5]
        }

    else:
        raise HTTPException(status_code=400, detail="Invalid curriculum type")
