"""
test_claim_extractor.py

STEP 2 / Part 13: automated tests for app/extraction/claim_extractor.py
and app/extraction/llm_providers.py.

Covers:
- structured ClaimRecord validation
- invalid LLM output (malformed JSON, invalid enum values)
- valid LLM output
- vague claim handling
- source/page preservation
- mock extraction mode
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.extraction.claim_extractor import extract_claims_from_page, extract_claims_from_pages  # noqa: E402
from app.extraction.llm_providers import BaseLLMProvider, MockLLMProvider  # noqa: E402
from app.extraction.mock_data import get_canned_responses_for_sample_pdf  # noqa: E402
from app.extraction.pdf_parser import PageText, parse_pdf  # noqa: E402

SAMPLE_PDF = PROJECT_ROOT / "data" / "sample_pdfs" / "synthetic_esg_report.pdf"


class _FixedResponseProvider(BaseLLMProvider):
    """Test double: always returns a fixed raw string, regardless of prompt."""

    provider_label = "test-fixed"

    def __init__(self, response: str):
        self._response = response

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self._response


def _page(text: str, page_number: int = 1) -> PageText:
    return PageText(page_number=page_number, text=text, source_document="unit_test.pdf", char_count=len(text))


# ---------------------------------------------------------------------------
# Mock extraction mode, full pipeline (Part 8)
# ---------------------------------------------------------------------------

def test_mock_extraction_mode_on_sample_pdf():
    assert SAMPLE_PDF.exists(), "Run scripts/generate_sample_pdf.py first."
    pages = parse_pdf(SAMPLE_PDF)
    provider = MockLLMProvider(canned_responses=get_canned_responses_for_sample_pdf())
    results = extract_claims_from_pages(pages, provider=provider, company_hint="GreenLeaf Industries Ltd.")

    all_claims = [c for r in results for c in r.claims]
    assert len(all_claims) == 10
    for c in all_claims:
        # Every claim from the mock provider must be clearly labelled as mock,
        # never mistaken for a real LLM result (Part 8 requirement).
        assert c.extraction_method == "mock"
        assert c.claim_id.startswith("CLM-MOCK-")


# ---------------------------------------------------------------------------
# Valid LLM output
# ---------------------------------------------------------------------------

def test_valid_llm_output_produces_validated_claim():
    raw = json.dumps({
        "claims": [{
            "original_text": "We reduced Scope 1 emissions by 40% in FY2024.",
            "metric": "Scope 1 emissions",
            "value": 40,
            "unit": "%",
            "scope": "Scope 1",
            "boundary": None,
            "baseline_year": None,
            "reporting_period": "FY2024",
            "claim_type": "result",
            "checkability": "CHECKABLE",
        }]
    })
    provider = _FixedResponseProvider(raw)
    page = _page("We reduced Scope 1 emissions by 40% in FY2024.")
    result = extract_claims_from_page(page, provider, company_hint="TestCo")

    assert len(result.claims) == 1
    assert result.errors == []
    claim = result.claims[0]
    assert claim.value == 40
    assert claim.scope == "Scope 1"
    assert claim.source_document == "unit_test.pdf"
    assert claim.page_number == 1
    assert claim.company == "TestCo"


# ---------------------------------------------------------------------------
# Invalid LLM output: malformed JSON
# ---------------------------------------------------------------------------

def test_malformed_json_is_reported_not_crashed():
    provider = _FixedResponseProvider("this is not { valid json at all")
    page = _page("Some ESG text.")
    result = extract_claims_from_page(page, provider, company_hint="TestCo")

    assert result.claims == []
    assert len(result.errors) == 1
    assert "Malformed JSON" in result.errors[0] or "JSON" in result.errors[0]


# ---------------------------------------------------------------------------
# Invalid LLM output: invalid enum value fails Pydantic validation cleanly
# ---------------------------------------------------------------------------

def test_invalid_enum_value_is_rejected_not_silently_accepted():
    raw = json.dumps({
        "claims": [{
            "original_text": "We reduced emissions.",
            "metric": "emissions",
            "value": 10,
            "unit": "%",
            "scope": None,
            "boundary": None,
            "baseline_year": None,
            "reporting_period": "FY2024",
            "claim_type": "definitely_not_a_real_type",  # invalid enum
            "checkability": "CHECKABLE",
        }]
    })
    provider = _FixedResponseProvider(raw)
    page = _page("We reduced emissions.")
    result = extract_claims_from_page(page, provider, company_hint="TestCo")

    assert result.claims == []
    assert len(result.errors) == 1
    assert "failed validation" in result.errors[0]


def test_claims_not_a_list_is_reported():
    raw = json.dumps({"claims": "not-a-list"})
    provider = _FixedResponseProvider(raw)
    page = _page("Some text.")
    result = extract_claims_from_page(page, provider, company_hint="TestCo")
    assert result.claims == []
    assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# Vague claim handling
# ---------------------------------------------------------------------------

def test_vague_claim_extracted_with_null_fields():
    raw = json.dumps({
        "claims": [{
            "original_text": "We care deeply about the planet.",
            "metric": None,
            "value": None,
            "unit": None,
            "scope": None,
            "boundary": None,
            "baseline_year": None,
            "reporting_period": None,
            "claim_type": "commitment",
            "checkability": "NOT_CHECKABLE",
        }]
    })
    provider = _FixedResponseProvider(raw)
    page = _page("We care deeply about the planet.")
    result = extract_claims_from_page(page, provider, company_hint="TestCo")

    assert len(result.claims) == 1
    claim = result.claims[0]
    assert claim.checkability.value == "NOT_CHECKABLE"
    assert claim.metric is None
    assert claim.value is None


# ---------------------------------------------------------------------------
# Empty page handling
# ---------------------------------------------------------------------------

def test_empty_page_produces_no_claims_and_no_provider_call():
    calls = {"count": 0}

    class _CountingProvider(BaseLLMProvider):
        provider_label = "counting"

        def complete(self, system_prompt: str, user_prompt: str) -> str:
            calls["count"] += 1
            return json.dumps({"claims": []})

    page = _page("", page_number=5)
    result = extract_claims_from_page(page, _CountingProvider(), company_hint="TestCo")

    assert result.claims == []
    assert result.errors == []
    assert calls["count"] == 0  # short-circuited before calling the provider


# ---------------------------------------------------------------------------
# Source/page preservation and character offsets
# ---------------------------------------------------------------------------

def test_char_offsets_found_when_text_matches():
    page_text = "Intro sentence. We reduced Scope 1 emissions by 40% in FY2024. Closing sentence."
    raw = json.dumps({
        "claims": [{
            "original_text": "We reduced Scope 1 emissions by 40% in FY2024.",
            "metric": "Scope 1 emissions", "value": 40, "unit": "%", "scope": "Scope 1",
            "boundary": None, "baseline_year": None, "reporting_period": "FY2024",
            "claim_type": "result", "checkability": "CHECKABLE",
        }]
    })
    provider = _FixedResponseProvider(raw)
    page = _page(page_text, page_number=7)
    result = extract_claims_from_page(page, provider, company_hint="TestCo")

    claim = result.claims[0]
    assert claim.page_number == 7
    assert claim.char_start is not None and claim.char_end is not None
    assert page_text[claim.char_start:claim.char_end] == claim.original_text


def test_char_offsets_none_when_text_not_found():
    raw = json.dumps({
        "claims": [{
            "original_text": "This exact sentence does not appear on the page.",
            "metric": None, "value": None, "unit": None, "scope": None,
            "boundary": None, "baseline_year": None, "reporting_period": None,
            "claim_type": "commitment", "checkability": "NOT_CHECKABLE",
        }]
    })
    provider = _FixedResponseProvider(raw)
    page = _page("Completely unrelated page text.", page_number=2)
    result = extract_claims_from_page(page, provider, company_hint="TestCo")

    claim = result.claims[0]
    assert claim.char_start is None
    assert claim.char_end is None
