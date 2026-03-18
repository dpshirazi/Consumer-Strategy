import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from sharpe import build_equity_curve, compute_always_buy_sharpe

BLUE   = "#1565C0"
ORANGE = "#E65100"
GREEN  = "#2E7D32"
RED    = "#C62828"
GRAY   = "#888888"

def _style(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

def _get_equity(all_trades, all_prices, starting_cash, buy_days, sell_days):
    strat_curve, strat_rets = build_equity_curve(
        all_trades, all_prices, starting_cash, buy_days, sell_days
    )
    ab_curve, ab_rets = compute_always_buy_sharpe(
        all_trades, all_prices, starting_cash, buy_days, sell_days, fixed_pos=0.50
    )
    if strat_curve is None or ab_curve is None:
        return None, None, None, None

    # align both curves to same date range
    equity_df = pd.DataFrame({"strat": strat_curve, "ab": ab_curve}).dropna(how="any")
    strat_curve = equity_df["strat"]
    ab_curve    = equity_df["ab"]

    # realign returns to same date range
    rets_df    = pd.DataFrame({"s": strat_rets, "b": ab_rets}).dropna(how="any")
    strat_rets = rets_df["s"]
    ab_rets    = rets_df["b"]

    return strat_curve, strat_rets, ab_curve, ab_rets

def _chart_normalized_equity(ax, all_trades, all_prices, starting_cash, buy_days, sell_days):
    strat_curve, _, ab_curve, _ = _get_equity(
        all_trades, all_prices, starting_cash, buy_days, sell_days
    )
    if strat_curve is None:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return

    s = strat_curve / strat_curve.iloc[0]
    b = ab_curve    / ab_curve.iloc[0]

    final_s = s.iloc[-1]
    final_b = b.iloc[-1]
    ret_s   = (final_s - 1) * 100
    ret_b   = (final_b - 1) * 100

    ax.plot(s.index, s, color=BLUE,   linewidth=2,
            label=f"Strategy       ({ret_s:+.1f}%,  final: {final_s:.3f})")
    ax.plot(b.index, b, color=ORANGE, linewidth=1.8, linestyle="--",
            label=f"Always Buy 50% ({ret_b:+.1f}%,  final: {final_b:.3f})")
    ax.axhline(1.0, color=GRAY, linewidth=0.8, linestyle=":")
    ax.fill_between(s.index, s, b, where=(s >= b), alpha=0.12, color=BLUE,   interpolate=True)
    ax.fill_between(s.index, s, b, where=(s <  b), alpha=0.12, color=ORANGE, interpolate=True)
    ax.set_xlim(s.index[0], s.index[-1])
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
    _style(ax, "Portfolio Growth (Normalized to 1.00)", "Date", "Value (1.00 = start)")
    ax.legend(fontsize=9)

def _chart_drawdown(ax, all_trades, all_prices, starting_cash, buy_days, sell_days):
    strat_curve, _, ab_curve, _ = _get_equity(
        all_trades, all_prices, starting_cash, buy_days, sell_days
    )
    if strat_curve is None:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return
    def dd(eq): return (eq - eq.cummax()) / eq.cummax() * 100
    ds, db = dd(strat_curve), dd(ab_curve)
    ax.fill_between(ds.index, ds, 0, alpha=0.35, color=BLUE,
                    label=f"Strategy   (max: {ds.min():.1f}%)")
    ax.fill_between(db.index, db, 0, alpha=0.25, color=ORANGE,
                    label=f"Always Buy (max: {db.min():.1f}%)")
    ax.plot(ds.index, ds, color=BLUE,   linewidth=1.2)
    ax.plot(db.index, db, color=ORANGE, linewidth=1.2)
    ax.axhline(0, color=GRAY, linewidth=0.8)
    ax.set_xlim(ds.index[0], ds.index[-1])
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    _style(ax, "Drawdown from Peak", "Date", "Drawdown (%)")
    ax.legend(fontsize=9)

def _chart_rolling_sharpe(ax, strat_rets, ab_rets, window=252):
    if strat_rets is None or ab_rets is None or len(strat_rets) < window:
        ax.text(0.5, 0.5, "Insufficient data", ha="center", va="center", transform=ax.transAxes)
        return

    combined   = pd.DataFrame({"s": strat_rets, "b": ab_rets}).dropna(how="any")
    strat_rets = combined["s"]
    ab_rets    = combined["b"]

    def rolling_sharpe(r):
        m = r.rolling(window).mean()
        s = r.rolling(window).std(ddof=1)
        return (m / s * np.sqrt(252)).where(s > 1e-10)

    s = rolling_sharpe(strat_rets)
    b = rolling_sharpe(ab_rets)

    s_final = s.dropna().iloc[-1] if len(s.dropna()) > 0 else float("nan")
    b_final = b.dropna().iloc[-1] if len(b.dropna()) > 0 else float("nan")

    ax.plot(s.index, s, color=BLUE,   linewidth=1.8,
            label=f"Strategy   (final: {s_final:+.2f})")
    ax.plot(b.index, b, color=ORANGE, linewidth=1.5, linestyle="--",
            label=f"Always Buy (final: {b_final:+.2f})")
    ax.axhline( 0,   color=GRAY, linewidth=0.8, linestyle=":")
    ax.axhline( 0.5, color=GRAY, linewidth=0.6, linestyle=":", alpha=0.5)
    ax.axhline(-0.5, color=GRAY, linewidth=0.6, linestyle=":", alpha=0.5)
    ax.set_xlim(s.index[0], s.index[-1])
    _style(ax, f"Rolling Sharpe (1-Year / {window}-day window)", "Date", "Annualized Sharpe")
    ax.legend(fontsize=9)

def _chart_rolling_sortino(ax, strat_rets, ab_rets, window=252):
    if strat_rets is None or ab_rets is None or len(strat_rets) < window:
        ax.text(0.5, 0.5, "Insufficient data", ha="center", va="center", transform=ax.transAxes)
        return

    combined   = pd.DataFrame({"s": strat_rets, "b": ab_rets}).dropna(how="any")
    strat_rets = combined["s"]
    ab_rets    = combined["b"]

    def rolling_sortino(r):
        def sortino_window(x):
            m        = x.mean()
            downside = x[x < 0]
            ds_std   = downside.std(ddof=1) if len(downside) > 1 else np.nan
            return (m / ds_std * np.sqrt(252)) if ds_std and ds_std > 1e-10 else np.nan
        return r.rolling(window).apply(sortino_window, raw=False)

    s = rolling_sortino(strat_rets)
    b = rolling_sortino(ab_rets)

    s_final = s.dropna().iloc[-1] if len(s.dropna()) > 0 else float("nan")
    b_final = b.dropna().iloc[-1] if len(b.dropna()) > 0 else float("nan")

    ax.plot(s.index, s, color=BLUE,   linewidth=1.8,
            label=f"Strategy   (final: {s_final:+.2f})")
    ax.plot(b.index, b, color=ORANGE, linewidth=1.5, linestyle="--",
            label=f"Always Buy (final: {b_final:+.2f})")
    ax.axhline( 0,   color=GRAY, linewidth=0.8, linestyle=":")
    ax.axhline( 0.5, color=GRAY, linewidth=0.6, linestyle=":", alpha=0.5)
    ax.axhline(-0.5, color=GRAY, linewidth=0.6, linestyle=":", alpha=0.5)
    ax.set_xlim(s.index[0], s.index[-1])
    _style(ax, f"Rolling Sortino (1-Year / {window}-day window)", "Date", "Annualized Sortino")
    ax.legend(fontsize=9)

def _chart_signal_vs_return(ax, all_trades):
    rows = []
    for ticker, df in all_trades.items():
        for _, row in df[df["signal"] == True].iterrows():
            rows.append({
                "x": float(row["signal_strength"]),
                "y": float(row["trade_return_pct"]),
                "win": row["outcome"] == "WIN"
            })
    if not rows:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return
    df = pd.DataFrame(rows)
    ax.scatter(df["x"], df["y"], c=[GREEN if w else RED for w in df["win"]],
               alpha=0.45, s=35, edgecolors="none")
    if df["x"].std() > 1e-10:
        m, b = np.polyfit(df["x"], df["y"], 1)
        xs = np.linspace(df["x"].min(), df["x"].max(), 100)
        ax.plot(xs, m * xs + b, color=BLUE, linewidth=2, label=f"OLS slope: {m:+.2f}%/unit")
        corr = np.corrcoef(df["x"], df["y"])[0, 1]
        ax.text(0.97, 0.97, f"r = {corr:+.3f}\nn = {len(df)}",
                transform=ax.transAxes, ha="right", va="top", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))
    ax.axhline(0, color=GRAY, linewidth=0.8, linestyle=":")
    ax.axvline(0.5, color=GRAY, linewidth=0.8, linestyle=":")
    _style(ax, "Signal Strength vs. Trade Return", "Signal Strength", "Trade Return (%)")
    ax.legend(fontsize=8)

