#!/usr/bin/env python3
# ================================================================
#  lulu_signal.py
#
#  Standalone signal checker for Lululemon (LULU).
#  No WRDS connection needed — uses hardcoded analyst estimates
#  from public sources (Visible Alpha / Wall Street consensus).
#
#  Run:  python lulu_signal.py
#
#  What it does:
#    1. Fetches Google Trends for "lululemon" (US + Global)
#    2. Applies 80/20 revenue-weighted composite (US heavy)
#    3. Computes trends_ratio = this_Q / prior_Q
#    4. Computes analyst_ratio = consensus_estimate / prior_year_actual
#    5. raw_signal = trends_ratio / analyst_ratio
#    6. Runs raw_signal through a sigmoid → signal_strength [0, 1]
#    7. Fires BUY if signal_strength > 0.5, else SKIP
#    8. Prints a full diagnostic breakdown
# ================================================================

import time
import warnings
import numpy as np
import pandas as pd
from pytrends.request import TrendReq

warnings.filterwarnings("ignore")


# ── 1. Configuration ──────────────────────────────────────────────

KEYWORD = "lululemon"

# LULU uses a 52/53-week retail fiscal calendar ending on the Sunday
# nearest January 31. Quarter boundaries come from Compustat (datadate).
#
# Verified from Compustat / LULU earnings releases:
#   FY2025 Q3 ended  : 2025-11-02  → Q4 FY2025 starts 2025-11-03
#   FY2025 Q4 ends   : 2026-02-01  (Sunday nearest Jan 31 2026)
#
#   FY2024 Q3 ended  : 2024-11-03  → Q4 FY2024 starts 2024-11-04
#   FY2024 Q4 ended  : 2025-02-02  (Sunday nearest Jan 31 2025 — confirmed)
#
# End dates matter more than start dates because pytrends is weekly:
# a one-day end difference can include or drop the final week entirely.
THIS_Q_START  = "2025-11-03"
THIS_Q_END    = "2026-02-01"
PRIOR_Q_START = "2024-11-04"
PRIOR_Q_END   = "2025-02-02"

# Combined window for single-call fetch (see fetch_all_trends).
# Must span PRIOR_Q_START through THIS_Q_END so both quarters are
# normalised on the same 0–100 scale within one pytrends response.
COMBINED_START = PRIOR_Q_START   # "2024-11-04"
COMBINED_END   = THIS_Q_END      # "2026-02-01"

# Revenue geography weights.
# LULU: ~80% North America, ~20% international.
# Rationale: US Google Trends searches skew transactional (purchasing intent);
# international searches skew aspirational (brand awareness).
# Canada is a meaningful market but can't be isolated from "global" in pytrends
# without a separate geo="CA" fetch — see NOTES at bottom if you want to add it.
GEO_WEIGHT_US     = 0.80
GEO_WEIGHT_GLOBAL = 0.20   # = 1 - GEO_WEIGHT_US

# Analyst estimates (public consensus as of Mar 15 2026).
# Source: Visible Alpha / Wall Street consensus.
#   Q4 FY2025 revenue estimate : ~$3.575B (mid of guidance range $3.56–$3.59B)
#   Q4 FY2024 actual revenue   :  $3.613B (Compustat / earnings release)
# analyst_ratio < 1 means analysts expect a slight YoY decline — a LOW bar.
Q4_FY2025_ESTIMATE  = 3.575   # $B, consensus
Q4_FY2024_ACTUAL    = 3.613   # $B, prior year actual

# Signal parameters — match your strategy defaults in strategy.py
SIGNAL_THRESHOLD  = 0.50   # signal_strength must exceed this to fire BUY
SIGMOID_STEEPNESS = 10     # controls how sharply the sigmoid transitions
RAW_SIGNAL_CAP    = 2.0    # prevents outlier trends spikes from dominating


# ── 2. Helper: sigmoid ────────────────────────────────────────────

def ratio_to_signal(raw_ratio, steepness=SIGMOID_STEEPNESS, cap=RAW_SIGNAL_CAP):
    """
    Maps raw_signal (a ratio) → signal_strength in [0, 1] via sigmoid.

    Why sigmoid instead of raw ratio?
      - Ratios have no upper bound; sigmoid compresses to [0,1] → comparable across stocks.
      - The inflection point is at raw_ratio = 1.0 (YoY flat).
      - steepness=10 means the sigmoid is steep: raw_ratio of 1.1 → ~0.73, 0.9 → ~0.27.
      - This rewards meaningfully positive trend divergence and punishes negative.
    """
    if pd.isna(raw_ratio) or raw_ratio <= 0:
        return 0.0
    raw_ratio = min(raw_ratio, cap)
    return float(1 / (1 + np.exp(-steepness * (raw_ratio - 1))))


