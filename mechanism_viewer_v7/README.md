# mechanism_viewer_v7

**机制查看器 v7** — 对应 **`react_v7`**（系列第 08 篇 · ReAct 加强与 done 验收）。

默认版本 **`v7_delivery`**；**运行轨迹** Tab 展示本轮自动选角、计划比选、ReAct 工具链及 **done 验收** 状态（含 `done` 未通过时的 `[FAIL]` 与 Observation JSON）。Markdown 验收规则与代码一致：按**标题行**匹配，非正文子串——无需单独改查看器，加载 `react_v7` 即可。

真实 API 三组实验：`cd ../react_v7` 后 `python run_live_experiments.py`（需 `ZHIPU_API_KEY`）。

## 启动

```powershell
cd agent_lab/mechanism_viewer_v7
pip install -r requirements.txt
python mechanism_client.py
```

或双击 `启动机制查看器.bat`。

第 07 篇对照仍可用 `mechanism_viewer_v6`。
