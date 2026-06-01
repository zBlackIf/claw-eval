import pandas as pd
import numpy as np

# 计算ATR指标用于衡量市场波动性
price_df['tr'] = np.maximum(
    price_df['high'] - price_df['low'],
    np.maximum(
        abs(price_df['high'] - price_df['close'].shift(1)),
        abs(price_df['low'] - price_df['close'].shift(1))
    )
)
price_df['atr'] = price_df['tr'].rolling(windo

# 计算均线
price_df['ma_short'] = price_df['close'].rolling(window=10).mean()
price_df['ma_long'] = price_df['close'].rolling(window=30).mean()

# BUG: 使用了位运算符而非逻辑运算符
entries = (price_df['close'] > price_df['ma_short']) & (price_df['ma_short'] > price_df['ma_long']) & (price_df['atr'] > price_df['atr'].rolling(window=5).mean())

exits = (price_df['close'] < price_df['ma_short']) | (price_df['atr'] < price_df['atr'].rolling(window=10).mean() * 0.5)
