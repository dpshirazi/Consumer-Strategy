# ================================================================
#  strategy.py — Signal calculation + trade simulation
# ================================================================

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import timedelta
from helpers import get_price, sum_trends_exact          # ← required
from config  import STARTING_CASH, SIGNAL_THRESHOLD, POSITION_MIN, POSITION_MAX

RAW_SIGNAL_CAP = 2.0


def _ratio_to_signal(raw_ratio, steepness=10):
    if pd.isna(raw_ratio) or raw_ratio <= 0:
        return 0.0
    raw_ratio = min(raw_ratio, RAW_SIGNAL_CAP)
    return float(1 / (1 + np.exp(-steepness * (raw_ratio - 1))))


def _signal_to_position(signal_strength, threshold=SIGNAL_THRESHOLD, exponent=2):
    if signal_strength <= threshold:
        return POSITION_MIN
    t   = (signal_strength - threshold) / (1.0 - threshold)
    raw = POSITION_MIN + (POSITION_MAX - POSITION_MIN) * (t ** exponent)
    return float(np.clip(raw, POSITION_MIN, POSITION_MAX))


def compute_signals(earnings_df, trends_combined):
    """
    Add trends_ratio, raw_signal, signal_strength, and signal columns.
    Uses default params — optimizer re-applies signal thresholding itself.
    """
    df = earnings_df.copy()

    df["trends_this_q"] = np.array([
        sum_trends_exact(r["period_start"], r["period_end"], trends_combined)
        for _, r in df.iterrows()
    ], dtype=np.float64)

    df["trends_prior_q"] = np.array([
        sum_trends_exact(
            r["period_start"] - timedelta(days=364),
            r["period_end"]   - timedelta(days=364),
            trends_combined
        )
        for _, r in df.iterrows()
    ], dtype=np.float64)

    df["trends_ratio"] = df["trends_this_q"] / df["trends_prior_q"]
    df = df.dropna(subset=["trends_ratio"]).reset_index(drop=True)

    df["raw_signal"]      = df["trends_ratio"] / df["analyst_ratio"]
    df["signal_strength"] = df["raw_signal"].apply(_ratio_to_signal)
    df["signal"]          = df["signal_strength"] > SIGNAL_THRESHOLD

    n_buy  = df["signal"].sum()
    n_skip = (~df["signal"]).sum()
    print(f"  Signal: {n_buy} BUY, {n_skip} SKIP across {len(df)} quarters")

    return df


def download_prices(ticker, earnings_df):
    """Download adjusted stock prices from yfinance."""
    earliest = earnings_df["earnings_date"].min() - timedelta(days=60)
    try:
        stock_data = yf.download(
            ticker,
            start=earliest.strftime("%Y-%m-%d"),
            auto_adjust=True,
            progress=False
        )
        stock_data.index = pd.to_datetime(stock_data.index)
        return stock_data
    except Exception as e:
        print(f"  Price download error: {e}")
        return None


def simulate_trades(ticker, earnings_df, stock_data,
                    buy_days_before=14, sell_days_after=1,
                    signal_threshold=SIGNAL_THRESHOLD,
                    sigmoid_steepness=10,
                    pos_exponent=2):
    """
    Simulate earnings strategy trades with fully parameterized signal + sizing.

    Returns:
        trades_df:  full trade log DataFrame
        coin_opps:  list of dicts for coin flip benchmark
        final_cash: ending portfolio value
    """
    cash      = float(STARTING_CASH)
    trades    = []
    coin_opps = []

    for _, row in earnings_df.iterrows():
        ed        = row["earnings_date"]
        buy_date  = ed - timedelta(days=buy_days_before)
        sell_date = ed + timedelta(days=sell_days_after)
        entry     = get_price(buy_date,  stock_data)
        exit_p    = get_price(sell_date, stock_data)

        # Re-apply signal with current steepness + threshold params
        sig    = _ratio_to_signal(row["raw_signal"], sigmoid_steepness)
        signal = sig > signal_threshold

        if np.isnan(entry) or np.isnan(exit_p):
            trades.append(_build_trade_row(
                ticker, ed, row, sig, pos_size=0.0,
                entry=None, exit_p=None, ret=0.0, pnl=0.0,
                cash=cash, outcome="SKIP",
                signal_threshold=signal_threshold   # ← pass param through
            ))
            continue

        coin_opps.append({
            "pos_size": _signal_to_position(sig, signal_threshold, pos_exponent),
            "entry":    entry,
            "exit":     exit_p,
        })

        if not signal:
            trades.append(_build_trade_row(
                ticker, ed, row, sig, pos_size=0.0,
                entry=entry, exit_p=None, ret=0.0, pnl=0.0,
                cash=cash, outcome="SKIP",
                signal_threshold=signal_threshold   # ← pass param through
            ))
            continue

        pos_size = _signal_to_position(sig, signal_threshold, pos_exponent)
        ret      = (exit_p - entry) / entry
        pnl      = cash * pos_size * ret
        cash    += pnl

        trades.append(_build_trade_row(
            ticker, ed, row, sig, pos_size=pos_size,
            entry=entry, exit_p=exit_p, ret=ret, pnl=pnl,
            cash=cash, outcome="WIN" if pnl > 0 else "LOSS",
            signal_threshold=signal_threshold       # ← pass param through
        ))

    return pd.DataFrame(trades), coin_opps, cash


def compute_stats(trades_df, final_cash):
    executed = trades_df[trades_df["signal"] == True]
    wins     = executed[executed["outcome"] == "WIN"]
    losses   = executed[executed["outcome"] == "LOSS"]

    return {
        "ending_cash": final_cash,
        "total_ret":   (final_cash - STARTING_CASH) / STARTING_CASH * 100,
        "n_quarters":  len(trades_df),
        "n_trades":    len(executed),
        "win_rate":    len(wins)   / len(executed) * 100 if len(executed) > 0 else 0,
        "avg_ret":     executed["trade_return_pct"].mean() if len(executed) > 0 else 0,
        "avg_win":     wins["trade_return_pct"].mean()     if len(wins)     > 0 else 0,
        "avg_loss":    losses["trade_return_pct"].mean()   if len(losses)   > 0 else 0,
        "avg_pos":     executed["pos_size"].mean()         if len(executed) > 0 else 0,
        "sharpe":      float(executed["trade_return_pct"].mean() / executed["trade_return_pct"].std())
                       if len(executed) > 1 and executed["trade_return_pct"].std() > 0 else 0,
    }


def _build_trade_row(ticker, ed, row, sig, pos_size, entry, exit_p,
                     ret, pnl, cash, outcome, signal_threshold=SIGNAL_THRESHOLD):
    # FIX: use the signal_threshold param (not the global constant) so the
    # signal boolean is consistent when the optimizer varies the threshold.
    return {
        "ticker":           ticker,
        "earnings_date":    ed.date(),
        "signal":           sig > signal_threshold,          # ← was hardcoded
        "signal_strength":  round(sig, 3),
        "pos_size":         round(pos_size, 2),
        "trends_ratio":     round(row["trends_ratio"], 3),
        "analyst_ratio":    round(row["analyst_ratio"], 3),
        "raw_signal":       round(row["raw_signal"], 3),
        "entry_price":      round(entry, 2)  if entry  is not None and not np.isnan(entry)  else None,
        "exit_price":       round(exit_p, 2) if exit_p is not None and not np.isnan(exit_p) else None,
        "trade_return_pct": round(ret * 100, 2),
        "pnl":              round(pnl, 2),
        "portfolio_value":  round(cash, 2),
        "outcome":          outcome,
    }