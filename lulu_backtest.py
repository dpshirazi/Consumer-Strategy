#!/usr/bin/env python3
# ================================================================
#  lulu_backtest.py
#
#  Standalone backtest for Lululemon (LULU) only.
#  Runs the full historical simulation twice:
#    - Run A: original 50/50 US/Global trends weighting
#    - Run B: 80/20 revenue-weighted (US heavy)
#
#  Then compares both against the Always Buy 50% benchmark
#  and prints a full side-by-side diagnostic.
#
#  Requires:
#    - WRDS credentials (same as main strategy)
#    - trends_cache.pkl or trends_cache_extended.pkl in working dir
#    - strategy.py, sharpe.py, benchmark.py, helpers.py, config.py,
#      wrds_data.py all present in the same directory
#
#  Run:  python lulu_backtest.py
# ================================================================

import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch

warnings.filterwarnings("ignore")
np.random.seed(42)

from config    import STARTING_CASH, SIGNAL_THRESHOLD, POSITION_MIN, POSITION_MAX
from wrds_data import connect_wrds, pull_compustat, pull_ibes_sales, build_earnings_table
from strategy  import compute_signals, download_prices, simulate_trades, compute_stats
from benchmark import run_coin_flip, run_always_buy, coin_flip_stats, beats_coin_pct
from sharpe    import build_equity_curve, compute_sharpe, compute_always_buy_sharpe

import os, pickle


# ── Configuration ─────────────────────────────────────────────────

TICKER      = "LULU"
IBES_TICKER = "LULU"
KEYWORD     = "lululemon"
BUY_DAYS    = 3
SELL_DAYS   = 2
N_SIMS      = 1000

WEIGHTS = {
    "50/50 (original)":         0.50,
    "80/20 (revenue-weighted)": 0.80,
}

CACHE_PATHS = [
    "trends_cache.pkl",
    "trends_cache_extended.pkl",
    "trends_cache_supplemental.pkl",
]

BLUE   = "#1565C0"
PURPLE = "#6A1B9A"
ORANGE = "#E65100"
GREEN  = "#2E7D32"
RED    = "#C62828"
GRAY   = "#888888"


# ── Step 1: Load trends ───────────────────────────────────────────

def load_trends_for_lulu():
    """
    Load raw LULU trends from cache. Deliberately ignores search_volume
    since it was baked at 50/50 at fetch time — we recompute it ourselves
    from search_us and search_global so weighting changes don't require
    a new API call.
    """
    for path in CACHE_PATHS:
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            cache = pickle.load(f)
        if TICKER in cache:
            df = cache[TICKER].copy()
            print(f"  Loaded LULU trends from '{path}' ({len(df)} weeks)")
            if "search_us" not in df.columns or "search_global" not in df.columns:
                print(f"  WARNING: cache missing search_us/search_global — cannot reweight.")
                print(f"  Re-fetch by deleting the cache file and re-running code.py once.")
                return None, False
            return df, True
    print(f"  ERROR: LULU not found in any cache file.")
    print(f"  Run fetch_trends() from trends.py first, or run code.py once.")
    return None, False


def apply_geo_weight(trends_df, geo_weight_us):
    """
    Recompute search_volume with the given US revenue weight.
    Does not modify the original DataFrame.
    """
    df = trends_df.copy()
    df["search_volume"] = (
        df["search_us"]     * geo_weight_us +
        df["search_global"] * (1 - geo_weight_us)
    )
    return df


# ── Step 2: Pull fundamentals ─────────────────────────────────────

def pull_lulu_fundamentals(db):
    print(f"\n  Pulling Compustat for {TICKER}...")
    rev_df = pull_compustat(db, TICKER)
    if rev_df is None:
        raise RuntimeError(f"No Compustat data for {TICKER}")

    print(f"  Pulling IBES for {TICKER}...")
    ibes_df = pull_ibes_sales(db, TICKER, IBES_TICKER, rev_df=rev_df)
    if ibes_df is None:
        raise RuntimeError(f"No IBES data for {TICKER}")

    earnings_df = build_earnings_table(rev_df, ibes_df)
    if earnings_df is None or len(earnings_df) == 0:
        raise RuntimeError(f"Could not build earnings table for {TICKER}")

    print(f"  {len(earnings_df)} quarters of fundamentals built.")
    return earnings_df


# ── Step 3: Compute shared always-buy benchmark ───────────────────

