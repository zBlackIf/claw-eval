"""fund_trader.py — 基金申购 / 赎回核心逻辑（含若干 bug，需审计）。

模块语义：
- 申购 (subscribe)：用户买入基金，扣现金，加份额（基于当日 NAV）
- 赎回 (redeem)：用户卖出份额，扣份额，加现金（基于当日 NAV，扣手续费）
- T+1 确认：T 日下单按 T 日收盘 NAV；T+1 才能赎回（避免日内套利）
- 手续费规则：申购 1.5% 前端；赎回根据持有时长阶梯（< 7d: 1.5%, 7-30d: 0.5%, >30d: 0%）
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
        # BUG-1: 没有校验用户现金是否充足
        # 应该：if self.cash.get(user_id, 0) < cash_amount: raise ...
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
            # BUG-2: 加权平均成本计算错误 — 应该用 net_cash / new_total_shares
            # 当前写法：错误地把 avg_cost 当成简单算术平均
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

        # BUG-3: T+1 校验缺失 —— 应阻止申购当日赎回
        # 正确：if trade_date <= pos.last_buy_date: raise ValueError("T+1 not satisfied")

        holding_days = (trade_date - pos.last_buy_date).days
        # BUG-4: 阶梯写反 —— 实际：< 7d 应该 1.5%、>30d 0%；下面的写反了
        if holding_days >= 30:
            fee_rate = 0.015                # 应该 0
        elif holding_days >= 7:
            fee_rate = 0.005
        else:
            fee_rate = 0.0                  # 应该 0.015

        gross_cash = shares * nav
        fee = gross_cash * fee_rate
        net_cash = gross_cash - fee

        pos.shares -= shares
        if pos.shares < 1e-9:
            del self.positions[key]

        # BUG-5: 浮点比较直接用 0；上面 < 1e-9 是 OK 的，但删除后用 self.cash[user_id] +=
        # 没保护，若 user_id 在 cash 里不存在（极少见），KeyError
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
