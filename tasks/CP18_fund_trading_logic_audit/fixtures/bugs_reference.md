# fund_trader.py 已知 bug 清单（grader 内部参考，不暴露给模型）

被审计模块 `fund_trader.py` 包含 5 个 bug，按严重程度排序：

## BUG-1: 申购未校验现金充足（CRITICAL，资金风险）
- 位置：`subscribe()` 内 `self.cash[user_id] = self.cash.get(user_id, 0) - cash_amount`
- 表现：用户现金不足时仍能下单，账户出现负数 cash
- 修复：先 `if self.cash.get(user_id, 0) < cash_amount: raise InsufficientFundsError`

## BUG-2: 加权平均成本计算错误（HIGH，盈亏统计不准）
- 位置：`subscribe()` 内补仓时 `pos.avg_cost = (pos.avg_cost + nav) / 2`
- 表现：当前用「上一次成本」和「这次 NAV」的简单算术平均，与持仓权重无关；
  应该按持仓份额加权：
  `new_avg_cost = (pos.shares * pos.avg_cost + shares * nav) / (pos.shares + shares)`
- 影响：用户看到的盈亏额、止盈止损线都错；监管报表也错

## BUG-3: T+1 校验缺失（CRITICAL，监管违规 + 套利漏洞）
- 位置：`redeem()` 内未检查 trade_date vs pos.last_buy_date
- 表现：用户当日申购后可立即赎回，构成日内套利；公募基金监管禁止
- 修复：`if trade_date <= pos.last_buy_date: raise TPlusOneViolation`

## BUG-4: 赎回手续费阶梯写反（HIGH，损害用户利益且违规）
- 位置：`redeem()` 内的 `if holding_days >= 30: fee_rate = 0.015` 起的三段判断
- 表现：当前实现：
  * 持有 ≥ 30 天 → 收 1.5%（应该 0%）
  * 持有 7-30 天 → 收 0.5%（正确）
  * 持有 < 7 天 → 收 0%（应该 1.5%）
- 修复：把第一档和第三档对调

## BUG-5: cash 字典 KeyError 风险（LOW，边界情况）
- 位置：`redeem()` 内 `self.cash[user_id] += net_cash`
- 表现：若该用户从未做过 subscribe（cash 字典里没 user_id），但有 position
  （如通过其他渠道导入），赎回时 KeyError
- 修复：`self.cash[user_id] = self.cash.get(user_id, 0) + net_cash`

## 评分锚点（grader 用）
满分需要至少识别 BUG-1, BUG-2, BUG-3, BUG-4（核心 4 个）；BUG-5 是加分项。
错误指出的 bug（false positive）会扣分。
