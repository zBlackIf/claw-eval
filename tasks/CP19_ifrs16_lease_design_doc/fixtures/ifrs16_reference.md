# IFRS 16 关键公式与概念参考（grader 内部对照用，不暴露给模型）

## 1. 使用权资产（Right-of-Use Asset, RoU）

**初始计量**：

```
RoU_initial = PV(future_lease_payments)
            + lease_payments_at_or_before_commencement
            + initial_direct_costs
            - lease_incentives
            + estimated_dismantling_costs
```

**后续计量**（成本模式，承租人最常用）：
- 按 **直线法** 在 `useful_life_months`（或租赁期，孰短）摊销
- `RoU_book_value(t) = RoU_initial − Σ depreciation(1..t)`

## 2. 租赁负债（Lease Liability）

**初始计量**：
```
Liability_initial = PV(future_lease_payments, discount_rate, payment_timing)
```

**后续计量**（实际利率法）：
```
interest_part(t)  = liability_balance(t-1) × effective_monthly_rate
principal_part(t) = payment(t) − interest_part(t)
liability(t)      = liability(t-1) − principal_part(t)
```

**月利率换算**（关键陷阱：不要直接除以 12）：
```
effective_monthly_rate = (1 + annual_rate)^(1/12) − 1
```

## 3. 折现率（Discount Rate）

按优先级取数：
1. **隐含利率**（implicit rate）—— 如果可计算
2. **增量借款利率**（IBR, Incremental Borrowing Rate）—— 实务最常用
3. 审计追溯：IBR 必须记录取数日期、参考基准（如同期同币种公司债 / Treasury）、加点幅度

## 4. 短期租赁豁免（Short-Term Lease Exemption）

- 期限 **≤ 12 个月**
- 不进 RoU / Liability
- 直线法计入 P&L 费用
- 必须**单独披露**短期租赁费用总额

## 5. 低价值租赁豁免（Low-Value Lease Exemption）

- 单项资产新购价值 **≤ $5,000 USD**（折算）
- 典型：办公电脑、平板、小型办公设备
- 不进 RoU / Liability
- 直线法计入 P&L 费用

## 6. 租赁修改（Lease Modification）

触发场景：续约 / 取消 / 缩减 / 扩张 / 付款条件变化。

处理流程：
1. 重新确定剩余租赁期
2. 用 modification date 当日 **revised discount rate**（新的 IBR）重新折现剩余支付
3. 调整 lease_liability 到新现值
4. 差额冲减 RoU（如调整后 RoU < 0，剩余部分进 P&L）
5. **不属于**单独租赁的扩张需要走这条路；新增独立资产的扩张属于新租赁

## 7. 必须覆盖的会计科目

| 科目 | 借/贷 | 触发事件 |
|---|---|---|
| 使用权资产 | 借 | 起租日 |
| 租赁负债 | 贷 | 起租日 |
| 财务费用-租赁利息 | 借 | 月度 |
| 折旧费用-使用权 | 借 | 月度 |
| 银行存款 | 贷 | 月度付款 |
| P&L-短期租赁费用 | 借 | 短期租赁付款 |
| P&L-低价值租赁费用 | 借 | 低价值租赁付款 |

## 8. 披露要求（合并报表附注）

- 各类租赁负债的到期分布（≤1y, 1-5y, >5y）
- RoU 资产按类别汇总
- 短期租赁与低价值租赁费用合计（必须分开披露）
- 与现金流量表的勾稽（融资活动支付的本金 vs 经营活动支付的利息）

## 9. 设计文档必须覆盖的"5+2"

设计文档应覆盖以下 5 个核心模块：
1. **起租与终止**（initial recognition + termination）
2. **月度核算**（depreciation + interest amortization + payment split）
3. **租赁修改**（modification with revised IBR）
4. **豁免分类**（short-term + low-value 自动识别）
5. **披露报表**（aging + classification）

加 2 个治理模块：
6. **IBR 治理**（取数源、审计 trail）
7. **审计追溯**（变更日志 + 重算回放）

## 10. 常见实现陷阱

| 陷阱 | 正确做法 |
|---|---|
| `monthly_rate = annual_rate / 12` | 应该 `(1 + annual_rate)^(1/12) − 1` |
| 修改不重新折现 | 必须用 modification date 当日 revised IBR |
| 短期 / 低价值混入 RoU | 应识别并单独走 P&L |
| 把折旧期等于租赁期 | 应取 `min(useful_life, lease_term)`（除非所有权转移） |
| 在事中支付（in_advance）当年末支付算 | PV 公式要区分 annuity_due vs annuity_in_arrears |
