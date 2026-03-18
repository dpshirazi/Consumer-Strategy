# ================================================================
#  optimize.py — Walk-forward optimization
#
#  For each fold:
#    - Train on earlier years  → find best params (max quarterly Sharpe)
#    - Test  on next year      → record out-of-sample performance
#
#  Final result: average test Sharpe across all folds
# ================================================================

import numpy as np
import pandas as pd
import itertools
from datetime import timedelta

from config  import STARTING_CASH, POSITION_MIN, POSITION_MAX
from helpers import get_price, sum_trends_exact

# ── Parameter grid ────────────────────────────────────────────────
PARAM_GRID = {
    "buy_days_before":   [1, 2, 3, 5, 7, 10, 14],
    "sell_days_after":   [1, 2, 3, 4, 5, 6, 7],
    "signal_threshold":  [0.4, 0.5, 0.6],
    "sigmoid_steepness": [5, 10, 15],
    "pos_exponent":      [1, 2, 3],
}

# ── Walk-forward folds (train_end is exclusive of test period) ─────
FOLDS = [
    {"train": (2020, 2022), "test": 2023},
    {"train": (2020, 2023), "test": 2024},
    {"train": (2020, 2024), "test": 2025},
]


# ── Core functions (param-aware versions of helpers) ──────────────

def _ratio_to_signal(raw_ratio, steepness, cap=2.0):
    if pd.isna(raw_ratio) or raw_ratio <= 0:
        return 0.0
    raw_ratio = min(raw_ratio, cap)
    return float(1 / (1 + np.exp(-steepness * (raw_ratio - 1))))


def _signal_to_position(signal_strength, threshold, exponent):
    if signal_strength <= threshold:
        return POSITION_MIN
    t   = (signal_strength - threshold) / (1.0 - threshold)
    raw = POSITION_MIN + (POSITION_MAX - POSITION_MIN) * (t ** exponent)
    return float(np.clip(raw, POSITION_MIN, POSITION_MAX))


def _run_single(earnings_df, stock_data, params, year_filter=None):
    """
    Run one stock/one param set through the trade simulator.
    If year_filter is (start_year, end_year), only trade quarters
    where earnings_date.year is in that range (inclusive).

    Returns list of (earnings_date, trade_return_pct, pos_size) for traded quarters.
    """
    buy_days   = params["buy_days_before"]
    sell_days  = params["sell_days_after"]
    steepness  = params["sigmoid_steepness"]
    threshold  = params["signal_threshold"]
    exponent   = params["pos_exponent"]

    records = []

    for _, row in earnings_df.iterrows():
        ed = row["earnings_date"]

        if year_filter is not None:
            y1, y2 = year_filter
            if not (y1 <= ed.year <= y2):
                continue

        buy_date  = ed - timedelta(days=buy_days)
        sell_date = ed + timedelta(days=sell_days)
        entry     = get_price(buy_date,  stock_data)
        exit_p    = get_price(sell_date, stock_data)

        if np.isnan(entry) or np.isnan(exit_p):
            continue

        sig      = _ratio_to_signal(row["raw_signal"], steepness)
        signal   = sig > threshold
        if not signal:
            continue

        pos_size = _signal_to_position(sig, threshold, exponent)
        ret_pct  = (exit_p - entry) / entry * 100

        records.append({
            "earnings_date":    ed,
            "trade_return_pct": ret_pct,
            "pos_size":         pos_size,
        })

    return records


def _portfolio_quarterly_sharpe(all_records):
    """
    Given a list of trade records across all stocks, compute
    quarterly portfolio Sharpe:
      - Group by earnings_date quarter
      - Each stock equally weighted (1/n_stocks_that_quarter)
      - Portfolio return = sum(ret * pos_size / n)
      - Sharpe = mean(quarterly_rets) / std(quarterly_rets) * sqrt(4)
    """
    if not all_records:
        return -999.0

    df = pd.DataFrame(all_records)
    df["quarter"] = df["earnings_date"].dt.to_period("Q")

    period_rets = []
    for _, group in df.groupby("quarter"):
        n          = len(group)
        period_ret = (group["trade_return_pct"] * group["pos_size"] / n).sum()
        period_rets.append(period_ret)

    if len(period_rets) < 3:   # need at least 3 quarters to compute meaningful Sharpe
        return -999.0

    arr = np.array(period_rets)
    if arr.std() == 0:
        return -999.0

    return float((arr.mean() / arr.std()) * np.sqrt(4))


