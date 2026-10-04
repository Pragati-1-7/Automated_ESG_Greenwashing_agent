"""Per-report build context."""
from __future__ import annotations
from pathlib import Path
from . import data
from .layout import esc

BUILD = Path(__file__).parent / "_build"


class Ctx:
    def __init__(self, key: str):
        self.key = key
        self.co = data.company(key)
        self.pal = data.palette(key, self.co["brand_colour"])
        self.plain_name = self.co["name"]
        self.name = esc(self.co["name"])
        self.short = esc(self.co["short_name"])
        self.plain_title = self.co["report_title"]
        head, _, tail = self.plain_title.partition(": ")
        self.cover_kicker = esc(head)
        self.cover_title = esc(tail)
        self.hdr_title = head
        self.cover_sub = self.name
        self.kicker_top = "Sustainability disclosure"
        self.cover_addr = f"{esc(self.co['hq_city'])}, {esc(self.co['hq_state'])} | {esc(self.co['listing'])}"
        self.ftr_left = f"{self.co['short_name']} | Fictional company, academic demonstration"
        self.back_text = ""
        self.dir = BUILD / key
        self.imgdir = self.dir / "img"
        self.imgdir.mkdir(parents=True, exist_ok=True)
        self.used_claims: list[str] = []
        self.t = self.co.get("true")

    # ----- claims -----
    def claim(self, cid: str) -> str:
        """Verbatim claim sentence (HTML-escaped; spec claims contain no markup characters)."""
        self.used_claims.append(cid)
        import re
        txt = esc(data.claim_text(self.co, cid))
        # keep hyphenated tokens on one line so text extractors never see a line-end hyphen break
        return re.sub(r"(\S*\w-\w\S*)", r'<span style="white-space:nowrap">\1</span>', txt)

    def check_claims_used(self):
        want = [c["id"] for c in self.co["claims"]]
        missing = [c for c in want if c not in self.used_claims]
        dup = {c for c in self.used_claims if self.used_claims.count(c) > 1}
        if missing or dup:
            raise RuntimeError(f"{self.key}: claims missing={missing} duplicated={sorted(dup)}")

    # ----- images -----
    def img(self, name: str) -> str:
        return (self.imgdir / name).as_uri()

    def path(self, name: str) -> str:
        return str(self.imgdir / name)

    @property
    def fy(self):
        return data.YLAB
