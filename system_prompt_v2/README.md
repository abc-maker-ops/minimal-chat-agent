# system_prompt_v2

第 03 篇配套：在 `minimal_chat_v1` 上增加 **L1 system** 与 **L3 Few-shot 范例**（`prompts/few_shot.json`）。

**默认按 Few-shot 启动**（system + 3 组 JSON 情绪分类范例）；`USE_FEW_SHOT=0` 仅用于 Zero-shot 对照实验。

## 运行

**桌面机制查看器（推荐）**

```powershell
$env:ZHIPU_API_KEY="你的Key"
cd system_prompt_v2
pip install -r requirements.txt
python mechanism_client.py
```

或在 `mechanism_viewer_v1` / `mechanism_viewer_v2` 目录运行同一程序；**窗口顶部** 可切换 Agent 版本（Few-shot / Zero-shot / 第02篇 v1）。Windows 可双击 `mechanism_viewer_v2/启动机制查看器.bat`。

**终端 CLI**

```powershell
$env:ZHIPU_API_KEY="你的Key"
cd system_prompt_v2
pip install -r requirements.txt
python minimal_agent.py
```

## 模式对照

| 环境变量 | L3 范例 | 叫法 |
|----------|---------|------|
| 默认（未设或 `USE_FEW_SHOT=1`） | `few_shot.json` 全部注入 | **Few-shot**（本篇默认实现） |
| `USE_FEW_SHOT=0` | 不注入 | **Zero-shot**（保留 system） |

依赖同目录上一级的 `minimal_chat_v1/agent_session.py`。

---

## 来源与关注

本代码来源于微信公众号 **「新时代软开」** 的 AI Agent 开发系列教程。欢迎关注公众号，获取图文教程与后续篇章代码。
