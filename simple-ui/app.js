const TIER_LABELS = {
  1: "Tier 1 - Regulatory filing",
  2: "Tier 2 - Regulator / tribunal",
  3: "Tier 3 - Audited report",
  4: "Tier 4 - Company PR",
  5: "Tier 5 - News"
};

const VERDICT_COLORS = {
  ALIGN: "#1a7f37",
  CONTRADICT: "#b42318",
  INSUFFICIENT_EVIDENCE: "#946800",
  NOT_APPLICABLE: "#6b7280"
};

const VERDICT_BG = {
  ALIGN: "#e6f4ea",
  CONTRADICT: "#fbeae8",
  INSUFFICIENT_EVIDENCE: "#fdf3e0",
  NOT_APPLICABLE: "#eef0f2"
};

let lastAnalyzeResult = null;
let lastAnalyzeMode = "mock";
let lastDatasetResult = null;
let selectedAnalyzeClaim = null;
let selectedDatasetClaim = null;
let activeTab = "Full report";

function backendUrl() {
  return document.getElementById("backendUrl").value.replace(/\/$/, "");
}

function currentConfig() {
  return {
    mode: document.getElementById("modeSelect").value,
    topK: Number(document.getElementById("topKRange").value),
    useSemantic: document.getElementById("semanticCheck").checked
  };
}

