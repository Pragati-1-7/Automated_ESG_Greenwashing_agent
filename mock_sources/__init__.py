"""mock_sources: a stand-alone FastAPI service that imitates external ESG data
providers (SEBI BRSR filings, CPCB OCEMS, NGT/SPCB orders, GFW forest alerts,
REC registry, assurance statements and a news wire). Agents reach evidence ONLY
through this service. All data is synthetic (see data_gen/)."""
