# DX-ISSUE-0006：根入口将当前协议版本错误标为 `v1.0.0`

状态：`resolved`

创建日期：2026-08-05

严重程度：medium

来源：2026-08-05 对当前 `HEAD`（`259085abd8c324a53840f55a6783fa31eb874fbb`）进行的全仓 review；用户授权将严重度最高、已验证的问题记录为 Issue。

确认：2026-08-05，用户明确要求将本轮 review 创建的全部 6 个 Issue 置为确认状态。

## 问题

仓库根入口将 Protocol specification 描述为 “the normative Draft `v1.0.0`”，但其链接目标的协议
overview 头部声明当前版本为 `v1.1.0`。这不是 archived protocol 的标签，而是用户进入当前规范所经过的主入口，
会向人和 agent 提供过期版本事实。

## 具体场景

一个从仓库根开始选择规范的读者依次读取当前入口与其链接目标：

```text
index.md, "Protocol specification": "the normative Draft v1.0.0"
  -> spec/overview.md, 文档头部: "版本：v1.1.0"
```

根索引紧接着又单独列出 archived `v0.1.0`，所以这两处相互矛盾的版本文字都会参与读者判断哪个版本才是 current。

## 当前错误状态

同一条 current-protocol navigation path 暴露两个不同版本值。读者若只读取根入口，会记录或实现 `v1.0.0`；
读者若继续进入 authority，才发现其实际使用的是 `v1.1.0`。`v1.1.0` 已引入对结构化 link 注释 YAML mapping
书写形式的放宽，因此这不是不影响理解的排版差异。

## 正确行为

根入口对 current specification 的可见版本必须与其 authority document 的版本一致，即在当前树中为 `v1.1.0`；
archive 入口仍可保留各自准确的历史版本。读者不应通过同一导航链得到冲突的 current-version 事实。

## 受影响范围与条件

- 从根 `index.md` 发现和选择当前 doctidex 协议的用户、agent 与工具。
- 无须特殊环境或输入；直接阅读根入口即可观察。

## Authority 与证据

- [根索引的 Protocol specification 链接](../../index.md#L27)将其目标标注为 `v1.0.0`。
- [当前协议 overview](../../spec/overview.md#L1)在文档头部声明 “版本：`v1.1.0`”，并说明该版本相对 `v1.0.0`
  放宽了结构化 link 注释的 YAML mapping 书写形式。
- 根索引同一段另行链接 archived `v0.1.0`，因此该错误会影响 current/archived 协议的选择与理解，而非单纯历史描述。

## 影响与后续决定

用户可能依据根入口错误选择或引用 `v1.0.0`，从而遗漏当前 `v1.1.0` 的协议能力和约束。后续应仅更新当前入口的
版本陈述，并在任何 release/version 文案变更时增加链接目标与可见版本的一致性检查。Issue 目前不授权修改入口文档。

## 处置

解决：2026-08-05，用户明确要求将本轮六项 Issue 标记为 `resolved`。根据
[DX-REQ-0021.6](../requirements/0021-resolve-confirmed-review-issues/06-root-protocol-version-entry.md)，根 `index.md` 的
Protocol specification entry 已更正为 current Draft `v1.1.0`，仍指向 `spec/overview.md`；archived `v0.1.0` entry
与协议本文均未改写。

验证：人工比对根入口与 `spec/overview.md` 文档头部，二者均为 `v1.1.0`；全根及 Requirement scope 的 validator 和
`git diff --check` 均通过。

残余边界：协议版本的唯一 authority 仍是 `spec/overview.md`。根索引只是当前入口的准确说明，未来版本升级仍需同时审查
入口文案与 authority header。
