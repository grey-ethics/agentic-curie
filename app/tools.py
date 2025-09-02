"""
app/tools.py

Agent tools for Agentic Curie.

- merge_documents: merges/summarizes 2+ uploaded documents into one .docx
- resume_match: matches one JD (text or file) with one or more resumes and returns a CSV report

Notes:
- We import save_file lazily inside functions to avoid circular imports.
"""

from __future__ import annotations

from typing import List, Optional
import logging
from io import BytesIO

from agents import function_tool

from app.services.filestore import get_meta, get_path
from app.services.summarizer import (
    summarize_many_documents_into_one,
    extract_template_instructions,
)
from app.services.resume_matcher import (
    read_any_text,
    match_resumes_to_jd,
    results_to_csv_bytes,
)

# ------------------- MERGE DOCUMENTS -------------------

@function_tool
def merge_documents(file_ids: List[str], template_id: Optional[str] = None) -> str:
    """
    Merge/summarize 2+ uploaded documents into a single .docx.

    Args:
        file_ids: List of file IDs previously uploaded via /api/files/upload (>= 2)
        template_id: Optional file ID of a .docx template whose text acts as layout instructions

    Returns:
        Text with a direct download link to the generated .docx, or a helpful error message.
    """
    try:
        if not file_ids or len(file_ids) < 2:
            return "Please provide at least two file_ids."

        inputs = []
        for fid in file_ids:
            meta = get_meta(fid)
            path = get_path(fid)
            if not meta or not path:
                return f"File ID not found: {fid}"
            with open(path, "rb") as f:
                inputs.append((meta["filename"], f.read()))

        instructions = None
        if template_id:
            tmeta = get_meta(template_id)
            tpath = get_path(template_id)
            if not tmeta or not tpath:
                return f"Template ID not found: {template_id}"
            if not tmeta["filename"].lower().endswith(".docx"):
                return "Template must be a .docx file."
            with open(tpath, "rb") as tf:
                instructions = extract_template_instructions(BytesIO(tf.read()))

        docx_bytes, _token_stats = summarize_many_documents_into_one(inputs, instructions=instructions)

        from app.services.filestore import save_file
        out_id = save_file(
            docx_bytes,
            filename="Document_Generator_Output.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        download_url = f"/api/files/{out_id}/download"
        return f"Document generated successfully. Download: {download_url}"

    except Exception as e:
        logging.exception("Unexpected error in merge_documents")
        return f"Unexpected error: {e}"

# ------------------- RESUME MATCH -------------------

@function_tool
def resume_match(
    resume_file_ids: List[str],
    jd_file_id: Optional[str] = None,
    jd_text: Optional[str] = None
) -> str:
    """
    Compare resumes against a JD and return a CSV report with match scores and notes.

    Args:
        resume_file_ids: List of file IDs (one or more resumes)
        jd_file_id: Optional file ID for the JD (pdf/docx/txt). If provided, used over jd_text.
        jd_text: Optional JD text pasted by the user.

    Returns:
        Text with a direct download link to the generated CSV, plus a short preview.
    """
    try:
        if not resume_file_ids:
            return "Please provide at least one resume_file_id."

        # Load JD text
        jd_final_text = None
        if jd_file_id:
            jmeta = get_meta(jd_file_id)
            jpath = get_path(jd_file_id)
            if not jmeta or not jpath:
                return f"JD file not found: {jd_file_id}"
            with open(jpath, "rb") as jf:
                jd_final_text = read_any_text(jmeta["filename"], jf.read())
        if not jd_final_text:
            jd_final_text = (jd_text or "").strip()
        if not jd_final_text:
            return "Please provide a JD (either jd_file_id or jd_text)."

        # Load resume texts
        resumes = []
        for fid in resume_file_ids:
            meta = get_meta(fid)
            path = get_path(fid)
            if not meta or not path:
                return f"Resume file not found: {fid}"
            with open(path, "rb") as f:
                resumes.append((meta["filename"], f.read()))

        results = match_resumes_to_jd(jd_final_text, resumes)
        csv_bytes = results_to_csv_bytes(results)

        from app.services.filestore import save_file
        out_id = save_file(
            csv_bytes,
            filename="resume_match_report.csv",
            content_type="text/csv",
        )
        url = f"/api/files/{out_id}/download"

        # short textual preview (top 3 by score)
        top = sorted(results, key=lambda r: r.get("score",0), reverse=True)[:3]
        preview_lines = [f"{i+1}. {r['name']} — {r.get('score',0)}" for i,r in enumerate(top)]
        preview = "\n".join(preview_lines) if preview_lines else "No readable resumes."

        return f"Resume match complete. Top candidates:\n{preview}\n\nDownload CSV report: {url}"

    except Exception as e:
        logging.exception("Unexpected error in resume_match")
        return f"Unexpected error: {e}"
