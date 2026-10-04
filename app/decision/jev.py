"""
app/decision/jev.py

Decision engine: TypeSafe **Jev** (System One). Jev answers *typed* questions
about a text state and returns calibrated probabilities instead of prose:

  - Noul   -> P(yes) for a yes/no condition
  - Choice -> one option + a probability per option
  - Score  -> position on an ordered scale + a probability per level

Every agent judgement in this system (is this a claim? which metric? which
data sources? does this evidence support or contradict? final verdict?) is a
Jev question. Agents never parse free-form LLM text to make a decision.

Record / replay: every (state, questions) pair is hashed. In `live` mode the
answer is written to an append-only cassette (data/cassettes/jev/*.jsonl), so
the exact run can be replayed offline with JEV_MODE=replay (tests, demos
without network). This is the "record the API once" requirement.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings


class DecisionEngineError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Question builders (pure)
# ---------------------------------------------------------------------------

def noul(instructions: str) -> dict:
    return {"type": "noul", "instructions": instructions}


def choice(instructions: str, options: dict[str, str | None]) -> dict:
    return {"type": "choice", "instructions": instructions, "criteria": options}


def score(instructions: str, levels: list[str]) -> dict:
    return {"type": "score", "instructions": instructions, "criteria": levels}


# ---------------------------------------------------------------------------
# Normalised answers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NoulAnswer:
    p: float


@dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    confidence: float
    probabilities: dict[str, float]


@dataclass(frozen=True)
class ScoreAnswer:
    score: float              # 0..(n-1)
    confidence: float
    level: str                # most likely level label
    probabilities: dict[str, float]   # by level label
    normalised: float         # score / (n-1) in 0..1


def _parse(question: dict, raw: dict) -> NoulAnswer | ChoiceAnswer | ScoreAnswer:
    t = raw.get("type")
    if t == "noul":
        return NoulAnswer(p=float(raw["noul"]))
    if t == "choice":
        probs = {k: float(v) for k, v in raw.get("probabilities", {}).items()}
        return ChoiceAnswer(choice=raw["choice"], confidence=float(raw.get("confidence", probs.get(raw["choice"], 0))),
                            probabilities=probs)
    if t == "score":
        legend = raw.get("legend") or {str(i): l for i, l in enumerate(question["criteria"])}
        probs = {legend[k]: float(v) for k, v in raw.get("probabilities", {}).items()}
        n = max(1, len(legend) - 1)
        level = max(probs, key=probs.get) if probs else legend["0"]
        return ScoreAnswer(score=float(raw["score"]), confidence=float(raw.get("confidence", 0)), level=level,
                           probabilities=probs, normalised=round(float(raw["score"]) / n, 4))
    raise DecisionEngineError(f"Unknown answer type {t!r}")


# ---------------------------------------------------------------------------
# Cassette store (record / replay)
# ---------------------------------------------------------------------------

def request_key(model: str, state: str, questions: dict) -> str:
    blob = json.dumps({"m": model, "s": state, "q": questions}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


class Cassette:
    def __init__(self, directory: Path):
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "jev_cassette.jsonl"
        self._lock = threading.Lock()
        self._data: dict[str, dict] = {}
        for p in sorted(self.dir.glob("*.jsonl")):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self._data[rec["key"]] = rec["response"]

    def get(self, key: str) -> dict | None:
        return self._data.get(key)

    def put(self, key: str, state: str, questions: dict, response: dict) -> None:
        with self._lock:
            if key in self._data:
                return
            self._data[key] = response
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "state": state[:400], "questions": list(questions),
                                    "response": response}, ensure_ascii=False) + "\n")

    def __len__(self) -> int:
        return len(self._data)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

@dataclass
class JevStats:
    calls: int = 0
    cache_hits: int = 0
    input_tokens: int = 0
    errors: int = 0


@dataclass
class JevEngine:
    mode: str = field(default_factory=lambda: settings().jev_mode)
    model: str = field(default_factory=lambda: settings().jev_model)
    api_key: str | None = field(default_factory=lambda: settings().typesafe_api_key)
    base_url: str = field(default_factory=lambda: settings().typesafe_base_url)
    cassette_dir: Path = field(default_factory=lambda: settings().jev_cassette_dir)
    concurrency: int = field(default_factory=lambda: settings().jev_concurrency)
    stats: JevStats = field(default_factory=JevStats)
    model_version: str = "jev"

    def __post_init__(self):
        self.cassette = Cassette(self.cassette_dir)
        self._sems: dict[int, asyncio.Semaphore] = {}
        if self.mode == "live" and not self.api_key:
            # No key: fall back to replay so the system still runs on recorded answers.
            self.mode = "replay"

    @property
    def label(self) -> str:
        return f"{self.model_version} ({self.mode})"

    async def ask(self, state: str, questions: dict[str, dict]) -> dict[str, Any]:
        """Ask typed questions about one state. Returns {name: Answer}."""
        key = request_key(self.model, state, questions)
        raw = self.cassette.get(key)
        if raw is not None:
            self.stats.cache_hits += 1
        else:
            if self.mode != "live":
                raise DecisionEngineError(
                    "Jev answer not in cassette and JEV_MODE != live. Record it once with JEV_MODE=live.")
            raw = await self._call(state, questions)
            self.cassette.put(key, state, questions, raw)
        self.model_version = raw.get("model", self.model_version)
        self.stats.input_tokens += int(raw.get("usage", {}).get("input_tokens", 0))
        return {name: _parse(questions[name], raw["answers"][name]) for name in questions}

    async def _call(self, state: str, questions: dict) -> dict:
        loop_id = id(asyncio.get_running_loop())
        sem = self._sems.get(loop_id)
        if sem is None:
            sem = self._sems[loop_id] = asyncio.Semaphore(self.concurrency)
        payload = {"model": self.model, "state": state, "questions": questions}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        delay = 0.5
        async with sem:
            for attempt in range(5):
                try:
                    async with httpx.AsyncClient(timeout=45) as client:
                        r = await client.post(self.base_url, json=payload, headers=headers)
                    if r.status_code == 200:
                        self.stats.calls += 1
                        return r.json()
                    if r.status_code in (429, 500, 502, 503, 504):
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    self.stats.errors += 1
                    raise DecisionEngineError(f"Jev HTTP {r.status_code}: {r.text[:300]}")
                except httpx.HTTPError as exc:
                    if attempt == 4:
                        self.stats.errors += 1
                        raise DecisionEngineError(f"Jev network error: {exc}") from exc
                    await asyncio.sleep(delay)
                    delay *= 2
        self.stats.errors += 1
        raise DecisionEngineError("Jev rate-limited after retries")


_engine: JevEngine | None = None


def engine() -> JevEngine:
    global _engine
    if _engine is None:
        _engine = JevEngine()
    return _engine


def set_engine(e: JevEngine | None) -> None:
    global _engine
    _engine = e