def compute_shared_always_buy(earnings_df_base, trends_raw, stock_data):
    """
    Compute the always-buy benchmark ONCE, outside of either backtest run.

    BUG FIXED from previous version: always-buy was computed inside
    run_backtest() using the weighting-specific trades_df. The result
    happened to be identical across runs (compute_always_buy_sharpe
    ignores signals and overrides pos_size with fixed_pos=0.50), but
    it was conceptually wrong — the benchmark should be independent of
    the strategy being evaluated. Computing it once here makes that
    explicit and removes the duplication.

    Separate note on coin_opps: run_coin_flip() uses coin_opps pos_size
    which IS derived from signal_strength, so it differs slightly between
    runs. This is intentional — the coin flip asks "random direction but
    YOUR position sizing" which is a per-run question. run_always_buy()
    uses fixed_pos=0.50 and is therefore identical across runs; that's
    why we hoist it here.
    """
    trends_neutral = apply_geo_weight(trends_raw, 0.50)
    earnings_ab    = compute_signals(earnings_df_base.copy(), trends_neutral)
    ab_trades_df, _, _ = simulate_trades(
        TICKER, earnings_ab, stock_data,
        buy_days_before=BUY_DAYS, sell_days_after=SELL_DAYS,
    )

    ab_curve, ab_rets = compute_always_buy_sharpe(
        {TICKER: ab_trades_df}, {TICKER: stock_data},
        STARTING_CASH, BUY_DAYS, SELL_DAYS, fixed_pos=0.50
    )
    ab_sharpe = compute_sharpe(ab_rets, label="  Always Buy 50%")
    ab_final  = float(ab_curve.iloc[-1]) if ab_curve is not None else STARTING_CASH
    ab_ret    = (ab_final - STARTING_CASH) / STARTING_CASH * 100

    return {
        "curve":   ab_curve,
        "rets":    ab_rets,
        "sharpe":  ab_sharpe,
        "final":   ab_final,
        "ret_pct": ab_ret,
    }


# ── Step 4: Run one backtest pass ─────────────────────────────────

def run_backtest(earnings_df_base, trends_raw, stock_data, geo_weight_us, label):
    """
    Full backtest for one weighting. Signals are recomputed from scratch
    using the reweighted trends DataFrame so every downstream number
    (trends_ratio, raw_signal, signal_strength, BUY/SKIP, pos_size) is
    consistent with the weighting being tested.
    """
    weighted_trends = apply_geo_weight(trends_raw, geo_weight_us)
    earnings_df     = compute_signals(earnings_df_base.copy(), weighted_trends)

    if len(earnings_df) == 0:
        raise RuntimeError(f"No signal rows after compute_signals for {label}")

    trades_df, coin_opps, final_cash = simulate_trades(
        TICKER, earnings_df, stock_data,
        buy_days_before=BUY_DAYS,
        sell_days_after=SELL_DAYS,
    )

    coin_finals  = run_coin_flip(coin_opps, N_SIMS)
    cs           = coin_flip_stats(coin_finals)
    bc           = beats_coin_pct(final_cash, coin_finals)
    stats        = compute_stats(trades_df, final_cash)

    eq_curve, daily_rets = build_equity_curve(
        {TICKER: trades_df}, {TICKER: stock_data},
        STARTING_CASH, BUY_DAYS, SELL_DAYS
    )
    sharpe_strat = compute_sharpe(daily_rets, label=f"  {label} strategy")

    return {
        "label":         label,
        "geo_weight_us": geo_weight_us,
        "trades_df":     trades_df,
        "earnings_df":   earnings_df,
        "final_cash":    final_cash,
        "coin_finals":   coin_finals,
        "beats_coin":    bc,
        "coin_mean_ret": cs["mean_ret"],
        "eq_curve":      eq_curve,
        "daily_rets":    daily_rets,
        "sharpe_strat":  sharpe_strat,
        **stats,
    }


# ── Step 5: Print comparison ──────────────────────────────────────

