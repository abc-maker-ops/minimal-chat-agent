# mechanism_viewer_v1

**机制查看器（桌面窗口版）** — 系列统一 UI 入口。

与 `minimal_chat_v1`、`system_prompt_v2` 共用同一程序；**窗口顶部下拉框** 可切换 Agent 版本：

| 选项 | 说明 |
|------|------|
| 第02篇 · minimal_chat_v1 | 仅 user/assistant |
| 第03篇 · system + Few-shot | system + 3 组范例（默认本篇实验） |
| 第03篇 · system（Zero-shot） | 仅 system，无范例 |

## 运行

```powershell
$env:ZHIPU_API_KEY="你的Key"
cd mechanism_viewer_v1
pip install -r requirements.txt
python mechanism_client.py
```

Windows 可双击 **`启动机制查看器.bat`**（默认第 02 篇 v1）。

环境变量 `MECHANISM_AGENT_VERSION` 可指定启动版本：`v1_minimal`、`v2_fewshot`、`v2_zeroshot`。

`mechanism_viewer_v2/`、`system_prompt_v2/mechanism_client.py` 为便捷启动，默认 `v2_fewshot`。

## 标签页

| 标签页 | 内容 |
|--------|------|
| 机制面板 | 版本、模型、轮次、messages 条数、Token |
| messages JSON | 内存中维护的 `messages` 列表（Agent 视角） |
| API 原始报文 | 最近一轮 **发送 → LLM** 的请求体与 **LLM → 返回** 的原始 JSON |

切换版本会保留聊天区历史，并插入分隔线；右侧机制面板随新版本重置。v2「清空会话」会保留 system / Few-shot 种子。
