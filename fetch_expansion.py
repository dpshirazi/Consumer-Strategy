#!/usr/bin/env python3
# ================================================================
#  fetch_expansion.py
#
#  Fetches Google Trends for the expanded consumer universe:
#  restaurants, pets, fitness, beauty, specialty retail, and
#  more single-brand apparel/footwear.
#
#  COMPLETELY INDEPENDENT of the main strategy and supplemental
#  cache. Run once, then set USE_EXPANSION = True in config.py.
#
#  Safe to re-run — never overwrites already-fetched tickers.
# ================================================================

import os
import time
import random
import pickle
import pandas as pd
from pytrends.request import TrendReq

EXPANSION_STOCKS = {

    # ── Restaurants / QSR ─────────────────────────────────────────
    # Best new category for this signal. Search = transactional
    # intent. Analyst estimates lag viral moments by a full quarter.

    "CMG":   {"trends_keyword": "chipotle mexican grill",    "name": "Chipotle",              "ibes_ticker": "CMG"},
    "WING":  {"trends_keyword": "wingstop chicken wings",    "name": "Wingstop",              "ibes_ticker": "WING"},
    "TXRH":  {"trends_keyword": "texas roadhouse restaurant","name": "Texas Roadhouse",       "ibes_ticker": "TXRH"},
    "SHAK":  {"trends_keyword": "shake shack burger",        "name": "Shake Shack",           "ibes_ticker": "SHAK"},
    "BROS":  {"trends_keyword": "dutch bros coffee",         "name": "Dutch Bros Coffee",     "ibes_ticker": "BROS"},
    "DNUT":  {"trends_keyword": "krispy kreme donuts",       "name": "Krispy Kreme",          "ibes_ticker": "DNUT"},
    "FAT":   {"trends_keyword": "fatburger restaurant",      "name": "FAT Brands",            "ibes_ticker": "FAT"},
    "JACK":  {"trends_keyword": "jack in the box burger",    "name": "Jack in the Box",       "ibes_ticker": "JACK"},
    "PTLO":  {"trends_keyword": "portillos hot dogs",        "name": "Portillo's",            "ibes_ticker": "PTLO"},
    "DINE":  {"trends_keyword": "applebees restaurant",      "name": "Dine Brands (Applebee's)", "ibes_ticker": "DINE"},
    "EAT":   {"trends_keyword": "chilis restaurant",         "name": "Brinker (Chili's)",     "ibes_ticker": "EAT"},
    "CAKE":  {"trends_keyword": "cheesecake factory menu",   "name": "Cheesecake Factory",    "ibes_ticker": "CAKE"},
    "BJRI":  {"trends_keyword": "bj's restaurant brewhouse", "name": "BJ's Restaurants",      "ibes_ticker": "BJRI"},
    "RRGB":  {"trends_keyword": "red robin burger",          "name": "Red Robin",             "ibes_ticker": "RRGB"},
    "BLMN":  {"trends_keyword": "outback steakhouse",        "name": "Bloomin' Brands (Outback)", "ibes_ticker": "BLMN"},
    "DRI":   {"trends_keyword": "olive garden restaurant",   "name": "Darden (Olive Garden)", "ibes_ticker": "DRI"},
    "NDLS":  {"trends_keyword": "noodles and company",       "name": "Noodles & Company",     "ibes_ticker": "NDLS"},
    "FWRG":  {"trends_keyword": "first watch restaurant",    "name": "First Watch",           "ibes_ticker": "FWRG"},
    "CAVA":  {"trends_keyword": "cava mediterranean food",   "name": "CAVA Group",            "ibes_ticker": "CAVA"},
    "SMSM":  {"trends_keyword": "sweetgreen salad",          "name": "Sweetgreen",            "ibes_ticker": "SG"},

    # ── Pets ──────────────────────────────────────────────────────
    # High consumer intent, specific keywords, demand-driven revenue.

    "CHWY":  {"trends_keyword": "chewy pet food",            "name": "Chewy",                 "ibes_ticker": "CHWY"},
    "WOOF":  {"trends_keyword": "petco pet store",           "name": "Petco",                 "ibes_ticker": "WOOF"},
    "FRPT":  {"trends_keyword": "freshpet dog food",         "name": "Freshpet",              "ibes_ticker": "FRPT"},
    "BARK":  {"trends_keyword": "barkbox dog subscription",  "name": "BarkBox (BARK)",        "ibes_ticker": "BARK"},

    # ── Specialty Retail ──────────────────────────────────────────

    "FIVE":  {"trends_keyword": "five below store",          "name": "Five Below",            "ibes_ticker": "FIVE"},
    "BGFV":  {"trends_keyword": "big 5 sporting goods",      "name": "Big 5 Sporting Goods",  "ibes_ticker": "BGFV"},
    "PLAY":  {"trends_keyword": "dave and busters",          "name": "Dave & Buster's",       "ibes_ticker": "PLAY"},
    "BOWL":  {"trends_keyword": "bowlero bowling",           "name": "Bowlero",               "ibes_ticker": "BOWL"},
    "XPOF":  {"trends_keyword": "xponential fitness",        "name": "Xponential Fitness",    "ibes_ticker": "XPOF"},
    "YELP":  {"trends_keyword": "yelp restaurant reviews",   "name": "Yelp",                  "ibes_ticker": "YELP"},
    "VSCO":  {"trends_keyword": "victoria secret pink",      "name": "Victoria's Secret",     "ibes_ticker": "VSCO"},
    "BBWI":  {"trends_keyword": "bath body works",           "name": "Bath & Body Works",     "ibes_ticker": "BBWI"},
    "GME":   {"trends_keyword": "gamestop video games",      "name": "GameStop",              "ibes_ticker": "GME"},
    "SPWH":  {"trends_keyword": "sportsmans warehouse",      "name": "Sportsman's Warehouse", "ibes_ticker": "SPWH"},
    "LESL":  {"trends_keyword": "leslies pool supply",       "name": "Leslie's Pool",         "ibes_ticker": "LESL"},
    "PRTY":  {"trends_keyword": "party city supplies",       "name": "Party City",            "ibes_ticker": "PRTY"},

    # ── Online / Platform Retail ──────────────────────────────────

    "RVLV":  {"trends_keyword": "revolve clothing",          "name": "Revolve Group",         "ibes_ticker": "RVLV"},
    "TDUP":  {"trends_keyword": "thredup online thrift",     "name": "ThredUp",               "ibes_ticker": "TDUP"},
    "OSTK":  {"trends_keyword": "overstock furniture",       "name": "Overstock.com",         "ibes_ticker": "OSTK"},
    "RENT":  {"trends_keyword": "rent the runway dresses",   "name": "Rent the Runway",       "ibes_ticker": "RENT"},

    # ── Beauty / Personal Care (New Additions) ────────────────────

    "OLPX":  {"trends_keyword": "olaplex hair treatment",    "name": "Olaplex",               "ibes_ticker": "OLPX"},
    "IPAR":  {"trends_keyword": "jimmy choo perfume",        "name": "Inter Parfums",         "ibes_ticker": "IPAR"},
    "SKIN":  {"trends_keyword": "obagi skincare",            "name": "Obagi Medical",         "ibes_ticker": "SKIN"},
    "HIMS":  {"trends_keyword": "hims hair loss",            "name": "Hims & Hers Health",    "ibes_ticker": "HIMS"},
    "XELA":  {"trends_keyword": "salon loft hair",           "name": "Regis Corp / Salon Loft","ibes_ticker": "RGS"},

    # ── Fitness / Wellness ────────────────────────────────────────

    "PTON":  {"trends_keyword": "peloton bike",              "name": "Peloton",               "ibes_ticker": "PTON"},
    "PLNT":  {"trends_keyword": "planet fitness gym",        "name": "Planet Fitness",        "ibes_ticker": "PLNT"},
    "FNKO":  {"trends_keyword": "funko pop figure",          "name": "Funko",                 "ibes_ticker": "FNKO"},
    "BIRD":  {"trends_keyword": "allbirds shoes",            "name": "Allbirds",              "ibes_ticker": "BIRD"},
    "LULU2": {"trends_keyword": "lululemon mirror",          "name": "Lululemon Mirror (alt kw)", "ibes_ticker": "LULU"},
    # ^ alt keyword test only — do not add LULU2 to STOCKS in config.py

    # ── Home Goods ────────────────────────────────────────────────

    "WSM":   {"trends_keyword": "williams sonoma",           "name": "Williams-Sonoma",       "ibes_ticker": "WSM"},
    "RH":    {"trends_keyword": "restoration hardware",      "name": "RH",                    "ibes_ticker": "RH"},
    "ARHS":  {"trends_keyword": "arhaus furniture",          "name": "Arhaus",                "ibes_ticker": "ARHS"},
    "LOVE":  {"trends_keyword": "lovesac couch",             "name": "Lovesac",               "ibes_ticker": "LOVE"},
    "HVT":   {"trends_keyword": "haverty furniture store",   "name": "Haverty's Furniture",   "ibes_ticker": "HVT"},
    "SNBR":  {"trends_keyword": "sleep number mattress",     "name": "Sleep Number",          "ibes_ticker": "SNBR"},
    "TPX":   {"trends_keyword": "tempur pedic mattress",     "name": "Tempur Sealy",          "ibes_ticker": "TPX"},
    "PRPL":  {"trends_keyword": "purple mattress",           "name": "Purple Innovation",     "ibes_ticker": "PRPL"},

    # ── Apparel / Footwear (Remaining Gaps) ───────────────────────

    "CURV":  {"trends_keyword": "torrid plus size",          "name": "Torrid",                "ibes_ticker": "CURV"},
    "GIII":  {"trends_keyword": "dkny clothing",             "name": "G-III Apparel (DKNY)",  "ibes_ticker": "GIII"},
    "ONON2": {"trends_keyword": "on cloud running shoes",    "name": "On Running (alt kw)",   "ibes_ticker": "ONON"},
    # ^ alt keyword test only — do not add ONON2 to STOCKS in config.py
    "KELYA": {"trends_keyword": "wolverine work boots",      "name": "Kelley Services",       "ibes_ticker": "WWW"},
    "CATO":  {"trends_keyword": "cato fashions store",       "name": "Cato Corp",             "ibes_ticker": "CATO"},
    "DXLG":  {"trends_keyword": "destination xl big tall",   "name": "DXL Group",             "ibes_ticker": "DXLG"},
    "SCVL":  {"trends_keyword": "shoe carnival store",       "name": "Shoe Carnival",         "ibes_ticker": "SCVL"},
    "CAL":   {"trends_keyword": "naturalizer shoes",         "name": "Caleres (Naturalizer)", "ibes_ticker": "CAL"},
    "BURL2": {"trends_keyword": "burlington coat factory",   "name": "Burlington (alt kw)",   "ibes_ticker": "BURL"},
    # ^ alt keyword test only

    # ── Auto / Automotive Retail ──────────────────────────────────
    # Consumer-driven discretionary, search reflects purchase intent.

    "AN":    {"trends_keyword": "autonation car dealer",     "name": "AutoNation",            "ibes_ticker": "AN"},
    "KMX":   {"trends_keyword": "carmax used cars",          "name": "CarMax",                "ibes_ticker": "KMX"},
    "CVNA":  {"trends_keyword": "carvana buy car online",    "name": "Carvana",               "ibes_ticker": "CVNA"},
    "ORLY":  {"trends_keyword": "oreilly auto parts",        "name": "O'Reilly Auto Parts",   "ibes_ticker": "ORLY"},
    "AAP":   {"trends_keyword": "advance auto parts store",  "name": "Advance Auto Parts",    "ibes_ticker": "AAP"},

    # ── Travel / Experiences ─────────────────────────────────────
    # Post-COVID consumer spending on experiences is search-driven.

    "EXPE":  {"trends_keyword": "expedia flights hotels",    "name": "Expedia",               "ibes_ticker": "EXPE"},
    "BKNG":  {"trends_keyword": "booking com hotel",         "name": "Booking Holdings",      "ibes_ticker": "BKNG"},
    "ABNB":  {"trends_keyword": "airbnb vacation rental",    "name": "Airbnb",                "ibes_ticker": "ABNB"},
    "UBER":  {"trends_keyword": "uber eats delivery",        "name": "Uber (Eats focus)",     "ibes_ticker": "UBER"},
    "LYFT":  {"trends_keyword": "lyft ride share",           "name": "Lyft",                  "ibes_ticker": "LYFT"},
    "DASH":  {"trends_keyword": "doordash food delivery",    "name": "DoorDash",              "ibes_ticker": "DASH"},

    # ── Consumer Electronics / Gaming ─────────────────────────────

    "BBY":   {"trends_keyword": "best buy electronics store","name": "Best Buy",              "ibes_ticker": "BBY"},
    "SONO":  {"trends_keyword": "sonos speaker",             "name": "Sonos",                 "ibes_ticker": "SONO"},
    "HEAR":  {"trends_keyword": "turtle beach gaming headset","name": "Turtle Beach",         "ibes_ticker": "HEAR"},
    "VZIO":  {"trends_keyword": "vizio tv",                  "name": "VIZIO",                 "ibes_ticker": "VZIO"},
    "AAPL2": {"trends_keyword": "apple watch series",        "name": "Apple Watch (signal test)", "ibes_ticker": "AAPL"},
    # ^ AAPL is mega-cap and highly efficient — for research only

}

EXPANSION_CACHE = "trends_cache_expansion.pkl"


def fetch_expansion(cache_path=EXPANSION_CACHE, stocks=EXPANSION_STOCKS):
    """
    Fetch Google Trends for expansion stocks.
    Loads existing cache and only fetches missing tickers.
    Safe to re-run — never overwrites already-fetched data.
    """
    pytrends = TrendReq(hl="en-US", tz=360)
    trends_data = {}

    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            trends_data = pickle.load(f)
        already  = set(trends_data.keys())
        missing  = {t: s for t, s in stocks.items() if t not in already}
        if not missing:
            print(f"Expansion cache complete ({len(trends_data)} tickers). Nothing to fetch.")
            return trends_data
        print(f"Expansion cache has {len(trends_data)} tickers. "
              f"Fetching {len(missing)} missing: {list(missing.keys())}")
        stocks = missing
    else:
        print(f"Creating expansion cache. Fetching {len(stocks)} tickers "
              f"(this will take ~{len(stocks) * 40 // 60} minutes)...")

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

    print(f"\nExpansion cache saved: '{cache_path}' ({len(trends_data)} tickers total)")
    return trends_data


if __name__ == "__main__":
    fetch_expansion()