async function pollHealth() {
  const el = document.getElementById("healthStatus");
  try {
    const res = await fetch(backendUrl() + "/health", { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      el.textContent = "online";
      el.className = "status-ok";
    } else {
      el.textContent = "unreachable";
      el.className = "status-bad";
    }
  } catch (e) {
    el.textContent = "unreachable";
    el.className = "status-bad";
  }
}

async function parseErrorDetail(res) {
  try {
    const body = await res.json();
    return body.detail || res.statusText;
  } catch (e) {
    return res.statusText || ("HTTP " + res.status);
  }
}

async function analyzeRequest(file, useDemo, company) {
  const config = currentConfig();
  const form = new FormData();
  form.append("use_demo", String(useDemo));
  form.append("company", company || "");
  form.append("mode", config.mode);
  form.append("top_k", String(config.topK));
  form.append("use_semantic", String(config.useSemantic));
  if (file) form.append("file", file);

  const res = await fetch(backendUrl() + "/analyze", { method: "POST", body: form });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  lastAnalyzeMode = config.mode;
  return res.json();
}

async function datasetRequest() {
  const config = currentConfig();
  const url = new URL(backendUrl() + "/demo/dataset");
  url.searchParams.set("top_k", config.topK);
  url.searchParams.set("use_semantic", config.useSemantic);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

function disclaimerBannerHtml(result) {
  return (
    '<div class="banner banner-warning">' +
    '<strong>Synthetic evidence corpus:</strong> ' + result.synthetic_evidence_notice +
    '<br>' + result.disclaimer +
    '</div>'
  );
}

function contextStripHtml(result, mode) {
  return (
    '<div class="context-strip">' +
    '<span><strong>Analyzing:</strong> ' + result.source_document + '</span>' +
    '<span><strong>Company:</strong> ' + result.company + '</span>' +
    '<span><strong>Extraction mode:</strong> ' + mode + '</span>' +
    '</div>'
  );
}

function summaryHtml(summary) {
  let html = '<section><h2>Executive summary</h2><div class="kpi-row">';
  const cards = [
    ["Total claims", summary.total_claims],
    ["Checkable", summary.checkable_claims],
    ["Not checkable", summary.not_checkable_claims],
    ["Aligned", summary.align_count],
    ["Contradicted", summary.contradict_count],
    ["Insufficient evidence", summary.insufficient_evidence_count]
  ];
  for (const [label, value] of cards) {
    html += '<div class="kpi-card"><div class="kpi-value">' + value + '</div><div class="kpi-label">' + label + '</div></div>';
  }
  html += '</div>';
  if (summary.average_risk_score !== null) {
    html += (
      '<div class="kpi-card kpi-wide">' +
      '<div class="kpi-value">' + summary.average_risk_score.toFixed(1) + ' / 100</div>' +
      '<div class="kpi-label">Average greenwashing risk score (checkable claims)</div>' +
      '<p class="hint">The risk score is a rule-based triage indicator used to prioritize claims for human review. It is not a probability of greenwashing.</p>' +
      '</div>'
    );
  }
  html += '</section>';
  return html;
}

function verdictBadgeHtml(verdict) {
  const color = VERDICT_COLORS[verdict] || "#6b7280";
  const bg = VERDICT_BG[verdict] || "#eef0f2";
  return '<span class="badge" style="color:' + color + ';background-color:' + bg + '">' + verdict + '</span>';
}

function truncate(text, n) {
  return text.length > n ? text.slice(0, n) + "..." : text;
}

function claimsTableHtml(records, selectedId) {
  if (records.length === 0) return '<p class="hint">No claims to display.</p>';
  let html = '<section><h2>Claim analysis</h2><div class="table-wrap"><table><thead><tr>' +
    '<th>Claim ID</th><th>Claim</th><th>Checkability</th><th>Verification</th><th>Risk score</th><th>Risk band</th>' +
    '</tr></thead><tbody>';
  for (const r of records) {
    const cr = r.checkability_result;
    const vr = r.verification_result;
    const rs = r.risk_score_result;
    const selectedClass = r.claim_id === selectedId ? "row-selected" : "";
    html += '<tr class="' + selectedClass + '" data-claim-id="' + r.claim_id + '">' +
      '<td>' + r.claim_id + '</td>' +
      '<td>' + truncate(r.claim_text, 90) + '</td>' +
      '<td>' + (cr ? cr.checkability : "-") + '</td>' +
      '<td>' + (vr ? verdictBadgeHtml(vr.verdict) : "-") + '</td>' +
      '<td>' + (rs ? rs.risk_score : "-") + '</td>' +
      '<td>' + (rs ? rs.risk_band : "-") + '</td>' +
      '</tr>';
  }
  html += '</tbody></table></div>';
  html += '<div class="claim-select"><label for="claimPicker">Select a claim to inspect in detail</label>' +
    '<select id="claimPicker">';
  for (const r of records) {
    const sel = r.claim_id === selectedId ? "selected" : "";
    html += '<option value="' + r.claim_id + '" ' + sel + '>' + r.claim_id + '</option>';
  }
  html += '</select></div>';
  html += '<div id="claimDetailMount"></div>';
  html += '</section>';
  return html;
}

const TABS = ["Full report", "Checkability", "Evidence", "Verification", "Numerical checks", "Risk score", "Audit trail"];

function claimDetailHtml(record) {
  const cr = record.checkability_result;
  const rr = record.retrieval_result;
  const vr = record.verification_result;
  const rs = record.risk_score_result;

  let html = '<div class="claim-detail">';
  html += '<h3>Claim detail - ' + record.claim_id + '</h3>';
  html += '<p class="claim-text">' + record.claim_text + '</p>';
  html += '<p class="hint">Company: ' + record.company + '</p>';

  html += '<div class="tabs">';
  for (const t of TABS) {
    const cls = t === activeTab ? "tab tab-active" : "tab";
    html += '<button class="' + cls + '" data-tab="' + t + '">' + t + '</button>';
  }
  html += '</div>';

  html += '<div class="tab-panel">';

  if (activeTab === "Full report") {
    html += '<h4>Claim</h4>';
    html += '<p>' + record.claim_text + '</p>';
    html += '<p class="hint">Company: ' + record.company + '</p>';

    html += '<h4>Checkability</h4>';
    if (cr) {
      html += '<p><strong>' + cr.checkability + '</strong> - ' + cr.reason + '</p>';
    } else {
      html += '<p>No checkability result available.</p>';
    }

    if (vr) {
      const color = VERDICT_COLORS[vr.verdict] || "#374151";
      html += '<h4>Verification</h4>';
      html += '<p style="color:' + color + '"><strong>' + vr.verdict + '</strong></p>';
      html += '<p>' + vr.reason + '</p>';
    }

    if (rs) {
      html += '<h4>Risk score</h4>';
      html += '<p>' + rs.risk_score.toFixed(0) + ' / 100 - ' + rs.risk_band + ' risk</p>';
      const topFactors = [...rs.factors].sort((a, b) => b.points - a.points).slice(0, 3);
      for (const f of topFactors) {
        html += '<p>+' + f.points.toFixed(0) + ' pts - <strong>' + f.factor + '</strong>: ' + f.reason + '</p>';
      }
    }

    if (rr && rr.evidence.length > 0) {
      html += '<h4>External evidence found</h4>';
      for (const ev of rr.evidence) {
        const tierLabel = TIER_LABELS[ev.source_tier] || ("Tier " + ev.source_tier);
        html += '<div class="evidence-item">';
        html += '<p><strong>' + ev.source + '</strong> - ' + tierLabel + '</p>';
        html += '<p>' + ev.retrieved_text + '</p>';
        html += '</div>';
      }
    }

    html += '<p class="hint">' + (rs ? rs.disclaimer : "This is a triage indicator for human review, not a legal determination of greenwashing.") + '</p>';
  }

  if (activeTab === "Checkability") {
    if (cr) {
      html += '<p><strong>Claim type:</strong> ' + cr.claim_type + '</p>';
      html += '<p><strong>Checkability:</strong> ' + cr.checkability + '</p>';
      html += '<p><strong>Completeness score:</strong> ' + cr.checkability_completeness.toFixed(0) + '/100</p>';
      html += '<p><strong>Reason:</strong> ' + cr.reason + '</p>';
      if (cr.satisfied_fields.length) {
        html += '<p><strong>Satisfied:</strong> ' + cr.satisfied_fields.map((f) => "checked " + f).join(", ") + '</p>';
      }
      if (cr.missing_fields.length) {
        html += '<p><strong>Missing:</strong> ' + cr.missing_fields.join(", ") + '</p>';
      }
      html += '<details><summary>All rule results</summary><ul>';
      for (const rule of cr.rule_results) {
        const status = rule.passed ? "PASS" : (!rule.applicable ? "N/A" : "FAIL");
        html += '<li>[' + status + '] <strong>' + rule.rule_name + '</strong>: ' + rule.detail + '</li>';
      }
      html += '</ul></details>';
    } else {
      html += '<p>No checkability result available.</p>';
    }
  }

  if (activeTab === "Evidence") {
    if (rr && rr.evidence.length > 0) {
      html += '<p class="hint">Development / synthetic evidence corpus, not real regulatory records.</p>';
      html += '<details><summary>Search queries generated</summary><ul>';
      for (const q of rr.query_plan.queries) html += '<li>' + q + '</li>';
      html += '</ul></details>';
      for (const ev of rr.evidence) {
        const tierLabel = TIER_LABELS[ev.source_tier] || ("Tier " + ev.source_tier);
        html += '<div class="evidence-item">';
        html += '<p><strong>[' + ev.rank + '] ' + ev.source + '</strong>: ' + tierLabel + '</p>';
        html += '<p>' + ev.retrieved_text + '</p>';
        html += '<p class="hint">Publication date: ' + ev.publication_date +
          ' | BM25: ' + ev.bm25_score.toFixed(3) +
          ' | Semantic: ' + ev.semantic_score.toFixed(3) +
          ' | Combined: ' + ev.combined_score.toFixed(3) + '</p>';
        html += '<hr></div>';
      }
    } else if (rr) {
      html += '<p>No evidence retrieved for this claim.</p>';
    } else {
      html += '<p>This claim was not checkable, so no evidence retrieval was run.</p>';
    }
  }

  if (activeTab === "Verification") {
    if (vr) {
      const color = VERDICT_COLORS[vr.verdict] || "#374151";
      html += '<h4 style="color:' + color + '">' + vr.verdict + '</h4>';
      html += '<p><strong>Why:</strong> ' + vr.reason + '</p>';
      html += '<p>Supporting evidence: ' + (vr.supporting_evidence_ids.join(", ") || "none") + '</p>';
      html += '<p>Contradicting evidence: ' + (vr.contradicting_evidence_ids.join(", ") || "none") + '</p>';
      html += '<p>Insufficient or inconclusive evidence: ' + (vr.insufficient_evidence_ids.join(", ") || "none") + '</p>';
      if (vr.highest_authority_tier) {
        html += '<p>Highest-authority source tier used: ' + vr.highest_authority_tier + '</p>';
      }
    } else {
      html += '<p>No verification result (claim not checkable).</p>';
    }
  }

  if (activeTab === "Numerical checks") {
    if (vr && vr.numerical_checks.length > 0) {
      for (const nc of vr.numerical_checks) {
        const status = nc.passed ? "PASS" : (nc.skipped ? "SKIPPED" : "MISMATCH");
        html += '<div class="evidence-item">';
        html += '<p><strong>[' + status + '] ' + nc.check_type + '</strong></p>';
        html += '<div class="numeric-grid"><span>Claimed value: ' + (nc.claim_value ?? "-") + '</span>' +
          '<span>Evidence value: ' + (nc.evidence_value ?? "-") + '</span>' +
          '<span>Tolerance: ' + nc.tolerance_pct + '%</span></div>';
        html += '<p>' + nc.detail + '</p><hr></div>';
      }
    } else {
      html += '<p>No deterministic numerical checks were applicable to this claim.</p>';
    }
  }

  if (activeTab === "Risk score") {
    if (rs) {
      html += '<h4>' + rs.risk_score.toFixed(0) + ' / 100 - ' + rs.risk_band + ' risk</h4>';
      html += '<p>' + rs.summary + '</p>';
      const factors = [...rs.factors].sort((a, b) => b.points - a.points);
      for (const f of factors) {
        html += '<p>+' + f.points.toFixed(0) + ' pts, <strong>' + f.factor + '</strong>: ' + f.reason + '</p>';
      }
      html += '<p class="hint">' + rs.disclaimer + '</p>';
    } else {
      html += '<p>No risk score computed (claim not checkable).</p>';
    }
  }

  if (activeTab === "Audit trail") {
    html += auditTrailHtml(record);
  }

  html += '</div></div>';
  return html;
}

function auditTrailHtml(record) {
  const cr = record.checkability_result;
  const rr = record.retrieval_result;
  const vr = record.verification_result;
  const rs = record.risk_score_result;

  let html = '<p class="hint">Full step-by-step trace of how this result was produced. Nothing below is invented by the frontend, it is the exact backend output for this claim.</p>';

  const step = (title, body) => {
    html += '<div class="audit-step"><strong>' + title + '</strong><div>' + body + '</div></div>';
  };

  step("1. Source document", "Company: " + record.company);
  step("2. Extracted claim", record.claim_text);
  step("3. Checkability decision", cr ? ('<strong>' + cr.checkability + '</strong>: ' + cr.reason) : "Not evaluated.");

  if (rr && rr.query_plan.queries.length > 0) {
    step("4. Search queries generated", '<ul>' + rr.query_plan.queries.map((q) => '<li>' + q + '</li>').join("") + '</ul>');
  } else {
    step("4. Search queries generated", "No queries generated (claim not checkable).");
  }

  step("5. Evidence retrieved", rr && rr.evidence.length > 0 ? (rr.evidence.length + " item(s) retrieved from the synthetic evidence corpus.") : "No evidence retrieved.");

  if (rr && rr.evidence.length > 0) {
    let table = '<table class="mini-table"><thead><tr><th>Rank</th><th>Evidence ID</th><th>BM25</th><th>Semantic</th><th>Combined</th></tr></thead><tbody>';
    for (const ev of rr.evidence) {
      table += '<tr><td>' + ev.rank + '</td><td>' + ev.evidence_id + '</td><td>' + ev.bm25_score.toFixed(3) +
        '</td><td>' + ev.semantic_score.toFixed(3) + '</td><td>' + ev.combined_score.toFixed(3) + '</td></tr>';
    }
    table += '</tbody></table>';
    step("6. Evidence ranking", table);
  } else {
    step("6. Evidence ranking", "No ranking to show.");
  }

  if (vr && vr.numerical_checks.length > 0) {
    const items = vr.numerical_checks.map((nc) => {
      const status = nc.passed ? "PASS" : (nc.skipped ? "SKIPPED" : "MISMATCH");
      return '<li>[' + status + '] ' + nc.check_type + ': ' + nc.detail + '</li>';
    }).join("");
    step("7. Numerical checks", '<ul>' + items + '</ul>');
  } else {
    step("7. Numerical checks", "No numerical checks were applicable.");
  }

  step("8. Verification", vr ? ('<strong>' + vr.verdict + '</strong>: ' + vr.reason) : "Not applicable.");

  if (rs && rs.factors.length > 0) {
    const factors = [...rs.factors].sort((a, b) => b.points - a.points);
    const items = factors.map((f) => '<li>+' + f.points.toFixed(0) + ' pts, ' + f.factor + ': ' + f.reason + '</li>').join("");
    step("9. Risk factors", '<ul>' + items + '</ul>');
  } else {
    step("9. Risk factors", "No risk factors (claim not checkable).");
  }

  step("10. Final score", rs ? (rs.risk_score.toFixed(0) + ' / 100, ' + rs.risk_band + ' risk') : "No score computed.");

  html += '<button id="rawJsonBtn" class="link-button">Show raw audit record (JSON)</button>';
  html += '<pre id="rawJsonBox" style="display:none;"></pre>';

  setTimeout(() => {
    const btn = document.getElementById("rawJsonBtn");
    const box = document.getElementById("rawJsonBox");
    if (!btn) return;
    btn.addEventListener("click", () => {
      const showing = box.style.display !== "none";
      box.style.display = showing ? "none" : "block";
      btn.textContent = showing ? "Show raw audit record (JSON)" : "Hide raw audit record (JSON)";
      if (!showing) box.textContent = JSON.stringify(record, null, 2);
    });
  }, 0);

  return html;
}

function renderClaimsSection(mount, records, selectedId, onSelect) {
  mount.innerHTML = claimsTableHtml(records, selectedId);
  mount.querySelectorAll("tbody tr").forEach((row) => {
    row.addEventListener("click", () => onSelect(row.getAttribute("data-claim-id")));
  });
  const picker = document.getElementById("claimPicker");
  if (picker) {
    picker.addEventListener("change", (e) => onSelect(e.target.value));
  }
  const detailMount = document.getElementById("claimDetailMount");
  const record = records.find((r) => r.claim_id === selectedId) || records[0];
  if (detailMount && record) {
    detailMount.innerHTML = claimDetailHtml(record);
    detailMount.querySelectorAll(".tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        activeTab = btn.getAttribute("data-tab");
        detailMount.innerHTML = claimDetailHtml(record);
        attachTabHandlers(detailMount, record);
      });
    });
  }
}

