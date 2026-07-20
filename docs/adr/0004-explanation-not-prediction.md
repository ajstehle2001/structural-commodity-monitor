# ADR 0004: Explanation, not prediction

## Status
Accepted.

## Context
The structural curve fits price levels against inventory state. The natural temptation is to trade its residuals: if price is 1 sigma above structure, bet on convergence. Whether that works is an empirical question, and it was tested: two pre-registered attempts to demonstrate that the inventory state predicts subsequent 4-12 week price movement both failed.

## Decision
The system claims explanation only. `monitor.model` contains no forecasting machinery. The failed prediction tests are documented in METHODOLOGY.md with the same prominence as the passed structural fit. Configurations that pair the residual with narrative intensity are treated as hypotheses under the decay rule - they graduate to any active use only after consecutive out-of-sample quarters of demonstrated performance, and are retired permanently when they stop working.

## Consequences
The system is entitled to be believed when it says price is stretched, precisely because it does not claim to know when the stretch resolves. This is Weymar's own boundary from 1965: he named what his model could not see, and operated inside that boundary. A model that admits its limits is a smaller model and a more trustworthy one; the framework treats the boundary as the asset.
