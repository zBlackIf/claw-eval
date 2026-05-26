# 量化策略优化原则

## 硬性约束
1. 禁止使用未来函数（shift必须为正数，不能使用未发生数据）
2. 禁止过拟合优化（参数不能过度拟合特定时间段）
3. 所有代码在全局作用域，不能定义自定义函数
4. 布尔运算必须使用 and/or/not，禁止 &/|/~
5. entries 和 exits 必须是布尔 Series

## 优化目标
- 提升收益（当前total_return为-12.3%）
- 降低回撤（当前max_drawdown为28.5%）
- 提高稳定性（当前sharpe_ratio为0.35）

## 回测环境
- 可用变量：price_df, pd, np
- price_df列：open, high, low, close, volume
- 引擎：vectorbt
