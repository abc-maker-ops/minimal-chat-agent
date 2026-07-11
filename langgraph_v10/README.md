# langgraph_v10

系列**第 10 篇**代码：在 v8 工具表上，用 **LangChain ChatModel** + **LangGraph StateGraph** 编排 ReAct 环。

```powershell
cd agent_lab/langgraph_v10
pip install -r requirements.txt
$env:ZHIPU_API_KEY="你的密钥"
python minimal_agent.py
```

可选环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `MAX_REACT_STEPS` / `MAX_GRAPH_STEPS` | `10` | agent 节点最大轮次 |
| `TOOL_CHOICE_FIRST` | `required` | 首轮 tool_choice（经 v8 bridge） |
| `FORCE_DONE_ON_TEXT_EXIT` | `1` | 写入后未验收时走 `force_done_gate` |
| `LANGGRAPH_CHECKPOINT` | `0` | 设为 `1` 启用 MemorySaver + thread_id |

机制查看器：`agent_lab/mechanism_viewer_v10/`

离线冒烟：`python smoke_test_experiments.py`

对照 v8：`agent_lab/react_v8/`（同一工具与 done 语义）
