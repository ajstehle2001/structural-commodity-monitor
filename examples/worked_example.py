"""End-to-end worked example on synthetic data.

Runs the full methodology: generate a market with known ground truth,
declare a pre-registered test, fit the structural curve, record the
outcome, compute today's residual, and simulate the decay rule's
quarterly discipline. Prints a markdown walkthrough.

Run:  python examples/worked_example.py > examples/worked_example_output.md
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monitor.decay import QuarterlyEvaluation, SignalRecord, SignalStatus  # noqa: E402
from monitor.model import fit_structural_curve, fit_with_spike_exclusion, residuals_in_sigma  # noqa: E402
from monitor.registry import Registry, TestDeclaration  # noqa: E402
from monitor.synthetic import SyntheticParams, generate_weekly_series  # noqa: E402


def main() -> None:
    print("# Worked example: the full methodology on synthetic data\n")
    print(
        "Everything below runs on generated data with known ground truth "
        "(true curve: a=8.0, b=1.8). No licensed data, no live position.\n"
    )

    # 1. The market
    params = SyntheticParams(seed=42)
    df = generate_weekly_series(params)
    print("## 1. The market\n")
    print(f"- {len(df)} weeks of synthetic data")
    print(f"- Inventory ratio range: {df.ir.min():.2f} to {df.ir.max():.2f}")
    print(f"- Price range: {df.price.min():,.0f} to {df.price.max():,.0f}\n")

    # 2. Pre-register the test BEFORE fitting
    print("## 2. Pre-register the test (before running it)\n")
    with tempfile.TemporaryDirectory() as tmp:
        reg = Registry(Path(tmp))
        decl = TestDeclaration(
            test_id="demo-levels-fit-01",
            hypothesis="ln(P) is linear in 1/IR with positive slope",
            specification="OLS of ln(price) on 1/IR, all weeks, full sample",
            pass_criteria="slope > 0 and p_value < 0.01",
        )
        reg.declare(decl)
        print(f"- Declared `{decl.test_id}`")
        print(f"- Declaration SHA-256: `{decl.sha256[:16]}...`")
        print("- The hash freezes hypothesis, specification, and pass criteria.\n")

        # 3. Run the fit and record the outcome
        print("## 3. Fit the structural curve\n")
        fit = fit_structural_curve(df["ir"], df["price"])
        passed = fit.b > 0 and fit.p_value < 0.01
        reg.record_outcome(
            decl.test_id,
            passed=passed,
            metrics={"a": fit.a, "b": fit.b, "p_value": fit.p_value, "r2": fit.r_squared},
        )
        print(f"- Fitted: ln(P) = {fit.a:.3f} + {fit.b:.3f} x (1/IR)")
        print(f"- True generator: ln(P) = {params.a:.3f} + {params.b:.3f} x (1/IR)")
        print(f"- p-value: {fit.p_value:.2e} | R^2: {fit.r_squared:.3f}")
        print(f"- Verdict recorded in registry: **{reg.verdict(decl.test_id).upper()}**\n")

    # 4. Robustness: spike exclusion
    print("## 4. Robustness: does the coefficient survive spike exclusion?\n")
    stability = fit_with_spike_exclusion(df["ir"], df["price"])
    print(f"- Full-sample b: {stability.full.b:.3f}")
    print(f"- Spike-excluded b: {stability.excluded.b:.3f}")
    print(f"- Relative change: {stability.b_relative_change:.1%}")
    print(f"- Stable (<=25% tolerance): **{stability.is_stable()}**\n")

    # 5. Today's residual
    print("## 5. Where does price sit relative to structure today?\n")
    sig = residuals_in_sigma(stability.full, df["ir"], df["price"])
    last = df.iloc[-1]
    fair = float(stability.full.fair_value(last.ir))
    print(f"- Latest week IR: {last.ir:.2f}")
    print(f"- Structural fair value: {fair:,.0f}")
    print(f"- Market price: {last.price:,.0f}")
    print(f"- Residual: **{sig.iloc[-1]:+.2f} sigma**\n")

    # 6. The decay rule in action
    print("## 6. The decay rule: signals must keep earning their place\n")
    signal = SignalRecord(signal_id="demo-fade-pattern")
    quarters = [
        ("2026Q3", True), ("2026Q4", True),   # graduates
        ("2027Q1", False), ("2027Q2", False),  # retires
    ]
    for period, ok in quarters:
        status = signal.record_quarter(QuarterlyEvaluation(period=period, passed=ok))
        print(f"- {period}: {'pass' if ok else 'FAIL'} -> status: {status.value}")
    assert signal.status == SignalStatus.RETIRED
    print(
        "\nRetirement is permanent: resurrecting this idea requires a new "
        "pre-registered declaration, restarting the graduation clock.\n"
    )

    print("---\n")
    print(
        "*The point of the exercise: every claim above is either enforced by "
        "code (registry, decay rule, validation boundaries) or measured "
        "against known ground truth (coefficient recovery). Conviction is "
        "never load-bearing.*"
    )


if __name__ == "__main__":
    main()
