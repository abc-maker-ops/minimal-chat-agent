# minimal_chat_v1

第 02 篇配套：**只调 Chat API + 多轮 messages**，暂不带头部的 `system`。

## 环境

```bash
cd minimal_chat_v1
pip install -r requirements.txt
```

### 1. 设置 API Key（必须用环境变量，不要写进 `.env`）

在 [智谱开放平台](https://open.bigmodel.cn/usercenter/apikeys) 申请 Key 后：

**PowerShell（当前终端有效）**

```powershell
$env:ZHIPU_API_KEY="你的智谱Key"
```

**Windows cmd**

```cmd
set ZHIPU_API_KEY=你的智谱Key
```

**Linux / macOS**

```bash
export ZHIPU_API_KEY=你的智谱Key
```

也可兼容旧变量名 `OPENAI_API_KEY`（二选一即可）。

### 2. 可选：非敏感项放进 `.env`

```bash
copy .env.example .env
```

`.env` 里只建议放 `ZHIPU_BASE_URL`、`ZHIPU_MODEL`、`OPENAI_TEMPERATURE` 等，**不要放 Key**。

## 运行

**终端 CLI**

```bash
python minimal_agent.py
```

**桌面机制查看器**（看 messages 条数、Token、JSON 列表）：见 `../mechanism_viewer_v1/`，运行 `python mechanism_client.py` 弹出窗口。

## 本版本边界

| 有 | 无 |
|----|-----|
| `chat.completions` 多轮对话 | `system` → **system_prompt_v2** |
| 可选 temperature、max_tokens | 工具、ReAct |

## 下一版本

- **system_prompt_v2**（第 03 篇）：读 `system.txt`，`messages` 开头加 `system` 角色。

---

## 来源与关注

本代码来源于微信公众号 **「新时代软开」** 的 AI Agent 开发系列教程。欢迎关注公众号，获取图文教程与后续篇章代码更新。
