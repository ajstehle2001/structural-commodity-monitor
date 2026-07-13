"""LLM-as-reading-machine: structured extraction from archived report text.

The motivating problem: five years of weekly inventory data buried in
PDF research reports whose text layers defeat conventional parsers.
An LLM reads each report and emits structured rows.

Three design rules make this trustworthy enough for production:

1. INDEPENDENT SOURCING OF CRITICAL VALUES. Prices are never extracted.
   The schema has no price field, so no extraction error can ever touch
   the number that matters most. Prices come from market data feeds.
2. EXTRACTION IS UNTRUSTED UNTIL VALIDATED. Every extracted record
   passes explicit plausibility checks (non-negative, within physical
   bounds, parseable date). Failures raise; nothing malformed continues.
3. SUSPICION IS ESCALATED, NOT RESOLVED. Series-level checks flag
   week-over-week moves beyond a threshold as suspect. Suspect records
   are quarantined for human review - the system never auto-corrects,
   because an auto-correction is just an extraction error with better
   manners.

The LLM interface is a Protocol; tests run against scripted fakes with
no network. An optional Anthropic adapter is provided for real use
(requires `pip install -e ".[llm]"`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Protocol


class ExtractionError(Exception):
    """Raised when extraction output is malformed or fails validation."""


class LLMClient(Protocol):
    """Minimal LLM seam: one system+user completion returning text."""

    def complete(self, *, system: str, user: str) -> str: ...


EXTRACTION_SYSTEM_PROMPT = """You are a data extraction machine reading a weekly cocoa market report.

Extract the certified warehouse stock figures for the two exchanges.

Your output must be VALID JSON matching this schema exactly:
{
  "report_date": "YYYY-MM-DD",
  "ny_certified_stocks_kt": <number, thousand metric tonnes>,
  "london_certified_stocks_kt": <number, thousand metric tonnes>
}

Rules:
- Output ONLY the JSON object. No prose, no markdown fences.
- Report figures exactly as stated in the text. Do not convert units
  unless the text gives tonnes (divide by 1000 for kt).
- If a required figure is genuinely absent from the text, use null.
- NEVER extract or output prices. Prices are sourced independently.
"""

# Physical plausibility bounds for certified cocoa stocks, generous by
# design: they catch unit confusion (tonnes vs thousand tonnes) and
# hallucinated magnitudes, not ordinary variation.
STOCKS_MIN_KT = 0.0
STOCKS_MAX_KT = 1000.0

# Week-over-week relative change above this is flagged for human review.
SUSPECT_WOW_CHANGE = 0.30


@dataclass(frozen=True)
class WeeklyStockRecord:
    """One validated week of certified stocks. No price field, by design."""

    report_date: date
    ny_certified_stocks_kt: float | None
    london_certified_stocks_kt: float | None

    @property
    def total_kt(self) -> float | None:
        if self.ny_certified_stocks_kt is None or self.london_certified_stocks_kt is None:
            return None
        return self.ny_certified_stocks_kt + self.london_certified_stocks_kt


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate_stock_value(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ExtractionError(f"{field_name}: expected number or null, got {value!r}")
    v = float(value)
    if not (STOCKS_MIN_KT <= v <= STOCKS_MAX_KT):
        raise ExtractionError(
            f"{field_name}: {v} kt outside plausible bounds "
            f"[{STOCKS_MIN_KT}, {STOCKS_MAX_KT}] - likely unit confusion or hallucination"
        )
    return v


def parse_extraction(raw_text: str) -> WeeklyStockRecord:
    """Parse and validate one extraction response. The trust boundary.

    Raises ExtractionError on malformed JSON, missing fields, wrong
    types, unparseable dates, or values outside physical bounds.
    """
    try:
        data = json.loads(_strip_fences(raw_text))
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"Extraction output is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ExtractionError(f"Expected JSON object, got {type(data).__name__}")

    required = {"report_date", "ny_certified_stocks_kt", "london_certified_stocks_kt"}
    missing = required - set(data)
    if missing:
        raise ExtractionError(f"Missing required fields: {sorted(missing)}")
    if "price" in {k.lower() for k in data} or any("price" in k.lower() for k in data):
        raise ExtractionError(
            "Extraction contains a price-like field. Prices are sourced "
            "independently and must never come from extraction."
        )

    try:
        report_date = date.fromisoformat(str(data["report_date"]))
    except ValueError as exc:
        raise ExtractionError(f"Unparseable report_date: {data['report_date']!r}") from exc

    return WeeklyStockRecord(
        report_date=report_date,
        ny_certified_stocks_kt=_validate_stock_value(
            data["ny_certified_stocks_kt"], "ny_certified_stocks_kt"
        ),
        london_certified_stocks_kt=_validate_stock_value(
            data["london_certified_stocks_kt"], "london_certified_stocks_kt"
        ),
    )


def extract_weekly_stocks(report_text: str, llm: LLMClient) -> WeeklyStockRecord:
    """Run one report through the LLM and the validation trust boundary."""
    raw = llm.complete(system=EXTRACTION_SYSTEM_PROMPT, user=report_text)
    return parse_extraction(raw)


@dataclass(frozen=True)
class SeriesFlag:
    """A record flagged as suspect during series-level validation."""

    record: WeeklyStockRecord
    reason: str


def validate_series(records: list[WeeklyStockRecord]) -> list[SeriesFlag]:
    """Cross-week sanity checks. Returns flags; never mutates or corrects.

    Flags:
    - week-over-week total change beyond SUSPECT_WOW_CHANGE
    - duplicate report dates
    - dates out of order

    The caller (a human, or a pipeline that routes to a human) decides
    what to do with flagged records. Auto-correction is deliberately
    not offered.
    """
    flags: list[SeriesFlag] = []
    seen_dates: set[date] = set()
    prev: WeeklyStockRecord | None = None

    for rec in records:
        if rec.report_date in seen_dates:
            flags.append(SeriesFlag(rec, f"duplicate report_date {rec.report_date}"))
        seen_dates.add(rec.report_date)

        if prev is not None:
            if rec.report_date < prev.report_date:
                flags.append(
                    SeriesFlag(rec, f"out of order: {rec.report_date} after {prev.report_date}")
                )
            if prev.total_kt and rec.total_kt:
                change = abs(rec.total_kt - prev.total_kt) / prev.total_kt
                if change > SUSPECT_WOW_CHANGE:
                    flags.append(
                        SeriesFlag(
                            rec,
                            f"week-over-week total change {change:.0%} exceeds "
                            f"{SUSPECT_WOW_CHANGE:.0%} - quarantine for human review",
                        )
                    )
        prev = rec

    return flags


class AnthropicExtractionClient:
    """Optional real LLM adapter. Requires the 'llm' extra.

    Kept import-lazy so the core package has no LLM dependency and the
    test suite runs with zero network access.
    """

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "AnthropicExtractionClient requires the anthropic package: "
                'pip install -e ".[llm]"'
            ) from exc
        self._client = anthropic.Anthropic()
        self._model = model

    def complete(self, *, system: str, user: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "\n".join(b.text for b in message.content if b.type == "text")
