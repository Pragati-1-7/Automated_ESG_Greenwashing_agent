# Architecture (v2)

```mermaid
flowchart TD
    PDF[ESG report PDF] --> ING[Ingest: PyMuPDF layout parsing]
    ING --> RES[Resolver agent: registry tool + Jev same-entity]
    RES --> EXT[Extractor agent: Jev is-claim + metric, per sentence]
    EXT --> TRI[Triage agent: Jev A3CG action, vagueness, materiality]
    TRI -->|not checkable| AGG
    TRI -->|Send, one per checkable claim| SUB
    subgraph SUB [Per-claim sub-graph, runs in parallel]
      DEC[Decomposer: atomic sub-claims, Jev check type] --> ROU[Router: Jev P(source useful) x 8]
      ROU --> INV[Investigator: source tools + calculator, Jev 'sufficient?', widen once]
      INV --> JUD[Judge: Jev relevance gate + stance per evidence and sub-claim]
      JUD --> VER[Verdict: Jev ALIGN / CONTRADICT / INSUFFICIENT + severity, citation validator]
    end
    INV <-->|HTTP| MS[(mock_sources: BRSR, OCEMS, NGT/SPCB, GFW alerts, RECs, assurance, news)]
    SUB --> AGG[Risk aggregator: fitted logistic weights]
    AGG --> REP[Reporter: summary + audit trail]
    REP --> UI[React UI via SSE]
```

## Principles

1. **Decisions are typed questions, not parsed prose.** Every judgement is a Jev Noul / Choice / Score with probabilities. Question texts live in `app/agents/prompts.py` (versioned).
2. **Tools fetch and compute, agents decide.** Builders in `app/agents/evidence.py` fetch through `app/tools/sources.py`, format citeable evidence and call `app/tools/calculator.py`. They never decide truth.
3. **Everything is observable.** Every step emits an `AgentEvent`. These are streamed over SSE and form the audit trail.
4. **Everything is reproducible.** Decision-engine answers are cassette-recorded (`data/cassettes/jev/`), so `JEV_MODE=replay` reruns any recorded analysis offline.
5. **Functional modules.** Agents are `async` functions over pydantic models. The graph file only wires them, and ablation switches (`app/core/ablation.py`) let the evaluation turn single components off.

## Why not A2A?

All agents are owned and deployed together in one process, so the Agent2Agent protocol would add network hops and failure modes without value. Interoperability is offered where it matters: the data sources are an MCP server (`mock_sources/mcp_server.py`).
