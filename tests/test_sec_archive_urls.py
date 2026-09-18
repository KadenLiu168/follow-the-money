"""SEC source URLs use the canonical CIK form of the locator they point at.

SEC EDGAR has two canonical CIK representations in its verified locators: the
submissions API is ten-digit zero-padded while every Archive path is the
unpadded integer. The padded Archive path 301-redirects to the canonical form,
so publishing it would record a redirecting alias in place of the evidence
locator.
"""

from __future__ import annotations

import json
import re

from follow_the_money.feed.validate import _SEC_ARCHIVE_CIK_PATTERN
from follow_the_money.providers.adapters import SecEdgarAdapter
from follow_the_money.providers.sec_13f import FilingCandidate
from follow_the_money.providers.sec_beneficial_ownership import (
    derive_beneficial_ownership_historical_url,
    derive_beneficial_ownership_xml_url,
)
from follow_the_money.providers.sec_form4 import derive_form4_xml_url
from follow_the_money.providers.urls import sec_archive_cik
from tests.test_adapters import FakeClient, FakeResponse

CIK = "0001067983"
ACCESSION = "0001067983-26-000002"
WINDOW = {"start": "2026-08-09T00:20:00Z", "end": "2026-08-11T00:20:00Z"}


def test_submissions_url_keeps_the_padded_cik_while_archive_urls_are_unpadded():
    adapter = SecEdgarAdapter(watched_ciks=(CIK,))
    client = FakeClient(b"{}")

    adapter.fetch(WINDOW, client)

    assert client.requests == ["https://data.sec.gov/submissions/CIK0001067983.json"]


def test_13f_complete_submission_url_uses_the_unpadded_archive_cik():
    adapter = SecEdgarAdapter(watched_ciks=(CIK,))
    candidate = FilingCandidate(
        cik=CIK,
        accession_number=ACCESSION,
        form="13F-HR",
        report_period="2026-06-30",
        filed_at="2026-08-10T00:00:00.000Z",
        accepted_at="2026-08-10T12:00:00.000Z",
    )

    assert adapter._complete_url(candidate) == (
        "https://www.sec.gov/Archives/edgar/data/1067983/000106798326000002/"
        "0001067983-26-000002.txt"
    )


def test_13f_v1_document_url_uses_the_unpadded_archive_cik():
    body = {
        "filings": {
            "recent": {
                "form": ["13F-HR"],
                "filingDate": ["2026-08-10"],
                "accessionNumber": [ACCESSION],
                "primaryDocument": ["primary_doc.xml"],
                "cik": [CIK],
            }
        }
    }
    response = FakeResponse(json.dumps(body).encode())

    items = SecEdgarAdapter(watched_ciks=(CIK,)).normalize(response, WINDOW)

    assert [item["source"]["url"] for item in items] == [
        "https://www.sec.gov/Archives/edgar/data/1067983/000106798326000002/primary_doc.xml"
    ]


def test_form4_xml_url_uses_the_unpadded_archive_cik():
    assert (
        derive_form4_xml_url(CIK, ACCESSION, "xslF345X06/primary_doc.xml")
        == "https://www.sec.gov/Archives/edgar/data/1067983/000106798326000002/primary_doc.xml"
    )


def test_beneficial_ownership_urls_use_the_unpadded_archive_cik():
    assert (
        derive_beneficial_ownership_xml_url(CIK, ACCESSION, "xslSCHEDULE_13G_X02/primary_doc.xml")
        == "https://www.sec.gov/Archives/edgar/data/1067983/000106798326000002/primary_doc.xml"
    )
    assert (
        derive_beneficial_ownership_historical_url(CIK, ACCESSION, "xslSCHEDULE_13G_X02/legacy.htm")
        == "https://www.sec.gov/Archives/edgar/data/1067983/000106798326000002/legacy.htm"
    )


def test_archive_cik_conversion_matches_the_publisher_paths():
    # Every construction site derives its path segment from this one helper, so
    # the helper's output is the only Archive CIK form the Feed can publish.
    assert sec_archive_cik(CIK) == "1067983"
    assert sec_archive_cik(CIK) != CIK


def test_validator_archive_cik_shape_matches_the_helper():
    # The beneficial-ownership snapshot check has no filer CIK in scope, so it
    # validates the canonical shape instead. That shape must track the helper and
    # must not accept the padded alias.
    assert re.fullmatch(_SEC_ARCHIVE_CIK_PATTERN, sec_archive_cik(CIK))
    assert re.fullmatch(_SEC_ARCHIVE_CIK_PATTERN, sec_archive_cik("0000000000"))
    assert not re.fullmatch(_SEC_ARCHIVE_CIK_PATTERN, CIK)
    assert not re.fullmatch(_SEC_ARCHIVE_CIK_PATTERN, "01067983")
