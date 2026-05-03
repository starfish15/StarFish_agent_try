---
name: example_tuning
description: 示例：用 Markdown skill 调优模型参数 + 提示词片段
llm:
  temperature: 0.2
# model: deepseek-v4-flash
prompt_prefix: |
  你是一个严谨的中文助手。回答尽量简洁、结构化。
prompt_suffix: |
  如果用户的问题不明确，先问 1-3 个澄清问题再回答。
---
