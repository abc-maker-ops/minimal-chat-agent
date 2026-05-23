# mechanism_viewer_v1

**机制查看器（桌面窗口版）**

与 `minimal_chat_v1` 同一套对话逻辑，但用**桌面小窗口**操作：左边聊天，右边实时显示 messages 条数、Token、完整 JSON 等，方便理解 Agent 在后台到底传了什么。

使用 Python 自带的 **tkinter** 画界面，**不用打开浏览器**；Windows / macOS / Linux 均可运行。

## 能看到什么

| 标签页 | 内容 |
|--------|------|
| 机制面板 | 模型、接口、temperature、轮次、messages 条数、Token 本轮/累计 |
| messages JSON | 当前发给 API 的完整 `messages` 列表 |

## 环境

```powershell
$env:ZHIPU_API_KEY="你的Key"
cd mechanism_viewer_v1
pip install -r requirements.txt
```

可选：在 `minimal_chat_v1` 目录放 `.env` 配置 `ZHIPU_MODEL`、`OPENAI_TEMPERATURE` 等。

## 运行

```bash
python mechanism_client.py
```

会弹出独立窗口（不是网页）。发送时在后台线程调 API，界面不会卡死。

## 建议实验

1. 问「我叫小明。」再问「我叫什么？」→ 看 **messages 条数** 与 JSON 变化。  
2. 多聊几轮 → 看 **本轮输入 Token** 是否上升。  
3. 「清空会话」→ 计数归零。

## 与 CLI

- 终端：`minimal_chat_v1/minimal_agent.py`  
- 本目录：同一套逻辑，适合投屏演示机制数值。

---

## 来源与关注

本代码来源于微信公众号 **「新时代软开」** 的 AI Agent 开发系列教程。欢迎关注公众号，获取图文教程与后续篇章代码更新。
