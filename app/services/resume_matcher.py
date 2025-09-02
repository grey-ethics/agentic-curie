# app/services/resume_matcher.py
from __future__ import annotations

from io import BytesIO, StringIO
from typing import List, Tuple, Optional, Dict
import csv

from docx import Document
from openai import OpenAI

from app.services.pdf_utils import extract_text_from_pdf_bytes
from app.core.config import settings

import logging

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def _read_docx_text(docx_bytes: bytes) -> str:
    doc = Document(BytesIO(docx_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text)

def read_any_text(filename: str, data: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        return extract_text_from_pdf_bytes(data)
    elif ext == "docx":
        return _read_docx_text(data)
    else:
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""

def _chat_json(prompt: str, model: str = None) -> Dict:
    """
    Ask the model to return strict JSON. We parse lightly (model should comply).
    """
    model = model or settings.OPENAI_MODEL
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"user","content":prompt}],
        temperature=0.2,
        response_format={"type":"json_object"},  # JSON mode for newer models
    )
    txt = resp.choices[0].message.content
    try:
        import json
        return json.loads(txt)
    except Exception:
        logging.warning("Resume match JSON parse fallback. Raw: %s", txt[:300])
        # crude fallback
        return {"raw": txt}

def score_single_resume(jd_text: str, resume_text: str) -> Dict:
    """
    Returns a dict with keys: score, strengths, gaps, summary
    """
    prompt = f"""
You are a recruiter. Compare the following Job Description (JD) with a single resume and produce a JSON object with fields:
- score: integer 0..100 (overall match quality)
- strengths: array of short strings (top aligned aspects)
- gaps: array of short strings (missing or weak aspects)
- summary: short one-paragraph rationale

JD:
{jd_text}

Resume:
{resume_text}
"""
    data = _chat_json(prompt)
    # normalize
    out = {
        "score": None,
        "strengths": [],
        "gaps": [],
        "summary": "",
        "raw": None
    }
    try:
        if "score" in data: out["score"] = int(data["score"])
        if "strengths" in data and isinstance(data["strengths"], list): out["strengths"] = data["strengths"]
        if "gaps" in data and isinstance(data["gaps"], list): out["gaps"] = data["gaps"]
        if "summary" in data: out["summary"] = str(data["summary"])
    except Exception:
        pass
    if out["score"] is None:
        out["raw"] = data
        out["score"] = 0
    return out

def match_resumes_to_jd(
    jd_text: str,
    resumes: List[Tuple[str, bytes]],
) -> List[Dict]:
    """
    resumes: list of (filename, bytes)
    Returns: list of result dicts per resume: {name, score, strengths, gaps, summary}
    """
    results = []
    for fname, blob in resumes:
        rtext = read_any_text(fname, blob)
        if not rtext.strip():
            results.append({"name": fname, "score": 0, "strengths": [], "gaps": ["Unreadable"], "summary": "Could not extract text."})
            continue
        info = score_single_resume(jd_text, rtext)
        info["name"] = fname
        results.append(info)
    return results

def results_to_csv_bytes(items: List[Dict]) -> bytes:
    """
    Create a compact CSV containing name, score, strengths(g|sep), gaps(g|sep), summary
    """
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["Resume", "Score", "Strengths", "Gaps", "Summary"])
    for it in items:
        strengths = " | ".join(it.get("strengths", []))
        gaps = " | ".join(it.get("gaps", []))
        w.writerow([it.get("name",""), it.get("score",0), strengths, gaps, it.get("summary","")])
    return buf.getvalue().encode("utf-8")
