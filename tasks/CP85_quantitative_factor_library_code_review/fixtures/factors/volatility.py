"""Volatility factor calculations."""
import pandas as pd
import numpy as np


def realized_volatility(prices: pd.DataFrame, window: int = 20) -> pd.Series:
    """Calculate annualized realized volatility."""
    log_returns = np.log(prices / prices.shift(1))
    vol = log_returns.rolling(window=window).std() * np.sqrt(252)
    return vol.iloc[-1]


def idiosyncratic_volatility(returns: pd.DataFrame,
                              market_returns: pd.Series,
                              window: int = 60) -> pd.Series:
    """Calculate idiosyncratic vol after removing market beta."""
    residuals = pd.DataFrame(index=returns.index, columns=returns.columns)

    for col in returns.columns:
        stock_ret = returns[col].dropna()
        mkt_ret = market_returns.loc[stock_ret.index]
        if len(stock_ret) < window:
            residuals[col] = np.nan
            continue
        beta = stock_ret.rolling(window).cov(mkt_ret) / mkt_ret.rolling(window).var()
        residuals[col] = stock_ret - beta * mkt_ret

    return residuals.rolling(window).std().iloc[-1] * np.sqrt(252)
