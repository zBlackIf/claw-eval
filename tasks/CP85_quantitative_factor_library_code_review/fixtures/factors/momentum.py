"""Momentum factor calculations for stock universe."""
import pandas as pd
import numpy as np


def calculate_momentum(prices: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """Calculate momentum factor as return over lookback period.

    Args:
        prices: DataFrame with DatetimeIndex and stock tickers as columns
        lookback: Number of trading days to look back

    Returns:
        Series of momentum scores per stock (latest date)
    """
    returns = prices.pct_change(lookback)
    # Use the most recent return as the momentum score
    momentum = returns.iloc[-1]
    return momentum


def calculate_momentum_with_reversal(prices: pd.DataFrame,
                                      lookback: int = 20,
                                      skip_recent: int = 5) -> pd.Series:
    """Momentum with short-term reversal adjustment.

    Skip the most recent `skip_recent` days to avoid short-term reversal.
    """
    # BUG: Look-ahead bias -- shift(-skip_recent) looks into the FUTURE
    future_adjusted = prices.shift(-skip_recent)
    returns = future_adjusted.pct_change(lookback)
    momentum = returns.iloc[-1]
    return momentum


def rolling_momentum(prices: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """Rolling momentum for each stock over time."""
    return prices.pct_change(window)
