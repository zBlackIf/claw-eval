"""fund_trader.py — 基金申购 / 赎回核心模块。

业务约定（来自财务部产品需求）：
- 申购 (subscribe)：用户买入基金，按当日 NAV 扣现金（含申购前端手续费），加份额
- 赎回 (redeem)：用户卖出份额，按当日 NAV 加现金（扣阶梯赎回手续费）
- T+1 确认：T 日申购的份额，T+1 才能赎回（监管要求，避免日内套利）
- 申购手续费：1.5% 前端
- 赎回手续费阶梯（按持有时长 holding_days）：
  * 持有 < 7 天 → 1.5%
  * 7 ≤ 持有 < 30 天 → 0.5%
  * 持有 ≥ 30 天 → 0%
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


@dataclass
class Position:
    user_id: str
    fund_code: str
    shares: float
    avg_cost: float                        # 加权平均成本
    last_buy_date: date                    # 最近一次申购日（用于赎回手续费阶梯）


@dataclass
class Trade:
    trade_id: str
    user_id: str
    fund_code: str
    trade_date: date
    side: str                              # "subscribe" | "redeem"
    nav: float
    amount_cash: float
    shares: float
    fee: float


@dataclass
class FundTrader:
    cash: dict[str, float] = field(default_factory=dict)         # user_id -> cash
    positions: dict[tuple[str, str], Position] = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)

    SUBSCRIPTION_FEE_RATE = 0.015

    def subscribe(self, user_id: str, fund_code: str, cash_amount: float,
                  nav: float, trade_date: date) -> Trade:
        if cash_amount <= 0:
            raise ValueError("cash_amount must be positive")
        self.cash[user_id] = self.cash.get(user_id, 0) - cash_amount

        fee = cash_amount * self.SUBSCRIPTION_FEE_RATE
        net_cash = cash_amount - fee
        shares = net_cash / nav

        key = (user_id, fund_code)
        pos = self.positions.get(key)
        if pos is None:
            self.positions[key] = Position(
                user_id=user_id, fund_code=fund_code,
                shares=shares, avg_cost=nav, last_buy_date=trade_date,
            )
        else:
            pos.avg_cost = (pos.avg_cost + nav) / 2
            pos.shares += shares
            pos.last_buy_date = trade_date

        trade = Trade(
            trade_id=f"T-{len(self.trades)+1:06d}",
            user_id=user_id, fund_code=fund_code, trade_date=trade_date,
            side="subscribe", nav=nav, amount_cash=cash_amount,
            shares=shares, fee=fee,
        )
        self.trades.append(trade)
        return trade

    def redeem(self, user_id: str, fund_code: str, shares: float,
               nav: float, trade_date: date) -> Trade:
        key = (user_id, fund_code)
        pos = self.positions.get(key)
        if pos is None or pos.shares < shares:
            raise ValueError("insufficient shares")

        holding_days = (trade_date - pos.last_buy_date).days
        if holding_days >= 30:
            fee_rate = 0.015
        elif holding_days >= 7:
            fee_rate = 0.005
        else:
            fee_rate = 0.0

        gross_cash = shares * nav
        fee = gross_cash * fee_rate
        net_cash = gross_cash - fee

        pos.shares -= shares
        if pos.shares < 1e-9:
            del self.positions[key]

        self.cash[user_id] += net_cash

        trade = Trade(
            trade_id=f"T-{len(self.trades)+1:06d}",
            user_id=user_id, fund_code=fund_code, trade_date=trade_date,
            side="redeem", nav=nav, amount_cash=net_cash,
            shares=-shares, fee=fee,
        )
        self.trades.append(trade)
        return trade

    def position_value(self, user_id: str, fund_code: str,
                       current_nav: float) -> Optional[float]:
        pos = self.positions.get((user_id, fund_code))
        if pos is None:
            return None
        return pos.shares * current_nav
