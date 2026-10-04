"""Shared test setup: every decision-engine (Jev) answer is REPLAYED from the
recorded cassette in data/cassettes/jev/. No network, no API key needed."""

import os

os.environ["JEV_MODE"] = "replay"
os.environ.pop("TYPESAFE_API_KEY", None)
os.environ.pop("JEV_API_KEY", None)
os.environ["LLM_PROVIDER"] = "mock"
os.environ["MOCK_SOURCES_URL"] = "inproc"