function attachTabHandlers(mount, record) {
  mount.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeTab = btn.getAttribute("data-tab");
      mount.innerHTML = claimDetailHtml(record);
      attachTabHandlers(mount, record);
    });
  });
}

function renderAnalyzeResults(result) {
  const mount = document.getElementById("analyzeResults");
  if (!result) {
    mount.innerHTML = "";
    return;
  }
  let html = "<hr>" + contextStripHtml(result, lastAnalyzeMode) + disclaimerBannerHtml(result);
  if (result.status === "no_claims") {
    html += '<div class="banner banner-error">' + result.message;
    if (result.extraction_errors && result.extraction_errors.length) {
      html += '<details><summary>Extraction details</summary><ul>' +
        result.extraction_errors.map((e) => '<li>' + e + '</li>').join("") + '</ul></details>';
    }
    html += '</div>';
    mount.innerHTML = html;
    return;
  }
  html += summaryHtml(result.summary);
  mount.innerHTML = html;

  const claimsMount = document.createElement("div");
  mount.appendChild(claimsMount);
  if (!selectedAnalyzeClaim && result.audit_records.length) {
    selectedAnalyzeClaim = result.audit_records[0].claim_id;
  }
  renderClaimsSection(claimsMount, result.audit_records, selectedAnalyzeClaim, (id) => {
    selectedAnalyzeClaim = id;
    activeTab = "Checkability";
    renderAnalyzeResults(result);
  });
}