def print_comparison(results_list, ab):
    print(f"\n{'=' * 70}")
    print(f"  LULU BACKTEST — GEO WEIGHT COMPARISON")
    print(f"{'=' * 70}")

    header = f"  {'Metric':<30} " + "  ".join(f"{r['label']:>22}" for r in results_list)
    print(header)
    print(f"  {'─' * 68}")

    def row(label, fmt, getter):
        cells = "  ".join(fmt.format(getter(r)) for r in results_list)
        print(f"  {label:<30} {cells}")

    row("Geo weight (US)",       "{:>22.0%}",   lambda r: r["geo_weight_us"])
    row("Quarters traded",       "{:>22}",      lambda r: r["n_trades"])
    row("Total quarters",        "{:>22}",      lambda r: r["n_quarters"])
    row("Strategy return",       "{:>+21.1f}%", lambda r: r["total_ret"])
    row("Coin flip avg return",  "{:>+21.1f}%", lambda r: r["coin_mean_ret"])
    row("Beats coin flip",       "{:>21.0f}%",  lambda r: r["beats_coin"])
    row("Win rate",              "{:>21.1f}%",  lambda r: r["win_rate"])
    row("Avg win",               "{:>+21.1f}%", lambda r: r["avg_win"])
    row("Avg loss",              "{:>+21.1f}%", lambda r: r["avg_loss"])
    row("Avg position size",     "{:>21.1f}%",  lambda r: r["avg_pos"] * 100)
    row("Strategy Sharpe",       "{:>+21.3f}",  lambda r: r["sharpe_strat"])
    row("Ending cash",           "{:>21,.0f}",  lambda r: r["final_cash"])

    print(f"\n  Always Buy 50% (shared benchmark, independent of weighting):")
    print(f"    Return : {ab['ret_pct']:>+.1f}%")
    print(f"    Sharpe : {ab['sharpe']:>+.3f}")
    print(f"    Final  : ${ab['final']:>,.0f}")
    print(f"  Starting cash: ${STARTING_CASH:,}")

    print(f"\n  NOTE: Coin flip benchmarks differ slightly between runs because")
    print(f"  they use each run's signal-derived position sizes (intentional —")
    print(f"  answers 'random direction, same sizing as this run').")

    # ── Divergence analysis ───────────────────────────────────────
    if len(results_list) == 2:
        a = results_list[0]["trades_df"].copy()
        b = results_list[1]["trades_df"].copy()

        merged = pd.merge(
            a[["earnings_date", "signal", "signal_strength", "pos_size",
               "trade_return_pct", "outcome"]].rename(columns={
                   "signal": "sig_a", "signal_strength": "ss_a",
                   "pos_size": "pos_a", "trade_return_pct": "ret_a",
                   "outcome": "out_a"}),
            b[["earnings_date", "signal", "signal_strength", "pos_size"]].rename(columns={
                   "signal": "sig_b", "signal_strength": "ss_b",
                   "pos_size": "pos_b"}),
            on="earnings_date", how="outer"
        )

        diffs = merged[merged["sig_a"] != merged["sig_b"]]
        if len(diffs) == 0:
            print(f"\n  Signal agreement: both weightings fired IDENTICAL BUY/SKIP")
            print(f"  on every quarter. The weighting shifted signal_strength and")
            print(f"  position sizes but not the binary trade decision.")
            print(f"  → See the P&L delta chart and position bar chart for the impact.")
        else:
            print(f"\n  {'─' * 68}")
            print(f"  QUARTERS WHERE SIGNALS DIVERGED ({len(diffs)} quarters)")
            print(f"  {'Date':<14} {'50/50':>10} {'80/20':>10} "
                  f"{'ss 50/50':>10} {'ss 80/20':>10} {'Actual ret':>11}")
            print(f"  {'─' * 66}")
            for _, rd in diffs.iterrows():
                print(f"  {str(rd['earnings_date'])[:10]:<14} "
                      f"{'BUY' if rd['sig_a'] else 'SKIP':>10} "
                      f"{'BUY' if rd['sig_b'] else 'SKIP':>10} "
                      f"{rd['ss_a']:>10.3f} {rd['ss_b']:>10.3f} "
                      f"{rd['ret_a']:>+10.1f}%")

        both_buy = merged[(merged["sig_a"] == True) & (merged["sig_b"] == True)]
        if len(both_buy) > 0:
            ss_delta  = both_buy["ss_b"] - both_buy["ss_a"]
            pos_delta = both_buy["pos_b"] - both_buy["pos_a"]
            print(f"\n  On {len(both_buy)} quarters both fired BUY:")
            print(f"    Mean signal_strength shift  (80/20 − 50/50): {ss_delta.mean():>+.4f}")
            print(f"    Mean position size shift    (80/20 − 50/50): {pos_delta.mean():>+.1%}")
            direction = "MORE conviction → larger positions" if ss_delta.mean() > 0 \
                        else "LESS conviction → smaller positions"
            print(f"    → 80/20 fires with {direction}")

    print(f"\n{'=' * 70}")


# ── Step 6: Per-quarter trade log ─────────────────────────────────

