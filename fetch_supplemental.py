#!/usr/bin/env python3
# ================================================================
#  fetch_supplemental.py
#
#  Fetches Google Trends for additional consumer stocks and saves
#  to trends_cache_supplemental.pkl.
#
#  This script is COMPLETELY INDEPENDENT of the main strategy.
#  Run it once, then set USE_SUPPLEMENTAL = True in config.py
#  to include these stocks in future backtests.
#
#  To add more stocks later: just add them to SUPPLEMENTAL_STOCKS
#  below and re-run. The cache merges automatically.
# ================================================================

import os
import time
import random
import pickle
import pandas as pd
from pytrends.request import TrendReq

# ── Add or remove stocks here freely ─────────────────────────────
# RULE: Every stock here must be a single brand/concept.
# Multi-brand conglomerates (LVMH, PVH, Tapestry, etc.) are
# excluded because no single search term represents the whole company.
SUPPLEMENTAL_STOCKS = {

    # ── Single-Brand Apparel ──────────────────────────────────────
    "LEVI":  {"trends_keyword": "levis jeans",          "name": "Levi Strauss",        "ibes_ticker": "LEVI"},
    "EXPR":  {"trends_keyword": "express clothing",     "name": "Express",             "ibes_ticker": "EXPR"},
    "ASOS":  {"trends_keyword": "asos fashion",         "name": "ASOS",                "ibes_ticker": "ASOS"},
    "CHICO": {"trends_keyword": "chicos clothing",      "name": "Chico's FAS",         "ibes_ticker": "CHS"},
    "ANN":   {"trends_keyword": "ann taylor",           "name": "Ann Taylor (Ascena)", "ibes_ticker": "ASNA"},
    "TORRID":{"trends_keyword": "torrid plus size",     "name": "Torrid",              "ibes_ticker": "CURV"},

    # ── Single-Brand Footwear ─────────────────────────────────────
    "SKX":   {"trends_keyword": "skechers shoes",       "name": "Skechers",            "ibes_ticker": "SKX"},
    "CROX":  {"trends_keyword": "crocs shoes",          "name": "Crocs",               "ibes_ticker": "CROX"},
    "BOOT":  {"trends_keyword": "boot barn",            "name": "Boot Barn",           "ibes_ticker": "BOOT"},
    "ONON":  {"trends_keyword": "on cloud shoes",       "name": "On Running (alt kw)", "ibes_ticker": "ONON"},

    # ── Single-Brand Outdoor / Lifestyle ─────────────────────────
    "YETI":  {"trends_keyword": "yeti tumbler",         "name": "YETI Holdings",       "ibes_ticker": "YETI"},
    "HELE":  {"trends_keyword": "hydro flask",          "name": "Helen of Troy",       "ibes_ticker": "HELE"},
    "SFIX":  {"trends_keyword": "stitch fix",           "name": "Stitch Fix",          "ibes_ticker": "SFIX"},
    "REAL":  {"trends_keyword": "the realreal luxury",  "name": "The RealReal",        "ibes_ticker": "REAL"},
    "POSH":  {"trends_keyword": "poshmark app",         "name": "Poshmark",            "ibes_ticker": "POSH"},

    # ── Single-Brand Beauty / Personal Care ──────────────────────
    "ELF":   {"trends_keyword": "elf cosmetics",        "name": "e.l.f. Beauty",       "ibes_ticker": "ELF"},
    "ULTA":  {"trends_keyword": "ulta beauty",          "name": "Ulta Beauty",         "ibes_ticker": "ULTA"},
    "COTY":  {"trends_keyword": "coty perfume",         "name": "Coty",                "ibes_ticker": "COTY"},

    # ── Single-Brand Accessories / Jewelry ───────────────────────
    "FOSL":  {"trends_keyword": "fossil watch",         "name": "Fossil Group",        "ibes_ticker": "FOSL"},
    "SIG":   {"trends_keyword": "kay jewelers",         "name": "Signet Jewelers",     "ibes_ticker": "SIG"},
    "LAZR":  {"trends_keyword": "pandora jewelry",      "name": "Pandora (PANDY)",     "ibes_ticker": "PANDY"},
}

SUPPLEMENTAL_CACHE = "trends_cache_supplemental.pkl"


def fetch_supplemental(cache_path=SUPPLEMENTAL_CACHE, stocks=SUPPLEMENTAL_STOCKS):
    """
    Fetch Google Trends for supplemental stocks.
    Loads existing cache and only fetches missing tickers.
    Safe to re-run — never overwrites already-fetched data.
    """
    pytrends = TrendReq(hl="en-US", tz=360)
    trends_data = {}

    # Load existing supplemental cache if present
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            trends_data = pickle.load(f)
        already = set(trends_data.keys())
        missing = {t: s for t, s in stocks.items() if t not in already}
        if not missing:
            print(f"Supplemental cache complete ({len(trends_data)} tickers). Nothing to fetch.")
            return trends_data
        print(f"Supplemental cache has {len(trends_data)} tickers. Fetching {len(missing)} missing...")
        stocks = missing
    else:
        print(f"Creating supplemental cache. Fetching {len(stocks)} tickers...")

    for ticker, info in stocks.items():
        keyword = info["trends_keyword"]
        print(f"  [{ticker}] '{keyword}'...")

        for attempt in range(3):
            try:
                pytrends.build_payload([keyword], cat=0, timeframe="today 5-y", geo="US")
                time.sleep(10 + random.uniform(2, 5))
                us = pytrends.interest_over_time()

                pytrends.build_payload([keyword], cat=0, timeframe="today 5-y", geo="")
                time.sleep(10 + random.uniform(2, 5))
                gl = pytrends.interest_over_time()

                if us.empty or gl.empty:
                    print(f"    WARNING: empty response, skipping.")
                    break

                us = us.drop(columns=["isPartial"], errors="ignore")
                gl = gl.drop(columns=["isPartial"], errors="ignore")
                us.index = gl.index = pd.to_datetime(us.index)
                us.columns = ["search_us"]
                gl.columns = ["search_global"]

                combined = us.join(gl, how="inner")
                combined["search_volume"] = (
                    combined["search_us"] * 0.5 + combined["search_global"] * 0.5
                )
                trends_data[ticker] = combined
                print(f"    Got {len(combined)} weeks")
                break

            except Exception as e:
                if "429" in str(e):
                    wait = 60 * (attempt + 1)
                    print(f"    Rate limited (attempt {attempt+1}/3), waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"    ERROR: {e}, skipping.")
                    break

        # Save after every ticker so progress is never lost
        with open(cache_path, "wb") as f:
            pickle.dump(trends_data, f)

        time.sleep(15 + random.uniform(0, 5))

    print(f"\nSupplemental cache saved: '{cache_path}' ({len(trends_data)} tickers total)")
    return trends_data


if __name__ == "__main__":
    fetch_supplemental()