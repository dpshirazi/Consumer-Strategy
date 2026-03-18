# ================================================================
#  plotting.py — All chart generation
# ================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import STARTING_CASH, STOCKS


def plot_strategy(strat_name, all_results, all_trades, all_coin_results,
             strat_combined_ret, coin_combined_ret, always_buy_combined_ret,
             total_invested,
             save_path="earnings_strategy_vs_coinflip.png"):

    valid_tickers = [t for t in STOCKS if t in all_results]
    n_plot        = len(valid_tickers)
    if n_plot == 0:
        print("No valid tickers to plot.")
        return

    fig, axes = plt.subplots(n_plot, 2, figsize=(16, 4.5 * n_plot))
    if n_plot == 1:
        axes = [axes]

    fig.suptitle(
        f"{strat_name} — Consumer Apparel Earnings Strategy vs Benchmarks\n"
        f"Strategy: {strat_combined_ret:+.1f}%  |  "
        f"Always Buy 50%: {always_buy_combined_ret:+.1f}%  |  "
        f"Coin Flip Avg: {coin_combined_ret:+.1f}%",
        fontsize=12, fontweight="bold"
    )

    for i, ticker in enumerate(valid_tickers):
        info      = STOCKS[ticker]
        trades_df = all_trades[ticker]
        r         = all_results[ticker]
        coin_dist = all_coin_results.get(ticker, np.array([STARTING_CASH]))

        _plot_portfolio(axes[i][0], ticker, info, trades_df, r, coin_dist)
        _plot_histogram(axes[i][1], ticker, info, r, coin_dist)

    plt.tight_layout()
    plt.savefig(save_path, dpi=130, bbox_inches="tight")
    print(f"\n📊 Chart saved to: {save_path}")
    plt.show()


def print_summary(strat_name, all_results, all_trades, strat_total, coin_total,
                  always_buy_total, total_invested):

    strat_ret      = (strat_total      - total_invested) / total_invested * 100
    coin_ret       = (coin_total       - total_invested) / total_invested * 100
    always_buy_ret = (always_buy_total - total_invested) / total_invested * 100

    W = 97
    print("\n" + "=" * W)
    print(f"  COMBINED SUMMARY — {strat_name}")
    print("=" * W)
    print(f"  {'Stock':<22} {'Strategy':>9} {'AlwaysBuy':>10} {'Coin Avg':>9} "
          f"{'Beats Coin':>11} {'Trades':>7} {'Win%':>6} {'AvgW':>7} {'AvgL':>7} {'Sharpe':>7}")
    print("  " + "-" * (W - 2))

    all_executed = []
    for ticker, r in all_results.items():
        beat_str  = f"{r['beats_coin_pct']:.0f}%"
        beat_flag = "✅" if r['beats_coin_pct'] >= 60 else ("⚠️" if r['beats_coin_pct'] >= 40 else "❌")
        print(f"  {r['name']:<22} {r['total_ret']:>+8.1f}% {r['always_buy_ret']:>+9.1f}% "
              f"{r['coin_mean_ret']:>+8.1f}%   {beat_str:>6} {beat_flag}  "
              f"{r['n_trades']:>5} {r['win_rate']:>5.0f}% "
              f"{r['avg_win']:>+6.1f}% {r['avg_loss']:>+6.1f}% {r['sharpe']:>+6.2f}")
        if ticker in all_trades:
            all_executed.append(all_trades[ticker][all_trades[ticker]["signal"] == True])

    if all_executed:
        import numpy as np
        combined = pd.concat(all_executed)
        ow = len(combined[combined["outcome"] == "WIN"]) / len(combined) * 100
        oa = combined["trade_return_pct"].mean()
        print("  " + "-" * (W - 2))
        print(f"  {'OVERALL':<22} {strat_ret:>+8.1f}% {always_buy_ret:>+9.1f}% "
              f"{coin_ret:>+8.1f}%   {'':>9}  {len(combined):>5} {ow:>5.0f}% {oa:>+6.1f}%")

    print(f"\n  Total Invested   : ${total_invested:>10,.0f}  (${STARTING_CASH:,}/stock)")
    print(f"  Strategy Total   : ${strat_total:>10,.0f}  ({strat_ret:+.1f}%)")
    print(f"  Always Buy Total : ${always_buy_total:>10,.0f}  ({always_buy_ret:+.1f}%)")
    print(f"  Coin Flip Avg    : ${coin_total:>10,.0f}  ({coin_ret:+.1f}%)")
    print(f"  (Sharpe ratios printed separately via daily equity curve)")
    print(f"\n  ✅ = strategy beats coin flip >60% of simulations")
    print(f"  ⚠️  = inconclusive (40–60%)")
    print(f"  ❌ = coin flip wins >60% of simulations")
    print("=" * W)

    return strat_ret, coin_ret, always_buy_ret


