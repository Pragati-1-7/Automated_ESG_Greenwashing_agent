"""
claim_extractor.py

STEP 2: the claim extraction engine.

PIPELINE (per page)
--------------------
    PageText (from pdf_parser.py)
        -> build prompt from prompts/claim_extraction_prompt.md
        -> send to an LLMProvider (mock / groq / ollama)
        -> parse the provider's raw text as JSON
        -> validate each item against app.utils.schemas.ClaimRecord
        -> (bounded retry once on malformed/invalid output)
        -> return list[ClaimRecord]

This module NEVER invents field values. If the LLM's JSON is malformed or
fails Pydantic validation twice in a row, that page's failure is reported
and skipped -- it does not crash the whole run, and it does not silently
fabricate a "best guess" claim.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from app.extraction.llm_providers import BaseLLMProvider, MockLLMProvider
from app.extraction.mock_data import get_canned_responses_for_sample_pdf
from app.extraction.pdf_parser import PageText
from app.utils.schemas import ClaimRecord

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_PATH = PROJECT_ROOT / "prompts" / "claim_extraction_prompt.md"

_MAX_RETRIES = 1  # Part 9: bounded retry, never infinite.


class PromptNotFoundError(Exception):
    """Raised if the prompt template file is missing."""


@dataclass
class PageExtractionResult:
    """What extraction produced (or failed to produce) for a single page."""

    page_number: int
    claims: list[ClaimRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    raw_response: Optional[str] = None


def _load_prompt_template() -> tuple[str, str]:
    """Reads prompts/claim_extraction_prompt.md and splits it into
    (system_prompt, user_prompt_template).

    The file has a '## SYSTEM' section and a '## USER (template)' section,
    each containing a fenced or unfenced block of prompt text. We extract
    the SYSTEM section body and the USER section's template body (the part
    inside the ``` fences under "USER (template)").
    """
    if not PROMPT_PATH.exists():
        raise PromptNotFoundError(f"Prompt template not found: {PROMPT_PATH}")

    text = PROMPT_PATH.read_text(encoding="utf-8")

    system_match = re.search(r"## SYSTEM\n\n(.*?)\n---\n\n## USER", text, re.DOTALL)
    if not system_match:
        raise PromptNotFoundError("Could not locate '## SYSTEM' section in prompt template.")
    system_prompt = system_match.group(1).strip()

    user_match = re.search(r"## USER \(template\)\n\n```\n(.*?)\n```", text, re.DOTALL)
    if not user_match:
        raise PromptNotFoundError("Could not locate '## USER (template)' section in prompt template.")
    user_template = user_match.group(1)

    return system_prompt, user_template


def _build_user_prompt(
    user_template: str, company_hint: str, source_document: str, page_number: int, page_text: str
) -> str:
    return (
        user_template.replace("{company_hint}", company_hint or "UNKNOWN")
        .replace("{source_document}", source_document)
        .replace("{page_number}", str(page_number))
        .replace("{page_text}", page_text)
    )


def _strip_code_fences(raw: str) -> str:
    """LLMs sometimes wrap JSON in ```json ... ``` even when told not to.
    Strip that defensively before parsing."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _find_char_offsets(page_text: str, original_text: str) -> tuple[Optional[int], Optional[int]]:
    """Best-effort character offset lookup for source traceability (Part 10).

    PDF text extraction frequently inserts line-wrap newlines in the middle
    of a sentence, so we normalize whitespace (collapse runs of whitespace
    to a single space) on BOTH sides before searching. The returned offsets
    are therefore offsets into the *normalized* page text, not the raw
    pdfplumber output -- documented here and in PROJECT_PROGRESS_STEP_2.md
    as a known limitation. If the claim text can't be found verbatim (e.g.
    the LLM paraphrased slightly), we return (None, None) rather than
    guessing.
    """
    normalized_page = _normalize_whitespace(page_text)
    normalized_claim = _normalize_whitespace(original_text)

    if not normalized_claim:
        return None, None

    idx = normalized_page.find(normalized_claim)
    if idx == -1:
        return None, None
    return idx, idx + len(normalized_claim)


def _claim_id(page_number: int, index_on_page: int, prefix: str) -> str:
    return f"CLM-{prefix}-P{page_number:02d}-{index_on_page:03d}"


def extract_claims_from_page(
    page: PageText,
    provider: BaseLLMProvider,
    company_hint: str,
    id_prefix: str = "EXT",
) -> PageExtractionResult:
    """Extract ESG claims from a single page using the given provider.

    Args:
        page: a PageText from pdf_parser.parse_pdf().
        provider: any BaseLLMProvider (mock, groq, or ollama).
        company_hint: the company name to include in the prompt, used only
            to help the LLM disambiguate pronouns -- it does NOT override
            what the LLM actually extracts for the `company` concept, since
            ClaimRecord.company is not populated in Step 2 (see note below).
        id_prefix: short tag embedded in generated claim_ids, e.g. "MOCK"
            or "EXT", so mock and real output are distinguishable by ID
            alone in addition to extraction_method.

    Returns:
        A PageExtractionResult with validated ClaimRecords and/or errors.

    NOTE ON ClaimRecord.company: the Step 1 schema requires `company` on
    every claim. Step 2's prompt does not ask the LLM to invent a company
    name per claim (Part 6 forbids inventing facts); instead we set
    `company` to `company_hint` for every claim on this page, since the
    company name is a document-level fact supplied by the caller (typically
    the PDF filename or a value the user provides), not something the LLM
    should infer sentence-by-sentence.
    """
    result = PageExtractionResult(page_number=page.page_number)

    if not page.text.strip():
        # Empty page: nothing to extract, not an error.
        return result

    system_prompt, user_template = _load_prompt_template()
    user_prompt = _build_user_prompt(
        user_template, company_hint, page.source_document, page.page_number, page.text
    )

    attempt = 0
    last_error: Optional[str] = None
    raw_response: Optional[str] = None

    while attempt <= _MAX_RETRIES:
        attempt += 1
        try:
            raw_response = provider.complete(system_prompt, user_prompt)
        except Exception as e:  # noqa: BLE001
            last_error = f"Provider call failed on attempt {attempt}: {e}"
            continue

        result.raw_response = raw_response
        cleaned = _strip_code_fences(raw_response)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            last_error = f"Malformed JSON on attempt {attempt}: {e}"
            if attempt <= _MAX_RETRIES:
                user_prompt = (
                    user_prompt
                    + "\n\nYour previous response was not valid JSON. "
                    + "Return ONLY a valid JSON object matching the required shape, nothing else."
                )
            continue

        raw_claims = parsed.get("claims", [])
        if not isinstance(raw_claims, list):
            last_error = f"'claims' was not a list on attempt {attempt}: {type(raw_claims)}"
            continue

        validated: list[ClaimRecord] = []
        page_errors: list[str] = []
        for i, raw_claim in enumerate(raw_claims, start=1):
            record_dict = dict(raw_claim)
            record_dict["claim_id"] = _claim_id(page.page_number, i, id_prefix)
            record_dict["company"] = company_hint
            record_dict["source_document"] = page.source_document
            record_dict["page_number"] = page.page_number
            record_dict["extraction_method"] = provider.provider_label

            original_text = record_dict.get("original_text", "") or ""
            char_start, char_end = _find_char_offsets(page.text, original_text)
            record_dict["char_start"] = char_start
            record_dict["char_end"] = char_end

            try:
                validated.append(ClaimRecord(**record_dict))
            except ValidationError as e:
                page_errors.append(f"Claim {i} on page {page.page_number} failed validation: {e}")

        result.claims = validated
        result.errors = page_errors
        return result

    # All attempts exhausted without producing usable JSON.
    result.errors = [last_error or "Unknown extraction failure."]
    return result


def extract_claims_from_pages(
    pages: list[PageText],
    provider: Optional[BaseLLMProvider] = None,
    company_hint: str = "UNKNOWN",
    id_prefix: Optional[str] = None,
) -> list[PageExtractionResult]:
    """Run extraction across every page of a parsed PDF.

    Args:
        pages: output of pdf_parser.parse_pdf().
        provider: an LLM provider. Defaults to a MockLLMProvider pre-loaded
            with the bundled sample PDF's canned responses (convenient for
            quick demos on the sample PDF; for a different PDF, pass an
            explicit provider from app.extraction.llm_providers.get_provider()).
        company_hint: company name to stamp onto every extracted claim.
        id_prefix: overrides the claim_id prefix; defaults to "MOCK" for the
            mock provider and "EXT" for real providers, so mock/real output
            is distinguishable at a glance even without checking extraction_method.
    """
    if provider is None:
        provider = MockLLMProvider(canned_responses=get_canned_responses_for_sample_pdf())

    if id_prefix is None:
        id_prefix = "MOCK" if isinstance(provider, MockLLMProvider) else "EXT"

    return [
        extract_claims_from_page(page, provider, company_hint, id_prefix=id_prefix)
        for page in pages
    ]
