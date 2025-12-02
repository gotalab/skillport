"""Embedding provider abstraction."""

from __future__ import annotations

import sys
from typing import List, Optional

from skillport.shared.config import Config


def get_embedding(text: str, config: Config) -> Optional[List[float]]:
    """Fetch embedding according to provider; returns None when provider='none'."""
    provider = config.embedding_provider
    text = text.replace("\n", " ")

    if provider == "none":
        return None

    try:
        if provider == "openai":
            # Prefer OpenAI v1+/v2 client; fall back to legacy SDK if unavailable.
            try:
                from openai import OpenAI  # type: ignore
            except Exception:
                OpenAI = None  # type: ignore

            if OpenAI:
                client = OpenAI(api_key=config.openai_api_key)
                resp = client.embeddings.create(
                    input=[text], model=config.openai_embedding_model
                )
                return resp.data[0].embedding

            import openai  # lazy import for legacy <1.x

            openai.api_key = config.openai_api_key
            resp = openai.Embedding.create(
                input=[text], model=config.openai_embedding_model
            )
            return resp["data"][0]["embedding"]

        if provider == "gemini":
            from google import genai  # lazy import

            client = genai.Client(api_key=config.gemini_api_key)
            result = client.models.embed_content(
                model=config.gemini_embedding_model, contents=text
            )
            if result.embeddings:
                return list(result.embeddings[0].values)
            raise ValueError("Gemini embedding response missing embeddings")

        raise ValueError(f"Unsupported embedding_provider: {provider}")
    except Exception as exc:
        print(f"Embedding error ({provider}): {exc}", file=sys.stderr)
        raise


__all__ = ["get_embedding"]
