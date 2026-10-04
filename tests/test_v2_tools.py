"""v2 deterministic tools: claim parser, calculator, PDF ingest."""

import json
from pathlib import Path

import pytest

from app.ingest.pdf import IngestError, parse_pdf, split_sentences
from app.tools import calculator as calc
from app.tools.claim_parser import facility_hint, fy_from, numbers, parse, periods
from data_gen.spec import DEMO_COMPANIES

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "data" / "reports"


@pytest.mark.parametrize("text,fy", [("FY2024-25", "FY2025"), ("FY 2022-23", "FY2023"), ("2023-24", "FY2024"),
                                     ("FY25", "FY2025"), ("FY2021", "FY2021")])
def test_fy_from(text, fy):
    assert fy_from(text) == fy


def test_periods_baseline_patterns():
    assert periods("We cut Scope 1 by 40% against our FY2020 baseline.") == (None, "FY2020")
    assert periods("Intensity fell between FY2020 and FY2025.") == ("FY2025", "FY2020")
    assert periods("LTIFR improved from 0.52 in FY2020 to 0.30 in FY2025.") == ("FY2025", "FY2020")
    assert periods("Emissions are 17% lower than in FY2019-20.") == (None, "FY2020")


def test_numbers_indian_units_and_noise():
    vals = [(n.value, n.unit) for n in numbers("We recovered 1.8 lakh tonnes of waste in FY2025.")]
    assert vals == [(180000.0, "tonnes")]
    assert [(n.value, n.unit) for n in numbers("Our absolute Scope 1 emissions fell 40%.")] == [(40.0, "%")]
    assert numbers("Figure 12.1 Gross wages paid to women.") == []
    assert [n.unit for n in numbers("Withdrawal was 9,420,894 ML.")] == ["ml"]


def test_facility_hint():
    assert facility_hint("Our Keonjhar mining operations caused zero deforestation.") == "Keonjhar"
    assert facility_hint("No forest loss within 5 km of our Sundargarh Bauxite Mine.") == "Sundargarh Bauxite"


def test_calculator():
    c = calc.pct_change(11_800_000, 10_856_000)
    assert c.result == -8.0 and "-8.0%" in c.expression
    assert calc.share_pct(6_838_000, 7_400_000).result == 92.41
    assert calc.multiple(2.0, 3.1).result == 1.55
    assert calc.relative_gap(0.12, 0.41).result == -70.73
    with pytest.raises(ZeroDivisionError):
        calc.pct_change(0, 5)


def test_sentence_split_keeps_abbreviations():
    s = split_sentences("NGT imposed Rs. 4.2 crore on Vajra Steel Ltd. in 2024. It was paid.")
    assert len(s) == 2


@pytest.mark.parametrize("idx,key", [(0, "vajra"), (1, "sahyadri"), (2, "kaveri"), (3, "aurelia")])
def test_every_planted_claim_is_ingested_verbatim_on_the_right_page(idx, key):
    man = {m["key"]: m for m in json.loads((REPORTS / "manifest.json").read_text())}
    doc = parse_pdf(REPORTS / man[key]["filename"])
    pages = {s.text: s.page for s in doc.sentences}
    expected_page = {c["id"]: c["page"] for c in man[key]["claims"]}
    for c in DEMO_COMPANIES[idx]["claims"]:
        assert c["text"] in pages, c["id"]
        assert pages[c["text"]] == expected_page[c["id"]], c["id"]
    assert doc.page_count >= 20


def test_ingest_rejects_garbage(tmp_path):
    bad = tmp_path / "x.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(IngestError):
        parse_pdf(bad)
