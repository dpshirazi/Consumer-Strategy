# ================================================================
#  helpers.py — Shared utility functions
# ================================================================

import numpy as np
import pandas as pd
from datetime import timedelta


def get_price(date, df):
    """Get the first available closing price on or after date."""
    subset = df.loc[df.index >= pd.Timestamp(date)]
    if subset.empty:
        return np.nan
    return float(np.array(subset["Close"].iloc[0]).flat[0])


def sum_trends_exact(start_date, end_date, trends_df):
    """
    Sum weekly search densities within exact date window.
    Returns NaN if fewer than 4 weeks of data found.
    """
    mask = (trends_df.index >= pd.Timestamp(start_date)) & \
           (trends_df.index <= pd.Timestamp(end_date))
    vals = trends_df.loc[mask, "search_volume"]
    if len(vals) >= 4:
        return float(vals.sum())
    return float("nan")


def find_prior_year_row(row, df, col):
    """Find the value of col from the same fiscal quarter one year ago."""
    target = row["period_end"] - timedelta(days=365)
    df2    = df.copy()
    df2["diff"] = (df2["period_end"] - target).abs()
    closest = df2.nsmallest(1, "diff").iloc[0]
    if closest["diff"] > timedelta(days=45):
        return np.nan
    return closest[col]