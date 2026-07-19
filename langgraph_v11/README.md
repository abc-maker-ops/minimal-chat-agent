# langgraph_v11

系列**第 11 篇**代码：在 `langgraph_v10` 图编排之上补齐：

1. **LangChain StructuredTool** 封装（执行仍走 v8 `run_tool`）
2. **`tools` 节点并行**（对齐第 09 篇 Parallel）
3. **Checkpoint + 人审 `interrupt`**（写文件 / `done` 前可打断）

```powershell
cd agent_lab/langgraph_v11
pip install -r requirements.txt
$env:ZHIPU_API_KEY="你的密钥"
python minimal_agent.py
```

| 变量 | 默认 | 说明 |
|------|------|------|
| `PARALLEL_TOOL_CALLS` | `1` | `0` 强制串行，便于对照 |
| `HUMAN_GATE` | 关 | `1` 时写文件/`done` 前进入 `human_gate` |
| `AUTO_APPROVE` | `1` | 人审自动通过；终端交互设 `0` |
| `LANGGRAPH_CHECKPOINT` | 关 | `1` 启用 MemorySaver（人审开启时也会自动开） |
| `MAX_REACT_STEPS` | `10` | agent 节点上限 |

机制查看器：`agent_lab/mechanism_viewer_v11/`

离线冒烟：`python smoke_test_experiments.py`
