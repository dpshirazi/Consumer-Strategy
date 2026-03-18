# ================================================================
#  regression.py — OLS Regression Analysis
#
#  Question: Does (trends_ratio / analyst_ratio) predict returns?
#
#  This tests the actual signal the strategy uses — not the
#  components individually. One feature, one coefficient, one
#  clean answer.
# ================================================================

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats


def _build_dataset(all_trades):
    """Collect all executed trades into a single DataFrame."""
    rows = []
    for ticker, trades_df in all_trades.items():
        executed = trades_df[trades_df["signal"] == True].copy()
        for _, row in executed.iterrows():
            rows.append({
                "ticker":        ticker,
                "earnings_date": row["earnings_date"],
                "trends_ratio":  row["trends_ratio"],
                "analyst_ratio": row["analyst_ratio"],
                "ret_pct":       row["trade_return_pct"],
            })
    df = pd.DataFrame(rows).dropna()
    # Compute the actual signal used by the strategy
    df["composite_signal"] = df["trends_ratio"] / df["analyst_ratio"]
    return df


def _run_ols(x, y):
    """Simple OLS: y = a + b*x. Returns (a, b, p_val_b, r2, r2_adj) or all None on failure."""
    n = len(x)
    if n < 4:
        return None, None, None, None, None

    # Guard: if signal has no variance, OLS is undefined
    if np.std(x) < 1e-10:
        return None, None, None, None, None

    X = np.column_stack([np.ones(n), x])
    try:
        beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return None, None, None, None, None

    y_hat  = X @ beta
    resid  = y - y_hat
    sigma2 = (resid @ resid) / (n - 2)
    var_b  = sigma2 * np.linalg.inv(X.T @ X)
    se     = np.sqrt(np.diag(var_b))
    t_stat = beta / se
    pvals  = [2 * (1 - stats.t.cdf(abs(t), df=n-2)) for t in t_stat]
    ss_res = resid @ resid
    ss_tot = ((y - y.mean()) ** 2).sum()
    if ss_tot < 1e-10:
        return None, None, None, None, None
    r2     = 1 - ss_res / ss_tot
    r2_adj = 1 - (1 - r2) * (n - 1) / (n - 2)
    return beta[0], beta[1], pvals[1], r2, r2_adj


def run_walk_forward_regression(all_earnings, all_prices, all_trades):
    """
    OLS regression: does (trends_ratio / analyst_ratio) predict returns?
    Tests the actual composite signal used by the strategy.
    """
    print(f"\n{'='*65}")
    print(f"  OLS REGRESSION ANALYSIS")
    print(f"  Question: Does (trends_ratio / analyst_ratio) predict returns?")
    print(f"{'='*65}\n")

    df = _build_dataset(all_trades)

    if len(df) < 20:
        print(f"  Not enough trades ({len(df)} found, need 20+).")
        return [], None

    print(f"  Sample : {len(df)} executed trades across {df['ticker'].nunique()} stocks")
    print(f"  Period : {str(df['earnings_date'].min())[:10]} → {str(df['earnings_date'].max())[:10]}\n")

    x = df["composite_signal"].values
    y = df["ret_pct"].values

    intercept, slope, pval, r2, r2_adj = _run_ols(x, y)

    if intercept is None:
        print("  OLS failed to converge on full dataset. Skipping regression.")
        print(f"{'='*65}\n")
        return [], None

    corr = df["composite_signal"].corr(df["ret_pct"])

    # ── Print results ─────────────────────────────────────────────
    sig = "✅ YES" if pval < 0.05 else ("⚠️  MARGINAL" if pval < 0.10 else "❌ NO")

    print(f"  {'Variable':<28} {'Coefficient':>12} {'p-value':>10}  {'Significant?':>14}")
    print(f"  {'-'*68}")
    print(f"  {'const':<28} {intercept:>+11.3f}  {'':>9}")
    print(f"  {'composite_signal (T/A ratio)':<28} {slope:>+11.3f}  {pval:>9.3f}  {sig:>14}")
    print(f"\n  R-squared      : {r2:.4f}  ({'weak' if r2 < 0.05 else 'moderate' if r2 < 0.15 else 'strong'} fit)")
    print(f"  Adj. R-squared : {r2_adj:.4f}")
    print(f"  Correlation    : r = {corr:+.3f}")

    print(f"\n  INTERPRETATION")
    print(f"  {'-'*60}")
    if slope > 0:
        print(f"  A higher composite signal is associated with higher returns (+{slope:.2f}% per unit).")
    else:
        print(f"  A higher composite signal is associated with lower returns ({slope:.2f}% per unit).")

    if pval < 0.05:
        print(f"  This relationship IS statistically significant (p={pval:.3f}).")
        print(f"  The signal has genuine predictive power over trade returns.")
    elif pval < 0.10:
        print(f"  This relationship is MARGINALLY significant (p={pval:.3f}).")
        print(f"  There is weak evidence the signal predicts returns.")
    else:
        print(f"  This relationship is NOT statistically significant (p={pval:.3f}).")
        print(f"  The strategy's edge comes from risk reduction (lower vol),")
        print(f"  not from the signal linearly predicting return magnitude.")

    # ── Scatter plot ──────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 6))
    fig.suptitle(
        "Does the Composite Signal Predict Returns?\n"
        "OLS: ret_pct = a + b x (trends_ratio / analyst_ratio)",
        fontsize=12, fontweight="bold"
    )

    colors = ["#2E7D32" if r > 0 else "#C62828" for r in y]
    ax.scatter(x, y, c=colors, alpha=0.5, s=45, edgecolors="none",
               label="Executed trades  (green=WIN, red=LOSS)")

    x_range = np.linspace(np.percentile(x, 2), np.percentile(x, 98), 100)
    ax.plot(x_range, intercept + slope * x_range,
            color="#1565C0", linewidth=2,
            label=f"OLS fit  (b={slope:+.3f}, p={pval:.3f})")

    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Composite Signal  (trends_ratio / analyst_ratio)", fontsize=11)
    ax.set_ylabel("Trade Return (%)", fontsize=11)
    ax.set_title(f"r = {corr:+.3f}  |  R2 = {r2:.4f}  |  n = {len(df)} trades", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.25)

    plt.tight_layout()
    plt.savefig("results_regression.png", dpi=130, bbox_inches="tight")
    print(f"\n  Scatter plot saved to: results_regression.png")
    print(f"{'='*65}\n")

    return [], None