def run_walk_forward(all_earnings, all_prices):
    """
    Main walk-forward optimization loop.

    Args:
        all_earnings: dict  ticker → earnings_df (with raw_signal already computed)
        all_prices:   dict  ticker → stock price DataFrame

    Returns:
        best_params_per_fold: list of dicts
        test_results:         list of {fold, params, train_sharpe, test_sharpe}
        recommended_params:   param set with best average test Sharpe
    """
    # Build all param combinations
    keys   = list(PARAM_GRID.keys())
    combos = list(itertools.product(*[PARAM_GRID[k] for k in keys]))
    params_list = [dict(zip(keys, c)) for c in combos]
    n_combos    = len(params_list)

    print(f"\n{'='*65}")
    print(f"  WALK-FORWARD OPTIMIZATION")
    print(f"  {n_combos} parameter combinations × {len(FOLDS)} folds")
    print(f"{'='*65}")

    fold_results     = []
    best_per_fold    = []

    for fold in FOLDS:
        train_start, train_end = fold["train"]
        test_year              = fold["test"]

        print(f"\n  Fold: Train {train_start}–{train_end}  →  Test {test_year}")
        print(f"  Searching {n_combos} combinations...")

        # ── Training pass ─────────────────────────────────────────
        best_train_sharpe = -999.0
        best_params       = None

        for i, params in enumerate(params_list):
            all_records = []
            for ticker, earnings_df in all_earnings.items():
                if ticker not in all_prices:
                    continue
                records = _run_single(
                    earnings_df, all_prices[ticker], params,
                    year_filter=(train_start, train_end)
                )
                all_records.extend(records)

            sharpe = _portfolio_quarterly_sharpe(all_records)
            if sharpe > best_train_sharpe:
                best_train_sharpe = sharpe
                best_params       = params.copy()

            if (i + 1) % 50 == 0:
                print(f"    [{i+1}/{n_combos}] best so far: {best_train_sharpe:.3f}")

        print(f"  Best train Sharpe: {best_train_sharpe:.3f}")
        print(f"  Best params: {best_params}")

        # ── Test pass (out-of-sample) ─────────────────────────────
        test_records = []
        for ticker, earnings_df in all_earnings.items():
            if ticker not in all_prices:
                continue
            records = _run_single(
                earnings_df, all_prices[ticker], best_params,
                year_filter=(test_year, test_year)
            )
            test_records.extend(records)

        test_sharpe = _portfolio_quarterly_sharpe(test_records)
        n_test_trades = len(test_records)

        print(f"  Test  Sharpe: {test_sharpe:.3f}  ({n_test_trades} trades in {test_year})")

        best_per_fold.append(best_params)
        fold_results.append({
            "fold":          f"{train_start}-{train_end} → {test_year}",
            "best_params":   best_params,
            "train_sharpe":  best_train_sharpe,
            "test_sharpe":   test_sharpe,
            "n_test_trades": n_test_trades,
        })

    # ── Summary ───────────────────────────────────────────────────
    avg_test_sharpe = np.mean([r["test_sharpe"] for r in fold_results])

    print(f"\n{'='*65}")
    print(f"  WALK-FORWARD RESULTS")
    print(f"{'='*65}")
    print(f"  {'Fold':<28} {'Train Sharpe':>13} {'Test Sharpe':>12} {'Trades':>7}")
    print(f"  {'-'*63}")
    for r in fold_results:
        print(f"  {r['fold']:<28} {r['train_sharpe']:>+12.3f} {r['test_sharpe']:>+11.3f} {r['n_test_trades']:>7}")
    print(f"  {'-'*63}")
    print(f"  {'Average test Sharpe':<28} {'':>13} {avg_test_sharpe:>+11.3f}")

    # ── Pick recommended params ───────────────────────────────────
    # Use the params from the most recent fold (trained on most data)
    recommended = best_per_fold[-1]
    print(f"\n  Recommended params (from most recent fold):")
    for k, v in recommended.items():
        print(f"    {k:<22} = {v}")
    print(f"{'='*65}\n")

    return best_per_fold, fold_results, recommended