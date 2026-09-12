"""Mistral embedding client for RAG indexing and query-time search."""

from __future__ import annotations

from collections.abc import Sequence

from mistralai import Mistral

from hbms.core.config import Settings, get_settings

EMBEDDING_DIMENSIONS = 1024


class EmbeddingError(RuntimeError):
    """Raised when the embedding provider returns an unexpected payload."""


def embed_texts(
    texts: Sequence[str],
    *,
    settings: Settings | None = None,
    batch_size: int = 16,
) -> list[list[float]]:
    if not texts:
        return []

    cfg = settings or get_settings()
    if not cfg.mistral_api_key:
        msg = "MISTRAL_API_KEY is not configured."
        raise EmbeddingError(msg)

    client = Mistral(api_key=cfg.mistral_api_key)
    vectors: list[list[float]] = []
    model = cfg.mistral_embed_model

    for start in range(0, len(texts), batch_size):
        batch = list(texts[start : start + batch_size])
        response = client.embeddings.create(model=model, inputs=batch)
        if response.data is None or len(response.data) != len(batch):
            msg = "Embedding response size did not match input batch size."
            raise EmbeddingError(msg)
        ordered = sorted(response.data, key=lambda item: item.index or 0)
        for item in ordered:
            if item.embedding is None:
                msg = "Embedding provider returned a null vector."
                raise EmbeddingError(msg)
            if len(item.embedding) != EMBEDDING_DIMENSIONS:
                msg = (
                    f"Expected {EMBEDDING_DIMENSIONS}-d embeddings, "
                    f"got {len(item.embedding)}."
                )
                raise EmbeddingError(msg)
            vectors.append(list(item.embedding))

    return vectors


def embed_query(text: str, *, settings: Settings | None = None) -> list[float]:
    vectors = embed_texts([text], settings=settings)
    return vectors[0]
