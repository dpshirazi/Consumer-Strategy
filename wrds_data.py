# ================================================================
#  wrds_data.py — Compustat + IBES data pulling
# ================================================================

import numpy as np
import pandas as pd
from datetime import timedelta
from helpers import find_prior_year_row


def connect_wrds():
    """Connect to WRDS and return db object."""
    import wrds
    print("Connecting to WRDS...")
    db = wrds.Connection()
    print("Connected!\n")
    return db


def pull_compustat(db, ticker):
    sql = (
        "SELECT tic, datadate, rdq, revtq, epspxq "
        "FROM comp.fundq "
        "WHERE tic = '" + ticker + "' "
        "AND indfmt = 'INDL' AND datafmt = 'STD' "
        "AND popsrc = 'D' AND consol = 'C' "
        "AND revtq IS NOT NULL "
        "ORDER BY datadate"
    )
    try:
        df = db.raw_sql(sql, date_cols=["datadate", "rdq"])
    except Exception as e:
        print(f"  Compustat error: {e}, attempting rollback...")
        try:
            db.connection.rollback()
            df = db.raw_sql(sql, date_cols=["datadate", "rdq"])
        except Exception as e2:
            print(f"  Compustat failed: {e2}")
            return None

    if len(df) == 0:
        print(f"  No Compustat data for {ticker}.")
        return None

    df = (df.dropna(subset=["revtq", "datadate"])
          .rename(columns={"datadate": "period_end", "rdq": "earnings_date",
                           "revtq": "revenue", "epspxq": "eps_actual"})
          .sort_values("period_end").reset_index(drop=True))

    df["period_start"] = df["period_end"].shift(1) + timedelta(days=1)
    df.loc[df["period_start"].isna(), "period_start"] = (
        df.loc[df["period_start"].isna(), "period_end"] - timedelta(days=92)
    )

    print(f"  Compustat: {len(df)} quarters")
    return df


def pull_ibes_sales(db, ticker, ibes_ticker, rev_df=None):
    """
    Pull analyst revenue estimates from IBES.
    First tries SAL from ibes.statsum_xepsus (correct table for non-EPS measures).
    Falls back to EPS from ibes.statsum_epsus if SAL unavailable.
    Only keeps estimates published BEFORE the earnings announcement date
    to prevent look-ahead bias.
    """
    df = pd.DataFrame()

    # Primary: SAL (revenue) from xepsus table
    for field in ["ticker", "oftic"]:
        lookup = ibes_ticker if field == "ticker" else ticker
        sql = (
            "SELECT ticker, statpers, meanest, fpedats "
            "FROM ibes.statsum_xepsus "
            "WHERE " + field + " = '" + lookup + "' "
            "AND fpi = '6' AND fiscalp = 'QTR' AND measure = 'SAL' "
            "ORDER BY fpedats, statpers"
        )
        try:
            df = db.raw_sql(sql, date_cols=["statpers", "fpedats"])
            if len(df) > 0:
                print(f"  IBES: {len(df)} SAL (revenue) observations (via {field})")
                break
        except Exception:
            df = pd.DataFrame()

    # Fallback: EPS from epsus table
    if len(df) == 0:
        for field in ["ticker", "oftic"]:
            lookup = ibes_ticker if field == "ticker" else ticker
            sql = (
                "SELECT ticker, statpers, meanest, fpedats "
                "FROM ibes.statsum_epsus "
                "WHERE " + field + " = '" + lookup + "' "
                "AND fpi = '6' AND fiscalp = 'QTR' AND measure = 'EPS' "
                "ORDER BY fpedats, statpers"
            )
            try:
                df = db.raw_sql(sql, date_cols=["statpers", "fpedats"])
                if len(df) > 0:
                    print(f"  IBES: {len(df)} EPS observations (via {field}, SAL unavailable)")
                    break
            except Exception:
                df = pd.DataFrame()

    if len(df) == 0:
        print(f"  WARNING: No IBES data for {ticker}.")
        return None

    df = df.dropna(subset=["meanest", "fpedats"])

    # ── CRITICAL FIX ──────────────────────────────────────────────
    # Only keep estimates published BEFORE the earnings announcement.
    # Post-announcement estimates reflect actual results → look-ahead bias.
    if rev_df is not None:
        rdq_map = rev_df.set_index("period_end")["earnings_date"].to_dict()
        df["earnings_date_rdq"] = df["fpedats"].map(rdq_map)
        df = df[df["statpers"] < df["earnings_date_rdq"]]
    # ──────────────────────────────────────────────────────────────

    latest = (
        df.sort_values("statpers")
        .groupby("fpedats").last()
        .reset_index()
    )[["fpedats", "meanest"]].rename(
        columns={"fpedats": "period_end", "meanest": "rev_estimate"}
    )

    return latest


def build_earnings_table(rev_df, ibes_df):
    earnings_df = pd.merge(
        rev_df[["period_start", "period_end", "earnings_date", "revenue"]],
        ibes_df, on="period_end", how="left"
    ).sort_values("period_end").reset_index(drop=True)

    earnings_df = earnings_df.dropna(subset=["revenue"]).reset_index(drop=True)
    for col in ["period_end", "period_start", "earnings_date"]:
        earnings_df[col] = pd.to_datetime(earnings_df[col])

    earnings_df["rev_prior_year"] = np.array(
        [find_prior_year_row(r, earnings_df, "revenue")
         for _, r in earnings_df.iterrows()],
        dtype=object
    ).astype(float)

    earnings_df["analyst_ratio"] = (
        earnings_df["rev_estimate"] / earnings_df["rev_prior_year"].abs()
    )
    earnings_df = earnings_df.dropna(subset=["analyst_ratio"]).reset_index(drop=True)

    if len(earnings_df) == 0:
        return None

    return earnings_df