import json
from pathlib import Path

_NB = Path(__file__).parent.parent / "notebooks" / "analysis.ipynb"


def test_notebook_exists() -> None:
    assert _NB.exists()
    assert _NB.stat().st_size > 100


def test_notebook_valid_ipynb() -> None:
    nb = json.loads(_NB.read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4
    sources = " ".join(
        "".join(cell["source"]) for cell in nb["cells"] if cell["cell_type"] == "code"
    )
    assert "museums" in sources
    assert "regression" in sources
    assert "matplotlib" in sources or "plt" in sources
