# AI Agent 最小聊天示例（开源）

用 Python 从零实现 **Chat API 多轮对话 Agent**：程序维护 `messages`，每轮把整段历史发给模型。

| 目录 | 说明 |
|------|------|
| [`minimal_chat_v1/`](minimal_chat_v1/) | **第 02 篇 · 终端 CLI**（无 system） |
| [`system_prompt_v2/`](system_prompt_v2/) | **第 03 篇 · system + Few-shot / Zero-shot** |
| [`role_setting_v3/`](role_setting_v3/) | **第 04 篇 · 多角色 YAML + 指定/自动选取角色** |
| [`reasoning_v4/`](reasoning_v4/) | **第 05 篇 · 思维链 / 简化思维树（CoT / ToT）** |
| [`reflection_v5/`](reflection_v5/) | **第 06 篇 · 批评 / 精炼 / 自洽性（Reflection 质检）** |
| [`react_v6/`](react_v6/) | **第 07 篇 · 商用 Agent 一体化运行机制 + ReAct** |
| [`react_v7/`](react_v7/) | **第 08 篇 · ReAct 加强 + done 验收** |
| [`react_v8/`](react_v8/) | **第 09 篇 · tool_choice / parallel / Schema** |
| [`langgraph_v10/`](langgraph_v10/) | **第 10 篇 · LangChain + LangGraph 图编排** |

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

Zero-shot 对照：`$env:USE_FEW_SHOT="0"` 后重启。

## 第 04 篇（多角色 + 自动选取角色）

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
$env:AGENT_ROLE="teacher"   # 或 strict_reviewer / auto
cd role_setting_v3
pip install -r requirements.txt
python minimal_agent.py
```

## 第 05 篇（思维链 + 简化思维树）

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
$env:AGENT_ROLE="teacher"
cd reasoning_v4
pip install -r requirements.txt
python minimal_agent.py
```

思维树对照：`$env:REASONING_MODE="tot"` 后重启。

## 第 06 篇（批评 / 精炼 / 自洽性）

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
$env:AGENT_ROLE="teacher"
cd reflection_v5
pip install -r requirements.txt
python minimal_agent.py
```

质检模式：`$env:QUALITY_MODE="consistency"`（自洽性）或 `"refine"`（批评 + 精炼）；默认 `off` 等同 v4 CoT/ToT。叠加思维树：`$env:REASONING_MODE="tot"`。

## 第 07 篇（商用 Agent · 一体化运行机制 + ReAct）

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
cd react_v6
pip install -r requirements.txt
python minimal_agent.py
```

无需设置 `AGENT_ROLE` / `REACT_MODE` / `QUALITY_MODE` / `REASONING_MODE`；程序按任务自动选角、比选、修订与 ReAct。安全上限：`MAX_REACT_STEPS=8`。

## 第 08 篇（结构化交付 · done 机器验收）

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
cd react_v7
pip install -r requirements.txt
python minimal_agent.py
```

工作区默认 `react_v7/workspace/`（可用 `AGENT_WORKSPACE` 覆盖）。工具含 `read_file` / `list_dir` / `write_text` / `done`。`MAX_REACT_STEPS` 默认 `10`。

## 第 09 篇（tool_choice / parallel / JSON Schema）

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
cd react_v8
pip install -r requirements.txt
python minimal_agent.py
```

可选：`PARALLEL_TOOL_CALLS`、`TOOL_CHOICE_FIRST`（默认 `required`）、`TOOL_SCHEMA_PROFILE=good|legacy`。机制查看器 `mechanism_viewer_v8/`。

## 第 10 篇（LangChain + LangGraph 图编排）

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
cd langgraph_v10
pip install -r requirements.txt
python minimal_agent.py
```

工具表经 `bridge_v8` 复用 v8；编排层为 LangGraph `StateGraph`（`agent` ↔ `tools` + `force_done_gate`）。可选：`LANGGRAPH_CHECKPOINT=1` 启用 `MemorySaver`。机制查看器 `mechanism_viewer_v10/`。离线冒烟：`python smoke_test_experiments.py`。

前九篇机制对照仍可用 `mechanism_viewer_v2`～`v8`；第 10 篇用 `mechanism_viewer_v10`。

## 机制查看器

桌面 GUI，可视化 `messages`、角色设定、推理与质检旁路、API 原始报文等。核心实现在 [`mechanism_viewer_v1/`](mechanism_viewer_v1/)；`mechanism_viewer_v2`～`v6` 为各篇便捷入口（双击 `启动机制查看器.bat` 或运行目录下 `mechanism_client.py`）。

| 目录 | 默认选中 |
|------|----------|
| [`mechanism_viewer_v1/`](mechanism_viewer_v1/) | 第 02 篇 · minimal |
| [`mechanism_viewer_v2/`](mechanism_viewer_v2/) | 第 03 篇 · Few-shot |
| [`mechanism_viewer_v3/`](mechanism_viewer_v3/) | 第 04 篇 · 角色设定 |
| [`mechanism_viewer_v4/`](mechanism_viewer_v4/) | 第 05 篇 · CoT |
| [`mechanism_viewer_v5/`](mechanism_viewer_v5/) | 第 06 篇 · 批评与精炼 |
| [`mechanism_viewer_v6/`](mechanism_viewer_v6/) | **第 07 篇 · 商用 Agent（运行轨迹）** |
| [`mechanism_viewer_v7/`](mechanism_viewer_v7/) | **第 08 篇 · ReAct 加强（运行轨迹 + done）** |
| [`mechanism_viewer_v8/`](mechanism_viewer_v8/) | **第 09 篇 · 工具工程化（parallel + tool_choice）** |
| [`mechanism_viewer_v10/`](mechanism_viewer_v10/) | **第 10 篇 · LangGraph 图编排（节点路径 + v8 工具链）** |

## 来源与关注

本仓库为微信公众号 **「新时代软开」**《AI Agent 开发系列》教程配套代码。欢迎关注公众号获取图文教程。

---

## License

MIT — 见 [LICENSE](LICENSE)。
