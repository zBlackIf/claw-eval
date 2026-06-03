"""Feature engineering pipeline for ML model training."""
import pandas as pd
import numpy as np
from factors.momentum import calculate_momentum, rolling_momentum
from factors.volatility import realized_volatility
from factors.value import composite_value


class FeatureEngine:
    """Orchestrates factor calculation and feature matrix construction."""

    def __init__(self, prices: pd.DataFrame, fundamentals: pd.DataFrame):
        self.prices = prices
        self.fundamentals = fundamentals

    def build_features(self, date: str) -> pd.DataFrame:
        """Build feature matrix for a given date."""
        price_slice = self.prices.loc[:date]
        features = pd.DataFrame(index=price_slice.columns)

        features["momentum_20d"] = calculate_momentum(price_slice, 20)
        features["momentum_60d"] = calculate_momentum(price_slice, 60)
        features["volatility_20d"] = realized_volatility(price_slice, 20)

        if date in self.fundamentals.index:
            fund_data = self.fundamentals.loc[date]
            features["value_score"] = composite_value(
                fund_data.get("book_value", pd.Series()),
                fund_data.get("earnings", pd.Series()),
                fund_data.get("market_cap", pd.Series()),
                price_slice.iloc[-1],
            )

        return features

    def build_training_set(self, dates: list) -> pd.DataFrame:
        """Build training dataset across multiple dates.

        WARNING: This is very slow for large universes.
        """
        all_features = []

        # PERFORMANCE BUG: iterrows-style loop, should be vectorized
        for date in dates:
            features = self.build_features(date)
            features["date"] = date

            # Calculate forward returns as labels
            future_idx = self.prices.index.get_loc(date)
            if future_idx + 20 < len(self.prices):
                future_prices = self.prices.iloc[future_idx + 20]
                current_prices = self.prices.loc[date]
                features["forward_return_20d"] = (future_prices - current_prices) / current_prices

            all_features.append(features)

        result = pd.concat(all_features)

        # Winsorize extreme values
        for col in result.select_dtypes(include=[np.number]).columns:
            lower = result[col].quantile(0.01)
            upper = result[col].quantile(0.99)
            result[col] = result[col].clip(lower, upper)

        return result