def print_trade_log(results_list):
    print(f"\n{'─' * 95}")
    print(f"  FULL QUARTER LOG")
    print(f"  {'Date':<12} "
          f"{'50/50 sig':>10} {'ss':>7} {'pos':>7}  "
          f"{'80/20 sig':>10} {'ss':>7} {'pos':>7}  "
          f"{'Actual ret':>11}  Note")
    print(f"  {'─' * 93}")

    a = results_list[0]["trades_df"].copy()
    b = results_list[1]["trades_df"].copy()
    a["earnings_date"] = pd.to_datetime(a["earnings_date"])
    b["earnings_date"] = pd.to_datetime(b["earnings_date"])

    merged = pd.merge(
        a[["earnings_date", "signal", "signal_strength", "pos_size",
           "trade_return_pct", "entry_price", "outcome"]].rename(columns={
               "signal": "sig_a", "signal_strength": "ss_a",
               "pos_size": "pos_a", "outcome": "out_a"}),
        b[["earnings_date", "signal", "signal_strength", "pos_size"]].rename(columns={
               "signal": "sig_b", "signal_strength": "ss_b", "pos_size": "pos_b"}),
        on="earnings_date"
    ).sort_values("earnings_date")

    for _, r in merged.iterrows():
        sig_a_str = "BUY ✓" if r["sig_a"] else "SKIP  "
        sig_b_str = "BUY ✓" if r["sig_b"] else "SKIP  "

        # BUG FIXED: trade_return_pct is 0.0 for SKIP rows — do not display
        # that as a real return. Only show it when price data existed AND
        # at least one run actually traded the quarter.
        if (r["sig_a"] or r["sig_b"]) and pd.notna(r["entry_price"]):
            ret_str = f"{r['trade_return_pct']:>+.1f}%"
        else:
            ret_str = "     —"

        note = ""
        if r["sig_a"] != r["sig_b"]:
            note = "◀ DIVERGED"
        elif r["sig_a"] and abs(r["pos_b"] - r["pos_a"]) > 0.03:
            delta = r["pos_b"] - r["pos_a"]
            note  = f"pos shift {delta:>+.0%}"

        print(f"  {str(r['earnings_date'])[:10]:<12} "
              f"{sig_a_str:>10} {r['ss_a']:>7.3f} {r['pos_a']:>6.0%}  "
              f"{sig_b_str:>10} {r['ss_b']:>7.3f} {r['pos_b']:>6.0%}  "
              f"{ret_str:>11}  {note}")

    print(f"  {'─' * 93}")


# ── Step 7: Chart ─────────────────────────────────────────────────

