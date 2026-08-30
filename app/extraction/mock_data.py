"""
mock_data.py

STEP 2 / Part 8: Deterministic canned extraction results for the bundled
synthetic sample PDF (data/sample_pdfs/synthetic_esg_report.pdf).

WHY THIS FILE EXISTS
---------------------
MockLLMProvider (llm_providers.py) needs *something* to return instead of a
real LLM response, so tests and offline runs are deterministic and require
no API key. This file is the single source of truth for what the mock
should return for each page of the sample PDF -- it is intentionally kept
separate from llm_providers.py (a generic provider) and claim_extractor.py
(generic extraction logic), so the mock data for THIS ONE PDF doesn't
clutter the general-purpose code.

The `original_text` values here are written as clean, single-spaced
sentences (as a human would read them), matching how claim_extractor.py
normalizes whitespace when it looks up character offsets in the page text
(see claim_extractor.py::_find_char_offsets). They are NOT copy-pasted raw
pdfplumber output, which contains mid-sentence line-wrap newlines.

If data/sample_pdfs/synthetic_esg_report.pdf ever changes, this file and
data/sample_pdfs/expected_claims.json must be updated to match.
"""

from __future__ import annotations

import json

# Maps page_number -> the exact JSON string the mock LLM "returns" for that
# page, in the same shape the real prompt asks for (see
# prompts/claim_extraction_prompt.md).

_PAGE_1_CLAIMS = {
    "claims": [
        {
            "original_text": (
                "Sustainability remains at the heart of everything we do, and we continue to "
                "strive for a greener tomorrow."
            ),
            "metric": None,
            "value": None,
            "unit": None,
            "scope": None,
            "boundary": None,
            "baseline_year": None,
            "reporting_period": None,
            "claim_type": "commitment",
            "checkability": "NOT_CHECKABLE",
        }
    ]
}

_PAGE_2_CLAIMS = {
    "claims": [
        {
            "original_text": (
                "In FY2024, GreenLeaf Industries Ltd. reduced its Scope 1 greenhouse gas "
                "emissions by 18% compared to a 2019 baseline, from 42,000 tCO2e to 34,440 "
                "tCO2e at the company-wide level."
            ),
            "metric": "Scope 1 greenhouse gas emissions",
            "value": 18,
            "unit": "%",
            "scope": "Scope 1",
            "boundary": "company-wide",
            "baseline_year": "2019",
            "reporting_period": "FY2024",
            "claim_type": "result",
            "checkability": "CHECKABLE",
        },
        {
            "original_text": (
                "During FY2024, 32% of the electricity consumed at our manufacturing "
                "facilities was sourced from renewable energy."
            ),
            "metric": "renewable electricity share",
            "value": 32,
            "unit": "%",
            "scope": None,
            "boundary": "manufacturing facilities",
            "baseline_year": None,
            "reporting_period": "FY2024",
            "claim_type": "result",
            "checkability": "CHECKABLE",
        },
        {
            "original_text": (
                "We recycled 8,500 tonnes of industrial waste in FY2024, up from 6,200 "
                "tonnes in FY2023."
            ),
            "metric": "recycled industrial waste",
            "value": 8500,
            "unit": "tonnes",
            "scope": None,
            "boundary": None,
            "baseline_year": "FY2023",
            "reporting_period": "FY2024",
            "claim_type": "result",
            "checkability": "CHECKABLE",
        },
        {
            "original_text": (
                "We engaged with 65% of our key suppliers, by procurement spend, to assess "
                "Scope 3 emissions across our value chain in FY2024."
            ),
            "metric": "supplier engagement on Scope 3 emissions assessment",
            "value": 65,
            "unit": "%",
            "scope": "Scope 3",
            "boundary": "key suppliers by procurement spend",
            "baseline_year": None,
            "reporting_period": "FY2024",
            "claim_type": "result",
            "checkability": "CHECKABLE",
        },
    ]
}

_PAGE_3_CLAIMS = {
    "claims": [
        {
            "original_text": (
                "As of March 2024, women comprised 27% of our total workforce, up from "
                "19% in 2019."
            ),
            "metric": "women in workforce",
            "value": 27,
            "unit": "%",
            "scope": None,
            "boundary": "total workforce",
            "baseline_year": "2019",
            "reporting_period": "as of March 2024",
            "claim_type": "result",
            "checkability": "CHECKABLE",
        },
        {
            "original_text": (
                "Employee lost-time injury frequency rate improved by 12% during FY2024."
            ),
            "metric": "lost-time injury frequency rate",
            "value": 12,
            "unit": "%",
            "scope": None,
            "boundary": None,
            "baseline_year": None,
            "reporting_period": "FY2024",
            "claim_type": "result",
            "checkability": "CHECKABLE",
        },
    ]
}

_PAGE_4_CLAIMS = {
    "claims": [
        {
            "original_text": (
                "GreenLeaf Industries Ltd. maintained zero regulatory non-compliance "
                "notices from the Ministry of Environment, Forest and Climate Change "
                "during FY2024."
            ),
            "metric": "regulatory non-compliance notices",
            "value": 0,
            "unit": "count",
            "scope": None,
            "boundary": None,
            "baseline_year": None,
            "reporting_period": "FY2024",
            "claim_type": "result",
            "checkability": "CHECKABLE",
        },
        {
            "original_text": (
                "We are committed to achieving net-zero Scope 1 and Scope 2 emissions "
                "by 2040."
            ),
            "metric": None,
            "value": None,
            "unit": None,
            "scope": "Scope 1 and Scope 2",
            "boundary": None,
            "baseline_year": None,
            "reporting_period": None,
            "claim_type": "target",
            "checkability": "NOT_CHECKABLE",
        },
        {
            "original_text": (
                "Our governance framework is built on the principles of transparency, "
                "accountability, and stakeholder trust."
            ),
            "metric": None,
            "value": None,
            "unit": None,
            "scope": None,
            "boundary": None,
            "baseline_year": None,
            "reporting_period": None,
            "claim_type": "commitment",
            "checkability": "NOT_CHECKABLE",
        },
    ]
}


def get_canned_responses_for_sample_pdf() -> dict[int, str]:
    """Returns the page_number -> JSON-string mapping for MockLLMProvider,
    matching data/sample_pdfs/synthetic_esg_report.pdf exactly."""
    return {
        1: json.dumps(_PAGE_1_CLAIMS),
        2: json.dumps(_PAGE_2_CLAIMS),
        3: json.dumps(_PAGE_3_CLAIMS),
        4: json.dumps(_PAGE_4_CLAIMS),
    }
