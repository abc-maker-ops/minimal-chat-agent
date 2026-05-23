# AI Agent 最小聊天示例（开源）

用 Python 从零实现一个**最小的 AI 聊天 Agent**：调用大模型 Chat 接口，在程序里维护多轮对话列表（`messages`），每轮把**整段历史**发给模型。

本仓库包含两个入口，逻辑相同、界面不同：

| 目录 | 说明 |
|------|------|
| [`minimal_chat_v1/`](minimal_chat_v1/) | **终端版**：命令行里输入问题、看回复 |
| [`mechanism_viewer_v1/`](mechanism_viewer_v1/) | **桌面版**：窗口里聊天，并实时查看 messages 条数、Token 等 |

示例**不含**系统提示词（`system`）和工具调用，专注演示 Agent 最基础的一环：**记对话 + 调 API**。默认对接智谱 **GLM-4.7-Flash**（OpenAI 兼容接口）。API Key 用环境变量 `ZHIPU_API_KEY`，勿提交到 Git。

## 快速开始

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
cd minimal_chat_v1
pip install -r requirements.txt
python minimal_agent.py
```

桌面查看器见 [`mechanism_viewer_v1/README.md`](mechanism_viewer_v1/README.md)。

## 来源与关注

本仓库I Agent 开发系列》教程代码来源于微信公众号 **「新时代软开」**。欢迎关注公众号，获取图文教程与后续篇章代码。

---

## License

MIT — 见 [LICENSE](LICENSE)。
