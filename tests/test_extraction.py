"""Tests for the extraction trust boundary. Zero network - all fakes."""

from __future__ import annotations

from datetime import date

import pytest

from monitor.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    ExtractionError,
    WeeklyStockRecord,
    extract_weekly_stocks,
    parse_extraction,
    validate_series,
)


class FakeLLM:
    """Returns a scripted response and records the call."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[dict] = []

    def complete(self, *, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        return self.response


GOOD_JSON = (
    '{"report_date": "2026-07-09", '
    '"ny_certified_stocks_kt": 173.4, "london_certified_stocks_kt": 97.6}'
)


def rec(d: str, ny: float | None, ldn: float | None) -> WeeklyStockRecord:
    return WeeklyStockRecord(
        report_date=date.fromisoformat(d),
        ny_certified_stocks_kt=ny,
        london_certified_stocks_kt=ldn,
    )


# --- parse_extraction: the trust boundary ----------------------------------


def test_parses_clean_json():
    r = parse_extraction(GOOD_JSON)
    assert r.report_date == date(2026, 7, 9)
    assert r.total_kt == pytest.approx(271.0)


def test_strips_markdown_fences():
    fenced = f"```json\n{GOOD_JSON}\n```"
    r = parse_extraction(fenced)
    assert r.total_kt == pytest.approx(271.0)


def test_rejects_malformed_json():
    with pytest.raises(ExtractionError, match="not valid JSON"):
        parse_extraction('{"report_date": "2026-07-09", "ny_certified')


def test_rejects_missing_fields():
    with pytest.raises(ExtractionError, match="Missing required fields"):
        parse_extraction('{"report_date": "2026-07-09"}')


def test_rejects_price_like_fields():
    """The independent-sourcing rule, enforced: extraction may not carry prices."""
    with_price = (
        '{"report_date": "2026-07-09", "ny_certified_stocks_kt": 173.4, '
        '"london_certified_stocks_kt": 97.6, "settlement_price": 6366}'
    )
    with pytest.raises(ExtractionError, match="[Pp]rice"):
        parse_extraction(with_price)


def test_rejects_out_of_bounds_value():
    """271000 kt is the unit-confusion case: tonnes reported as kt."""
    confused = (
        '{"report_date": "2026-07-09", "ny_certified_stocks_kt": 173400, '
        '"london_certified_stocks_kt": 97.6}'
    )
    with pytest.raises(ExtractionError, match="plausible bounds"):
        parse_extraction(confused)


def test_rejects_negative_stocks():
    negative = (
        '{"report_date": "2026-07-09", "ny_certified_stocks_kt": -5.0, '
        '"london_certified_stocks_kt": 97.6}'
    )
    with pytest.raises(ExtractionError, match="plausible bounds"):
        parse_extraction(negative)


def test_rejects_string_where_number_expected():
    stringy = (
        '{"report_date": "2026-07-09", "ny_certified_stocks_kt": "173.4", '
        '"london_certified_stocks_kt": 97.6}'
    )
    with pytest.raises(ExtractionError, match="expected number or null"):
        parse_extraction(stringy)


def test_rejects_unparseable_date():
    bad_date = (
        '{"report_date": "July 9th 2026", "ny_certified_stocks_kt": 173.4, '
        '"london_certified_stocks_kt": 97.6}'
    )
    with pytest.raises(ExtractionError, match="report_date"):
        parse_extraction(bad_date)


def test_null_values_allowed_total_is_none():
    partial = (
        '{"report_date": "2026-07-09", "ny_certified_stocks_kt": null, '
        '"london_certified_stocks_kt": 97.6}'
    )
    r = parse_extraction(partial)
    assert r.ny_certified_stocks_kt is None
    assert r.total_kt is None


# --- extract_weekly_stocks: the seam ----------------------------------------


def test_extract_calls_llm_with_prompt_and_report():
    llm = FakeLLM(GOOD_JSON)
    r = extract_weekly_stocks("REPORT TEXT HERE", llm)
    assert r.total_kt == pytest.approx(271.0)
    assert llm.calls[0]["system"] == EXTRACTION_SYSTEM_PROMPT
    assert llm.calls[0]["user"] == "REPORT TEXT HERE"


# --- validate_series: quarantine, never auto-correct -------------------------


def test_clean_series_no_flags():
    series = [
        rec("2026-06-25", 170.0, 95.0),
        rec("2026-07-02", 172.0, 96.0),
        rec("2026-07-09", 173.4, 97.6),
    ]
    assert validate_series(series) == []


def test_flags_large_wow_jump():
    series = [
        rec("2026-07-02", 170.0, 95.0),
        rec("2026-07-09", 90.0, 40.0),  # ~51% drop in one week
    ]
    flags = validate_series(series)
    assert len(flags) == 1
    assert "quarantine" in flags[0].reason


def test_flags_duplicate_dates():
    series = [rec("2026-07-09", 170.0, 95.0), rec("2026-07-09", 171.0, 95.5)]
    flags = validate_series(series)
    assert any("duplicate" in f.reason for f in flags)


def test_flags_out_of_order_dates():
    series = [rec("2026-07-09", 170.0, 95.0), rec("2026-07-02", 168.0, 94.0)]
    flags = validate_series(series)
    assert any("out of order" in f.reason for f in flags)


def test_series_validation_never_mutates():
    series = [
        rec("2026-07-02", 170.0, 95.0),
        rec("2026-07-09", 90.0, 40.0),
    ]
    before = list(series)
    validate_series(series)
    assert series == before
