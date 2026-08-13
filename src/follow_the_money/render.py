"""Deterministic Chinese Markdown renderer (task 10.3/10.4).

Design section 16:

- Fixed heading order: 市场仪表盘, 市场状态, 重点事件, 其他重要事件,
  conditional 资金流与持仓, 未来 24 小时关注, 结论.
- Every text fragment is treated as a text node: ``& < >`` become HTML
  entities, then every remaining ASCII punctuation code point in the four
  ranges ``U+0021-002F``, ``U+003A-0040``, ``U+005B-0060``, ``U+007B-007E``
  receives a backslash. This neutralizes fences, setext markers, links, and
  raw HTML; no input-supplied Markdown/link syntax is emitted.
- Only renderer-owned fixed-label HTTPS links may be emitted.
- Rejects ``Cc``/``Cf``/``Cs``/``Zl``/``Zp`` (incl. bidi/zero-width/U+2028/29)
  and collapses whitespace to one ASCII space.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .unicode import validate_prose

HEADING_ORDER = (
    "市场仪表盘",
    "市场状态",
    "重点事件",
    "其他重要事件",
    "资金流与持仓",
    "未来 24 小时关注",
    "结论",
)

_ENTITY = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}

_PUNCT_RANGES = (
    (0x21, 0x2F),
    (0x3A, 0x40),
    (0x5B, 0x60),
    (0x7B, 0x7E),
)


class RenderError(ValueError):
    """Rendering failed closed."""


def escape_text_node(text: str) -> str:
    """Escape one text fragment as a Markdown-safe text node."""
    cleaned = validate_prose(text, where="text-node")
    out: list[str] = []
    for ch in cleaned:
        if ch in _ENTITY:
            out.append(_ENTITY[ch])
            continue
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in _PUNCT_RANGES):
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _heading(level: int, text: str) -> str:
    cleaned = validate_prose(text, where="heading")
    return f"{'#' * level} {cleaned}"


_CREDENTIAL_URL_PARAMS = re.compile(
    r"[?&](token|api_key|apikey|key|secret|password|sig|signature|auth)=", re.IGNORECASE
)


def render_link(label: str, url: str) -> str:
    """Renderer-owned fixed-label HTTPS link.

    Only credential-free https targets may be emitted; query parameters that
    look like credentials are rejected.
    """
    if not url.startswith("https://"):
        raise RenderError("links must be https")
    if _CREDENTIAL_URL_PARAMS.search(url):
        raise RenderError("links must not carry credential material")
    cleaned_label = escape_text_node(label)
    # Percent-encode unsafe URL characters for the target.
    safe = re.sub(
        r"[^A-Za-z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]", lambda m: f"%{ord(m.group(0)):02X}", url
    )
    return f"[{cleaned_label}]({safe})"


def render_dashboard(roles: Sequence[Mapping[str, Any]]) -> str:
    lines = [_heading(2, HEADING_ORDER[0])]
    if not roles:
        lines.append("- 暂无可用数据")
        return "\n".join(lines) + "\n"
    for role in roles:
        display = escape_text_node(role.get("display", role.get("role_id", "")))
        available = role.get("available", False)
        if not available:
            lines.append(f"- {display}：不可用")
            continue
        ret = role.get("return_pct")
        yield_change = role.get("yield_change_bps")
        anomaly = role.get("anomalous")
        parts = [f"- {display}"]
        if ret is not None:
            parts.append(f"：{ret}%")
        elif yield_change is not None:
            parts.append(f"：{yield_change} bp")
        if anomaly:
            parts.append(" **异常波动**")
        if role.get("representative_link"):
            parts.append(f"（{render_link('来源', role['representative_link'])}）")
        lines.append("".join(parts))
    return "\n".join(lines) + "\n"


def render_market_state(state: Mapping[str, Any]) -> str:
    lines = [_heading(2, HEADING_ORDER[1])]
    regime = state.get("regime", "unknown")
    label = {
        "risk_on": "风险偏好",
        "neutral": "中性",
        "risk_off": "风险规避",
        "unknown": "未知",
    }.get(regime, regime)
    lines.append(f"- 市场状态：{label}")
    vector = state.get("vector", {})
    for dim in ("risk_appetite", "rates", "liquidity", "growth", "inflation"):
        v = vector.get(dim, "unknown")
        zh = {
            "risk_appetite": "风险偏好",
            "rates": "利率",
            "liquidity": "流动性",
            "growth": "增长",
            "inflation": "通胀",
        }[dim]
        vzh = {"supportive": "支撑", "neutral": "中性", "adverse": "压制", "unknown": "未知"}.get(
            v, v
        )
        lines.append(f"  - {zh}：{vzh}")
    explanation = state.get("explanation")
    if explanation:
        lines.append(f"- 说明：{escape_text_node(explanation)}")
    return "\n".join(lines) + "\n"


def render_events(full: Sequence[Mapping[str, Any]], compact: Sequence[Mapping[str, Any]]) -> str:
    out: list[str] = []
    if full:
        out.append(_heading(2, HEADING_ORDER[2]))
        for e in full:
            out.append(_render_full_event(e))
    if compact:
        out.append(_heading(2, HEADING_ORDER[3]))
        for e in compact:
            out.append(_render_compact_event(e))
    if not full and not compact:
        out.append(_heading(2, HEADING_ORDER[2]))
        out.append("- 暂无符合质量门槛的事件")
    return "\n".join(out) + "\n"


def _render_full_event(e: Mapping[str, Any]) -> str:
    label = escape_text_node(e.get("display_label", e.get("event_id", "")))
    lines = [_heading(3, label)]
    confidence = e.get("confidence", "unresolved")
    lines.append(f"- 置信度：{confidence}")
    for field, heading in (
        ("fact_summary", "事实摘要"),
        ("why_it_matters", "为何重要"),
        ("reaction_attribution", "市场反应"),
        ("price_in", "定价状态"),
        ("money_flow", "资金流"),
        ("asset_mappings", "资产影响"),
        ("alternative", "替代解读"),
        ("uncertainty", "不确定性"),
    ):
        value = e.get(field)
        if value:
            lines.append(f"- {heading}：{escape_text_node(value)}")
    links = e.get("source_links", [])
    if links:
        lines.append("- 来源：" + "；".join(render_link("来源", u) for u in links))
    return "\n".join(lines)


def _render_compact_event(e: Mapping[str, Any]) -> str:
    label = escape_text_node(e.get("display_label", e.get("event_id", "")))
    lines = [_heading(3, label)]
    confidence = e.get("confidence", "unresolved")
    lines.append(f"- 置信度：{confidence}")
    if e.get("fact_summary"):
        lines.append(f"- 事实摘要：{escape_text_node(e['fact_summary'])}")
    if e.get("why_it_matters"):
        lines.append(f"- 为何重要：{escape_text_node(e['why_it_matters'])}")
    if e.get("uncertainty"):
        lines.append(f"- 不确定性：{escape_text_node(e['uncertainty'])}")
    links = e.get("source_links", [])
    if links:
        lines.append("- 来源：" + "；".join(render_link("来源", u) for u in links))
    return "\n".join(lines)


def render_flow(entries: Sequence[Mapping[str, Any]]) -> str:
    if not entries:
        return ""
    lines = [_heading(2, HEADING_ORDER[4])]
    for e in entries:
        status = {"confirmed": "确认", "indicated": "迹象"}.get(
            e.get("status", ""), e.get("status", "")
        )
        text = escape_text_node(e.get("text", ""))
        lines.append(f"- {status}：{text}")
    return "\n".join(lines) + "\n"


def render_watchlist(entries: Sequence[Mapping[str, Any]]) -> str:
    lines = [_heading(2, HEADING_ORDER[5])]
    if not entries:
        lines.append("- 未来 24 小时无关键日程")
        return "\n".join(lines) + "\n"
    for e in entries:
        priority = {"critical": "关键", "high": "重要"}.get(
            e.get("priority", ""), e.get("priority", "")
        )
        label = escape_text_node(e.get("label", e.get("calendar_id", "")))
        scheduled = e.get("scheduled_at", "")
        lines.append(f"- [{priority}] {label}（{scheduled}）")
        if e.get("explanation"):
            lines.append(f"  - {escape_text_node(e['explanation'])}")
    return "\n".join(lines) + "\n"


def render_bottom_line(points: Sequence[Mapping[str, Any]]) -> str:
    lines = [_heading(2, HEADING_ORDER[6])]
    if not points:
        lines.append("- 暂无结论")
        return "\n".join(lines) + "\n"
    for p in points:
        lines.append(f"- {escape_text_node(p.get('text', ''))}")
    return "\n".join(lines) + "\n"


def render_brief(brief: Mapping[str, Any]) -> str:
    """Render the authoritative Brief object to deterministic Markdown."""
    sections = [
        render_dashboard(brief.get("dashboard", [])),
        render_market_state(brief.get("market_state", {})),
        render_events(brief.get("full_events", []), brief.get("compact_events", [])),
        render_flow(brief.get("money_flow_section", [])),
        render_watchlist(brief.get("watchlist", [])),
        render_bottom_line(brief.get("bottom_line", [])),
    ]
    header = []
    cutoff = brief.get("evidence_cutoff_at", "")
    generated = brief.get("brief_generated_at", "")
    if cutoff:
        header.append(f"证据截止：{cutoff}")
    if generated:
        header.append(f"生成时间：{generated}")
    body = "\n".join(s for s in sections if s)
    return "\n".join(header + [body]) + "\n"
