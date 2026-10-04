"""Agents on recorded decision-engine answers (JEV_MODE=replay, set in conftest).

These run the real agent code; only the Jev HTTP responses are replayed."""

import asyncio
import json
from pathlib import Path

import pytest

from app.agents import extractor
from app.agents.judge import validate_citations
from app.decision.jev import engine
from app.graph.claims import verify_claim
from app.ingest.pdf import parse_pdf
from app.llm.providers import MockLLM
from data_gen.spec import DEMO_COMPANIES

ROOT = Path(__file__).resolve().parent.parent
CASES = {json.loads(l)["case_id"]: json.loads(l) for l in (ROOT / "data/benchmark/cases.jsonl").read_text().splitlines()}


def test_extractor_finds_every_planted_claim_in_kaveri():
    doc = parse_pdf(ROOT / "data/reports/kaveri_threads_brsr_fy2025.pdf")
    found = asyncio.run(extractor.extract(doc.sentences, engine()))
    texts = {f["sentence"].text: f for f in found}
    for c in DEMO_COMPANIES[2]["claims"]:
        assert c["text"] in texts, c["id"]
        if c["metric"]:
            assert texts[c["text"]]["metric"] in (c["metric"], None) or c["id"] == "KAV-11"


def test_screen_drops_table_rows_and_back_matter():
    from app.core.models import Sentence
    s = [Sentence(sid="1", text="Water footprint Total water withdrawal kL 13,00,000 12,40,000 11,80,000 10,00,000",
                  page=1, section="BRSR"),
         Sentence(sid="2", text="Emissions are reported as tonnes of CO2 equivalent in this index.", page=2,
                  section="GRI content index"),
         Sentence(sid="3", text="We reduced our Scope 1 emissions by 10% since FY2020.", page=3, section="Climate")]
    assert [x.sid for x in extractor.screen(s)] == ["3"]


@pytest.mark.parametrize("case_id", ["BM-001", "BM-002", "BM-066", "BM-103", "BM-108", "BM-151"])
def test_benchmark_cases_on_recorded_answers(case_id):
    c = CASES[case_id]
    claim, match = asyncio.run(verify_claim(c["claim_text"], c["company_name"], engine(), MockLLM(),
                                            doc_fy=c["fy"] or "FY2025", claim_id=case_id))
    assert claim.verdict.label == c["label"]
    cited = [e.evidence_id for s in claim.sub_claims for e in s.evidence]
    assert validate_citations(claim.sub_claims, cited) == []
    assert 0 <= claim.risk.score <= 100


def test_unknown_company_abstains():
    claim, match = asyncio.run(verify_claim("Our LTIFR stood at 0.05 in FY2025.", "Aurelia Renewables Pvt Ltd",
                                            engine(), MockLLM()))
    assert not match.resolved
    assert claim.verdict.label == "INSUFFICIENT_EVIDENCE"
