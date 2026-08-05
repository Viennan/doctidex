# DX-ISSUE-0002：协议 validator 将仅含 query 的 link 误当作当前文档 file-path link

状态：`resolved`

创建日期：2026-08-05

严重程度：high

来源：2026-08-05 对当前 `HEAD`（`259085abd8c324a53840f55a6783fa31eb874fbb`）进行的全仓 review；用户授权将严重度最高、已验证的问题记录为 Issue。

确认：2026-08-05，用户明确要求将本轮 review 创建的全部 6 个 Issue 置为确认状态。

## 问题

协议只允许根绝对路径、根内相对路径，或仅有 anchor 的当前文档定位作为 doctidex file-path link。当前 validator
对 `?view=1` 这类仅含 query、没有 scheme 或 netloc 的 link 仍判定为 file link；`urlsplit()` 得到空 path 后，
`_resolve_link()` 直接返回当前 document。因此该 link 会被当作合法的当前文档阅读边，不会获得无效 link finding。

query-only link 不是协议列举的三种路径形式，也不是仅有 anchor。它可以作为普通 Markdown hyperlink 存在，但不应
参与 doctidex 的索引、可达性或路径符合性判断。

## 具体场景

在一个除此之外完全符合协议的 root 中，根索引到 `guide.md` 有普通阅读边，而 `guide.md` 包含只改变阅读器 query
state 的链接：

```markdown
<!-- index.md 的正文 -->
[Guide](guide.md)

<!-- guide.md 的正文 -->
[以紧凑视图阅读](?view=compact)
```

执行 `doctidex-git validate ROOT --json` 时，`urlsplit("?view=compact")` 的 path 为空。当前实现既没有排除 query，
也没有排除该 target，因此将它解析为 `guide.md` 本身。

## 当前错误状态

在其余结构都有效时，validator 会把这个 link 作为 current document 的 file-path edge 处理，验证可得到
`"protocol_structure": "pass"`，且不会为该 link 产生路径无效 finding。内部观察结果等价于：

```text
raw target: ?view=compact
is_file_link: true
resolved target: ROOT/guide.md
```

这会使一个不符合协议 file-path 形式的 hyperlink 被用于 link graph；即使此例的自环没有扩大可达集合，其他依赖
link 分类的检查也会接收到错误的 file-link 事实。

## 正确行为

`?view=compact` 可以保留为普通 Markdown hyperlink，但不能成为 doctidex file-path edge，也不能用于可达性或
符合性证明。实现可以把它分类为非 file-path link 而不报告协议错误；关键是它不能再解析为当前文档的根内相对路径。

## 受影响范围与条件

- Python protocol validator 的 link classification、target resolution 与由其计算的可达性结果。
- safe Markdown 文档包含相对格式的 query-only link，例如 `[查看](?view=1)`。

## Authority 与证据

- [协议第 7 节](../../spec/overview.md#7-可达性)规定，可形成阅读边的 link target 必须是第 8 节所列形式。
- [协议第 8 节](../../spec/overview.md#8-文档-link-与结构化注释)仅示例并定义根绝对路径、根内相对路径和仅有
  anchor 的当前文档定位；其他非 file-path hyperlink 不参与协议判断。
- [validation.py](../../impls/libs/python/whero/doctidex/protocol/validation.py#L734) 至 [validation.py](../../impls/libs/python/whero/doctidex/protocol/validation.py#L762) 忽略 `parsed.query`：空 `parsed.path` 返回当前 document，且 `_is_file_link()` 只排除 scheme/netloc。
- [协议测试](../../impls/libs/python/tests/test_protocol.py#L1) 至 [test_protocol.py](../../impls/libs/python/tests/test_protocol.py#L370) 覆盖 anchor、root-relative 与相对路径，但未覆盖 query-only link。

## 影响与后续决定

validator 会错误认可不受协议支持的阅读边，导致实现宣称符合而实际结构不满足路径规则。修复应先明确普通 query
hyperlink 的分类结果，再使 resolver 与 `is_file_link` 使用同一规则，并加入 query-only、path 加 query、anchor 加
query 等边界测试。Issue 目前不授权协议或实现修改。

## 处置

解决：2026-08-05，用户明确要求将本轮六项 Issue 标记为 `resolved`。根据
[DX-REQ-0021.2](../requirements/0021-resolve-confirmed-review-issues/02-validator-query-link-classification.md)，
Python validator 的 `_is_file_link()` 与 `_resolve_link()` 现在共用 URL 分类：有 scheme、netloc 或非空 query 的
Markdown hyperlink 均不形成 doctidex file-path edge；fragment 中的 `?` 仍属于 anchor 文本。

验证：`test_query_links_do_not_form_file_path_edges` 直接断言 `?view=compact` 与 `guide.md?view=compact` 不形成 edge，
而 `#details?view=compact` 仍解析为当前文档 anchor；完整 Python tests、Ruff、全根及 Requirement scope 的 validator、
`git diff --check` 均通过。

残余边界：这只定义 doctidex validator 对 Markdown link 的协议图分类，不限制阅读器对 query hyperlink 的呈现或导航行为。
