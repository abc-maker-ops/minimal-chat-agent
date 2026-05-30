# mechanism_viewer_v2

与 **`mechanism_viewer_v1`** 共用同一套 `mechanism_client.py`（窗口顶部可切换 Agent 版本）。

本目录启动时**默认选中**「第03篇 · system + Few-shot」。

```powershell
$env:ZHIPU_API_KEY="你的Key"
cd mechanism_viewer_v2
pip install -r requirements.txt
python mechanism_client.py
```

也可在 `system_prompt_v2` 目录直接运行 `python mechanism_client.py`（同样默认 Few-shot）。

统一入口（推荐记这一个路径）：`agent_lab/mechanism_viewer_v1/mechanism_client.py`
