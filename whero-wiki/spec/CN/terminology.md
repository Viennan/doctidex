# Whero Wiki 协议术语

协议状态：**v0.0.2 当前版本**。这些术语定义当前协议。

在协议文档中使用下列准确术语。首次引入术语或术语间的区别很重要时，使用反引号包围术语。

## 核心术语

- `Whero Wiki` 是一种以目录为根的知识组织，由有效的 `whero-wiki-meta.md` 标识。
- `Wiki Root` 是包含该身份文件的目录。目录名称不属于身份协议。
- `Maintained Document` 是由 Whero Wiki 编写或维护的文档。`Collected Source` 是从外部取得且不在原地维护其正文的快照。
- `Framework Document` 是识别、导航、校验或操作 Wiki 所需的维护文档。沿选中祖先路径必须携带的框架文档称为 `View-Required Document`。
- `External Reference` 把包含目录树之外拥有的内容放置到稳定逻辑路径。每个外部引用使用 `Mount` 或 `Whero Wiki View` 作为投影方式。
- `Mount` 完整暴露外部仓库或目录。其传输形式可以是相对符号链接、普通 Git checkout 或 Git submodule。
- `Whero Wiki View`，简称 `View`，是对 `Whero Wiki` 或另一个 `View` 保持结构、可选择且透读的投影。
- `Preserved Boundary` 是阻止 Whero 在文件或目录内部进行维护的本地所有权规则。它不是传输或投影机制。
- `Selection` 是为 `View` 请求的源逻辑文件或目录。`Effective Root` 是补全框架文件、提升 whole-only 边界或穿过的 source symlink，并应用 collapse 后的物化根。因此，selection 与 effective root 可以不同，而不改变调用方的意图。
- `Source-Reachable Path` 是直接 source Wiki 或 source View 中存在的逻辑路径，包括通过已声明 Mount 和 source 所有权规则允许的符号链接到达的路径。物化时保留该直接 source 路径，不用最终 resolve 后的目标替换它。
- `Source Locator` 记录如何定位或恢复外部源。`Source Identity` 记录经过审阅或已物化的源状态。

## 保留词汇

使用 `View` 表示选择性投影及其物化结果。普通组织分组使用目录、子树、主题或集合等词。

`Disclosure` 只保留为描述暴露内容这一动作的普通动词，不再作为协议对象名称。`Preserved` 描述维护所有权，不描述内容位于本地、远端、Mount 中还是已被选择。

## 规范名称

View 元数据文档命名为 `whero-wiki-view.md`，并设置 `whero_view: true`。
必须随 selection 携带的 framework context 设置 `whero_view_required: true`。
View 校验 profile 命名为 `view`。
