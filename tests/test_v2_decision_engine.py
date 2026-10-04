"""Jev decision-engine adapter: question builders, answer parsing, record/replay."""

import asyncio

import pytest

from app.decision.jev import (Cassette, ChoiceAnswer, DecisionEngineError, JevEngine, NoulAnswer, ScoreAnswer,
                              _parse, choice, noul, request_key, score)


def test_builders_match_api_shape():
    assert noul("q") == {"type": "noul", "instructions": "q"}
    assert choice("q", {"a": None})["criteria"] == {"a": None}
    assert score("q", ["lo", "hi"])["criteria"] == ["lo", "hi"]


def test_parse_all_answer_types():
    assert _parse(noul("q"), {"type": "noul", "noul": 0.86}) == NoulAnswer(p=0.86)
    c = _parse(choice("q", {"a": None, "b": None}),
               {"type": "choice", "choice": "b", "confidence": 0.9, "probabilities": {"a": 0.1, "b": 0.9}})
    assert isinstance(c, ChoiceAnswer) and c.choice == "b" and c.probabilities["a"] == 0.1
    s = _parse(score("q", ["none", "minor", "moderate", "severe"]),
               {"type": "score", "score": 2.98, "confidence": 0.98,
                "legend": {"0": "none", "1": "minor", "2": "moderate", "3": "severe"},
                "probabilities": {"0": 0.0, "1": 0.0, "2": 0.01, "3": 0.99}})
    assert isinstance(s, ScoreAnswer) and s.level == "severe" and abs(s.normalised - 0.9933) < 1e-3


def test_request_key_is_order_independent():
    q1 = {"a": noul("x"), "b": noul("y")}
    q2 = {"b": noul("y"), "a": noul("x")}
    assert request_key("m", "s", q1) == request_key("m", "s", q2)
    assert request_key("m", "s", q1) != request_key("m", "s2", q1)


def test_cassette_replay_roundtrip(tmp_path):
    cas = Cassette(tmp_path)
    q = {"ok": noul("is it ok?")}
    k = request_key("jev-latest", "state", q)
    cas.put(k, "state", q, {"model": "jev-1.13.0", "answers": {"ok": {"type": "noul", "noul": 0.7}},
                            "usage": {"input_tokens": 10}})
    eng = JevEngine(mode="replay", api_key=None, cassette_dir=tmp_path)
    ans = asyncio.run(eng.ask("state", q))
    assert ans["ok"].p == 0.7 and eng.stats.cache_hits == 1 and eng.model_version == "jev-1.13.0"
    with pytest.raises(DecisionEngineError):
        asyncio.run(eng.ask("unseen state", q))


def test_live_without_key_falls_back_to_replay(tmp_path):
    assert JevEngine(mode="live", api_key=None, cassette_dir=tmp_path).mode == "replay"
