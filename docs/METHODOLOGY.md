# Methodology

## The theory of storage, in plain words

Commodity prices are not set by this year's harvest. They are set by the relationship between **inventories** and **consumption** — how much sits in warehouses relative to how fast factories are drawing it down.

When warehouses are full, one more tonne in storage barely matters: price is low and quiet. When warehouses run toward empty, price explodes, because every industrial consumer simultaneously pays whatever it takes to keep production lines running. Economists call the premium paid for physical availability the **convenience yield**. Its shape as a function of inventory is a playground slide: steep near scarcity, flat in abundance.

Weymar (1965) formalized this for cocoa and demonstrated a second, subtler result: much of the market's boom-bust cycle is **internally generated**. High prices suppress consumption only after a long lag (his example: 1960s candy bars sold at fixed nickel price points, so manufacturers responded to cocoa costs by changing bar weight — which required new molds and took months). Suppressed consumption refills warehouses; full warehouses depress price; the loop repeats. Market commentary, meanwhile, attributes every move to whatever crop headline coincides with it.

## The single state variable

Theory says price depends on inventories *relative to* consumption — a fixed stock level is a glut if the world grinds slowly and a shortage if it grinds fast. So the system reduces market state to one number, the **inventory ratio**:In words: how many units of annual demand are already sitting in the warehouse?

Certified stocks (warehouses approved by the ICE exchanges) are a *visible slice* of world inventory, not the whole. The system therefore works in relative terms — sigma bands against its own history — rather than trusting absolute levels.

## The curve

Theory predicts price falls steeply as IR shrinks toward zero and flattens as IR grows. The simplest functional form with exactly that behavior is a constant plus a coefficient on the **reciprocal** of the ratio, in log-price space:`1/IR` explodes as IR approaches zero (the panic zone) and fades toward nothing as IR grows (the glut zone). The coefficients `a` and `b` are **estimated, not assumed** — fitted by ordinary least squares on the weekly series.

Two robustness disciplines apply to the fit:

1. **Spike exclusion.** The fit is re-run with the most extreme historical episode excluded. If the coefficient on `1/IR` changes materially, the relationship is a souvenir of one wild year, not a property of the market. (In the production calibration that motivated this repo, the coefficient barely moved — that stability, not the fit statistic, is the meaningful result.)
2. **Sign and significance before goodness-of-fit.** A high R² with the wrong sign is worthless; a modest R² with the theoretically predicted sign and p < 0.01 is informative.

## The residual, in sigma units

Each day:

1. Compute fair value from the curve: `P_fair = exp(a + b/IR)`
2. Compare with the actual settlement price
3. Express the gap in units of one standard deviation of the model's historical misses

A residual of **+1.0σ** means the market trades about one typical model-error above what inventories justify. **+2.0σ** is the historical extreme. The sigma scale gives "how far is price from structure?" a consistent meaning across regimes.

What a large positive residual means: the market is paying for something the inventory data cannot see — typically fear about *next season's* supply. Whether that fear proves correct is exactly the question this model cannot answer, and says so.

## The evidence standard: pre-registration

Every statistical test in this framework follows one discipline: **the hypothesis, the exact specification, and the pass/fail criteria are written down before the test is run.** No third attempt is permitted after a failure. Results cannot be curated.

The evidence table from the production calibration:

| Test | Question | Verdict |
|---|---|---|
| Structural fit (levels) | Does price actually sit on the storage curve? | **PASSED.** Correct sign, significant, and the fit strengthened when the extreme spike was excluded. |
| Prediction (two attempts) | Does the inventory state predict the next 4–12 weeks of price movement? | **FAILED, twice.** No statistically usable forecasting power. Recorded; no further attempts made. |
| Narrative backtest | Do combinations of price-vs-structure and story-intensity line up with subsequent moves? | **MIXED.** One configuration showed a consistent pattern across three historical episodes — treated as an n=3 in-sample hypothesis, testable only on future unseen data. |

**Why publish the failures?** Because they license everything else. A model that claims only explanation can be trusted when it says price is stretched. A model that claimed prediction would have to be graded as a forecaster — and this one would fail that grade.

## Governance: frozen parameters and the decay rule

- **Frozen parameters.** The fitted curve, sigma scale, and any alert thresholds are frozen and documented once adopted. Nothing may be tuned to rescue a result — a signal that only works under revised thresholds is a dead signal wearing new clothes.
- **Out-of-sample discipline.** All backtest results are partly in-sample by construction. History can *disqualify* ideas; it cannot prove them. The only fully valid evidence accrues forward, on data the model has never seen.
- **The decay rule.** Quarterly, all signals are re-scored on accumulated out-of-sample data. Signals stay only while they keep working on unseen data, and are retired without eulogy when they stop. Unproven hypotheses may graduate to active use only after consecutive quarters of out-of-sample performance.

## Honest limits

1. Certified stocks are a visible slice of world inventories, not the whole.
2. Any single-cycle calibration has thin coverage at the extremes of its own range; readings there carry explicit low-confidence labels.
3. The model is structurally blind to forward-looking supply expectations — Weymar's own declared boundary from 1965. The system's job is not to be blind to nothing; it is to know and say exactly where it is blind.