# ── 3. Fetch Google Trends ────────────────────────────────────────

def fetch_combined_window(pytrends_obj, keyword, geo, label):
    """
    Fetch a single wide window spanning PRIOR_Q_START → THIS_Q_END,
    then slice into this-quarter and prior-quarter sub-series.

    WHY ONE WIDE CALL INSTEAD OF TWO NARROW CALLS:
      pytrends normalises each response independently to 0–100, where
      100 = the peak week within that specific request's timeframe.
      If you fetch this_q and prior_q as separate calls, each gets its
      own peak week and its own scale. That makes their sums incomparable:
      a sum of 800 from one call and 750 from another tells you nothing
      about relative search volume because the denominators differ.

      Fetching one window that contains both quarters forces pytrends to
      normalise across the entire span — the same peak week anchors both
      quarters to the same scale. The ratio this_sum / prior_sum is then
      a genuine YoY comparison. ✓

    Returns (this_q_series, prior_q_series) or (None, None) on failure.
    Both series share the same 0–100 normalisation.
    """
    timeframe = f"{COMBINED_START} {COMBINED_END}"
    for attempt in range(3):
        try:
            pytrends_obj.build_payload([keyword], cat=0, timeframe=timeframe, geo=geo)
            time.sleep(4 + attempt * 6)
            df = pytrends_obj.interest_over_time()
            if df.empty:
                print(f"    WARNING: empty response [{label} / {geo or 'global'}]")
                return None, None
            df = df.drop(columns=["isPartial"], errors="ignore")
            df.index = pd.to_datetime(df.index)

            # Slice into the two quarter windows using the corrected fiscal dates
            this_q  = df.loc[THIS_Q_START  : THIS_Q_END,  keyword]
            prior_q = df.loc[PRIOR_Q_START : PRIOR_Q_END, keyword]

            # Warn if either slice is suspiciously short (< 10 weeks for a ~13-week quarter)
            for name, s in [("this_Q", this_q), ("prior_Q", prior_q)]:
                if len(s) < 10:
                    print(f"    WARNING: {name} slice has only {len(s)} weeks "
                          f"— expected ~13. Check that fiscal dates are correct.")

            print(f"    [{label} / {geo or 'global'}]  "
                  f"combined={len(df)}wks  "
                  f"this_Q={len(this_q)}wks (sum={this_q.sum():.0f})  "
                  f"prior_Q={len(prior_q)}wks (sum={prior_q.sum():.0f})")
            return this_q, prior_q

        except Exception as e:
            if "429" in str(e):
                wait = 60 * (attempt + 1)
                print(f"    Rate limited [{label}], waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    ERROR [{label}]: {e}")
                return None, None

    return None, None


def fetch_all_trends():
    """
    Fetch US and global trends in two calls (one per geo), each spanning
    the full PRIOR_Q_START → THIS_Q_END window so both quarters are on
    the same normalisation scale.

    Returns a dict with keys: this_us, this_gl, prior_us, prior_gl
    Each value is a pandas Series or None if the fetch failed.
    """
    pytrends = TrendReq(hl="en-US", tz=360)

    print(f"\nFetching Google Trends for '{KEYWORD}'...")
    print(f"  Combined window : {COMBINED_START} → {COMBINED_END}")
    print(f"  This Q slice    : {THIS_Q_START} → {THIS_Q_END}")
    print(f"  Prior Q slice   : {PRIOR_Q_START} → {PRIOR_Q_END}")
    print(f"  (Single call per geo — both quarters share the same 0–100 scale)\n")

    this_us,  prior_us = fetch_combined_window(pytrends, KEYWORD, "US", "US")
    time.sleep(10)
    this_gl,  prior_gl = fetch_combined_window(pytrends, KEYWORD, "",   "Global")

    return {
        "this_us":  this_us,
        "this_gl":  this_gl,
        "prior_us": prior_us,
        "prior_gl": prior_gl,
    }


# ── 4. Compute weighted sums ──────────────────────────────────────