def run_charts(all_trades, all_prices, all_results, starting_cash,
               buy_days=3, sell_days=2, strat_rets=None, ab_rets=None,
               save_path="results_charts.png", **kwargs):

    fig, axes = plt.subplots(3, 2, figsize=(14, 21))
    fig.suptitle("Strategy Diagnostics", fontsize=13, fontweight="bold")

    _chart_normalized_equity(axes[0, 0], all_trades, all_prices, starting_cash, buy_days, sell_days)
    _chart_drawdown         (axes[0, 1], all_trades, all_prices, starting_cash, buy_days, sell_days)
    _chart_rolling_sharpe   (axes[1, 0], strat_rets, ab_rets)
    _chart_rolling_sortino  (axes[1, 1], strat_rets, ab_rets)
    _chart_signal_vs_return (axes[2, 0], all_trades)

    # leave bottom-right blank or add a note
    axes[2, 1].axis("off")
    axes[2, 1].text(0.5, 0.5, "Additional diagnostics\ncoming soon",
                    ha="center", va="center", transform=axes[2, 1].transAxes,
                    fontsize=11, color=GRAY)

    plt.tight_layout()
    plt.savefig(save_path, dpi=130, bbox_inches="tight")
    print(f"\n📊 Diagnostic charts saved to: {save_path}")
    plt.close()