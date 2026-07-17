from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def samples_dir() -> Path:
    root = Path(__file__).resolve().parents[4] / "samples" / "documents"
    staff4 = root / "staff4"
    return staff4 if staff4.exists() else root
