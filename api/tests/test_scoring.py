from api.handlers.utils import score_signals

def test_scoring_boundaries():
    s,a = score_signals({"delay":0,"weather":0,"geo":0,"payment":0})
    assert 0 <= s <= 100
    assert a == "allow"

    s,a = score_signals({"delay":1,"weather":1,"geo":1,"payment":1})
    assert 0 <= s <= 100
    assert a in {"review","hold"}  # depends on weight sum, should be high

def test_scoring_decisions():
    s,a = score_signals({"delay":0.2,"weather":0.2,"geo":0.1,"payment":0})
    assert a in {"allow","review"}  # lowish

    s,a = score_signals({"delay":0.9,"weather":0.8,"geo":0.7,"payment":0.5})
    assert a == "hold"
