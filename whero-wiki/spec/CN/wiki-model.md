# Whero Wiki 模型

协议状态：**v0.0.2 当前版本**。

## 身份

`Whero Wiki` 仅由 `Wiki Root` 中的 `whero-wiki-meta.md` 标识。该文件必须是受维护的 `Framework Document`，并包含：

```yaml
type: Whero Wiki
format_version: "0.0.2"
whero_wiki: true
whero_maintenance: true
whero_view_required: true
```

完整 Wiki 拥有普通的身份文件。`View` 通过相对符号链接暴露源身份，并添加自身的普通文件 `whero-wiki-view.md`。

## 文档分类

该模型有四类文档：

1. `Collected Source` 保留外部取得的原始字节，通常没有 Whero frontmatter。
2. `Maintained Document` 设置 `whero_maintenance: true`，包含由 Whero 编写或维护的知识。
3. `Framework Document` 由 Whero 维护；当每个选中后代都需要该文件来解释或操作 Wiki 时，设置 `whero_view_required: true`。
4. `whero-wiki-view.md` 是生成的 View 元数据。它受 Whero 维护并且是 View-required，但只存在于物化的 `View` 中。

`whero-wiki-meta.md`、受维护的 `index.md` 和受维护的 `log.md` 是标准框架文件名。维护知识文档不能仅因有用或经过策展就成为 View-required 文档。

## 所有权

除非路径进入 `External Reference` 或声明的 `Preserved Boundary`，否则最近的包含该路径的 `Wiki Root` 拥有该路径。外层 Wiki 可以导航和引用边界内的内容，但不得跨越该边界维护其中由其他主体拥有的内容。

普通外部仓库在其 `Mount` 根自动具有 preserved 语义。被 Mount 的 `Whero Wiki` 或 `View` 保留自己的 Whero 所有权和生命周期，而不继承包含 Wiki 的所有权。

## 导航与历史

使用小写 `index.md` 进行维护式导航，使用小写 `log.md` 记录有价值的维护历史。若文件为空洞则二者都不是必需的。当它们作为框架元数据存在时，设置 `whero_maintenance: true` 和 `whero_view_required: true`。

内部文档链接遵循[链接](links.md)。外部所有权和投影遵循[外部引用](external-references.md)。选择性投影遵循 [Whero Wiki View](views.md)。
