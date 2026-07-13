# structural-commodity-monitor

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A reference implementation of a structural fair-value monitor for physical commodity positions — LLM-based data extraction, pre-registered statistical testing, and signal-decay governance. Based on F. Helmut Weymar's 1965 MIT thesis, *The Dynamics of the World Cocoa Market*.

> **Status: Phase 1 — methodology and documentation.** Model core, pre-registration framework, extraction module, and worked examples land in subsequent phases. See [Roadmap](#roadmap).

## The idea

In 1965, Weymar submitted a doctoral thesis at MIT (advisers included Paul Samuelson) modeling the world cocoa market. He wrote it while employed by a confectionery manufacturer that funded the research because it wanted to understand the price of its most important raw material. The framework he advanced — the **theory of storage** — remains the academic standard for commodity price modeling. In 1969 his model called a sharp rise in cocoa prices; his employer acted on it and earned a large inventory profit, and Weymar left to co-found Commodities Corporation, one of the most storied trading firms in history.

Two of his insights drive this system:

1. **Inventories set the price, not this year's harvest.** What matters is how much of the commodity sits in warehouses relative to how fast it is being consumed. When stocks run toward empty, price does not rise linearly — it explodes, because every industrial consumer simultaneously pays whatever it takes to avoid stopping a production line. The practical shape is a playground slide: steep where stocks are scarce, flat where they are abundant.

2. **The market's own commentary systematically tells the story wrong.** Weymar simulated the cocoa market and showed that much of its boom-bust cycling is generated internally by lagged demand response. Yet the trade letters of his day attributed every move to whatever harvest headline coincided with it. The narrative is often noise with a good script — and that is measurable.

This repository implements both insights as a monitoring system: a **structural thermometer** (where does price sit relative to what inventories justify?) and a **narrative auditor** (how much of the market's current story rests on crop headlines versus inventory reality?).

## What this system is — and is not

| It is | It is not |
|---|---|
| A fitted, tested relationship between inventories and price: what price does physical reality justify today? | A forecast. Pre-registered predictive tests **failed**, and the failures are documented rather than reworked. |
| A conviction modifier feeding a pre-written decision framework | A trading signal generator. It sizes nothing and executes nothing. |
| A narrative auditor measuring story-vs-structure divergence | A replacement for judgment |
| Fully documented: every parameter frozen, every test pre-registered, a standing decay rule retiring signals that stop working | A black box |

The failed prediction tests are what license everything else. A system that admits it cannot forecast is entitled to be believed when it says price is stretched. Knowing the boundary is the asset — Weymar himself closed his thesis by naming what his model could not see, then built a career trading only inside the boundary he had drawn.

## Architecture

Five modules (landing across phases):

- **`extraction/`** — LLM-as-reading-machine: converts archived PDF research reports with unparseable text layers into a clean weekly inventory time series. Critical values (prices) are sourced independently from market data so no extraction error can touch the most important number.
- **`model/`** — the structural core: inventory ratio computation, curve fitting (`ln P = a + b/IR`), residual expressed in sigma units.
- **`narrative/`** — LLM scorer quantifying how much of weekly market commentary rests on supply-story headlines versus inventory fundamentals.
- **`registry/`** — pre-registration framework: test declarations committed as artifacts before tests run, pass/fail records, and an implemented decay rule (quarterly out-of-sample re-scoring; signals that stop working are retired).
- **`reporting/`** — daily brief generation with a single-source-of-numbers rule for multilingual output.

All demo data in this repository is **synthetic or public**. No licensed data series, no live position parameters.

## Documentation

- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) — the theory of storage, the single state variable, the fitted curve, the sigma residual, and the evidence table including what failed.
- [`docs/adr/`](docs/adr/) — Architecture Decision Records (landing in later phases).

## Roadmap

- [x] Phase 1: methodology documentation + repo skeleton
- [x] Phase 2: model core (IR, curve fit, residuals) + synthetic data generator + tests
- [x] Phase 3: pre-registration framework + decay rule as implemented mechanisms
- [x] Phase 4: LLM extraction module (Protocol seam, validation trust boundary, quarantine-not-correct series checks)
- [ ] Phase 5: narrative scorer + worked example notebook + ADRs

## Related work

This repo is methodology extracted from a private production system monitoring a real physical position. The production system's data (a licensed weekly research series), fitted coefficients, and position-management playbook are deliberately excluded. What remains is the part worth sharing: how to build, test, and govern a structural model honestly.

## License

MIT



