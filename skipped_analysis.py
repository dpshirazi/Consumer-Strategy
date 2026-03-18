# ================================================================
#  skipped_analysis.py — Skipped vs Traded Quarters Analysis
#
#  Core question: Do quarters the signal SKIPPED have worse
#  returns than quarters the signal TRADED?
#
#  If yes → the signal is genuinely filtering out bad quarters,
#  which is the real source of edge even if OLS says p > 0.05.
# ================================================================

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats


def run_skipped_analysis(all_trades, all_prices, buy_days_before=3, sell_days_after=2):
    """
    Compare returns of:
      - Traded quarters  (signal fired)
      - Skipped quarters (signal said no, but price data exists)

    For skipped quarters we compute the hypothetical return directly
    from price data using the same entry/exit window as the strategy.
    We cannot use trade_return_pct for skipped rows — it is stored as
    0.0 in strategy.py because no trade was executed.
    """
    from datetime import timedelta

    print(f"\n{'='*65}")
    print(f"  SKIPPED vs TRADED QUARTERS ANALYSIS")
    print(f"  Core test: does the signal filter out bad quarters?")
    print(f"{'='*65}\n")

    traded_rets  = []
    skipped_rets = []
    rows         = []

    for ticker, trades_df in all_trades.items():
        if ticker not in all_prices:
            continue

        prices_raw = all_prices[ticker]["Close"]
        prices = prices_raw.squeeze() if hasattr(prices_raw, "squeeze") else prices_raw
        if hasattr(prices, "columns"):
            prices = prices.iloc[:, 0]
        prices = prices.sort_index()

        for _, row in trades_df.iterrows():
            traded = row["signal"] == True

            if traded:
                # For traded rows, use the actual recorded return
                ret = row["trade_return_pct"]
                if pd.isna(ret):
                    continue
                traded_rets.append(ret)
                rows.append({"ticker": ticker, "date": row["earnings_date"],
                             "traded": True, "ret_pct": ret})
            else:
                # For skipped rows, compute hypothetical return from prices
                ed = pd.Timestamp(row["earnings_date"])
                entry_d = ed - timedelta(days=buy_days_before)
                exit_d  = ed + timedelta(days=sell_days_after)

                entry_cands = prices.index[prices.index >= entry_d]
                exit_cands  = prices.index[prices.index >= exit_d]
                if len(entry_cands) == 0 or len(exit_cands) == 0:
                    continue

                entry_p = float(np.array(prices[entry_cands[0]]).flat[0])
                exit_p  = float(np.array(prices[exit_cands[0]]).flat[0])

                if entry_p == 0 or np.isnan(entry_p) or np.isnan(exit_p):
                    continue

                ret = (exit_p - entry_p) / entry_p * 100
                skipped_rets.append(ret)
                rows.append({"ticker": ticker, "date": row["earnings_date"],
                             "traded": False, "ret_pct": ret})

    df = pd.DataFrame(rows)

    if len(traded_rets) == 0 or len(skipped_rets) == 0:
        print("  Not enough data to run analysis.")
        return

    traded_arr  = np.array(traded_rets)
    skipped_arr = np.array(skipped_rets)

    # ── Summary stats ─────────────────────────────────────────────
    def stats_block(arr, label):
        return {
            "label":    label,
            "n":        len(arr),
            "mean":     arr.mean(),
            "median":   np.median(arr),
            "std":      arr.std(),
            "win_rate": (arr > 0).mean() * 100,
            "p25":      np.percentile(arr, 25),
            "p75":      np.percentile(arr, 75),
        }

    t_stats = stats_block(traded_arr,  "Traded  (signal = BUY)")
    s_stats = stats_block(skipped_arr, "Skipped (signal = SKIP)")

    print(f"  {'Metric':<22} {'Traded':>12} {'Skipped':>12}")
    print(f"  {'-'*48}")
    print(f"  {'N quarters':<22} {t_stats['n']:>12} {s_stats['n']:>12}")
    print(f"  {'Mean return':<22} {t_stats['mean']:>+11.2f}% {s_stats['mean']:>+11.2f}%")
    print(f"  {'Median return':<22} {t_stats['median']:>+11.2f}% {s_stats['median']:>+11.2f}%")
    print(f"  {'Win rate':<22} {t_stats['win_rate']:>11.1f}% {s_stats['win_rate']:>11.1f}%")
    print(f"  {'Std dev':<22} {t_stats['std']:>11.2f}% {s_stats['std']:>11.2f}%")
    print(f"  {'25th percentile':<22} {t_stats['p25']:>+11.2f}% {s_stats['p25']:>+11.2f}%")
    print(f"  {'75th percentile':<22} {t_stats['p75']:>+11.2f}% {s_stats['p75']:>+11.2f}%")

    # ── t-test: is the difference statistically significant? ──────
    t_stat, p_val = stats.ttest_ind(traded_arr, skipped_arr, equal_var=False)
    diff = t_stats['mean'] - s_stats['mean']

    print(f"\n  {'─'*48}")
    print(f"  Mean difference (Traded − Skipped): {diff:>+.2f}%")
    print(f"  Welch t-test:  t = {t_stat:+.3f},  p = {p_val:.3f}")

    if p_val < 0.05:
        sig = "✅ SIGNIFICANT — signal filters out bad quarters"
    elif p_val < 0.10:
        sig = "⚠️  MARGINAL — weak evidence of filtering"
    else:
        sig = "❌ NOT significant — difference could be chance"

    print(f"  {sig}")

    # ── Win rate test (binomial) ───────────────────────────────────
    # H0: traded win rate == skipped win rate
    traded_wins  = int((traded_arr  > 0).sum())
    skipped_wins = int((skipped_arr > 0).sum())
    contingency  = np.array([
        [traded_wins,  len(traded_arr)  - traded_wins],
        [skipped_wins, len(skipped_arr) - skipped_wins]
    ])
    chi2, p_chi, _, _ = stats.chi2_contingency(contingency)
    print(f"\n  Win rate difference: {t_stats['win_rate']:>.1f}% vs {s_stats['win_rate']:>.1f}%")
    print(f"  Chi-square test:  χ² = {chi2:.3f},  p = {p_chi:.3f}")
    if p_chi < 0.05:
        print(f"  ✅ Win rates are significantly different")
    else:
        print(f"  ❌ Win rate difference not statistically significant")

    # ── Per-stock breakdown ───────────────────────────────────────
    print(f"\n  {'─'*65}")
    print(f"  PER-STOCK BREAKDOWN")
    print(f"  {'Ticker':<8} {'Traded Mean':>12} {'Skipped Mean':>13} {'Diff':>8} {'N Traded':>9} {'N Skipped':>10}")
    print(f"  {'─'*63}")

    per_stock = []
    for ticker, group in df.groupby("ticker"):
        t = group[group["traded"]  == True]["ret_pct"]
        s = group[group["traded"]  == False]["ret_pct"]
        if len(t) == 0 or len(s) == 0:
            continue
        diff_i = t.mean() - s.mean()
        per_stock.append((ticker, t.mean(), s.mean(), diff_i, len(t), len(s)))
        flag = "✅" if diff_i > 0 else "❌"
        print(f"  {ticker:<8} {t.mean():>+11.2f}% {s.mean():>+12.2f}% {diff_i:>+7.2f}% "
              f"{len(t):>9} {len(s):>10}  {flag}")

    n_positive = sum(1 for _, _, _, d, _, _ in per_stock if d > 0)
    print(f"\n  {n_positive}/{len(per_stock)} stocks show traded > skipped mean return")

    # ── Plot ──────────────────────────────────────────────────────
    _plot_skipped(traded_arr, skipped_arr, t_stats, s_stats, diff, p_val, per_stock)

    print(f"\n{'='*65}\n")
    return df


