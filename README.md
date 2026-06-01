# AI Agent 最小聊天示例（开源）

用 Python 从零实现 **Chat API 多轮对话 Agent**：程序维护 `messages`，每轮把整段历史发给模型。

| 目录 | 说明 |
|------|------|
| [`minimal_chat_v1/`](minimal_chat_v1/) | **第 02 篇 · 终端 CLI**（无 system） |
| [`mechanism_viewer_v1/`](mechanism_viewer_v1/) | **机制查看器**（桌面 GUI；可切换 v1 / v2 / v3 角色设定） |
| [`mechanism_viewer_v2/`](mechanism_viewer_v2/) | 查看器便捷入口，默认选中第 03 篇 Few-shot |
| [`system_prompt_v2/`](system_prompt_v2/) | **第 03 篇 · system + Few-shot / Zero-shot** |
| [`role_setting_v3/`](role_setting_v3/) | **第 04 篇 · 多角色 YAML + 指定/自动选取角色** |

默认对接智谱 **GLM-4.7-Flash**（OpenAI 兼容接口）。API Key 用环境变量 `ZHIPU_API_KEY`，勿提交到 Git。

## 快速开始（第 02 篇）

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
cd minimal_chat_v1
pip install -r requirements.txt
python minimal_agent.py
```

## 第 03 篇（system + Few-shot）

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
cd system_prompt_v2
pip install -r requirements.txt
python minimal_agent.py
```

Zero-shot 对照：`$env:USE_FEW_SHOT="0"` 后重启。机制查看器见 [`mechanism_viewer_v2/README.md`](mechanism_viewer_v2/README.md)。

## 第 04 篇（多角色 + 自动选取角色）

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
$env:AGENT_ROLE="teacher"   # 或 strict_reviewer / auto
cd role_setting_v3
pip install -r requirements.txt
python minimal_agent.py
```

机制查看器顶栏可选 **第04篇 · 角色设定**（Few-shot / Zero-shot / 自动选取角色）。离线校验：`python scripts/ci_smoke_test.py`。

## 来源与关注

本仓库为微信公众号 **「新时代软开」**《AI Agent 开发系列》教程配套代码。欢迎关注公众号获取图文教程。

---

## License

MIT — 见 [LICENSE](LICENSE)。
