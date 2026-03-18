#!/usr/bin/env python3
import warnings
import numpy as np

warnings.filterwarnings("ignore")
np.random.seed(42)

from config     import (STOCKS, STOCKS_OPTIMIZE, STOCKS_EXPANSION,
                        STARTING_CASH, N_SIMULATIONS,
                        TRENDS_CACHE, TRENDS_CACHE_EXTENDED,
                        TRENDS_CACHE_SUPPLEMENTAL, TRENDS_CACHE_EXPANSION,
                        USE_SUPPLEMENTAL, USE_EXPANSION)
from trends     import fetch_trends
from wrds_data  import connect_wrds, pull_compustat, pull_ibes_sales, build_earnings_table
from strategy   import compute_signals, download_prices, simulate_trades, compute_stats
from benchmark  import run_coin_flip, run_always_buy, coin_flip_stats, beats_coin_pct
from plotting   import plot_strategy, print_summary
from regression import run_walk_forward_regression

BUY_DAYS  = 3
SELL_DAYS = 2

# ── 1. Fetch data ─────────────────────────────────────────────────
print("=" * 65)
print("  Multi-Stock Earnings Strategy + OLS Regression Analysis")
print("=" * 65)

trends_data = fetch_trends(stocks=STOCKS_OPTIMIZE, cache_path=TRENDS_CACHE)
trends_ext  = fetch_trends(stocks=STOCKS, cache_path=TRENDS_CACHE_EXTENDED)
trends_data.update(trends_ext)

if USE_SUPPLEMENTAL:
    import os, pickle
    if os.path.exists(TRENDS_CACHE_SUPPLEMENTAL):
        with open(TRENDS_CACHE_SUPPLEMENTAL, "rb") as f:
            supplemental = pickle.load(f)
        new_tickers = {t: v for t, v in supplemental.items() if t not in trends_data}
        trends_data.update(new_tickers)
        print(f"Supplemental trends loaded: +{len(new_tickers)} tickers ({len(trends_data)} total)\n")
    else:
        print(f"WARNING: USE_SUPPLEMENTAL=True but '{TRENDS_CACHE_SUPPLEMENTAL}' not found.\n")

if USE_EXPANSION:
    import os, pickle
    if os.path.exists(TRENDS_CACHE_EXPANSION):
        with open(TRENDS_CACHE_EXPANSION, "rb") as f:
            expansion = pickle.load(f)
        new_tickers = {t: v for t, v in expansion.items() if t not in trends_data}
        trends_data.update(new_tickers)
        for ticker, info in STOCKS_EXPANSION.items():
            if ticker not in STOCKS:
                STOCKS[ticker] = info
        print(f"Expansion trends loaded: +{len(new_tickers)} tickers ({len(trends_data)} total)\n")
    else:
        print(f"WARNING: USE_EXPANSION=True but '{TRENDS_CACHE_EXPANSION}' not found.\n")

db = connect_wrds()

all_earnings = {}
all_prices   = {}

print("\nFetching data...")
for ticker, info in STOCKS.items():
    if ticker not in trends_data:
        continue
    rev_df = pull_compustat(db, ticker)
    if rev_df is None:
        continue
    ibes_df = pull_ibes_sales(db, ticker, info["ibes_ticker"], rev_df=rev_df)
    if ibes_df is None:
        continue
    earnings_df = build_earnings_table(rev_df, ibes_df)
    if earnings_df is None or len(earnings_df) == 0:
        continue
    earnings_df = compute_signals(earnings_df, trends_data[ticker])
    if len(earnings_df) == 0:
        continue
    stock_data = download_prices(ticker, earnings_df)
    if stock_data is None or len(stock_data) == 0:
        continue
    all_earnings[ticker] = earnings_df
    all_prices[ticker]   = stock_data

db.close()
print(f"  → {len(all_earnings)} stocks ready.\n")

# ── 2. Baseline strategy ──────────────────────────────────────────
print("=" * 65)
print(f"  BASELINE: {BUY_DAYS}-Day Entry, Exit +{SELL_DAYS}d")
print("=" * 65)

all_results  = {}
all_trades   = {}
all_coin_res = {}

