"""
scripts/cleanup_to_scrap.py

Moves everything the v2 system does not need into ./scrap/ (nothing is deleted).
Uses `git mv` for tracked files so history is kept, plain move otherwise.

NEVER touches .env (your keys stay exactly where they are).

    python scripts/cleanup_to_scrap.py          # do it
    python scripts/cleanup_to_scrap.py --dry    # just print what would move
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (source, destination inside scrap/)
MOVES = [
    # v1 apps / UIs
    ("streamlit_app", "v1_ui/streamlit_app"),
    ("simple-ui", "v1_ui/simple-ui"),
    ("main.py", "v1_app/main.py"),
    ("prompts", "v1_app/prompts"),
    (".env.example", ".env.example"),
    # v1 backend modules (v2 never imports them)
    ("app/extraction", "v1_app/app/extraction"),
    ("app/evaluation", "v1_app/app/evaluation"),
    ("app/retrieval", "v1_app/app/retrieval"),
    ("app/scoring", "v1_app/app/scoring"),
    ("app/utils", "v1_app/app/utils"),
    ("app/storage.py", "v1_app/app/storage.py"),
    ("app/api/pipeline.py", "v1_app/app/api/pipeline.py"),
    # old hand-written v1 dataset
    ("legacy", "legacy"),
    # v1 scripts
    *[(f"scripts/{f}", f"v1_scripts/{f}") for f in [
        "evaluate_extraction.py", "evaluate_hard_cases.py", "evaluate_retrieval_methods.py",
        "generate_edge_case_pdfs.py", "generate_sample_pdf.py", "run_extraction.py",
        "run_verification.py", "validate_dataset.py", "push_v2.ps1", "push_v2.sh"]],
    # v1 tests
    *[(f"tests/{f}", f"v1_tests/{f}") for f in [
        "test_api.py", "test_claim_extractor.py", "test_edge_cases.py", "test_numeric_checks.py",
        "test_pdf_parser.py", "test_pipeline.py", "test_retrieval.py", "test_risk_score.py",
        "test_storage.py", "test_verification.py"]],
    # v1 docs
    *[(f"docs/{f}", f"v1_docs/{f}") for f in [
        "ARCHITECTURE.md", "DEMO_FLOW.md", "FINAL_PROJECT_DOCUMENTATION.md", "PROJECT_PROGRESS_STEP_1.md",
        "PROJECT_PROGRESS_STEP_2.md", "PROJECT_PROGRESS_STEP_4_5.md", "PROJECT_STATUS_AND_VALIDATION.md",
        "UI_PLAN.md", "README_v1.md", "TECHNICAL_SUMMARY_v1.docx", "architecture_diagram.svg",
        "architecture_diagram.png"]],
    ("docs/review", "review_pdf_build"),
    # problem statement screenshots -> docs
    # (kept, just tidied: handled below as a docs move, not scrap)
    # v1 React pages (v2 UI does not use them)
    *[(f"web/src/components/{f}", f"v1_web/components/{f}") for f in [
        "ClaimDetail.tsx", "ClaimsTable.tsx", "ConfigPanel.tsx", "DatasetDemoPage.tsx",
        "DisclaimerBanner.tsx", "ExecutiveSummary.tsx", "UploadAnalyzePage.tsx"]],
    ("web/src/components/v2/LegacyPage.tsx", "v1_web/components/v2/LegacyPage.tsx"),
    *[(f"web/src/lib/{f}", f"v1_web/lib/{f}") for f in ["api.ts", "types.ts"]],
    ("web/screenshots", "web_screenshots_dev"),
    ("data/reports/previews", "report_previews"),
    # leftovers from earlier delivery
    ("esg_v2.zip", "esg_v2.zip"),
    ("CHANGED_FILES.txt", "CHANGED_FILES.txt"),
]

# Not scrap: tidy the problem-statement screenshots into docs/
TIDY = [("ss1.png", "docs/problem_statement/ss1.png"), ("ss2.png", "docs/problem_statement/ss2.png")]

PROTECTED = {".env", ".git", "venv", ".venv", "web/node_modules"}


def tracked(path: Path) -> bool:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
                       capture_output=True, text=True)
    return r.returncode == 0


def move(src_rel: str, dst_rel: str, dry: bool) -> None:
    if src_rel in PROTECTED:
        return
    src, dst = ROOT / src_rel, ROOT / dst_rel
    if not src.exists():
        return
    print(f"  {src_rel:55s} -> {dst_rel}")
    if dry:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if (ROOT / ".git").exists() and tracked(src):
        r = subprocess.run(["git", "mv", "-k", str(src), str(dst)], cwd=ROOT, capture_output=True, text=True)
        if src.exists():          # partially tracked folder: move the rest by hand
            if src.is_dir():
                for p in list(src.rglob("*")):
                    if p.is_file():
                        t = dst / p.relative_to(src)
                        t.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(p), str(t))
                shutil.rmtree(src, ignore_errors=True)
            else:
                shutil.move(str(src), str(dst))
    else:
        shutil.move(str(src), str(dst))


def main() -> None:
    dry = "--dry" in sys.argv
    env = ROOT / ".env"
    env_before = env.read_bytes() if env.exists() else None
    print("Moving unused files into scrap/ (nothing deleted, .env untouched)")
    for s, d in MOVES:
        move(s, f"scrap/{d}", dry)
    for s, d in TIDY:
        move(s, d, dry)
    if not dry:
        (ROOT / "scrap").mkdir(exist_ok=True)
        (ROOT / "scrap" / "README.md").write_text(
            "# scrap/\n\nEverything the v2 system does not need: the v1 rule-based backend, Streamlit and "
            "simple-ui, the old hand-written JSON dataset, v1 scripts/tests/docs, dev screenshots.\n"
            "Kept for reference only. Nothing in the main project imports from here.\n", encoding="utf-8")
        for p in [ROOT / "app" / "api" / "__pycache__"]:
            shutil.rmtree(p, ignore_errors=True)
    if env_before is not None:
        assert env.exists() and env.read_bytes() == env_before, ".env changed! (should never happen)"
        print(".env checked: untouched")
    print("done" if not dry else "dry run only")


if __name__ == "__main__":
    main()