function renderDatasetResults(result) {
  const mount = document.getElementById("datasetResults");
  if (!result) {
    mount.innerHTML = "";
    return;
  }
  let html = "<hr>" + contextStripHtml(result, "n/a (curated dataset, no extraction)") + disclaimerBannerHtml(result);
  html += summaryHtml(result.summary);
  mount.innerHTML = html;

  const claimsMount = document.createElement("div");
  mount.appendChild(claimsMount);
  if (!selectedDatasetClaim && result.audit_records.length) {
    selectedDatasetClaim = result.audit_records[0].claim_id;
  }
  renderClaimsSection(claimsMount, result.audit_records, selectedDatasetClaim, (id) => {
    selectedDatasetClaim = id;
    activeTab = "Checkability";
    renderDatasetResults(result);
  });
}

function setupPageSwitch() {
  document.querySelectorAll('input[name="page"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      const page = document.querySelector('input[name="page"]:checked').value;
      document.getElementById("analyzePage").style.display = page === "analyze" ? "block" : "none";
      document.getElementById("datasetPage").style.display = page === "dataset" ? "block" : "none";
    });
  });
}

function setupTopKDisplay() {
  const range = document.getElementById("topKRange");
  const label = document.getElementById("topKValue");
  range.addEventListener("input", () => {
    label.textContent = range.value;
  });
}

