# AI Agent 最小聊天示例（开源）

《AI Agent 开发系列》第 02 篇配套代码：**只调 Chat API + 多轮 `messages`**，无 system、无工具。

| 目录 | 说明 |
|------|------|
| [`minimal_chat_v1/`](minimal_chat_v1/) | 终端 CLI：维护 `messages`、循环调用智谱 GLM（OpenAI 兼容接口） |
| [`mechanism_viewer_v1/`](mechanism_viewer_v1/) | 桌面机制查看器：可视化 messages 条数、Token、JSON 列表 |

默认模型：**GLM-4.7-Flash**（`glm-4.7-flash`）。API Key 用环境变量 `ZHIPU_API_KEY`，勿提交到 Git。

## 快速开始

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
cd minimal_chat_v1
pip install -r requirements.txt
python minimal_agent.py
```

桌面查看器见 [`mechanism_viewer_v1/README.md`](mechanism_viewer_v1/README.md)。

## 来源与关注

本仓库代码来源于微信公众号 **「新时代软开」** 的 AI Agent 开发系列教程。欢迎关注公众号。

---

## License

MIT — 见 [LICENSE](LICENSE)。