def _plot_portfolio(ax, ticker, info, trades_df, r, coin_dist):
    port_dates = [pd.Timestamp(row["earnings_date"]) for _, row in trades_df.iterrows()]
    port_vals  = trades_df["portfolio_value"].tolist()

    coin_p10 = np.percentile(coin_dist, 10)
    coin_p50 = np.percentile(coin_dist, 50)
    coin_p90 = np.percentile(coin_dist, 90)

    ax.step(port_dates, port_vals, color="#1565C0", linewidth=2,
            where="post", label="Strategy", zorder=3)
    ax.axhline(STARTING_CASH,         color="gray",    linestyle="--", linewidth=1,   label="Start $10k")
    ax.axhline(r["always_buy_final"], color="#2E7D32", linestyle="-",  linewidth=1.5,
               label=f"Always Buy 50%: {r['always_buy_ret']:+.1f}%")
    ax.axhline(coin_p50,              color="#E65100", linestyle="-",  linewidth=1.5, label="Coin median")
    ax.axhline(coin_p10,              color="#E65100", linestyle=":",  linewidth=1)
    ax.axhline(coin_p90,              color="#E65100", linestyle=":",  linewidth=1,   label="Coin 10–90th %ile")
    ax.fill_between([port_dates[0], port_dates[-1]], coin_p10, coin_p90,
                    alpha=0.08, color="#E65100")

    for _, row in trades_df[trades_df["signal"] == True].iterrows():
        color = "#2E7D32" if row["outcome"] == "WIN" else "#C62828"
        ax.annotate(
            f"{row['trade_return_pct']:+.1f}%\n({row['pos_size']:.0%})",
            xy=(pd.Timestamp(row["earnings_date"]), row["portfolio_value"]),
            fontsize=6, color=color, ha="center", va="bottom"
        )

    ax.set_title(
        f"{info['name']} ({ticker})  |  "
        f"Strategy: {r['total_ret']:+.1f}%  "
        f"AlwaysBuy: {r['always_buy_ret']:+.1f}%  "
        f"Coin: {r['coin_mean_ret']:+.1f}%  |  Sharpe: {r['sharpe']:+.2f}",
        fontsize=8
    )
    ax.set_ylabel("Portfolio Value ($)")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)


def _plot_histogram(ax, ticker, info, r, coin_dist):
    coin_rets = (coin_dist - STARTING_CASH) / STARTING_CASH * 100
    pct_rank  = (coin_rets < r["total_ret"]).mean() * 100

    ax.hist(coin_rets, bins=60, color="#E65100", alpha=0.6, label="Coin flip returns")
    ax.axvline(r["total_ret"],      color="#1565C0", linewidth=2,
               label=f"Strategy: {r['total_ret']:+.1f}%")
    ax.axvline(r["always_buy_ret"], color="#2E7D32", linewidth=2,
               label=f"Always Buy 50%: {r['always_buy_ret']:+.1f}%")
    ax.axvline(coin_rets.mean(),    color="#E65100", linewidth=1.5, linestyle="--",
               label=f"Coin avg: {coin_rets.mean():+.1f}%")
    ax.axvline(0, color="gray", linewidth=1, linestyle=":")

    ax.set_title(
        f"{info['name']} — Strategy in {pct_rank:.0f}th percentile of coin flip dist",
        fontsize=8
    )
    ax.set_xlabel("Return (%)")
    ax.set_ylabel("# Simulations")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)