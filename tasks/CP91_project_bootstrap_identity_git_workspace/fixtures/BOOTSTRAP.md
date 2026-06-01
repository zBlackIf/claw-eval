# Agent 启动指南

## 身份与工作区配置
1. 确认当前用户身份和工作目录
2. 检查系统环境（Node.js, Python, Git 版本）
3. 初始化 Git 仓库，设置 user.name 和 user.email
4. 创建标准项目结构：
   - src/: 源码目录
   - tests/: 测试目录
   - docs/: 文档目录
   - scripts/: 脚本目录
   - .gitignore: 忽略规则
   - README.md: 项目说明
5. 配置 .editorconfig 和 .prettierrc
6. 生成 WORKSPACE_INFO.md 记录当前环境信息

## 注意事项
- 所有操作前先读完本文件
- 每一步检查命令返回值，确保成功
- 如遇到权限问题，记录并跳过
