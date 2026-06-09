# mechanism_viewer_v2

**机制查看器 v2** — 独立窗口，**仅累积观测 agent v1 + v2**（不可见 v3/v4）。

与 `mechanism_viewer_v1` 共用核心 `mechanism_client.py`，启动时 `profile=viewer2`：

| 可见版本 | 说明 |
|----------|------|
| 第02篇 · minimal_chat_v1 | 仅 user/assistant |
| 第03篇 · system + Few-shot | 默认选中 |
| 第03篇 · system（Zero-shot） | 仅 system |

无「角色设定」「推理与比选」标签页（那些从 v3/v4 查看器才有）。

## 运行

```powershell
$env:ZHIPU_API_KEY="你的Key"
cd mechanism_viewer_v2
pip install -r requirements.txt
python mechanism_client.py
```

Windows 可双击 **`启动机制查看器.bat`**。

对照 v3/v4 机制请分别启动 `mechanism_viewer_v3/`、`mechanism_viewer_v4/`。
