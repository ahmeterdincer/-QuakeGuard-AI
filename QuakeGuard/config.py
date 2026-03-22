"""Ortam bayrakları (.env)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def is_free_mode() -> bool:
    """Ücretsiz yığın: Groq (sohbet) + yerel HuggingFace embedding (RAG)."""
    return os.getenv("QUAKEGUARD_FREE", "").strip().lower() in ("1", "true", "yes", "on")
