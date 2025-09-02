"""
app/tools.py

Agent tools for Agentic Curie.

- merge_documents: Agent function-tool that merges/summarizes 2+ uploaded
  documents (PDF/DOCX) into a single .docx using the summarization pipeline.

Notes:
- We import `save_file` lazily inside the function to avoid circular imports.
- Tool returns a simple string so the agent can surface it to the chat UI.
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


@function_tool
def merge_documents(file_ids: List[str], template_id: Optional[str] = None) -> str:
    """
    Merge/summarize 2+ uploaded documents into a single .docx.

    Args:
        file_ids:
            List of file IDs previously uploaded via /api/files/upload.
            Must include at least two IDs.
        template_id:
            Optional file ID of a .docx template whose text acts as layout instructions.

    Returns:
        A human-readable message containing a direct download link to the generated .docx,
        or a helpful error message if something went wrong.
    """
    try:
        # Validate inputs
        if not file_ids or len(file_ids) < 2:
            return "Please provide at least two file_ids."

        # Load input files (bytes + original names)
        inputs = []
        for fid in file_ids:
            meta = get_meta(fid)
            path = get_path(fid)
            if not meta or not path:
                return f"File ID not found: {fid}"
            try:
                with open(path, "rb") as f:
                    inputs.append((meta["filename"], f.read()))
            except Exception as e:
                logging.exception("Failed reading file %s", fid)
                return f"Error reading file {fid}: {e}"

        # Optional template instructions
        instructions = None
        if template_id:
            tmeta = get_meta(template_id)
            tpath = get_path(template_id)
            if not tmeta or not tpath:
                return f"Template ID not found: {template_id}"
            if not tmeta["filename"].lower().endswith(".docx"):
                return "Template must be a .docx file."
            try:
                with open(tpath, "rb") as tf:
                    instructions = extract_template_instructions(BytesIO(tf.read()))
            except Exception as e:
                logging.exception("Failed reading template %s", template_id)
                return f"Error reading template {template_id}: {e}"

        # Run the summarization/merge pipeline
        try:
            docx_bytes, _token_stats = summarize_many_documents_into_one(
                inputs, instructions=instructions
            )
        except Exception as e:
            logging.exception("Summarization pipeline failed")
            return f"Summarization failed: {e}"

        # Save result to filestore (lazy import to avoid circular import at module import time)
        try:
            from app.services.filestore import save_file  # lazy import by design
            out_id = save_file(
                docx_bytes,
                filename="Document_Generator_Output.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        except Exception as e:
            logging.exception("Failed saving generated document")
            return f"Failed to save generated document: {e}"

        download_url = f"/api/files/{out_id}/download"
        return f"Document generated successfully. Download: {download_url}"

    except Exception as e:
        logging.exception("Unexpected error in merge_documents tool")
        return f"Unexpected error: {e}"