function setupAnalyze() {
  const fileInput = document.getElementById("pdfFile");
  const useDemoInput = document.getElementById("useDemo");
  const fileInfo = document.getElementById("fileInfo");
  const btn = document.getElementById("analyzeBtn");
  const status = document.getElementById("analyzeStatus");

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file) {
      fileInfo.style.display = "block";
      fileInfo.textContent = "File: " + file.name + " (" + (file.size / 1024).toFixed(1) + " KB)";
    } else {
      fileInfo.style.display = "none";
    }
  });

  btn.addEventListener("click", async () => {
    const file = fileInput.files[0] || null;
    const useDemo = useDemoInput.checked;
    const company = document.getElementById("companyInput").value;
    if (!file && !useDemo) return;

    btn.disabled = true;
    status.style.display = "block";
    status.textContent = "Running pipeline: parsing, extraction, checkability, retrieval, verification, risk scoring...";
    document.getElementById("analyzeResults").innerHTML = "";

    try {
      const result = await analyzeRequest(file, useDemo, company);
      lastAnalyzeResult = result;
      selectedAnalyzeClaim = null;
      activeTab = "Checkability";
      status.style.display = "none";
      renderAnalyzeResults(result);
    } catch (e) {
      status.style.display = "none";
      document.getElementById("analyzeResults").innerHTML =
        '<div class="banner banner-error">Analysis failed: ' + e.message + '</div>';
    } finally {
      btn.disabled = false;
    }
  });
}

function setupDataset() {
  const btn = document.getElementById("datasetBtn");
  const status = document.getElementById("datasetStatus");

  btn.addEventListener("click", async () => {
    btn.disabled = true;
    status.style.display = "block";
    status.textContent = "Running pipeline over the curated dataset...";
    document.getElementById("datasetResults").innerHTML = "";

    try {
      const result = await datasetRequest();
      lastDatasetResult = result;
      selectedDatasetClaim = null;
      activeTab = "Checkability";
      status.style.display = "none";
      renderDatasetResults(result);
    } catch (e) {
      status.style.display = "none";
      document.getElementById("datasetResults").innerHTML =
        '<div class="banner banner-error">Dataset demo failed: ' + e.message + '</div>';
    } finally {
      btn.disabled = false;
    }
  });
}

setupPageSwitch();
setupTopKDisplay();
setupAnalyze();
setupDataset();
pollHealth();
setInterval(pollHealth, 8000);
document.getElementById("backendUrl").addEventListener("change", pollHealth);
