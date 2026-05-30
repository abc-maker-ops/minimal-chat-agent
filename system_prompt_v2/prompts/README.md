# prompts 目录说明

| 文件 | 分层 | 写什么 | 不要写什么 |
|------|------|--------|------------|
| `system.txt` | L1 岗位 | 身份、语言、诚实、禁假读盘/假联网 | 某一任务的 JSON 字段细则（除非极短） |

Few-shot 模式下 `prompt_session.py` 还会在 system 末尾追加「按 Few-shot 范例格式作答」；Zero-shot 不追加。
| `few_shot.json` | L3 范例 | **默认 3 组**「输入→合格输出」短样本（Few-shot） | 长篇教程、与线上任务无关的范例 |

默认启动会加载全部条目。`USE_FEW_SHOT=0` 时不加载本文件（Zero-shot 对照）。

改 Prompt 后重启 `minimal_agent.py` 生效。对比实验时一次只改一层（先 system，再 few_shot），便于归因。