def plot_comparison(results_list, ab, save_path="lulu_backtest_comparison.png"):
    """
    4-panel chart — each panel answers a distinct question:

    [0,0] EQUITY CURVES — both strategies + shared always-buy.
          fill_between the two strategy curves highlights the gap
          even when the difference is small.

    [0,1] CUMULATIVE P&L DELTA (80/20 minus 50/50, in dollars).
          The most direct answer to "did the weighting help and when?"
          Green = 80/20 ahead, blue = 50/50 ahead, annotated final gap.
          This panel is useful even when BUY/SKIP decisions are identical
          because it captures the position-sizing effect directly.

    [1,0] POSITION SIZE PER BUY QUARTER — grouped bar chart.
          One bar pair per traded quarter: faded = 50/50, solid = 80/20.
          Bars are colored green (WIN) or red (LOSS) by outcome.
          Answers: "does 80/20 size up on winners or losers?"

    [1,1] ROLLING 4-QUARTER WIN RATE — both weightings.
          Single-stock backtests are dominated by a handful of quarters;
          this shows whether one weighting is consistently better or
          just lucky over a short stretch.

    PREVIOUS VERSION PROBLEMS FIXED:
    - Distribution chart showed same trades for both runs → useless.
    - Signal scatter had massive overlap → unreadable.
    - Always-buy was only shown from results_list[0] with no explanation.
    - No panel directly showed the magnitude of the weighting difference.
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    fig.suptitle(
        f"LULU Backtest — 50/50 vs 80/20 Geo Weight  |  "
        f"BUY_DAYS={BUY_DAYS}  SELL_DAYS={SELL_DAYS}  START=${STARTING_CASH:,}",
        fontsize=12, fontweight="bold"
    )

    colors = [BLUE, PURPLE]

    def style(ax, title):
        ax.set_title(title, fontsize=10, fontweight="bold", pad=8)
        ax.grid(True, alpha=0.2, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # ── [0,0] Equity curves ───────────────────────────────────────
    ax = axes[0, 0]
    curves_norm = []
    for r, color in zip(results_list, colors):
        if r["eq_curve"] is not None:
            s   = r["eq_curve"] / r["eq_curve"].iloc[0]
            ret = (s.iloc[-1] - 1) * 100
            ax.plot(s.index, s, color=color, linewidth=2.2, zorder=3,
                    label=f"{r['label']}  ({ret:>+.1f}%,  Sharpe {r['sharpe_strat']:>+.2f})")
            curves_norm.append(s)

    # Fill the gap between the two strategies so the difference is
    # visible even when the curves are close together
    if len(curves_norm) == 2:
        both = pd.DataFrame({"a": curves_norm[0], "b": curves_norm[1]}).dropna()
        ax.fill_between(both.index, both["a"], both["b"],
                        where=(both["b"] >= both["a"]),
                        alpha=0.15, color=PURPLE, label="80/20 ahead")
        ax.fill_between(both.index, both["a"], both["b"],
                        where=(both["b"] < both["a"]),
                        alpha=0.15, color=BLUE,   label="50/50 ahead")

    if ab["curve"] is not None:
        ab_n   = ab["curve"] / ab["curve"].iloc[0]
        ab_ret = (ab_n.iloc[-1] - 1) * 100
        ax.plot(ab_n.index, ab_n, color=ORANGE, linewidth=1.5, linestyle="--",
                label=f"Always Buy 50%  ({ab_ret:>+.1f}%,  Sharpe {ab['sharpe']:>+.2f})")

    ax.axhline(1.0, color=GRAY, linewidth=0.7, linestyle=":")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
    ax.set_ylabel("Value (1.00 = start)")
    ax.legend(fontsize=8, loc="upper left")
    style(ax, "Portfolio Growth (Normalized to 1.00)")

    # ── [0,1] Cumulative P&L delta ────────────────────────────────
    ax = axes[0, 1]
    if (results_list[0]["eq_curve"] is not None and
            results_list[1]["eq_curve"] is not None):

        df_delta = pd.DataFrame({
            "a": results_list[0]["eq_curve"],
            "b": results_list[1]["eq_curve"],
        }).dropna()
        delta = df_delta["b"] - df_delta["a"]   # 80/20 minus 50/50, dollars

        ax.fill_between(delta.index, delta, 0,
                        where=(delta >= 0), alpha=0.45, color=PURPLE,
                        label="80/20 ahead")
        ax.fill_between(delta.index, delta, 0,
                        where=(delta <  0), alpha=0.45, color=BLUE,
                        label="50/50 ahead")
        ax.plot(delta.index, delta, color=GRAY, linewidth=0.9, zorder=2)
        ax.axhline(0, color=GRAY, linewidth=1.0, zorder=3)

        final_delta = float(delta.iloc[-1])
        ax.annotate(
            f"Final gap: ${final_delta:>+,.0f}",
            xy=(delta.index[-1], final_delta),
            xytext=(-8, 14 if final_delta >= 0 else -18),
            textcoords="offset points",
            fontsize=9,
            color=PURPLE if final_delta >= 0 else BLUE,
            ha="right",
        )

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_ylabel("80/20 minus 50/50 ($)")
    ax.legend(fontsize=8)
    style(ax, "Cumulative P&L Delta  (80/20 − 50/50)")

    # ── [1,0] Per-quarter position sizes — grouped bar chart ──────
    ax = axes[1, 0]
    a_df = results_list[0]["trades_df"].copy()
    b_df = results_list[1]["trades_df"].copy()

    a_buy = a_df[a_df["signal"] == True].set_index("earnings_date")
    b_buy = b_df[b_df["signal"] == True].set_index("earnings_date")
    all_buy_dates = sorted(set(a_buy.index) | set(b_buy.index))

    if all_buy_dates:
        x      = np.arange(len(all_buy_dates))
        width  = 0.38

        pos_a = [float(a_buy.loc[d, "pos_size"]) if d in a_buy.index else 0.0
                 for d in all_buy_dates]
        pos_b = [float(b_buy.loc[d, "pos_size"]) if d in b_buy.index else 0.0
                 for d in all_buy_dates]

        # Color by outcome (use whichever run actually traded the quarter)
        outcomes = []
        for d in all_buy_dates:
            if d in a_buy.index:
                outcomes.append(a_buy.loc[d, "outcome"])
            elif d in b_buy.index:
                outcomes.append(b_buy.loc[d, "outcome"])
            else:
                outcomes.append("SKIP")
        bar_colors = [GREEN if o == "WIN" else RED for o in outcomes]

        ax.bar(x - width / 2, pos_a, width,
               color=bar_colors, alpha=0.50, label="50/50 (faded)")
        ax.bar(x + width / 2, pos_b, width,
               color=bar_colors, alpha=1.00, edgecolor="white", linewidth=0.4,
               label="80/20 (solid)")

        ax.set_xticks(x)
        labels_x = [str(d)[:7] for d in all_buy_dates]
        ax.set_xticklabels(labels_x, rotation=55, ha="right", fontsize=7)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
        ax.axhline(POSITION_MIN, color=GRAY, linewidth=0.7, linestyle=":",
                   label=f"Min pos ({POSITION_MIN:.0%})")
        ax.set_ylabel("Position Size")

        legend_els = [
            Patch(facecolor=GREEN, alpha=0.85, label="WIN quarter"),
            Patch(facecolor=RED,   alpha=0.85, label="LOSS quarter"),
            Patch(facecolor=GRAY,  alpha=0.45, label="50/50 (faded bar)"),
            Patch(facecolor=GRAY,  alpha=1.00, label="80/20 (solid bar)"),
        ]
        ax.legend(handles=legend_els, fontsize=7, ncol=2)

    style(ax, "Position Size per BUY Quarter\n(color = win/loss outcome)")

    # ── [1,1] Rolling 4-quarter win rate ─────────────────────────
    ax = axes[1, 1]
    for r, color in zip(results_list, colors):
        df = r["trades_df"][r["trades_df"]["signal"] == True].copy()
        df["earnings_date"] = pd.to_datetime(df["earnings_date"])
        df = df.sort_values("earnings_date")
        df["win"] = (df["outcome"] == "WIN").astype(float)

        if len(df) >= 4:
            df["rolling_wr"] = df["win"].rolling(4).mean() * 100
            ax.plot(df["earnings_date"], df["rolling_wr"],
                    color=color, linewidth=2, marker="o", markersize=4,
                    label=f"{r['label']}  (overall {r['win_rate']:.0f}%)")

    ax.axhline(50, color=GRAY, linewidth=1.0, linestyle="--", label="50% line")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Win Rate (%)")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.legend(fontsize=8)
    style(ax, "Rolling 4-Quarter Win Rate (BUY quarters only)")

    plt.tight_layout()
    plt.savefig(save_path, dpi=130, bbox_inches="tight")
    print(f"\n  Chart saved to: {save_path}")
    plt.close()


# ── Main ──────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  LULU GEO-WEIGHT BACKTEST")
    print("  Comparing 50/50 (original) vs 80/20 (revenue-weighted)")
    print("=" * 70)

    print(f"\nLoading trends cache...")
    trends_raw, can_reweight = load_trends_for_lulu()
    if trends_raw is None or not can_reweight:
        return

    print(f"\nConnecting to WRDS...")
    db = connect_wrds()
    try:
        earnings_df_base = pull_lulu_fundamentals(db)
    finally:
        db.close()
        print("  WRDS connection closed.")

    # Price download is weight-independent — do it once
    print(f"\nDownloading {TICKER} price history...")
    earnings_for_price = compute_signals(
        earnings_df_base.copy(), apply_geo_weight(trends_raw, 0.50)
    )
    stock_data = download_prices(TICKER, earnings_for_price)
    if stock_data is None:
        print("ERROR: Could not download price data.")
        return
    print(f"  {len(stock_data)} trading days loaded.")

    # Always-buy computed once, independent of strategy run
    print(f"\nComputing shared always-buy benchmark...")
    ab = compute_shared_always_buy(earnings_df_base, trends_raw, stock_data)

    # Run both backtests
    results_list = []
    for label, geo_weight_us in WEIGHTS.items():
        print(f"\n{'─' * 70}")
        print(f"  Running: {label}  (US weight = {geo_weight_us:.0%})")
        print(f"{'─' * 70}")
        results_list.append(
            run_backtest(earnings_df_base, trends_raw, stock_data, geo_weight_us, label)
        )

    print_comparison(results_list, ab)
    print_trade_log(results_list)
    plot_comparison(results_list, ab, save_path="lulu_backtest_comparison.png")

    print(f"\nDone. Chart saved to: lulu_backtest_comparison.png")
    print(f"\nReminder: single-stock backtest — a handful of quarters can dominate")
    print(f"the total return. The full portfolio run is more statistically robust.")


if __name__ == "__main__":
    main()