def weighted_sum(us_series, gl_series):
    """
    Combine US and global weekly series into a single revenue-weighted sum.

    Why sum instead of mean?
      sum_trends_exact() in helpers.py uses sum() — we match that here.
      The ratio (this/prior) cancels the scale, so sum vs mean doesn't matter
      as long as you're consistent in both windows. We use sum to stay faithful
      to the live strategy code.

    Why 80/20 instead of 50/50?
      LULU derives ~80% of revenue from North America. A US-only Google Trends
      signal is already a strong proxy for that. Overweighting international
      searches (which skew aspirational, not transactional) would dilute the
      signal with noise.
    """
    us_sum = float(us_series.sum()) if us_series is not None else None
    gl_sum = float(gl_series.sum()) if gl_series is not None else None

    if us_sum is None and gl_sum is None:
        return None
    if us_sum is None:
        # Fall back to global only — still informative, just noisier
        print("    WARNING: US trends unavailable, falling back to global only.")
        return gl_sum
    if gl_sum is None:
        # Fall back to US only
        print("    WARNING: Global trends unavailable, using US only.")
        return us_sum

    return us_sum * GEO_WEIGHT_US + gl_sum * GEO_WEIGHT_GLOBAL


# ── 5. Main signal computation ────────────────────────────────────

