
from io import BytesIO
import pdfplumber
import logging

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes using pdfplumber.
    """
    try:
        text_all = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for pg in pdf.pages:
                t = pg.extract_text() or ""
                if t:
                    text_all.append(t)
        return "\n".join(text_all)
    except Exception as e:
        logging.error(f"PDF extraction failed: {e}")
        return ""
