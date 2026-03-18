# ================================================================
#  benchmark.py — Coin flip + Always Buy benchmarks
# ================================================================

import numpy as np
from config import STARTING_CASH, N_SIMULATIONS


def run_coin_flip(coin_opps, n_sims=N_SIMULATIONS):
    """Random direction, same position sizes as strategy."""
    results = []
    for _ in range(n_sims):
        cash = float(STARTING_CASH)
        for opp in coin_opps:
            direction = 1 if np.random.random() > 0.5 else -1
            ret       = direction * (opp["exit"] - opp["entry"]) / opp["entry"]
            cash     += cash * opp["pos_size"] * ret
        results.append(cash)
    return np.array(results)


def run_always_buy(coin_opps, fixed_pos=0.50):
    """Buy every quarter at fixed 50% position, no signal needed.
    Returns (final_cash, list_of_trade_returns_pct).
    """
    cash    = float(STARTING_CASH)
    returns = []
    for opp in coin_opps:
        ret   = (opp["exit"] - opp["entry"]) / opp["entry"]
        cash += cash * fixed_pos * ret
        returns.append(ret * 100)
    return cash, returns


def coin_flip_stats(coin_finals):
    return {
        "mean":     coin_finals.mean(),
        "mean_ret": (coin_finals.mean() - STARTING_CASH) / STARTING_CASH * 100,
        "p10":      np.percentile(coin_finals, 10),
        "p50":      np.percentile(coin_finals, 50),
        "p90":      np.percentile(coin_finals, 90),
    }


def beats_coin_pct(strategy_final_cash, coin_finals):
    return float((strategy_final_cash > coin_finals).mean() * 100)