"""Face matching and embedding comparison using cosine similarity."""

import logging

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


def l2_normalize(embedding: np.ndarray) -> np.ndarray:
    """L2-normalize an embedding vector.

    Args:
        embedding: Input embedding array.

    Returns:
        L2-normalized embedding.
    """
    norm = np.linalg.norm(embedding)
    if norm > 0:
        return embedding / norm
    return embedding


async def find_best_match(
    db: AsyncSession,
    query_embedding: np.ndarray,
    threshold: float | None = None,
) -> tuple[str | None, float]:
    """Find the best matching student for a given face embedding.

    Uses pgvector native cosine distance via raw SQL for reliability.

    Args:
        db: Async database session.
        query_embedding: L2-normalized 512-dim query embedding.
        threshold: Minimum cosine similarity threshold.

    Returns:
        Tuple of (student_id or None, similarity_score).
    """
    if threshold is None:
        threshold = settings.COSINE_SIMILARITY_THRESHOLD

    embedding_str = "[" + ",".join(f"{x:.8f}" for x in query_embedding.tolist()) + "]"

    result = await db.execute(
        text("""
            SELECT e.student_id,
                   1 - (e.embedding <=> CAST(:emb AS vector)) AS similarity
            FROM embeddings e
            JOIN students s ON e.student_id = s.id
            WHERE s.is_active = true
            ORDER BY similarity DESC
            LIMIT 1
        """),
        {"emb": embedding_str}
    )

    row = result.first()

    if row is None:
        logger.info("No embeddings found in database during search.")
        return None, 0.0

    student_id, similarity = str(row[0]), float(row[1])

    logger.info(
        "MATCH ATTEMPT: student_id=%s, similarity=%.4f (threshold=%.2f)",
        student_id,
        similarity,
        threshold,
    )

    if similarity >= threshold:
        return student_id, similarity

    return None, similarity


async def find_matches_batch(
    db: AsyncSession,
    query_embeddings: list[np.ndarray],
    threshold: float | None = None,
) -> list[tuple[str | None, float]]:
    """Find best matches for a batch of face embeddings.

    Args:
        db: Async database session.
        query_embeddings: List of L2-normalized 512-dim embeddings.
        threshold: Minimum cosine similarity threshold.

    Returns:
        List of (student_id or None, similarity_score) tuples.
    """
    results: list[tuple[str | None, float]] = []
    for embedding in query_embeddings:
        match = await find_best_match(db, embedding, threshold)
        results.append(match)
    return results