def _plot_skipped(traded_arr, skipped_arr, t_stats, s_stats, diff, p_val, per_stock):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(
        "Skipped vs Traded Quarters — Does the Signal Filter Out Bad Quarters?\n"
        f"Traded mean: {t_stats['mean']:+.2f}%  |  "
        f"Skipped mean: {s_stats['mean']:+.2f}%  |  "
        f"Difference: {diff:+.2f}%  (p={p_val:.3f})",
        fontsize=11, fontweight="bold"
    )

    # ── Panel 1: Overlapping histograms ───────────────────────────
    ax = axes[0]
    bins = np.linspace(
        min(traded_arr.min(), skipped_arr.min()),
        max(traded_arr.max(), skipped_arr.max()),
        40
    )
    ax.hist(skipped_arr, bins=bins, alpha=0.55, color="#C62828",
            label=f"Skipped (n={len(skipped_arr)}, mean={s_stats['mean']:+.1f}%)")
    ax.hist(traded_arr,  bins=bins, alpha=0.55, color="#1565C0",
            label=f"Traded  (n={len(traded_arr)},  mean={t_stats['mean']:+.1f}%)")
    ax.axvline(t_stats['mean'], color="#1565C0", linewidth=2, linestyle="--")
    ax.axvline(s_stats['mean'], color="#C62828", linewidth=2, linestyle="--")
    ax.axvline(0, color="gray", linewidth=1, linestyle=":")
    ax.set_xlabel("Trade Return (%)")
    ax.set_ylabel("Count")
    ax.set_title("Return Distributions")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── Panel 2: Box plots ────────────────────────────────────────
    ax = axes[1]
    bp = ax.boxplot(
        [skipped_arr, traded_arr],
        labels=["Skipped", "Traded"],
        patch_artist=True,
        medianprops=dict(color="white", linewidth=2)
    )
    bp["boxes"][0].set_facecolor("#C62828")
    bp["boxes"][1].set_facecolor("#1565C0")
    for patch in bp["boxes"]:
        patch.set_alpha(0.7)
    ax.axhline(0, color="gray", linewidth=1, linestyle=":")
    ax.set_ylabel("Return (%)")
    ax.set_title(f"Box Plot\n(p={p_val:.3f})")
    ax.grid(True, alpha=0.3)

    # ── Panel 3: Per-stock diff bar chart ─────────────────────────
    ax = axes[2]
    per_stock_sorted = sorted(per_stock, key=lambda x: x[3], reverse=True)
    tickers = [r[0] for r in per_stock_sorted]
    diffs   = [r[3] for r in per_stock_sorted]
    colors  = ["#1565C0" if d > 0 else "#C62828" for d in diffs]
    ax.barh(tickers, diffs, color=colors, alpha=0.75)
    ax.axvline(0, color="gray", linewidth=1)
    ax.set_xlabel("Traded Mean − Skipped Mean (%)")
    ax.set_title("Per-Stock: Traded vs Skipped\n(blue = signal helped)")
    ax.grid(True, alpha=0.3, axis="x")
    ax.tick_params(axis="y", labelsize=7)

    plt.tight_layout()
    plt.savefig("results_skipped_analysis.png", dpi=130, bbox_inches="tight")
    print(f"\n  📊 Skipped analysis chart saved to: results_skipped_analysis.png")