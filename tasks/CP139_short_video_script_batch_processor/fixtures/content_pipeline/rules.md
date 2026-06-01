# 短视频脚本生成规则

## 输出格式

每条脚本生成一个独立的 .md 文件，文件名格式：`{campaign_id}_{platform}.md`

文件结构：

```
# Hook

（开场白内容）

## Body

（正文内容）

## CTA

（行动号召内容）

## Tags

- 标签1
- 标签2
- ...
```

## 平台时长限制

不同平台对脚本预估时长有上限要求：

| 平台 | 最大时长（秒） |
|------|--------------|
| douyin | 60 |
| kuaishou | 90 |
| video_hao | 120 |

如果模板预估时长超过平台限制，该条投放计划**跳过不生成**，在控制台输出警告信息。

## 变量替换规则

1. 模板中 `{{variable_name}}` 格式的占位符需要替换为实际值
2. 优先使用 campaigns.json 中该条投放的 `variables_override`
3. 如果 variables_override 中没有，查找 variables.json 的 `global_variables`
4. 如果都找不到，使用 variables.json 中的 `default_fallback` 值
5. tags 数组中的变量同样需要替换

## 平台兼容性检查

模板有 `platform_tags` 字段列出适用平台。如果投放计划指定的平台不在模板的
`platform_tags` 列表中，同样跳过该条，输出警告。

## 输出目录

所有生成文件放在 `/workspace/output/` 目录下。处理完成后在控制台输出汇总：
生成了多少条、跳过了多少条（含跳过原因）。
