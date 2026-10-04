# scripts/push_v2.ps1
# Commits the v2 work in 3 logical commits under YOUR git identity and pushes.
# No AI author or co-author lines are added.
#
# Usage (from the repo root, PowerShell):
#   .\scripts\push_v2.ps1                 # pushes to a new branch "v2-agentic" (safe default)
#   .\scripts\push_v2.ps1 -Branch main    # push straight to main
param([string]$Branch = "v2-agentic")
$ErrorActionPreference = "Stop"

$name  = git config user.name
$email = git config user.email
if (-not $name -or -not $email) { Write-Error "Set your identity first: git config user.name 'Your Name'; git config user.email 'you@example.com'" }
if ($name -match "(?i)claude|anthropic" -or $email -match "(?i)claude|anthropic") { Write-Error "git identity looks like an AI account ($name <$email>). Set your own identity first." }
Write-Host "Committing as: $name <$email>"

if (Test-Path .env) { git rm --cached -q --ignore-unmatch .env | Out-Null }   # never commit secrets

$current = git rev-parse --abbrev-ref HEAD
if ($Branch -ne $current) { git checkout -B $Branch }

# The old hand-written v1 dataset now lives in legacy/v1_data; remove the old copies.
foreach ($p in "data/claims","data/evidence","data/test","data/sample_pdfs") {
  if ((Test-Path "legacy/v1_data/$(Split-Path $p -Leaf)") -and (Test-Path $p)) { git rm -r -q --ignore-unmatch $p; if (Test-Path $p) { Remove-Item -Recurse -Force $p } }
}
if (Test-Path esg_v2.zip) { Remove-Item esg_v2.zip }
if (Test-Path CHANGED_FILES.txt) { Remove-Item CHANGED_FILES.txt }

function Commit($msg, $paths) {
  $existing = $paths | Where-Object { Test-Path $_ }
  if ($existing) { git add -A -- $existing }
  $staged = git diff --cached --name-only
  if ($staged) { git commit -q -m $msg; Write-Host "  committed: $msg" } else { Write-Host "  nothing to commit for: $msg" }
}

Commit "Add synthetic ESG world, mock data-source service and demo reports" @(
  "data_gen","mock_sources","report_gen","data/world","data/reports","data/benchmark","data/benchmark_heldout",
  "legacy","data/claims","data/evidence","data/test","data/sample_pdfs","tests/test_world_db.py","tests/test_benchmark.py")

Commit "Add Jev decision engine, LangGraph multi-agent pipeline, v2 API and evaluation" @(
  "app","eval","data/cassettes","data/models","tests","scripts","requirements.txt",".env.example",".gitignore","main.py",
  "streamlit_app","prompts")

Commit "Add v2 React UI, documentation and verification pack" @(
  "web","docs","README.md","verification_pack","simple-ui","ss1.png","ss2.png")

# anything left over
git add -A
if (git diff --cached --name-only) { git commit -q -m "Tidy remaining v2 files"; Write-Host "  committed: Tidy remaining v2 files" }

git log --oneline -5
git push -u origin $Branch
Write-Host "Pushed to origin/$Branch"