for ticker, info in STOCKS.items():
    if ticker not in all_earnings:
        continue

    trades_df, coin_opps, final_cash = simulate_trades(
        ticker, all_earnings[ticker], all_prices[ticker],
        buy_days_before=BUY_DAYS,
        sell_days_after=SELL_DAYS,
    )
    all_trades[ticker] = trades_df

    coin_finals                       = run_coin_flip(coin_opps, N_SIMULATIONS)
    always_buy_final, always_buy_rets = run_always_buy(coin_opps, fixed_pos=0.50)
    all_coin_res[ticker]              = coin_finals
    cs     = coin_flip_stats(coin_finals)
    bc     = beats_coin_pct(final_cash, coin_finals)
    ab_ret = (always_buy_final - STARTING_CASH) / STARTING_CASH * 100

    stats = compute_stats(trades_df, final_cash)
    all_results[ticker] = {
        **stats,
        "name":             info["name"],
        "coin_mean_ret":    cs["mean_ret"],
        "coin_p10":         cs["p10"],
        "coin_p90":         cs["p90"],
        "beats_coin_pct":   bc,
        "always_buy_final": always_buy_final,
        "always_buy_ret":   ab_ret,
        "always_buy_rets":  always_buy_rets,
    }

    print(f"  {ticker:<6} {info['name']:<28} "
          f"Strat: {stats['total_ret']:>+6.1f}%  "
          f"AlwaysBuy: {ab_ret:>+6.1f}%  "
          f"Trades: {stats['n_trades']}")

total_invested   = STARTING_CASH * len(all_results)
strat_total      = sum(r["ending_cash"]     for r in all_results.values())
coin_total       = sum(r["coin_mean_ret"] / 100 * STARTING_CASH + STARTING_CASH
                       for r in all_results.values())
always_buy_total = sum(r["always_buy_final"] for r in all_results.values())

strat_name = f"Baseline {BUY_DAYS}-Day Entry / Exit +{SELL_DAYS}d"
strat_ret, coin_ret, ab_ret = print_summary(
    strat_name, all_results, all_trades,
    strat_total, coin_total, always_buy_total, total_invested
)

plot_strategy(
    strat_name, all_results, all_trades, all_coin_res,
    strat_ret, coin_ret, ab_ret, total_invested,
    save_path="results_baseline.png"
)

# ── 3. Sharpe ─────────────────────────────────────────────────────
from sharpe import build_equity_curve, compute_sharpe, compute_always_buy_sharpe

print("\n" + "=" * 65)
print("  SHARPE  (daily equity curve, annualized)")
print("=" * 65)

equity_curve, daily_rets     = build_equity_curve(
    all_trades, all_prices, STARTING_CASH, BUY_DAYS, SELL_DAYS
)
strat_sharpe = compute_sharpe(daily_rets, label="Strategy")

ab_equity, ab_daily_rets     = compute_always_buy_sharpe(
    all_trades, all_prices, STARTING_CASH, BUY_DAYS, SELL_DAYS, fixed_pos=0.50
)
ab_sharpe = compute_sharpe(ab_daily_rets, label="Always Buy 50%")

print("=" * 65)

# ── 4. OLS Regression Analysis ────────────────────────────────────
fold_results, model_final = run_walk_forward_regression(
    all_earnings, all_prices, all_trades
)

# ── 5. Skipped vs Traded Quarters Analysis ────────────────────────
from skipped_analysis import run_skipped_analysis
run_skipped_analysis(all_trades, all_prices,
                     buy_days_before=BUY_DAYS, sell_days_after=SELL_DAYS)

# ── 6. Diagnostic charts ──────────────────────────────────────────
from charts import run_charts
run_charts(all_trades, all_prices, all_results, STARTING_CASH,
           buy_days=BUY_DAYS, sell_days=SELL_DAYS,
           strat_rets=daily_rets,
           ab_rets=ab_daily_rets,
           save_path="results_charts.png")
total_invested = STARTING_CASH * len(all_results)
strat_total = sum(r["ending_cash"] for r in all_results.values())
print(f"Invested: ${total_invested:,.0f}")
print(f"Final:    ${strat_total:,.0f}")
print(f"Return:   {(strat_total - total_invested) / total_invested * 100:+.1f}%")

for ticker, df in all_trades.items():
    executed = df[df["signal"] == True].head(5)
    print(f"\n{ticker}")
    print(executed[["earnings_date", "entry_price", "exit_price", 
                     "trade_return_pct", "signal_strength"]].to_string())


from sharpe import build_equity_curve
curve, rets = build_equity_curve(all_trades, all_prices, 10000, 3, 2)
print(curve.head(20))
print(curve.describe())

print("\nDone! 🚀")