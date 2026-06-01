# 微信桌面自动化项目

## 目标

通过 Python 自动化控制桌面微信客户端，实现从指定群组采集旅游消息并发布到朋友圈。

## 环境

- Zorin OS 主机运行 wechatAltman3 微信客户端
- Python 代码运行在 Flatpak 沙盒（VS Code）内
- 需要 flatpak-spawn --host 桥接到宿主机执行 GUI 操作

## 目标群组

1. 天天国内供应商产品群（一）
2. 天天逸游2群享包车出游福利
3. 广告群）天天假期&抵玩假期

## 依赖

- pyautogui: GUI 自动化
- pyperclip: 剪贴板操作
- xdotool: 窗口管理（主机侧）
