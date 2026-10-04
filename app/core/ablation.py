"""Ablation switches for the evaluation harness (eval/run_benchmark.py).
Production runs use the defaults; the harness flips one switch at a time to
measure what each component contributes."""

from __future__ import annotations

import contextvars
from dataclasses import dataclass


@dataclass(frozen=True)
class Flags:
    retrieval: bool = True              # False: verdict from the claim alone (no evidence)
    only_sources: tuple[str, ...] = ()  # e.g. ("news",) = plain unstructured RAG baseline
    max_rounds: int | None = None       # 1 = no FIRE-style second round
    relevance_gate: bool = True         # False: off-topic evidence may move the verdict


_flags: contextvars.ContextVar[Flags] = contextvars.ContextVar("ablation_flags", default=Flags())


def flags() -> Flags:
    return _flags.get()


def use_flags(f: Flags) -> contextvars.Token:
    return _flags.set(f)
