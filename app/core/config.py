"""Runtime configuration (environment variables / .env). One place, typed."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")


class Settings(BaseModel):
    # Decision engine (TypeSafe Jev)
    typesafe_api_key: str | None = None
    typesafe_base_url: str = "https://api.typesafe.ai/v1/systemone"
    jev_model: str = "jev-latest"
    # live   = call Jev, write every answer into the cassette store (default)
    # replay = never touch the network; answers must already be in the store (tests / offline demo)
    # off    = no decision engine (system reports it cannot decide)
    jev_mode: str = "live"
    jev_cassette_dir: Path = ROOT / "data" / "cassettes" / "jev"
    jev_concurrency: int = 12

    # Generative LLM slot: "mock" (deterministic, default) or "groq"
    llm_provider: str = "mock"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"

    # External data services
    mock_sources_url: str = "inproc"   # "inproc" = mount mock_sources ASGI app in-process; else http URL

    # Pipeline limits
    max_claims: int = 40
    max_investigation_rounds: int = 2
    data_dir: Path = ROOT / "data"


@lru_cache(maxsize=1)
def settings() -> Settings:
    e = os.environ.get
    return Settings(
        typesafe_api_key=e("TYPESAFE_API_KEY") or e("JEV_API_KEY"),
        typesafe_base_url=e("TYPESAFE_BASE_URL", "https://api.typesafe.ai/v1/systemone"),
        jev_model=e("JEV_MODEL", "jev-latest"),
        jev_mode=e("JEV_MODE", "live"),
        jev_cassette_dir=Path(e("JEV_CASSETTE_DIR", str(ROOT / "data" / "cassettes" / "jev"))),
        jev_concurrency=int(e("JEV_CONCURRENCY", "12")),
        llm_provider=e("LLM_PROVIDER", "mock"),
        groq_api_key=e("GROQ_API_KEY"),
        groq_model=e("GROQ_MODEL", "openai/gpt-oss-120b"),
        mock_sources_url=e("MOCK_SOURCES_URL", "inproc"),
        max_claims=int(e("MAX_CLAIMS", "40")),
        max_investigation_rounds=int(e("MAX_INVESTIGATION_ROUNDS", "2")),
    )
