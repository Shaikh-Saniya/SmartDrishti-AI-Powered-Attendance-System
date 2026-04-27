"""Unit tests for face matcher: cosine similarity and L2 normalization."""

import numpy as np
import pytest


def test_l2_normalize_unit_vector() -> None:
    """A unit vector should remain unchanged after normalization."""
    from app.ml.face_matcher import l2_normalize

    v = np.array([1.0, 0.0, 0.0])
    result = l2_normalize(v)
    np.testing.assert_array_almost_equal(result, v)


def test_l2_normalize_scales_correctly() -> None:
    """L2 normalization should produce a unit-norm vector."""
    from app.ml.face_matcher import l2_normalize

    v = np.array([3.0, 4.0])
    result = l2_normalize(v)
    assert abs(np.linalg.norm(result) - 1.0) < 1e-6
    np.testing.assert_array_almost_equal(result, [0.6, 0.8])


def test_l2_normalize_zero_vector() -> None:
    """Zero vector should remain zero (no division by zero)."""
    from app.ml.face_matcher import l2_normalize

    v = np.zeros(512)
    result = l2_normalize(v)
    np.testing.assert_array_equal(result, v)


def test_cosine_similarity_identical() -> None:
    """Identical normalized vectors should have similarity 1.0."""
    from app.ml.face_matcher import cosine_similarity, l2_normalize

    v = l2_normalize(np.random.randn(512))
    sim = cosine_similarity(v, v)
    assert abs(sim - 1.0) < 1e-6


def test_cosine_similarity_orthogonal() -> None:
    """Orthogonal vectors should have similarity ~0."""
    from app.ml.face_matcher import cosine_similarity

    v1 = np.zeros(512)
    v1[0] = 1.0
    v2 = np.zeros(512)
    v2[1] = 1.0
    sim = cosine_similarity(v1, v2)
    assert abs(sim) < 1e-6


def test_cosine_similarity_opposite() -> None:
    """Opposite vectors should have similarity -1.0."""
    from app.ml.face_matcher import cosine_similarity, l2_normalize

    v = l2_normalize(np.random.randn(512))
    sim = cosine_similarity(v, -v)
    assert abs(sim + 1.0) < 1e-6


def test_cosine_similarity_range() -> None:
    """Similarity of random normalized vectors should be in [-1, 1]."""
    from app.ml.face_matcher import cosine_similarity, l2_normalize

    for _ in range(100):
        v1 = l2_normalize(np.random.randn(512))
        v2 = l2_normalize(np.random.randn(512))
        sim = cosine_similarity(v1, v2)
        assert -1.0 - 1e-6 <= sim <= 1.0 + 1e-6
