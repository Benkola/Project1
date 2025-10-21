import importlib.util
from pathlib import Path

# load the score_handler module by filepath so tests don't depend on PYTHONPATH
mod_path = Path(__file__).resolve().parents[1] / "handlers" / "score_handler.py"
spec = importlib.util.spec_from_file_location("score_handler", str(mod_path))
score_handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score_handler)  # type: ignore

def test_score_rules_basic():
    s, action = score_handler.score_signals({"delay":0.7,"weather":0.5,"geo":0.2,"payment":0})
    assert 0 <= s <= 100
    assert action in ("allow","review","hold")