def compute_lulu_signal():

    import datetime
    today = datetime.date.today()

    print("=" * 60)
    print("  LULU Signal Checker — Q4 FY2025 Earnings")
    print(f"  Earnings date: March 17, 2026 (post-market)")
    print(f"  Today        : {today.strftime('%B %d, %Y')}")
    print(f"  Entry window : BUY_DAYS=3 → entry was ~March 14")
    print("=" * 60)

    # ── Step A: Fetch trends ──────────────────────────────────────
    data = fetch_all_trends()

    this_sum  = weighted_sum(data["this_us"],  data["this_gl"])
    prior_sum = weighted_sum(data["prior_us"], data["prior_gl"])

    if this_sum is None or prior_sum is None or prior_sum == 0:
        print("\nERROR: Could not compute trends_ratio — insufficient data.")
        return

    # ── Step B: Trends ratio ──────────────────────────────────────
    # trends_ratio = how much search volume changed YoY this quarter.
    # > 1.0 = more searches than last year = positive demand signal.
    # < 1.0 = fewer searches = negative demand signal.
    trends_ratio = this_sum / prior_sum

    # ── Step C: Analyst ratio ─────────────────────────────────────
    # analyst_ratio = what analysts expect relative to last year's actual.
    # > 1.0 = analysts expect growth (high bar to beat).
    # < 1.0 = analysts expect contraction (low bar — easier to beat).
    analyst_ratio = Q4_FY2025_ESTIMATE / Q4_FY2024_ACTUAL

    # ── Step D: Raw signal ────────────────────────────────────────
    # raw_signal = trends_ratio / analyst_ratio
    #
    # Intuition:
    #   If trends_ratio = 1.05 (searches up 5% YoY) and
    #      analyst_ratio = 0.99 (analysts expect -1% YoY),
    #   then raw_signal = 1.05 / 0.99 = 1.06 → sigmoid → ~0.65 → BUY.
    #
    #   The strategy is NOT just "are people searching more?"
    #   It's "are people searching MORE than analysts are assuming?"
    #   Analyst estimates are the baseline. Trends divergence from that
    #   baseline is the edge.
    raw_signal = trends_ratio / analyst_ratio

    # ── Step E: Sigmoid → signal_strength ────────────────────────
    signal_strength = ratio_to_signal(raw_signal)

    # ── Step F: Decision ──────────────────────────────────────────
    signal = signal_strength > SIGNAL_THRESHOLD

    # ── Step G: Position size (if BUY) ───────────────────────────
    # Mirrors _signal_to_position() in strategy.py
    POSITION_MIN = 0.10
    POSITION_MAX = 0.90
    POS_EXPONENT = 2
    if signal:
        t = (signal_strength - SIGNAL_THRESHOLD) / (1.0 - SIGNAL_THRESHOLD)
        pos_size = POSITION_MIN + (POSITION_MAX - POSITION_MIN) * (t ** POS_EXPONENT)
        pos_size = float(np.clip(pos_size, POSITION_MIN, POSITION_MAX))
    else:
        pos_size = 0.0

    # ── Print results ─────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  TRENDS INPUT")
    print(f"{'─' * 60}")
    print(f"  Keyword          : {KEYWORD}")
    print(f"  Geo weighting    : {GEO_WEIGHT_US*100:.0f}% US / {GEO_WEIGHT_GLOBAL*100:.0f}% Global")
    print(f"  This Q sum       : {this_sum:>10.1f}  ({THIS_Q_START} → {THIS_Q_END})")
    print(f"  Prior Q sum      : {prior_sum:>10.1f}  ({PRIOR_Q_START} → {PRIOR_Q_END})")
    print(f"  trends_ratio     : {trends_ratio:>10.4f}  {'↑ YoY' if trends_ratio > 1 else '↓ YoY'}")

    print(f"\n{'─' * 60}")
    print(f"  ANALYST INPUT")
    print(f"{'─' * 60}")
    print(f"  Q4 FY2025 estimate  : ${Q4_FY2025_ESTIMATE:.3f}B  (consensus)")
    print(f"  Q4 FY2024 actual    : ${Q4_FY2024_ACTUAL:.3f}B  (prior year)")
    print(f"  analyst_ratio       : {analyst_ratio:.4f}  "
          f"({'analysts expect growth — high bar' if analyst_ratio > 1 else 'analysts expect decline — low bar'})")

    print(f"\n{'─' * 60}")
    print(f"  SIGNAL COMPUTATION")
    print(f"{'─' * 60}")
    print(f"  raw_signal       = trends_ratio / analyst_ratio")
    print(f"                   = {trends_ratio:.4f} / {analyst_ratio:.4f}")
    print(f"                   = {raw_signal:.4f}")
    print(f"  signal_strength  = sigmoid(steepness={SIGMOID_STEEPNESS}, inflect=1.0)")
    print(f"                   = {signal_strength:.4f}")
    print(f"  threshold        = {SIGNAL_THRESHOLD}")

    print(f"\n{'═' * 60}")
    if signal:
        print(f"  SIGNAL:  ✅  BUY")
        print(f"  Position size : {pos_size:.0%} of portfolio")
        print(f"  Entry target  : ~March 14–15 (already in window)")
        print(f"  Exit target   : ~March 19 (sell_days=2 after March 17)")
    else:
        print(f"  SIGNAL:  ❌  SKIP")
        print(f"  signal_strength {signal_strength:.3f} did not clear threshold {SIGNAL_THRESHOLD}")
        print(f"  Interpretation: search volume does not materially exceed")
        print(f"  what analysts are already assuming in their estimates.")
    print(f"{'═' * 60}")

    # ── Sensitivity table ─────────────────────────────────────────
    # Shows how the signal would change if trends_ratio were different.
    # The actual trends_ratio is inserted into the table dynamically so
    # it always appears regardless of where it falls between the fixed rows.
    # BUG FIXED: the old marker used abs(tr - trends_ratio) < 0.01 against
    # fixed steps of 0.05–0.10, so it almost never matched. Now we insert
    # the actual value as its own row instead of hoping it lands nearby.
    print(f"\n  SENSITIVITY — what if trends_ratio were different?")
    print(f"  {'trends_ratio':>14} {'raw_signal':>12} {'sig_strength':>13} {'signal':>8}")
    print(f"  {'─' * 52}")

    fixed_rows = [0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20]
    # Only add the actual value if it doesn't fall within 0.025 of an existing row
    if not any(abs(trends_ratio - t) < 0.025 for t in fixed_rows):
        fixed_rows.append(trends_ratio)
    sensitivity_rows = sorted(fixed_rows)

    for tr in sensitivity_rows:
        rs     = tr / analyst_ratio
        ss     = ratio_to_signal(rs)
        flag   = "BUY ✅" if ss > SIGNAL_THRESHOLD else "SKIP ❌"
        marker = "  ← actual" if tr == trends_ratio else ""
        print(f"  {tr:>14.4f} {rs:>12.4f} {ss:>13.4f} {flag:>8}{marker}")

    print(f"\n  NOTE: This signal is point-in-time as of March 15, 2026.")
    print(f"  Earnings are March 17 post-market. Entry window (BUY_DAYS=3)")
    print(f"  technically opened March 14 — you are 1 day late to the")
    print(f"  strategy's tested entry. Proceed with awareness of that.")
    print(f"\n  This is not financial advice.")


# ── NOTES ON CANADA ───────────────────────────────────────────────
#
# LULU is headquartered in Vancouver and Canada is ~10–15% of revenue.
# pytrends geo="CA" would let you isolate Canadian search volume.
# A more precise weighting would be:
#   search_volume = 0.72 * search_us + 0.13 * search_ca + 0.15 * search_global
# To add this, duplicate the fetch calls with geo="CA" and add a
# search_ca column to your trends cache in fetch_supplemental.py.
# The current 80/20 approximation treats Canada as part of "global"
# which slightly dilutes the North American signal.

if __name__ == "__main__":
    compute_lulu_signal()