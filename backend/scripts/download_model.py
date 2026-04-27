"""Pre-download InsightFace buffalo_l model.

Run this before first application startup to avoid download delay.

Usage:
    cd backend
    python scripts/download_model.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def download_model() -> None:
    """Download the InsightFace buffalo_l model to ./models directory."""
    model_dir = Path("./models")
    model_dir.mkdir(parents=True, exist_ok=True)

    print("Downloading InsightFace buffalo_l model...")
    print(f"Model directory: {model_dir.resolve()}")
    print("This may take a few minutes (~300MB download)...")
    print()

    from insightface.app import FaceAnalysis

    app = FaceAnalysis(
        name="buffalo_l",
        root=str(model_dir),
        allowed_modules=["detection", "recognition"],
    )
    app.prepare(ctx_id=-1, det_size=(640, 640))

    print()
    print("✅ Model downloaded and verified successfully!")
    print(f"   Location: {model_dir.resolve()}")
    print("   You can now start the application.")


if __name__ == "__main__":
    download_model()
