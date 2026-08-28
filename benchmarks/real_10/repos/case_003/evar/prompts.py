from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


PROMPT_DIR = Path("prompts")


@dataclass(frozen=True)
class PromptTemplate:
    filename: str
    text: str
    sha256: str


def load_prompt(filename: str) -> PromptTemplate:
    path = PROMPT_DIR / filename
    text = path.read_text(encoding="utf-8")
    return PromptTemplate(
        filename=filename,
        text=text,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def prompt_filename(role: str, protocol: str) -> str:
    normalized = "evar" if protocol == "evar_hard" else protocol
    return f"{role}_{normalized}_v1.txt"
