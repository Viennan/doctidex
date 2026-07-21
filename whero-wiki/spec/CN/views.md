# Whero Wiki View

协议状态：**v0.0.2 当前版本**。

## 目录

- [身份与布局](#身份与布局)
- [Selection 处理](#selection-处理)
- [Source 路径矩阵](#source-路径矩阵)
- [Collapse](#collapse)
- [源变更安全](#源变更安全)
- [恢复](#恢复)

## 身份与布局

`View` 是对 `Whero Wiki` 或另一个 `View` 保持结构、透读的投影。它可以位于 Wiki 中，也可以位于普通目录中。

View 根包含：

- 指向源 `whero-wiki-meta.md` 的相对符号链接；
- 普通的生成文件 `whero-wiki-view.md`；
- 对应 `Effective Root` 的相对符号链接和生成容器。

`whero-wiki-view.md` 使用以下规范 frontmatter：

- 身份字段：`type: Whero Wiki View`、`format_version: "0.0.2"`、`whero_maintenance: true`、`whero_view_required: true` 和 `whero_view: true`；
- source locator 与 identity：相对 `source`、取值为 `path` 或 `git-commit` 的 `source_validation`；使用 Git 时还包括 `source_commit`、`source_git_path` 和可选的已清理 `source_git_remote_*` 字段；
- 策略与意图：`layout: source-relative`、`view_name`、`collapse_threshold`、`requested_selections` 和 `effective_roots`；
- 可选的重建诊断字段，例如不作为 selection authority 的 `disclosed_symlinks`。

`requested_selections` 和 `effective_roots` 都是安全的 source-logical POSIX 路径列表。前者是完整重建的意图事实来源；后者记录最近一次应用的计划，并可在元数据写入中断后根据可读链接重建。

每个生成的内容链接都指向直接 source Wiki 或 source View 中 `Effective Root` 对应的路径项。相对该 source 路径项计算链接，不把 source 符号链接 resolve 为最终目标。View of View 因此链接到 parent View，而不是其最终 source Wiki。

路径穿过 preserved path、Mount、嵌套 Wiki、source View 或符号链接时，物化的 View 不会仅因此重建显式边界。边界规则可能把 effective root 提升到某个祖先，但结果仍是在该 source-logical path 上保持结构的链接。

## Selection 处理

按以下顺序处理请求的 `Selection`：

1. 把便于调用方使用的路径或链接目标解析为源逻辑 POSIX 路径。调用方可以选择任何 `Source-Reachable Path`，包括穿过一个或多个所有权或引用边界的路径。
2. 报告歧义、未经允许的 source escape 或直接 source 中不存在的路径。不得从最终 Wiki 获取 source View 中隐藏或 unavailable 的内容。
3. 当边界规则要求整体文件、目录、preserved boundary、Mount 或穿过的 source symlink 时提升 selection。路径穿过一个或多个 source symlink 时，提升到第一个 symlink 路径项。这改变 `Effective Root`，不改变调用方 selection 的合法性或含义。
4. 添加祖先路径上当前可用的 `View-Required Document`。
5. 应用允许的自适应 collapse。
6. 修改前预检链接、冲突、source identity 和文件系统变更。

View 同时记录请求的 selections 和产生的 effective roots。增量扩增只改变目标 View，不得修改 source Wiki 或 source View。调用方不需要使用边界专用 flag，也不需要把内部 selection 替换为协议要求的整体暴露根。

## Source 路径矩阵

| 选中路径 | 必需投影 | 对 collapse 的影响 |
| --- | --- | --- |
| 普通自有文件或目录 | 在相同逻辑路径创建相对链接 | 使用正常 View 规则 |
| Preserved 根或其后代 | 提升并整体暴露 preserved 根 | 不检查或计数后代 |
| Mount 根或后代，无论内容类型 | 接受 selection，并将 effective root 提升为 Mount 根 | 整体暴露 Mount |
| Source View 或被引用 View 中 available 的路径 | 链接直接 source 中对应的路径项，不进一步 resolve | 可见范围不能超过该 source View |
| Source View 或被引用 View 中 unavailable 的路径 | 不物化；报告该路径在直接 source 中 unavailable | 不回退到最终 Wiki |
| Source 符号链接或通过它可达的后代 | 提升到第一个穿过的 source symlink，并链接该路径项而不 resolve | 暴露该 symlink 表示的 source-visible 内容 |
| 显式选择的祖先目录 | 链接该 source 目录并暴露其 source-visible 子树 | 目录 selection 授权该子树 |

穿过多个边界不会创建嵌套 View 元数据。相对直接 source 解析请求的逻辑路径，计算协议要求的祖先提升，并创建最终相对链接。

## Collapse

只有在替换结果准确暴露已授权 effective content 时，自适应 collapse 才能用一个指向直接 source 中匹配目录项的链接替换生成的后代。

- 计算 collapse 覆盖率前先完成 whole-boundary 提升。
- 显式目录 selection 授权其完整的 source-visible 子树，包括 source 中已经存在的边界路径项。
- Preserved boundary、Mount 和穿过的 source symlink 都是原子边界，planner 不单独检查或计数其内部文件。
- Source View 只贡献该 View 中当前 available 的路径。Unavailable source path 不参与覆盖率计算，也不能通过 collapse 到最终 source 目录来暴露。
- Collapse 决策属于已审阅计划，执行期间不得扩大。

## 源变更安全

对 Git 控制的源，记录已审阅 commit 和 Wiki 路径。只有在历史向前且内容或结构变更不与 effective root 相交时才能自动接受。修改前拒绝 selection 中 dirty、untracked 或 ignored 的内容。View 是透读的，因此诊断必须说明现有链接可能已经暴露变化后的源字节。

对通过路径标识的源，要求解析后的源与记录一致，除非经过审阅的恢复或 relocation plan 证实其 source identity 相同。

## 恢复

先恢复直接 source，再重建链接。在 dry plan 中校验 source identity、请求的 selections、effective roots、source path availability 和冲突。将每个相对链接重新指向对应的直接 source 路径项，并原子替换 `whero-wiki-view.md`。不得 resolve 穿透 source symlink，也不得从最终 Wiki 补充 source View 中缺失的路径。元数据写入中断后，可读链接仍是可用性事实来源；完整重建则以保存的 selections 作为意图事实来源。
