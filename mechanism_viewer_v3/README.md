# mechanism_viewer_v3

**机制查看器 v3** — 对应 **`role_setting_v3`**（系列第04篇）。

版本下拉**仅**：角色 Few-shot / Zero-shot / 自动选角。在 v2 观测之上增加 **角色设定** 标签页。**无**推理与比选（属 v4）。

```powershell
$env:ZHIPU_API_KEY="你的Key"
cd mechanism_viewer_v3
pip install -r requirements.txt
python mechanism_client.py
```

CoT / ToT 请用 `mechanism_viewer_v4/`。
