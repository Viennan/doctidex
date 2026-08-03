# Protocol 与根目录观测的实现

本组件在 Python 变体中实现[树与 validation](../../../architecture/tree-and-validation.md)：解析 Markdown
frontmatter 和链接，发现 responsible index/root，构建树观测，执行协议校验，并产生有界结果。它不解释 Git source、
manifest/runtime 或 host hook。

## 职责归属与入口

| 源码归属 | 职责与调用者 | 副作用与边界 |
|---|---|---|
| [`protocol/document.py`](../../../../../impls/libs/python/whero/doctidex/protocol/document.py) | `DoctidexDocument`、frontmatter 与 Markdown 链接解析；由 validator 和 external link 的 frontmatter 更新调用。 | 读取并回写 Markdown；重复 YAML 键和无效 frontmatter 属于确定性的校验事实。 |
| [`protocol/root.py`](../../../../../impls/libs/python/whero/doctidex/protocol/root.py) | `RootContext`、root 选择、路径规范化和归属观测。 | 产生 root/owner/content 的关系证据；不推断 Git source。 |
| [`protocol/validation.py`](../../../../../impls/libs/python/whero/doctidex/protocol/validation.py) | 协议树遍历、reachability/config/link 校验。 | 只读遍历并产生 finding/candidate；不执行写入操作或 AI。 |

CLI 路由通过 `validate` 与依赖 root 的 external/worktree commands 进入这些 owner。解析器将 doctidex
root-absolute paths 与 filesystem paths 区分开来。YAML/注释保留和链接分词是 Python 的选择；`doctidex.type`、
`root`、`boundary-set`、`atomic-indexing`、`unsafe`、root 选择和 scoped coverage 语义仍属于 Architecture。

## 观测流程

```text
CLI 的 ROOT/PATH/cwd
  -> RootContext 的选择与规范化
  -> responsible-index / local configuration 的观测
  -> document/link tree 的遍历
  -> 协议 finding 与语义 candidate
  -> result 的分页与渲染
```

对于 `external link`，同一套 document/root observation 会定位 responsible index，并在 external preflight 后只更新
相关的 boundary/unsafe declaration。它不决定 source identity 或 durable-link 语义；这些属于
[external presentation](external-presentation-and-mapping.md)，其物理作用仅在
[worksite inventory](../worksite-inventory-and-construction.md) 中统一清点。

## 证据与边界

[`test_protocol.py`](../../../../../impls/libs/python/tests/test_protocol.py) 覆盖 root/configuration/link
校验、reachability、safe/unsafe boundary behavior 与 scoped coverage。Git 专项集成测试位于
[`test_git_plugin.py`](../../../../../impls/libs/python/tests/test_git_plugin.py)，并在变更 external presentation 时覆盖
这套共享观测。

该实现不证明语义文字质量、source 的可信度、用户权限或 Git delivery。它报告协议观测事实与 candidate；agent/human
决定语义内容与授权。Parser AST 形状、YAML emitter 排序以及 filesystem traversal helper branches 都是局部机制，
不是 Architecture 要求的细节。
