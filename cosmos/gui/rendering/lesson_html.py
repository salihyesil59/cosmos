"""Convert lesson Markdown into Qt rich-text HTML.

Supported syntax on top of standard Markdown:

``$$ ... $$``            display formula (matplotlib mathtext)
``$ ... $``              inline formula
``[[key]]``              link to a glossary term (``[[key|shown text]]``)
``:::note Title``        callout box, closed by a line containing ``:::``
                         kinds: note, tip, key, warning, history, example, math
                         (``math`` marks a derivation, hidden in the intuitive view)
``:::try S1 Text``       single-line "Try it" link to a simulator
``{{figure:name}}``      figure drawn by :mod:`cosmos.gui.rendering.figures`
``[text](lesson:L1.2)``  link to another lesson
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

import markdown

from cosmos.gui.rendering import math as mathrender
from cosmos.gui.theme import Palette

SCREEN_PT_TO_PX = 96 / 72

_TRY = re.compile(r"^:::try[ \t]+(S\d+)[ \t]*(.*)$", re.MULTILINE)
_CALLOUT = re.compile(r"^:::(\w+)[ \t]*(.*?)\n(.*?)^:::[ \t]*$", re.MULTILINE | re.DOTALL)
_FIGURE = re.compile(r"^\{\{figure:(\w+)\}\}[ \t]*$", re.MULTILINE)
_DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_INLINE_MATH = re.compile(r"(?<![\\$])\$(?!\$)((?:[^$\\]|\\.)+?)\$")
# Proportional line height would also scale images, so image blocks use 100%.
_BLOCK_P = '<p align="center" style="line-height:100%; margin-top:10px; margin-bottom:10px;">'
_GLOSSARY = re.compile(r"\[\[([\w-]+)(?:\|([^\]]+))?\]\]")

CALLOUT_STYLES = {
    "note": ("accent", "Note"),
    "tip": ("success", "Tip"),
    "key": ("accent2", "Key idea"),
    "warning": ("danger", "Common misconception"),
    "history": ("warning", "History"),
    "example": ("accent", "Worked example"),
    "math": ("accent2", "The mathematics"),
    "try": ("accent", "Try it"),
}

# Callouts that carry the mathematical detail; hidden in the intuitive view (G7).
MATH_CALLOUTS = ("math", "example")
FULL_VIEW, INTUITIVE_VIEW = "full", "intuitive"


@dataclass
class RenderedDocument:
    html: str
    images: dict[str, bytes] = field(default_factory=dict)  # url -> PNG
    sizes: dict[str, tuple[int, int]] = field(default_factory=dict)
    hidden_formulas: int = 0     # display formulas left out of the intuitive view
    hidden_blocks: int = 0       # derivations and worked examples left out


@dataclass
class RenderContext:
    palette: Palette
    font_pt: float = 11.0
    device_ratio: float = 1.0
    simulator_titles: dict[str, str] = field(default_factory=dict)
    glossary_terms: dict[str, str] = field(default_factory=dict)
    math_view: str = FULL_VIEW    # FULL_VIEW shows every formula, INTUITIVE_VIEW hides them


def _with_article(title: str) -> str:
    """"the Cosmology Calculator", but "The Far Future" rather than "the The Far Future"."""
    return title if title.lower().startswith("the ") else f"the {title}"


class _Renderer:
    def __init__(self, ctx: RenderContext):
        self.ctx = ctx
        self.doc = RenderedDocument(html="")
        self._blocks: dict[str, str] = {}
        self.intuitive = ctx.math_view == INTUITIVE_VIEW

    # -------------------------------------------------------------- tokens
    def _token(self, html_fragment: str) -> str:
        token = f"CSMTOKEN{len(self._blocks)}Z"
        self._blocks[token] = html_fragment
        return token

    def _math_img(self, tex: str, display: bool) -> str:
        p = self.ctx.palette
        size = self.ctx.font_pt * (1.2 if display else 1.0)
        tex = " ".join(tex.split())
        try:
            png = mathrender.render_png(tex, p.text, size, self.ctx.device_ratio)
        except mathrender.MathError:
            return f'<code style="color:{p.danger}">{html.escape(tex)}</code>'
        url = f"math:{len(self.doc.images)}"
        return self._image(url, png, 'style="vertical-align: middle"' if not display else "")

    def _image(self, url: str, png: bytes, extra: str = "") -> str:
        from PySide6.QtGui import QImage

        img = QImage.fromData(png, "PNG")
        ratio = self.ctx.device_ratio
        w, h = round(img.width() / ratio), round(img.height() / ratio)
        self.doc.images[url] = png
        self.doc.sizes[url] = (w, h)
        return f'<img src="{url}" width="{w}" height="{h}" {extra}/>'

    # ------------------------------------------------------------ elements
    def _callout(self, kind: str, title: str, inner_html: str) -> str:
        p = self.ctx.palette
        color_attr, default_title = CALLOUT_STYLES.get(kind, CALLOUT_STYLES["note"])
        color = getattr(p, color_attr)
        bg = p.mix(color, 0.12)
        heading = html.escape(title.strip() or default_title)
        return (
            f'<table width="100%" cellspacing="0" cellpadding="0" '
            f'style="margin-top:10px; margin-bottom:10px; background-color:{bg};">'
            f'<tr><td width="5" style="background-color:{color};"></td>'
            f'<td style="padding:10px 14px 10px 14px;">'
            f'<p style="margin:0 0 4px 0;"><b style="color:{color};">{heading}</b></p>'
            f"{inner_html}</td></tr></table>"
        )

    def _try_block(self, sim_id: str, text: str) -> str:
        p = self.ctx.palette
        title = self.ctx.simulator_titles.get(sim_id, sim_id)
        body = self._inline_markdown(text) if text else ""
        link = (
            f'<p style="margin:6px 0 0 0;"><a href="sim:{sim_id}" style="color:{p.link}; '
            f'text-decoration:none;"><b>▶ Open {html.escape(_with_article(title))}</b></a></p>'
        )
        return self._callout("try", f"Try it: {title}", f"<p style='margin:0;'>{body}</p>{link}")

    def _figure(self, name: str) -> str:
        from cosmos.gui.rendering import figures      # E12: matplotlib, only when needed

        png = figures.render_png(name, self.ctx.palette, self.ctx.device_ratio)
        return f'{_BLOCK_P}{self._image(f"figure:{name}", png)}</p>'

    def _inline_markdown(self, text: str) -> str:
        out = markdown.markdown(self._prepare(text))
        out = re.sub(r"^<p>(.*)</p>$", r"\1", out.strip(), flags=re.DOTALL)
        return self._restore(out)

    # ------------------------------------------------------------ pipeline
    def _prepare(self, text: str) -> str:
        p = self.ctx.palette
        text = _TRY.sub(lambda m: "\n" + self._token(self._try_block(m.group(1), m.group(2))) + "\n", text)
        text = _CALLOUT.sub(self._callout_match, text)
        text = _FIGURE.sub(lambda m: "\n" + self._token(self._figure(m.group(1))) + "\n", text)
        text = _DISPLAY_MATH.sub(self._display_math_match, text)
        text = _INLINE_MATH.sub(lambda m: self._token(self._math_img(m.group(1), False)), text)

        def glossary_link(m):
            key, shown = m.group(1), m.group(2) or m.group(1).replace("-", " ")
            tip = html.escape(self.ctx.glossary_terms.get(key, ""), quote=True)
            return self._token(
                f'<a href="glossary:{key}" title="{tip}" style="color:{p.accent2}; '
                f'text-decoration:none;">{html.escape(shown)}</a>'
            )

        return _GLOSSARY.sub(glossary_link, text)

    def _callout_match(self, match: re.Match) -> str:
        kind = match.group(1)
        if self.intuitive and kind in MATH_CALLOUTS:
            self.doc.hidden_blocks += 1
            return "\n"
        body = self._render_fragment(match.group(3))
        return "\n" + self._token(self._callout(kind, match.group(2), body)) + "\n"

    def _display_math_match(self, match: re.Match) -> str:
        if self.intuitive:
            self.doc.hidden_formulas += 1
            return "\n\n"
        return "\n\n" + self._token(f'{_BLOCK_P}{self._math_img(match.group(1), True)}</p>') + "\n\n"

    def _render_fragment(self, text: str) -> str:
        out = markdown.markdown(self._prepare(text), extensions=["tables", "sane_lists"])
        return self._restore(out)

    def _restore(self, out: str) -> str:
        # Block tokens that markdown wrapped in a paragraph.
        for _ in range(3):  # tokens may nest (callouts containing formulas)
            for token, fragment in self._blocks.items():
                out = out.replace(f"<p>{token}</p>", fragment).replace(token, fragment)
        return out

    def render(self, text: str) -> RenderedDocument:
        body = self._render_fragment(text.replace("\r\n", "\n"))
        p = self.ctx.palette
        body = body.replace(
            "<table>",
            f'<table class="data" cellspacing="0" cellpadding="6" border="1" '
            f'style="border-color:{p.border}; margin-top:8px; margin-bottom:8px;">',
        )
        self.doc.html = f"<html><body>{body}</body></html>"
        return self.doc


def render_markdown(text: str, ctx: RenderContext) -> RenderedDocument:
    return _Renderer(ctx).render(text)


def stylesheet(palette: Palette, font_pt: float = 11.0) -> str:
    p = palette
    return f"""
    body {{ color: {p.text}; font-size: {font_pt}pt; }}
    h1 {{ font-size: {font_pt * 1.9:.1f}pt; font-weight: 600; margin-top: 4px; margin-bottom: 10px; }}
    h2 {{ font-size: {font_pt * 1.4:.1f}pt; font-weight: 600; color: {p.accent};
          margin-top: 22px; margin-bottom: 6px; }}
    h3 {{ font-size: {font_pt * 1.15:.1f}pt; font-weight: 600; margin-top: 16px; margin-bottom: 4px; }}
    p {{ margin-top: 6px; margin-bottom: 6px; line-height: 145%; }}
    li {{ margin-bottom: 4px; line-height: 140%; }}
    a {{ color: {p.link}; text-decoration: none; }}
    code {{ font-family: Consolas, 'Courier New', monospace; background-color: {p.surface_alt}; }}
    th {{ background-color: {p.surface_alt}; font-weight: 600; }}
    td, th {{ border-color: {p.border}; }}
    hr {{ color: {p.border}; }}
    """
