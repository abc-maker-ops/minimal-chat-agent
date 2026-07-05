# react_v8

系列**第 09 篇**代码：在 v7 读写与 `done` 基础上，深化 **JSON Schema 描述**、**tool_choice**、**Forced tool** 与 **Parallel Function Calling**。

```powershell
cd agent_lab/react_v8
pip install -r requirements.txt
$env:ZHIPU_API_KEY="你的密钥"
python minimal_agent.py
```

可选环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `PARALLEL_TOOL_CALLS` | `1` | 客户端并行执行安全工具；请求体在关闭时带 `parallel_tool_calls: false` |
| `TOOL_CHOICE_FIRST` | `required` | 首轮 `tool_choice`：`auto` / `required` / forced JSON |
| `TOOL_SCHEMA_PROFILE` | `good` | `legacy` 使用含糊 description（对照实验） |
| `FORCE_DONE_ON_TEXT_EXIT` | `1` | 已写入但未验收时，模型纯文字收尾则 forced `done` |

机制查看器：`agent_lab/mechanism_viewer_v8/`（`python mechanism_client.py` 或双击 `启动机制查看器.bat`）

离线冒烟：`python smoke_test_experiments.py`

批量在线验证（实验 1～3）：`python run_verify_experiments.py`
