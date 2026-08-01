# 协议解析与校验

## `protocol/document.py`

责任：读取/round-trip UTF-8 Markdown frontmatter，并用 CommonMark parser 提取文件 link。
非责任：root 选择、协议策略、Git 或 external mapping。

`MarkdownLink` 属性为 `label`、`target`、文档顺序 `order`。`DoctidexDocument` 属性为
`path`、round-trip `data`、Markdown `body`、原换行风格 `newline`；`doctidex` 和 `is_root`
提供只读视图，`links()` 返回 link，`render()`/`write()` 保留 YAML 注释与原字段并以同目录
临时文件、`fsync`、`os.replace` 原子发布。YAML 禁止重复键；解析错误转换为结构化错误。

## `protocol/root.py`

`RootContext(root, index)` 保存 exact 根和已解析根 index。`root_at` 只接受直接包含 root marker
的目录；`discover_roots` 从输入的词法父链返回全部根；`select_root` 实现显式 exact 选择、
包含约束以及 zero/multiple/mismatch 失败。`is_within` 使用平台绝对路径作词法包含判断，不
解析 doctidex link 或 external identity。

## `protocol/validation.py`

公共入口 `validate_protocol(context, scopes, limit, cursor)`；`normalize_scopes` 校验根绝对
目录、词法规范化、去重并消除已覆盖后代。内部 `IndexInfo` 保存目录、document 和三个局部
配置的规范化 `Path` 列表；`LinkFact` 保存 target 与是否可作为可达边。

`_Validator` 的属性为 context/root、protocol findings、semantic candidates、index map、
Markdown 内容、已扫描路径和 `scan_complete`。执行顺序固定为：

1. full coverage 不跟随目录 symlink 扫描全根；scoped coverage 只扫描 scope 子树、祖先 index
   与从这些 index 可达的必要 Markdown 导航支持；
2. 校验 root/index marker 与 index 连续性；
3. 解析最近负责的 `boundary-set`、`atomic-indexing`、`unsafe`，拒绝越根、越下级 scope 和
   现存非目录 boundary/atomic target；
4. 校验 atomic 元文件禁令、safe log marker 与连续性；
5. 解析根内 link 和关联 HTML 注释，计算首次 boundary；unsafe source link 只贡献可解析
   可达边，不重新承担被豁免的内容规则；
6. 以 visited path 计算每个负责范围的可达闭包；
7. 在当前 coverage 的完整领域结果上作 scope/support 过滤、稳定排序和分页。

文件不存在或不可读的必要 safe link、无效注释与不可达目标分别产生 Finding；semantic
candidate 不改变 protocol pass/fail。fingerprint 由已扫描路径的 mode/size/mtime 构成，内容
或集合变化使 cursor blocked。

并发边界：validation 不加锁且只读；扫描中变化可能形成一个已完成但 fingerprint 不连续的
观察，后续 cursor 会拒绝混合状态。scoped fingerprint 只覆盖 scope 与必要支持路径；scope
外未进入支持闭包的内容不会被读取，也不会使该 cursor 失效。

证据：`tests/test_protocol.py` 覆盖 safe/unsafe boundary 注释、可达性、index/log/atomic、
目录类型、reference-link 注释、scope 支持闭包与非目标子树隔离、双列表 budget 和 cursor
state；完整语义候选仍由 agent 判断。
