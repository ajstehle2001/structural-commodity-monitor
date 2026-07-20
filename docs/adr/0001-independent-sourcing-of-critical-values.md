# ADR 0001: Independent sourcing of critical values

## Status
Accepted.

## Context
The extraction pipeline uses an LLM to read archived PDF reports whose text layers defeat conventional parsers. LLM extraction is powerful but fallible: hallucinated digits, unit confusion, and misread tables are all realistic failure modes. The downstream model consumes two inputs: an inventory series and a price series. An error in the inventory series distorts one week's IR; an error in the price series corrupts the fitted curve, the sigma scale, and every residual computed from them.

## Decision
Prices are never extracted. The extraction schema has no price field, and the validation layer rejects any output containing a price-like key. Prices come exclusively from independent market data feeds.

## Consequences
No extraction error, however subtle, can ever touch the most important number in the system. The cost is a second data dependency (a market data source), which is acceptable: settlement prices are among the most widely available and independently verifiable numbers in finance. The rule is enforced in code (`parse_extraction` raises on price-like fields) and in the prompt ("NEVER extract or output prices"), with the code check as the binding layer - prompts are instructions, validation is law.
