# mechanism_viewer_v1

**机制查看器 v1** — 独立窗口，**仅观测 agent v1**（minimal_chat_v1）。

核心实现：`mechanism_client.py`（各代查看器共用此文件，通过 `profile` 控制可见版本与标签页）。

| profile | 可见 Agent 版本 | 额外标签页 |
|---------|-----------------|------------|
| viewer1（本目录） | 仅 v1_minimal | 无 |
| viewer2 | v1 + v2 | 无 |
| viewer3 | v1～v3 | 角色设定 |
| viewer4 | v1～v4 | 角色设定 + 推理与比选 |

## 运行

```powershell
$env:ZHIPU_API_KEY="你的Key"
cd mechanism_viewer_v1
pip install -r requirements.txt
python mechanism_client.py
```

Windows 可双击 **`启动机制查看器.bat`**。

环境变量：`MECHANISM_VIEWER_PROFILE=viewer1`，`MECHANISM_AGENT_VERSION=v1_minimal`。

要看 v2/v3/v4 机制，请启动对应目录的 `mechanism_viewer_v2/`、`mechanism_viewer_v3/`、`mechanism_viewer_v4/`，不要指望在一个窗口里切全系列。

## 标签页（viewer1）

| 标签页 | 内容 |
|--------|------|
| 机制面板 | 版本、模型、轮次、messages 条数、Token |
| messages JSON | 内存中维护的 `messages` 列表 |

viewer1 **不显示**「API 原始报文」标签页（从 viewer2 起才有）。
