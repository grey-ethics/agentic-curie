
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass
class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "10000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "400"))

settings = Settings()
