"""Tests for the narrative scorer trust boundary. Zero network."""

from __future__ import annotations

import pytest

from monitor.narrative import (
    NARRATIVE_SYSTEM_PROMPT,
    NarrativeScore,
    NarrativeScoringError,
    parse_narrative_score,
    score_commentary,
)


class FakeLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[dict] = []

    def complete(self, *, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        return self.response


GOOD_JSON = (
    '{"crop_story_intensity": 8, "inventory_grounding": 2, '
    '"fund_positioning_emphasis": 6, '
    '"dominant_narrative": "El Nino pod-count fears"}'
)


def test_parses_clean_json():
    s = parse_narrative_score(GOOD_JSON)
    assert s.crop_story_intensity == 8
    assert s.dominant_narrative == "El Nino pod-count fears"


def test_story_over_structure_property():
    s = parse_narrative_score(GOOD_JSON)
    assert s.story_over_structure == 6  # 8 - 2


def test_strips_fences():
    s = parse_narrative_score(f"```json\n{GOOD_JSON}\n```")
    assert s.inventory_grounding == 2


def test_rejects_malformed_json():
    with pytest.raises(NarrativeScoringError, match="not valid JSON"):
        parse_narrative_score('{"crop_story_intensity": 8,')


def test_rejects_missing_fields():
    with pytest.raises(NarrativeScoringError, match="Missing required fields"):
        parse_narrative_score('{"crop_story_intensity": 8}')


def test_rejects_out_of_range_score():
    high = GOOD_JSON.replace('"crop_story_intensity": 8', '"crop_story_intensity": 11')
    with pytest.raises(NarrativeScoringError, match="outside"):
        parse_narrative_score(high)


def test_rejects_non_integer_score():
    floaty = GOOD_JSON.replace('"crop_story_intensity": 8', '"crop_story_intensity": 8.5')
    with pytest.raises(NarrativeScoringError, match="expected integer"):
        parse_narrative_score(floaty)


def test_rejects_boolean_score():
    boolish = GOOD_JSON.replace('"crop_story_intensity": 8', '"crop_story_intensity": true')
    with pytest.raises(NarrativeScoringError, match="expected integer"):
        parse_narrative_score(boolish)


def test_rejects_empty_dominant_narrative():
    empty = GOOD_JSON.replace('"El Nino pod-count fears"', '"  "')
    with pytest.raises(NarrativeScoringError, match="non-empty"):
        parse_narrative_score(empty)


def test_score_commentary_seam():
    llm = FakeLLM(GOOD_JSON)
    s = score_commentary("WEEKLY REVIEW TEXT", llm)
    assert isinstance(s, NarrativeScore)
    assert llm.calls[0]["system"] == NARRATIVE_SYSTEM_PROMPT
    assert llm.calls[0]["user"] == "WEEKLY REVIEW TEXT"
