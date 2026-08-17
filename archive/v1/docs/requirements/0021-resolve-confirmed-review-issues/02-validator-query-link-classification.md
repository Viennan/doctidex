# 子需求 0021.2：validator 的 query link 分类

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0021.2` |
| 状态 | `implemented` |
| 日期 | 2026-08-05 |
| 所属大型 Requirement | [DX-REQ-0021](overview.md) |
| 对应 Issue | [DX-ISSUE-0002](../../issues/0002-validator-accepts-query-links.md) |
| 影响范围 | Python protocol link parser/resolver、可达性与 annotation 检查、protocol regression tests、Python Impls。 |
| 当前 authority | [协议第 7 节](../../../spec/overview.md#7-可达性)与[第 8 节](../../../spec/overview.md#8-文档-link-与结构化注释)。 |

## 1. 需求意图

Python validator 必须以协议的 file-path link 集合而不是 URL parser 的“无 scheme 即内部”近似规则建立阅读图。
仅有 query 的 hyperlink 不能被解析成当前文档，也不能由此绕过 file-path 规则。

## 2. 解决方案

以一次共享的 URL classification 作为 `_is_file_link()`、`_resolve_link()` 和 link observation 的唯一依据：

| Markdown target | 分类 | 可达性行为 |
|---|---|---|
| `guide.md`、`/guide.md`、`guide.md#part` | file-path link | 按根内路径解析并形成候选 edge。 |
| `#part` | anchor-only file-path link | 解析为当前文档。 |
| `?view=compact`、`guide.md?view=compact`、`?view=compact#part` | 非 file-path hyperlink | 保留为 Markdown 内容，但不形成 edge、不参与 annotation 或 path conformance。 |
| `#part?view=compact` | anchor-only file-path link | `?` 位于 fragment 内，是 anchor 文本的一部分，不是 URL query。 |
| 带 scheme 或 netloc 的 URL | 非 file-path hyperlink | 不参与 doctidex 图。 |

实现先以 `urlsplit()` 取得 components；只要 `scheme`、`netloc` 或 `query` 非空，就不将目标交给根内 path resolver。
当且仅当它是 protocol file-path link 时，resolver 才处理 path 与 fragment；annotation path 同样不得利用带 query
的值获得 current-document fallback。

## 3. 实现与文档影响

- 修改 `validation.py`，消除 `_is_file_link()` 与 `_resolve_link()` 对 query 的不一致；不得单独在后续 finding
  阶段补救，因为可达图已经依赖更早的分类。
- 在 `test_protocol.py` 直接观察 link classification/target，并通过全树 validation 断言 query-only case 不创建
  file-path edge。覆盖上表五类输入以及 safe boundary/unsafe annotation 旁的 query link。
- 协议文字已明确，不修改 `spec/overview.md`；Python Impls 更新为实现 evidence，而不把 URL query 分类描述成新的
  protocol requirement。

## 4. 验收标准

- 含 `[视图](?view=compact)` 的合法 `guide.md` 不因该 link 获得 current-document file edge；其余结构合法时 validation
  仍可通过，但该 link 不能用于证明任一路径可达。
- `guide.md?view=compact` 和 `?view=compact#part` 同样不形成 file edge；`#part` 与 `#part?view=compact` 仍按
  anchor-only 规则解析。
- root-relative、relative、anchor、boundary 和 unsafe 的既有合法测试保持通过，且测试直接防止 resolver 将 empty
  path 加 query 回退为 current document。
- Python Impls、相关 tests 和全套 validator tests 对新分类有可追溯 evidence。

## 5. 实施状态

2026-08-05 已完成实施。`_is_file_link()` 与 `_resolve_link()` 共用 scheme/netloc/query 分类，非空 query 不再形成
file-path edge；fragment 中的 query-like 文本保持 anchor 语义。`test_query_links_do_not_form_file_path_edges` 覆盖
query-only、path query 与 fragment case，Python Impls 已记录该实现证据。未修改协议文本；完整 Python tests、Ruff、
全根 validation 与 `git diff --check` 均通过。
