# react_v6

系列**第 07 篇**代码：**商用 Agent 一体化运行机制** + ReAct + `calculator`。

用户只发任务；程序自动叠层：system / Few-shot / CoT / 自动选角 / 按需计划比选 / 按需批评精炼 / ReAct 工具环。

```powershell
cd agent_lab/react_v6
pip install -r requirements.txt
$env:ZHIPU_API_KEY="你的密钥"
python minimal_agent.py
```

机制查看器：`agent_lab/mechanism_viewer_v6/`（**运行轨迹** Tab）。

离线冒烟（mock，无需 API）：`python smoke_test_experiments.py`
