# 需求 0008：doctidex-git 与协议 v1.0.0 对齐

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0008` |
| 状态 | `approved` |
| 日期 | 2026-07-30 |
| 批准日期 | 2026-08-01；用户明确批准本大型 Requirement 及其全部子需求 |
| 来源 | 用户要求创建大型 Requirement，承接需求 0005 中明确延期的 doctidex-git 对齐工作 |
| 影响范围 | doctidex-git 的 Architecture、Published Skills、CLI、Python 实现与测试 |
| 前置关系 | 后续承接 [DX-REQ-0005](../0005-protocol-v1-0-0.md) |

本大型 Requirement 承接协议 `v1.0.0` 发布后明确延期的 doctidex-git 对齐工作，并把
不兼容精简重构分为两个有序子需求：先完成语言无关 Architecture，再据此细化并实现
Python Details。实现已严格落实 Architecture 确定的 public surface、状态分层与生命周期：
package `1.0.0` 支持 Linux/macOS/Windows，使用 shared bare object cache，并提供不进入
Skills、仅清理无有效 linked worktree source 的显式 cache cleanup。Python 代码、Details、
测试、CI 与三个 Published Skills 已完成切换并通过验证。用户已明确批准两个子需求及本
大型 Requirement；全部记录因而进入 `approved`。

## 子需求导航

| ID | 子需求 | 摘要 | 状态 |
|---|---|---|---|
| `DX-REQ-0008.1` | [doctidex-git 面向协议 v1.0.0 的 Architecture 设计](01-doctidex-git-alignment.md) | 三 Skill user surface、validation、可恢复且与宿主 Git 追踪隔离并支持环状依赖的外部 Git 安装/链接、扁平 worktree 工作流和 CLI/JSON 公共契约。 | `approved` |
| `DX-REQ-0008.2` | [doctidex-git Python Details 与实现](02-python-details-and-implementation.md) | 严格按 Architecture 落实跨平台 Python `1.0.0`、shared bare object cache、受保护的 cache cleanup、external/worktree、portable/runtime 状态、并发、测试与旧实现替换。 | `approved` |

0008.1 完成 Read Skill 对不可访问 symlink 的引导，以及 link-parse 对主仓库与 install
仓库 portable mapping 的统一解析；匹配的 `0.1.0` 设计已经归档。0008.2 以最终
[v1.0.0 Architecture](../../doctidex-git/architecture/index.md) 为不可反向覆盖的契约，完成
Python 实现、Details、Published Skills、测试与 CI。两项子需求均保持独立生命周期；用户
明确批准全部子需求后，本 overview 再按聚合门槛进入 `approved`。

## Requirement 关系

- 本记录是 [DX-REQ-0005](../0005-protocol-v1-0-0.md) 的后续；0005 发布了协议
  `v1.0.0`，并将 doctidex-git 对齐明确延期至后续 Requirement。
