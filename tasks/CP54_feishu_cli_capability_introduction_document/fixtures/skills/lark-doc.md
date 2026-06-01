---
name: lark-doc
description: 飞书云文档：创建、读取、编辑飞书云文档。支持 DocxXML 与 Markdown 两种格式；可读取文档全文或按 block id / 关键词 / 标题章节做局部读取；编辑指令包含 block_insert_after / block_replace / block_delete / block_move_after / overwrite / append 等八种。
---

主要命令：
- `docs +create`：新建飞书云文档（DocxXML 或 Markdown）
- `docs +fetch`：读取文档内容，支持 simple / with-ids / full / outline / range / keyword / section 等模式
- `docs +update`：按指令编辑文档（block 级操作）
- `docs +search`：搜索云空间里的文档资源
