import pytest
import pandas as pd
import numpy as np
from factors.momentum import calculate_momentum
from factors.volatility import realized_volatility
from factors.value import book_to_market


@pytest.fixture
def sample_prices():
    dates = pd.date_range("2026-01-01", periods=60, freq="B")
    np.random.seed(42)
    data = {
        "AAPL": 100 + np.cumsum(np.random.randn(60) * 2),
        "GOOG": 200 + np.cumsum(np.random.randn(60) * 3),
    }
    return pd.DataFrame(data, index=dates)


def test_momentum_basic(sample_prices):
    result = calculate_momentum(sample_prices, lookback=20)
    assert len(result) == 2
    assert not result.isna().all()


def test_volatility_basic(sample_prices):
    result = realized_volatility(sample_prices, window=20)
    assert len(result) == 2
    assert (result > 0).all()


def test_book_to_market():
    bv = pd.Series({"AAPL": 50, "GOOG": 100})
    mc = pd.Series({"AAPL": 200, "GOOG": 500})
    result = book_to_market(bv, mc)
    assert result["AAPL"] == pytest.approx(0.25)
    assert result["GOOG"] == pytest.approx(0.20)
