import numpy as np
import pandas as pd
from datetime import timedelta


def build_equity_curve(all_trades, all_prices, starting_cash,
                       buy_days_before, sell_days_after):

    tickers = [t for t in all_trades if t in all_prices]
    if not tickers:
        return None, None

    # --- allocate capital equally across tickers ---
    capital_per_ticker = starting_cash / len(tickers)

    all_dates = sorted(set(d for t in tickers for d in all_prices[t].index))
    date_index = pd.DatetimeIndex(all_dates)

    sub_curves = {}

    for ticker in tickers:

        raw = all_prices[ticker]["Close"]
        prices = raw.squeeze() if hasattr(raw, "squeeze") else raw
        if hasattr(prices, "columns"):
            prices = prices.iloc[:, 0]

        prices = prices.sort_index()

        vals = pd.Series(np.nan, index=date_index, dtype=float)

        vals.loc[vals.index >= prices.index[0]] = capital_per_ticker
        cash = capital_per_ticker

        executed = (
            all_trades[ticker][all_trades[ticker]["outcome"].isin(["WIN", "LOSS"])]
            .copy()
            .sort_values("earnings_date")
        )

        resolved = []

        for _, trade in executed.iterrows():

            ed = pd.Timestamp(trade["earnings_date"])

            sc = prices.index[prices.index >= ed - timedelta(days=buy_days_before)]
            ex = prices.index[prices.index >= ed + timedelta(days=sell_days_after)]

            if not len(sc) or not len(ex) or sc[0] >= ex[0]:
                continue

            resolved.append((sc[0], ex[0], float(trade["pos_size"])))

        for t_idx, (entry_date, exit_date, pos_size) in enumerate(resolved):

            h = prices[(prices.index >= entry_date) & (prices.index <= exit_date)]

            if len(h) < 2:
                continue

            current_val = cash
            prev_p = float(np.array(h.iloc[0]).flat[0])

            for date, raw_p in h.items():

                p = float(np.array(raw_p).flat[0])

                if date == h.index[0]:
                    prev_p = p
                    continue

                ret = (p - prev_p) / prev_p if prev_p else 0

                current_val *= (1 + pos_size * ret)

                prev_p = p

                if date in vals.index:
                    vals[date] = current_val

            cash = current_val

            if exit_date in vals.index:

                next_entry = resolved[t_idx + 1][0] if t_idx + 1 < len(resolved) else None

                i0 = vals.index.get_loc(exit_date)

                i1 = (
                    vals.index.get_loc(next_entry)
                    if next_entry is not None and next_entry in vals.index
                    else len(vals)
                )

                vals.iloc[i0:i1] = cash

        sub_curves[ticker] = vals

    if not sub_curves:
        return None, None

    equity_df = pd.DataFrame(sub_curves).sort_index()
    equity_df = equity_df.ffill()

    # ── FIX: only start curve once every ticker has a value ──
    # Before this point the sum is artificially low (not all tickers active yet)
    first_full_date = equity_df.dropna(how="any").index[0]
    equity_df = equity_df.loc[equity_df.index >= first_full_date]

    portfolio_equity = equity_df.sum(axis=1)

    daily_rets = portfolio_equity.pct_change().dropna()

    return portfolio_equity, daily_rets


def compute_always_buy_sharpe(all_trades, all_prices, starting_cash,
                               buy_days_before, sell_days_after,
                               fixed_pos=0.50):

    ab_trades = {}

    for ticker, df in all_trades.items():

        ab = df[df["entry_price"].notna()].copy()

        ab["outcome"] = ab["trade_return_pct"].apply(
            lambda x: "WIN" if x > 0 else "LOSS"
        )

        ab["pos_size"] = fixed_pos

        ab_trades[ticker] = ab

    return build_equity_curve(
        ab_trades,
        all_prices,
        starting_cash,
        buy_days_before,
        sell_days_after,
    )


def compute_sharpe(daily_returns, label="Strategy"):

    if daily_returns is None or len(daily_returns) < 20:
        print(f"  {label}: insufficient data")
        return 0.0

    mean_d = daily_returns.mean()
    std_d = daily_returns.std(ddof=1)

    sharpe = (mean_d / std_d) * np.sqrt(252) if std_d > 1e-10 else 0.0

    ann_ret = (1 + mean_d) ** 252 - 1
    ann_vol = std_d * np.sqrt(252)

    print(f"  {label}:")
    print(f"    Ann. Return : {ann_ret*100:>+.2f}%")
    print(f"    Ann. Vol    : {ann_vol*100:>.2f}%")
    print(f"    Sharpe      : {sharpe:>+.3f}   [{len(daily_returns)} days]")

    return sharpe