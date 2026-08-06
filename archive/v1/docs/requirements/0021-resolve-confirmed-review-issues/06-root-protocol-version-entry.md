# 子需求 0021.6：root current-protocol 版本入口

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0021.6` |
| 状态 | `implemented` |
| 日期 | 2026-08-05 |
| 所属大型 Requirement | [DX-REQ-0021](overview.md) |
| 对应 Issue | [DX-ISSUE-0006](../../issues/0006-root-index-stale-protocol-version.md) |
| 影响范围 | 仓库根 `index.md` 的 Protocol specification 入口。 |
| 当前 authority | [`spec/overview.md`](../../../spec/overview.md) 文档头部的 current protocol version。 |

## 1. 需求意图

根入口必须准确地告诉人和 agent 其“Protocol specification”链接所指向的 current 规范版本。当前 authority 已是
`v1.1.0`，根文案中的 `v1.0.0` 不得继续作为 current-version 事实出现。

## 2. 解决方案

只修改根 `index.md` 中 Protocol specification 条目的版本文字，由 `v1.0.0` 更正为 `v1.1.0`。不改动
`spec/overview.md`、archived `v0.1.0` entry、协议发布状态或任何 implementation version；这些分别已有权威。

为防止同类入口漂移，在本项验收中直接比对 root entry 的 current-version label 与 link target document header。该检查
可以是文档 review checklist 或轻量自动化检查，但不得把未定义的 repository metadata 伪装成协议版本 authority。

## 3. 验收标准

- 根 `index.md` 的 Protocol specification 文本声明 `v1.1.0`，且其 link target 仍为 `spec/overview.md`。
- `spec/overview.md` 头部仍是唯一的 current protocol version authority；archived `v0.1.0` 链接和历史文字不被改写。
- 从根入口顺序读取时，不会得到与 authority header 冲突的 current protocol 版本值。
- 0021.3 同时修改根索引时，合并后的 frontmatter、链接和正文仍通过全根 validator。

## 4. 实施状态

2026-08-05 已完成实施。根 `index.md` 的 Protocol specification entry 现声明 `v1.1.0`，仍指向
`spec/overview.md`；历史 `v0.1.0` entry 与 protocol 本文均未改写。已与 0021.3 合并通过全根 validation；
DX-ISSUE-0006 的 `resolved` 状态仍需用户明确授权。
