# role_setting_v3

第 04 篇：角色文件（YAML）+ 手动/自动选角 + 商用级加载校验。

## 运行

```powershell
cd agent_lab/role_setting_v3
pip install -r requirements.txt
$env:ZHIPU_API_KEY="你的Key"
$env:AGENT_ROLE="teacher"    # 或 strict_reviewer / auto
python minimal_agent.py
```

- `AGENT_ROLE=auto`：首条 user 消息经 `role_router` 选角后再拼固定前缀。
- `USE_FEW_SHOT=0`：Zero-shot 对照。

机制查看器：在 `mechanism_viewer_v1` 选 **第04篇 · 角色设定**；右侧 **「角色设定」** 页查看当前角色、选角依据与 Prompt 全文；机制面板同步摘要。
