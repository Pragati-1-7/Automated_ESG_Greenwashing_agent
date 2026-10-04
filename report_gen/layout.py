"""HTML building blocks (Jinja-free). All helpers return HTML strings."""
from __future__ import annotations
import html
from pathlib import Path
from string import Template

TEMPLATES = Path(__file__).parent / "templates"


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def p(t: str) -> str:
    return f"<p>{t}</p>\n"


def stmt(t: str) -> str:
    """Full-width paragraph (column-span: all). Claim sentences always live in these so that
    text extractors read them as a single un-interleaved line sequence."""
    return f'<p class="stmt">{t}</p>\n'


def h3(t: str) -> str:
    return f"<h3>{t}</h3>\n"


def ul(items) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def callout(title: str, body: str = "", items=None) -> str:
    inner = f"<h4>{title}</h4>"
    if body:
        inner += f"<p>{body}</p>"
    if items:
        inner += ul(items)
    return f'<div class="callout">{inner}</div>\n'


def pull(text: str, cite: str = "") -> str:
    c = f"<cite>{cite}</cite>" if cite else ""
    return f'<blockquote class="pull">{text}{c}</blockquote>\n'


def figure(src: str, caption: str, wide: bool = True, num: str = "") -> str:
    cls = ' class="wide"' if wide else ""
    return f'<figure{cls}><img src="{src}" alt=""><figcaption><b>{num}</b> {caption}</figcaption></figure>\n'


def kpis(items) -> str:
    return '<div class="kpis">' + "".join(f"<div><b>{v}</b>{l}</div>" for v, l in items) + "</div>\n"


def table(cap: str, headers, rows, src: str = "", aligns=None, widths=None) -> str:
    n = len(headers)
    aligns = aligns or ["l"] + ["r"] * (n - 1)
    th = "".join(f'<th class="{a}">{h}</th>' for h, a in zip(headers, aligns))
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f'<td class="{a}">{c}</td>' for c, a in zip(r, aligns)) + "</tr>"
    s = f'<div class="span tbl"><div class="cap">{cap}</div><table class="data"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'
    if src:
        s += f'<div class="src">{src}</div>'
    return s + "</div>\n"


def notes(items) -> str:
    return '<div class="notes"><b>Notes</b><ol>' + "".join(f"<li>{i}</li>" for i in items) + "</ol></div>\n"


def chapter(num: str, title: str, subtitle: str, body: str, raw: bool = False, cls: str = "") -> str:
    head = (f'<div class="chap-head"><div class="num">{num}</div><div class="tt"><div class="kick">SECTION {num}</div>'
            f'<h1>{title}</h1><div class="st">{subtitle}</div></div></div>')
    inner = body if raw else f'<div class="cols">{body}</div>'
    return f'<section class="chapter {cls}">{head}{inner}</section>\n'


def toc(entries, groups=None) -> str:
    """entries: list of (num, title, page)."""
    out = '<section class="toc"><h1>Contents</h1><ol>'
    for num, title, page in entries:
        if groups and num in groups:
            out += f'</ol><div class="grp">{groups[num]}</div><ol>'
        out += f'<li><span class="n">{num}</span><span class="t">{title}</span><span class="pg">{page}</span></li>'
    return out + "</ol></section>\n"


def cover(ctx, art_url: str) -> str:
    return f'''<section class="cover"><img class="art" src="{art_url}" alt="">
<div class="top"><span>{ctx.kicker_top}</span></div>
<div class="block"></div>
<div class="ttl"><div class="kick">{ctx.cover_kicker}</div><h1>{ctx.cover_title}</h1><div class="sub">{ctx.cover_sub}</div></div>
<div class="meta"><span>{ctx.name}<br>{ctx.cover_addr}</span><span style="text-align:right">Reporting period 1 April 2024 to 31 March 2025<br>BRSR Core | GRI 2021 | TCFD</span></div></section>\n'''


def back_cover(ctx, art_url: str) -> str:
    return f'''<section class="back"><img src="{art_url}" alt="">
<div class="txt"><h2>{ctx.name}</h2>{ctx.back_text}</div>
<div class="fic">Fictional company. Generated for an academic ESG verification demo.</div></section>\n'''


def render_css(ctx) -> str:
    t = Template((TEMPLATES / "report.css").read_text())
    def q(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')
    pal = ctx.pal
    return t.substitute(brand=pal["brand"], dark=pal["dark"], mid=pal["mid"], tint=pal["tint"], tint2=pal["tint2"],
                        sec=pal["sec"], hdr_left=q(ctx.plain_name), hdr_right=q(ctx.hdr_title),
                        ftr_left=q(ctx.ftr_left))


def document(ctx, body: str) -> str:
    return (f'<!doctype html><html lang="en-IN"><head><meta charset="utf-8"><title>{esc(ctx.plain_title)}</title>'
            f'<style>{render_css(ctx)}</style></head><body>{body}</body></html>')
