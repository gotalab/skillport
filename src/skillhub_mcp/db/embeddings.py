from typing import List, Optional

import sys
import openai
from google import genai

from ..config import settings as default_settings


def get_embedding(text: str, settings_obj=None) -> Optional[List[float]]:
    """Provider-agnostic embedding fetcher.

    settings_obj: optional Settings-like object. Falls back to default global
    settings so existing callers continue to work.
    """

    settings = settings_obj or default_settings

    if settings.embedding_provider == "none":
        return None

    provider = settings.embedding_provider
    text = text.replace("\n", " ")

    try:
        if provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when embedding_provider='openai'")
            client = openai.Client(api_key=settings.openai_api_key)
            response = client.embeddings.create(input=[text], model=settings.embedding_model)
            return response.data[0].embedding

        if provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is required when embedding_provider='gemini'")
            client = genai.Client(api_key=settings.gemini_api_key)
            result = client.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=text,
            )
            if result.embeddings:
                return list(result.embeddings[0].values)
            raise ValueError("Gemini embedding response missing embeddings")

        raise ValueError(f"Unsupported embedding_provider: {provider}")

    except Exception as e:
        print(f"Embedding error ({provider}): {e}", file=sys.stderr)
        raise
