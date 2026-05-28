# ac-common-service 互斥校验接口 — Postman 请求参数生成

ac-common-service 项目有一个 **功能互斥校验** 接口
`POST /ac-common-service/function/exclusion/check`，用来在开通/关闭功能时
判断是否违反互斥规则（例：开了 "免密支付" 就不能开 "单笔限额 > 5000"）。

## 你有的参考

- `src/function_exclusion_check.py` — 接口 Controller 层
- `src/function_exclusion_check_svc.py` — Service 层（含请求/响应 dataclass）
- `src/function_exclusion_enum.py` — `FunctionCode` 枚举 + 互斥关系 map

## 你要交付的

`tests/postman_params.json` — 一个合法的 Postman Collection v2.1 单请求文件，
满足：

1. JSON 解析后是 dict；根键包含 `info` 和 `item`
2. `info.name` = `ac-common-service 功能互斥校验`
3. `item` 是长度 **≥ 3** 的数组（三个测试场景：
   - `case_no_conflict`：开 `PAY_NO_PASSWORD` + `DAILY_LIMIT` → 应通过
   - `case_conflict`：开 `PAY_NO_PASSWORD` + `LIMIT_PER_TXN_5K` → 应失败
   - `case_empty`：空 `function_codes` → 校验参数错误）
3. 每个 item 必须有 `name` / `request` / `request.method = POST` /
   `request.url.raw` 含 `/ac-common-service/function/exclusion/check` /
   `request.body.raw` 是合法 JSON
4. 每条 body 至少包含：`tenant_id` / `user_id` / `function_codes`（数组）
5. 用 **enum** 里真实存在的 `FunctionCode` 值（不要编造）

## 硬约束

- 单文件产物，JSON 必须 parseable
- 不要改 `src/` 下的任何现有文件
- 不新增其他测试文件（如 `postman_*.json` 只允许一份）
