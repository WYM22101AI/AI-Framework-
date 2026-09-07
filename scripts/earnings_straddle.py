"""
Earnings Straddle Analysis: would buying calls + puts before earnings be profitable?

A straddle costs money (the premium). It profits only if the stock moves MORE
than the market expected (i.e., more than the implied volatility priced in).

This analysis:
1. Finds all earnings dates for each stock
2. Measures the actual price move (close-to-close around earnings)
3. Estimates what a straddle would have cost (from historical IV patterns)
4. Determines if the actual move exceeded the expected move
5. Computes the P&L of systematically buying straddles before every earnings

Usage:
    python scripts/earnings_straddle.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd
import numpy as np
import config


def get_earnings_and_prices(conn, symbol: str) -> pd.DataFrame:
    """Get earnings dates with surrounding price data."""
    # Get earnings dates
    earnings = conn.execute(f"""
        SELECT reported_date, surprise_pct
        FROM earnings
        WHERE symbol = '{symbol}' AND reported_date IS NOT NULL
        ORDER BY reported_date
    """).fetchdf()

    if earnings.empty:
        return pd.DataFrame()

    # Get daily prices
    prices = conn.execute(f"""
        SELECT timestamp::DATE as date, open, close, high, low
        FROM daily_bars
        WHERE symbol = '{symbol}'
        ORDER BY timestamp
    """).fetchdf()

    if prices.empty:
        return pd.DataFrame()

    prices = prices.set_index("date").sort_index()

    results = []
    for _, row in earnings.iterrows():
        earn_date = pd.Timestamp(row["reported_date"])

        # Find price before earnings (last close before or on earnings date)
        before = prices[prices.index <= earn_date]
        if before.empty:
            continue
        close_before = before.iloc[-1]["close"]
        date_before = before.index[-1]

        # Find price after earnings (first close after earnings date)
        after = prices[prices.index > earn_date]
        if after.empty:
            continue
        close_after = after.iloc[0]["close"]
        open_after = after.iloc[0]["open"]
        date_after = after.index[0]

        # Actual move
        actual_move_pct = abs(close_after / close_before - 1) * 100
        direction = "UP" if close_after > close_before else "DOWN"

        # Overnight gap (close before -> open after)
        gap_pct = abs(open_after / close_before - 1) * 100

        # Get 20-day realized volatility before earnings (annualized)
        lookback = prices[prices.index < earn_date].tail(30)
        if len(lookback) >= 20:
            daily_returns = lookback["close"].pct_change().dropna()
            realized_vol = daily_returns.std() * np.sqrt(252)
            # Expected daily move from realized vol
            expected_daily_move = realized_vol / np.sqrt(252) * 100
        else:
            realized_vol = None
            expected_daily_move = None

        # Straddle P&L estimate
        # A typical ATM straddle costs ~1.5x the expected daily move
        # (IV is inflated before earnings, typically 1.5-2x realized vol)
        if expected_daily_move:
            straddle_cost_estimate = expected_daily_move * 1.5  # conservative estimate
            straddle_pnl = actual_move_pct - straddle_cost_estimate
        else:
            straddle_cost_estimate = None
            straddle_pnl = None

        results.append({
            "symbol": symbol,
            "earnings_date": earn_date,
            "date_before": date_before,
            "date_after": date_after,
            "close_before": close_before,
            "close_after": close_after,
            "actual_move_pct": actual_move_pct,
            "direction": direction,
            "gap_pct": gap_pct,
            "surprise_pct": row["surprise_pct"],
            "realized_vol": realized_vol,
            "expected_daily_move": expected_daily_move,
            "straddle_cost_est": straddle_cost_estimate,
            "straddle_pnl_est": straddle_pnl,
        })

    return pd.DataFrame(results)


def analyze_straddle_results(df: pd.DataFrame, symbol: str):
    """Print analysis of straddle profitability."""
    if df.empty:
        print(f"\n{symbol}: No earnings data")
        return

    valid = df.dropna(subset=["straddle_pnl_est"])
    if valid.empty:
        print(f"\n{symbol}: Insufficient price history for straddle analysis")
        return

    print(f"\n{'='*60}")
    print(f"  EARNINGS STRADDLE ANALYSIS: {symbol}")
    print(f"  {len(valid)} earnings events analyzed")
    print(f"{'='*60}")

    # Average move
    print(f"\n  Average actual move:    {valid['actual_move_pct'].mean():.1f}%")
    print(f"  Average expected move:  {valid['expected_daily_move'].mean():.1f}%")
    print(f"  Average straddle cost:  {valid['straddle_cost_est'].mean():.1f}%")
    print(f"  Ratio actual/expected:  {valid['actual_move_pct'].mean() / valid['expected_daily_move'].mean():.2f}x")

    # Straddle P&L
    profitable = (valid["straddle_pnl_est"] > 0).sum()
    total = len(valid)
    avg_pnl = valid["straddle_pnl_est"].mean()

    print(f"\n  Straddle win rate:      {profitable}/{total} ({profitable/total*100:.0f}%)")
    print(f"  Average straddle P&L:   {avg_pnl:+.2f}% per event")
    print(f"  Total estimated P&L:    {valid['straddle_pnl_est'].sum():+.1f}% (all events combined)")

    # Biggest moves
    print(f"\n  Top 3 moves:")
    top = valid.nlargest(3, "actual_move_pct")
    for _, r in top.iterrows():
        print(f"    {r['earnings_date'].date()}: {r['direction']} {r['actual_move_pct']:.1f}% (straddle P&L: {r['straddle_pnl_est']:+.1f}%)")

    # By surprise direction
    pos_surprise = valid[valid["surprise_pct"].notna() & (valid["surprise_pct"] > 0)]
    neg_surprise = valid[valid["surprise_pct"].notna() & (valid["surprise_pct"] < 0)]
    if len(pos_surprise) > 0:
        print(f"\n  Positive surprise events: {len(pos_surprise)}, avg move: {pos_surprise['actual_move_pct'].mean():.1f}%")
    if len(neg_surprise) > 0:
        print(f"  Negative surprise events: {len(neg_surprise)}, avg move: {neg_surprise['actual_move_pct'].mean():.1f}%")

    # Verdict
    print(f"\n  VERDICT: ", end="")
    if avg_pnl > 0.5:
        print("Straddles appear PROFITABLE on average (but check the sample size)")
    elif avg_pnl > -0.5:
        print("Straddles roughly BREAK EVEN (edge too small after costs)")
    else:
        print("Straddles LOSE MONEY on average (IV overprices the actual moves)")

    return {
        "symbol": symbol,
        "n_events": total,
        "avg_actual_move": valid["actual_move_pct"].mean(),
        "avg_expected_move": valid["expected_daily_move"].mean(),
        "straddle_win_rate": profitable / total,
        "avg_straddle_pnl": avg_pnl,
    }


if __name__ == "__main__":
    conn = duckdb.connect(config.DB_PATH, read_only=True)

    stocks = ["TSLA", "NVDA", "AMZN", "AAPL", "MSFT", "META", "AMD", "GOOG"]
    summaries = []

    for symbol in stocks:
        df = get_earnings_and_prices(conn, symbol)
        result = analyze_straddle_results(df, symbol)
        if result:
            summaries.append(result)

    conn.close()

    if summaries:
        print(f"\n\n{'='*70}")
        print("SUMMARY: EARNINGS STRADDLE ACROSS ALL STOCKS")
        print(f"{'='*70}")
        print(f"{'Stock':<8} {'Events':>7} {'Avg Move':>9} {'Win Rate':>9} {'Avg P&L':>9}")
        print(f"{'-'*8} {'-'*7} {'-'*9} {'-'*9} {'-'*9}")
        for s in summaries:
            print(f"{s['symbol']:<8} {s['n_events']:>7} {s['avg_actual_move']:>8.1f}% {s['straddle_win_rate']*100:>8.0f}% {s['avg_straddle_pnl']:>+8.2f}%")

        avg_all = np.mean([s["avg_straddle_pnl"] for s in summaries])
        print(f"\nOverall average straddle P&L: {avg_all:+.2f}% per event")
        if avg_all > 0:
            print("Conclusion: Earnings straddles show a slight edge across these stocks.")
        else:
            print("Conclusion: Earnings straddles lose money on average. IV overprices the moves.")
