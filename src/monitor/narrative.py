"""Narrative scorer: measuring how much of the market's story is story.

Weymar's second insight, operationalized: market commentary attributes
price moves to whatever supply headline coincides with them, even when
the move is internally generated. This module uses an LLM to read one
week's market commentary and score, on defined scales, how much of the
price explanation rests on crop/supply narratives versus inventory
fundamentals.

Same trust architecture as extraction.py:
- LLM behind a Protocol; tests run on scripted fakes, zero network.
- Output is untrusted until validated: integer ranges enforced,
  malformed JSON raises, out-of-range scores raise.
- The scorer measures narrative INTENSITY; it makes no claim about
  whether the narrative is TRUE. Pairing intensity with the structural
  residual is what generates testable configurations (e.g. "price far
  above structure while commentary loudly credits a crop story") -
  and those configurations then live or die by the pre-registration
  registry and the decay rule, not by anyone's conviction.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol


class NarrativeScoringError(Exception):
    """Raised when scorer output is malformed or out of range."""


class LLMClient(Protocol):
    """Minimal LLM seam: one system+user completion returning text."""

    def complete(self, *, system: str, user: str) -> str: ...


NARRATIVE_SYSTEM_PROMPT = """You are a market-commentary auditor reading one week's cocoa market review.

Score the commentary on three dimensions:

- crop_story_intensity (0-10): how much of the price explanation rests on
  harvest/weather/disease/pod-count narratives about FUTURE supply.
  0 = no crop narrative at all; 10 = the entire explanation is crop story.
- inventory_grounding (0-10): how much the commentary engages with CURRENT
  warehouse stocks and grindings. 0 = inventories never mentioned;
  10 = the explanation is anchored in inventory data.
- fund_positioning_emphasis (0-10): how much weight the commentary puts on
  speculative fund flows and positioning (COT data, short-covering).

Your output must be VALID JSON matching this schema exactly:
{
  "crop_story_intensity": <int 0-10>,
  "inventory_grounding": <int 0-10>,
  "fund_positioning_emphasis": <int 0-10>,
  "dominant_narrative": "<one short phrase naming the commentary's main explanation>"
}

Rules:
- Output ONLY the JSON object. No prose, no markdown fences.
- Score what the commentary SAYS, not whether it is correct. You are
  measuring the story, not judging it.
"""

SCORE_MIN = 0
SCORE_MAX = 10


@dataclass(frozen=True)
class NarrativeScore:
    """Validated weekly narrative measurement."""

    crop_story_intensity: int
    inventory_grounding: int
    fund_positioning_emphasis: int
    dominant_narrative: str

    @property
    def story_over_structure(self) -> int:
        """Positive when the week's explanation leans on stories about the
        future rather than measurable present inventories."""
        return self.crop_story_intensity - self.inventory_grounding


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate_score(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise NarrativeScoringError(f"{field_name}: expected integer, got {value!r}")
    if not (SCORE_MIN <= value <= SCORE_MAX):
        raise NarrativeScoringError(
            f"{field_name}: {value} outside [{SCORE_MIN}, {SCORE_MAX}]"
        )
    return value


def parse_narrative_score(raw_text: str) -> NarrativeScore:
    """Parse and validate one scorer response. The trust boundary."""
    try:
        data = json.loads(_strip_fences(raw_text))
    except json.JSONDecodeError as exc:
        raise NarrativeScoringError(f"Scorer output is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise NarrativeScoringError(f"Expected JSON object, got {type(data).__name__}")

    required = {
        "crop_story_intensity",
        "inventory_grounding",
        "fund_positioning_emphasis",
        "dominant_narrative",
    }
    missing = required - set(data)
    if missing:
        raise NarrativeScoringError(f"Missing required fields: {sorted(missing)}")

    dominant = data["dominant_narrative"]
    if not isinstance(dominant, str) or not dominant.strip():
        raise NarrativeScoringError("dominant_narrative must be a non-empty string")

    return NarrativeScore(
        crop_story_intensity=_validate_score(
            data["crop_story_intensity"], "crop_story_intensity"
        ),
        inventory_grounding=_validate_score(
            data["inventory_grounding"], "inventory_grounding"
        ),
        fund_positioning_emphasis=_validate_score(
            data["fund_positioning_emphasis"], "fund_positioning_emphasis"
        ),
        dominant_narrative=dominant.strip(),
    )


def score_commentary(commentary_text: str, llm: LLMClient) -> NarrativeScore:
    """Run one week's commentary through the LLM and validation."""
    raw = llm.complete(system=NARRATIVE_SYSTEM_PROMPT, user=commentary_text)
    return parse_narrative_score(raw)
