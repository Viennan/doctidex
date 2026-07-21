# Preserved Boundary

协议状态：**v0.0.2 当前版本**。

`Preserved Boundary` 阻止包含它的 Wiki 在文件或目录内进行原地维护。其内容仍可读取、搜索、链接和引用。Preserved 不会创建新的 source identity 或投影。

## 精确路径

在最近的受维护、View-required `index.md` 中声明精确路径：

```yaml
whero_preserved_paths:
  - vendor
  - exports/raw.md
```

路径必须是安全、非空的相对 POSIX 路径。它们不得指向框架文件、逃逸 Wiki、进入另一个外部引用，或在规范化边界后互相重叠。

## 直接子项 Pattern

直接子项正则表达式规则使用：

```yaml
whero_preserved_patterns:
  - '^generated-.*$'
  - '.*\.lock'
```

对声明 index 所在目录的直接子项 basename，使用支持 Unicode 的 `fullmatch` 应用每个表达式。不得递归。无匹配的表达式合法，这使项目可以在生成内容出现之前声明稳定策略。无效表达式属于一致性错误。

Pattern 永远不能 preserve 框架文件。精确规则和 pattern 规则解析为一个边界集合；重复匹配无害，祖先边界会遮蔽后代匹配。

## 维护与 View

不得在 preserved boundary 内注入元数据、修复链接、校验内部内容或创建框架文档。为 `View` 选择边界根或任何后代都是合法的，并把整个边界作为一个原子 effective root 暴露。调用方可以继续选择所需后代，不必知道或请求边界根。外层 planner 不检查 preserved 后代，也不将其计入 collapse。

普通外部 `Mount` 自动具有 preserved 语义，无需在 `whero_preserved_paths` 或 `whero_preserved_patterns` 中重复声明。
