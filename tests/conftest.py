import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def facts():
    return json.loads((ROOT / "reports" / "facts.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def con():
    from src.warehouse import connect
    c = connect(read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="session")
def customers():
    from src.clean import load
    return load()
