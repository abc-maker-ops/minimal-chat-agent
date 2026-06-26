# react_v7

系列**第 08 篇**代码：**ReAct 加强**——在 v6 一体化运行机制上扩展工作区 **read / list / write** 与环内 **`done` 验收**（读—改—验闭环）。

```powershell
cd agent_lab/react_v7
pip install -r requirements.txt
$env:ZHIPU_API_KEY="你的密钥"
python minimal_agent.py
```

可选：`$env:AGENT_WORKSPACE="自定义工作区绝对路径"`（默认 `react_v7/workspace/`）。

机制查看器：`agent_lab/mechanism_viewer_v7/`（**运行轨迹** Tab 含 done 状态）。

离线冒烟（mock，无需 API）：`python smoke_test_experiments.py`
