# User Instruction Memory

This file records user instructions, preferences, and teachings for reference in future interactions.

## Format

### User Instruction Entry
User instruction entries should follow this format:

[User Instruction Summary]
- Date: [YYYY-MM-DD]
- Context: [Mentioned scenario or time]
- Instructions:
  - [Content of user teaching or instruction, described line by line]

### Project Knowledge Entry
Entries discovered by the Agent during task execution should follow this format:

[Project Knowledge Summary]
- Date: [YYYY-MM-DD]
- Context: Discovered by Agent while performing [specific task description]
- Category: [Operations & Deployment|Build Methods|Testing Methods|Troubleshooting & Debugging|Workflow & Collaboration|Environment Configuration]
- Instructions:
  - [Specific knowledge points, described line by line]

## Deduplication Strategy
- Before adding a new entry, check for similar or identical instructions.
- If a duplicate is found, skip the new entry or merge it with the existing one.
- When merging, update the context or date information.
- This helps avoid redundant entries and keeps the memory file tidy.

## Entries

[User Instruction Summary]
- Date: 2026-08-02
- Context: 开始按 tasklist.md 逐任务开发 StoneVault 时用户给出指令
- Instructions:
  - 每个实施任务完成后自动执行 git commit 并 push 到远程仓库（origin master），无需再询问用户是否提交

[Project Knowledge Summary]
- Date: 2026-08-02
- Context: Discovered by Agent while performing git push 到 GitHub 时遇到认证失败
- Category: Environment Configuration
- Instructions:
  - 本环境通过 GIT_CONFIG_COUNT 环境变量强制注入 credential helper（/app/agent/bin/agent git-credential-helper），该 helper 服务不可用（返回 500）
  - push 前需用 `env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_0 -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_KEY_1 -u GIT_CONFIG_VALUE_1 git push ...` 清除注入后，配合 ~/.git-credentials（credential.helper=store）认证
  - 远程仓库为 https://github.com/t366/StoneVault.git
