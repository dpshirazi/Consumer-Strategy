# ================================================================
#  trends.py — Google Trends fetching with caching
# ================================================================

import os
import time
import random
import pickle
import pandas as pd
from pytrends.request import TrendReq
from config import STOCKS, TRENDS_CACHE


def fetch_trends(stocks=STOCKS, cache_path=TRENDS_CACHE):
    """
    Fetch Google Trends data (US + Global) for all stocks.
    Loads from cache if available — delete the cache file to re-fetch.

    Returns:
        dict: { ticker: DataFrame with columns [search_us, search_global, search_volume] }
    """
    pytrends    = TrendReq(hl="en-US", tz=360)
    trends_data = {}

    # Load existing cache if present, then only fetch what's missing
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            trends_data = pickle.load(f)
        # Also skip tickers already fetched in the original cache
        from config import TRENDS_CACHE
        orig_cache = set()
        if TRENDS_CACHE != cache_path and os.path.exists(TRENDS_CACHE):
            import pickle as _p
            orig_cache = set(_p.load(open(TRENDS_CACHE, "rb")).keys())
        missing = {t: s for t, s in stocks.items() if t not in trends_data and t not in orig_cache}
        if not missing:
            print(f"Loaded trends from cache ({len(trends_data)} tickers). "
                  f"Delete '{cache_path}' to re-fetch.\n")
            return trends_data
        print(f"  Cache has {len(trends_data)} tickers. "
              f"Fetching {len(missing)} missing: {list(missing.keys())}")
        stocks = missing
    else:
        # No extended cache yet — still skip tickers already in original cache
        from config import TRENDS_CACHE
        if TRENDS_CACHE != cache_path and os.path.exists(TRENDS_CACHE):
            import pickle as _p
            orig_cache = set(_p.load(open(TRENDS_CACHE, "rb")).keys())
            stocks = {t: s for t, s in stocks.items() if t not in orig_cache}
        print(f"Fetching Google Trends for {len(stocks)} NEW stocks (takes several minutes)...")

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

        # Polite delay between stocks to avoid rate limiting
        time.sleep(15 + random.uniform(0, 5))

    with open(cache_path, "wb") as f:
        pickle.dump(trends_data, f)
    print(f"\nTrends cached to '{cache_path}' ({len(trends_data)} tickers fetched).\n")

    return trends_data