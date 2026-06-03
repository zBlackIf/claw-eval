"""Value factor calculations."""
import pandas as pd
import numpy as np


def book_to_market(book_values: pd.Series, market_caps: pd.Series) -> pd.Series:
    """Calculate book-to-market ratio.

    Args:
        book_values: Book value per share for each stock
        market_caps: Market capitalization for each stock
    """
    # BUG: No protection against zero or negative market_caps
    ratio = book_values / market_caps
    return ratio


def earnings_yield(earnings: pd.Series, prices: pd.Series) -> pd.Series:
    """Calculate earnings yield (E/P ratio)."""
    # BUG: No handling of zero prices
    return earnings / prices


def composite_value(book_values: pd.Series,
                    earnings: pd.Series,
                    market_caps: pd.Series,
                    prices: pd.Series) -> pd.Series:
    """Composite value score combining B/M and E/P."""
    bm = book_to_market(book_values, market_caps)
    ey = earnings_yield(earnings, prices)

    # Z-score normalize each component
    bm_z = (bm - bm.mean()) / bm.std()
    ey_z = (ey - ey.mean()) / ey.std()

    return 0.5 * bm_z + 0.5 * ey_z
