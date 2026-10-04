"""
run_extraction.py

STEP 2: command-line entry point to run PDF -> claim extraction.

HOW TO RUN
----------
Mock mode (no API key needed, works out of the box on the bundled sample PDF):

    python scripts/run_extraction.py --mock

Real LLM mode (requires .env configured with GROQ_API_KEY or OLLAMA_BASE_URL):

    python scripts/run_extraction.py --provider groq --pdf path/to/report.pdf --company "Some Company"
    python scripts/run_extraction.py --provider ollama --pdf path/to/report.pdf --company "Some Company"

By default (no --pdf given) this runs on the bundled synthetic sample PDF.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.extraction.claim_extractor import extract_claims_from_pages  # noqa: E402
from app.extraction.llm_providers import LLMConfigurationError, MockLLMProvider, get_provider  # noqa: E402
from app.extraction.mock_data import get_canned_responses_for_sample_pdf  # noqa: E402
from app.extraction.pdf_parser import PDFParsingError, parse_pdf  # noqa: E402

DEFAULT_PDF = PROJECT_ROOT / "legacy" / "v1_data" / "sample_pdfs" / "synthetic_esg_report.pdf"


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")

    parser = argparse.ArgumentParser(description="Run the Step 2 ESG claim extraction pipeline.")
    parser.add_argument("--pdf", type=str, default=str(DEFAULT_PDF), help="Path to the ESG PDF.")
    parser.add_argument("--company", type=str, default="GreenLeaf Industries Ltd.", help="Company name hint.")
    parser.add_argument(
        "--provider", type=str, choices=["mock", "groq", "ollama"], default=None,
        help="LLM provider. Defaults to EXTRACTION_MODE env var, or 'mock' if unset.",
    )
    parser.add_argument("--mock", action="store_true", help="Shorthand for --provider mock.")
    parser.add_argument("--out", type=str, default=None, help="Optional path to write extracted claims as JSON.")
    args = parser.parse_args()

    mode = "mock" if args.mock else args.provider

    print("ESG Claim Extraction Pipeline (Step 2)")
    print(f"PDF:      {args.pdf}")
    print(f"Company:  {args.company}")
    print(f"Provider: {mode or '(from EXTRACTION_MODE env, default mock)'}\n")

    try:
        provider = get_provider(mode)
    except LLMConfigurationError as e:
        print(f"CONFIGURATION ERROR: {e}")
        return 1

    if provider.provider_label == "mock":
        if Path(args.pdf).name == DEFAULT_PDF.name:
            # Pre-load the canned responses that match the bundled sample PDF
            # exactly, so `--mock` works out of the box with zero configuration.
            provider = MockLLMProvider(canned_responses=get_canned_responses_for_sample_pdf())
        else:
            print(
                "NOTE: running MOCK mode on a PDF other than the bundled sample PDF. "
                "The mock provider only has canned answers for the sample PDF, so it "
                "will return zero claims for every page of this PDF. Use --provider "
                "groq/ollama for a real extraction on your own PDF.\n"
            )

    try:
        pages = parse_pdf(args.pdf)
    except PDFParsingError as e:
        print(f"PDF PARSING ERROR: {e}")
        return 1

    print(f"Parsed {len(pages)} page(s).\n")

    results = extract_claims_from_pages(pages, provider=provider, company_hint=args.company)

    all_claims = []
    total_errors = 0
    for r in results:
        print(f"Page {r.page_number}: {len(r.claims)} claim(s), {len(r.errors)} error(s)")
        for e in r.errors:
            print(f"    [ERROR] {e}")
        all_claims.extend(r.claims)
        total_errors += len(r.errors)

    print(f"\nTOTAL: {len(all_claims)} claim(s) extracted, {total_errors} error(s) [provider={provider.provider_label}]\n")

    for c in all_claims:
        print(f"  {c.claim_id} | {c.claim_type.value:13s} | {c.checkability.value:14s} | {c.original_text[:80]}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source_document": Path(args.pdf).name,
            "provider": provider.provider_label,
            "claim_count": len(all_claims),
            "claims": [c.model_dump(mode="json") for c in all_claims],
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote extracted claims to: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
