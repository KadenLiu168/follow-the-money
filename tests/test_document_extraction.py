"""Deterministic official-document extraction regressions."""

from __future__ import annotations

import hashlib
import unicodedata
from pathlib import Path

import pytest

from follow_the_money.providers.document import (
    SOURCE_CONTENT_MAX_CODE_POINTS,
    DocumentError,
    assemble_source_content,
    document_digest,
    extract_federal_reserve,
    extract_pboc,
    extract_sse,
    extract_szse,
    normalize_block,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ROOT = REPO_ROOT / "providers"

RECORDED_DETAILS = {
    "federal_reserve": (
        "federal_reserve",
        "fixtures/detail-monetary20260916a.htm",
        extract_federal_reserve,
    ),
    "pboc": ("pboc", "fixtures/detail-2026091815494839605.html", extract_pboc),
    "sse": ("sse", "fixtures/detail-c_20260918_10832703.shtml", extract_sse),
    "szse": ("szse", "fixtures/detail-t20260917_622911.html", extract_szse),
}

RECORDED_FIRST_AND_LAST = {
    "federal_reserve": (
        (
            "The Federal Open Market Committee approved the following statement for release "
            "by a 12 – 0 vote:"
        ),
        "Implementation Note issued September 16, 2026",
    ),
    "pboc": (
        (
            "2026年9月18日，中国人民银行与老挝人民民主共和国银行在广西南宁联合举办"
            "中老跨境数字支付互联互通启动会。中国人民银行副行长陆磊、"
            "老挝人民民主共和国银行副行长苏里萨克·萨姆努翁出席并致辞。"
        ),
        "中老两国央行相关部门负责人，商业银行、参与企业有关负责人参加会议。",
    ),
    "sse": ("上证公告（基金）【2026】2915号", "2026年09月18日"),
    "szse": ("各市场参与人：", "2026年9月17日"),
}


def _recorded(provider_id: str) -> bytes:
    _, relative, _ = RECORDED_DETAILS[provider_id]
    return (PROVIDER_ROOT / provider_id / relative).read_bytes()


def _pboc_document(inner: str) -> bytes:
    return (
        "<!doctype html><html><body>"
        '<nav><a href="/other">导航 2026-09-18</a></nav>'
        f'<div id="zoom" class="zoom1">{inner}</div>'
        "</body></html>"
    ).encode()


def test_recorded_provider_documents_produce_exact_bounded_text():
    for provider_id, (_, relative, extractor) in RECORDED_DETAILS.items():
        body = _recorded(provider_id)
        blocks = extractor(body)
        first, last = RECORDED_FIRST_AND_LAST[provider_id]
        assert blocks[0] == first, provider_id
        assert blocks[-1] == last, provider_id
        content = assemble_source_content(
            blocks, max_text_chars=SOURCE_CONTENT_MAX_CODE_POINTS, document_sha256="d" * 64
        )
        assert content.truncated is False
        assert content.text == "\n\n".join(blocks)
        assert 0 < len(content.text) <= SOURCE_CONTENT_MAX_CODE_POINTS
        assert unicodedata.is_normalized("NFC", content.text)
        # Whole-block assembly counts separators toward the closed budget.
        assert len(content.text) == sum(len(block) for block in blocks) + 2 * (len(blocks) - 1)


def test_recorded_raw_body_digest_is_the_exact_response_sha256():
    for provider_id in RECORDED_DETAILS:
        body = _recorded(provider_id)
        assert document_digest(body) == hashlib.sha256(body).hexdigest()
    body = _recorded("federal_reserve")
    assert document_digest(body) != document_digest(body + b" ")
    assert (
        PROVIDER_ROOT / "federal_reserve" / "fixtures" / "detail-monetary20260916a.htm"
    ).is_file()


def test_character_references_are_decoded_and_paragraph_order_is_preserved():
    body = _pboc_document(
        "<p>first &amp; second</p><p>dash &#8212; and less &lt; than</p><p>joined&nbsp;words</p>"
    )
    assert extract_pboc(body) == (
        "first & second",
        "dash — and less < than",
        "joined words",
    )


def test_blocks_are_nfc_normalized_and_intra_block_whitespace_is_folded():
    body = _pboc_document("<p>é   a\n\tb</p><p>  </p>")
    blocks = extract_pboc(body)
    assert blocks == ("é a b",)
    assert unicodedata.is_normalized("NFC", blocks[0])
    assert normalize_block("  a  b  ") == "a b"


def test_script_style_and_out_of_container_text_are_excluded():
    body = _pboc_document(
        "<p>kept</p>"
        "<script>var dropped = 'script text';</script>"
        "<style>.zoom1 { color: red }</style>"
    )
    assert extract_pboc(body) == ("kept",)

    outside = (
        b"<html><body><div class='nav'>navigation home</div>"
        b"<div id='zoom'><p>body only</p></div>"
        b"<footer>footer text</footer></body></html>"
    )
    assert extract_pboc(outside) == ("body only",)


def test_line_breaks_separate_container_level_runs():
    body = _pboc_document("公告编号<br><br>正文一<br>正文二")
    assert extract_pboc(body) == ("公告编号", "正文一", "正文二")


def test_missing_and_duplicate_containers_fail_closed():
    with pytest.raises(DocumentError, match="lacks the verified content container"):
        extract_pboc(b"<html><body><p>no container here</p></body></html>")
    with pytest.raises(DocumentError, match="duplicate content containers"):
        extract_pboc(_pboc_document("") + _pboc_document("<p>second</p>"))
    with pytest.raises(DocumentError, match="duplicate content containers"):
        extract_pboc(_pboc_document('<div id="zoom"><p>nested</p></div>'))


def test_invalid_utf8_non_html_and_attachment_only_sources_fail_closed():
    with pytest.raises(DocumentError, match="not decodable as utf-8"):
        extract_pboc(b'<div id="zoom">\xff\xfe bad bytes</div>')
    with pytest.raises(DocumentError, match="not HTML"):
        extract_pboc(b"%PDF-1.7 not a markup document")
    with pytest.raises(DocumentError, match="attachment-only"):
        extract_pboc(_pboc_document('<a href="/files/notice.pdf">附件：通知全文.pdf</a>'))
    with pytest.raises(DocumentError, match="no admissible text blocks"):
        extract_pboc(_pboc_document("<script>x</script>"))


def test_later_blocks_are_dropped_whole_and_mark_truncation():
    blocks = ("a" * 40, "b" * 40, "c" * 40)
    content = assemble_source_content(blocks, max_text_chars=82, document_sha256="d" * 64)
    assert content.text == "a" * 40 + "\n\n" + "b" * 40
    assert content.truncated is True

    exact = assemble_source_content(blocks, max_text_chars=124, document_sha256="d" * 64)
    assert exact.text == "\n\n".join(blocks)
    assert exact.truncated is False


def test_an_oversized_first_block_fails_closed():
    with pytest.raises(DocumentError, match="first admissible content block"):
        assemble_source_content(
            ("x" * 12001,), max_text_chars=SOURCE_CONTENT_MAX_CODE_POINTS, document_sha256="d" * 64
        )
    with pytest.raises(DocumentError, match="no admissible text blocks"):
        assemble_source_content(
            (), max_text_chars=SOURCE_CONTENT_MAX_CODE_POINTS, document_sha256="d" * 64
        )


def test_federal_reserve_body_column_is_the_verified_container():
    body = _pboc_document("<p>not the Fed container</p>")
    with pytest.raises(DocumentError, match="lacks the verified content container"):
        extract_federal_reserve(body)

    fed = (
        b"<html><body>"
        b'<div id="article">'
        b'<div class="heading col-xs-12 col-sm-8 col-md-8"><h3 class="title">T</h3></div>'
        b'<div class="col-xs-12 col-sm-8 col-md-8"><p>Release body</p></div>'
        b"</div>"
        b"</body></html>"
    )
    assert extract_federal_reserve(fed) == ("Release body",)
