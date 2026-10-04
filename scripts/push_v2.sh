#!/usr/bin/env bash
# Same as push_v2.ps1 for Git Bash / Linux / macOS. Usage: bash scripts/push_v2.sh [branch]
set -euo pipefail
BRANCH="${1:-v2-agentic}"
NAME="$(git config user.name || true)"; EMAIL="$(git config user.email || true)"
[ -n "$NAME" ] && [ -n "$EMAIL" ] || { echo "Set git user.name/user.email first"; exit 1; }
echo "$NAME $EMAIL" | grep -qiE "claude|anthropic" && { echo "git identity looks like an AI account; set your own"; exit 1; }
git rm --cached -q --ignore-unmatch .env >/dev/null 2>&1 || true
[ "$(git rev-parse --abbrev-ref HEAD)" = "$BRANCH" ] || git checkout -B "$BRANCH"
for p in data/claims data/evidence data/test data/sample_pdfs; do
  [ -e "legacy/v1_data/$(basename $p)" ] && [ -e "$p" ] && { git rm -r -q --ignore-unmatch "$p"; rm -rf "$p"; }
done
rm -f esg_v2.zip CHANGED_FILES.txt
commit() { msg="$1"; shift; ex=(); for p in "$@"; do [ -e "$p" ] && ex+=("$p"); done
  [ ${#ex[@]} -gt 0 ] && git add -A -- "${ex[@]}"
  git diff --cached --quiet || { git commit -q -m "$msg"; echo "  committed: $msg"; }; }
commit "Add synthetic ESG world, mock data-source service and demo reports" data_gen mock_sources report_gen data/world data/reports data/benchmark data/benchmark_heldout legacy data/claims data/evidence data/test data/sample_pdfs tests/test_world_db.py tests/test_benchmark.py
commit "Add Jev decision engine, LangGraph multi-agent pipeline, v2 API and evaluation" app eval data/cassettes data/models tests scripts requirements.txt .env.example .gitignore main.py streamlit_app prompts
commit "Add v2 React UI, documentation and verification pack" web docs README.md verification_pack simple-ui ss1.png ss2.png
git add -A; git diff --cached --quiet || git commit -q -m "Tidy remaining v2 files"
git log --oneline -5
git push -u origin "$BRANCH"
