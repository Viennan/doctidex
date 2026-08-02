# 协议解析与校验

## [`protocol/document.py`](../../../../../impls/libs/python/whero/doctidex/protocol/document.py)

责任：读取/round-trip UTF-8 Markdown frontmatter，并用 CommonMark parser 提取文件 link。
非责任：root 选择、协议策略、Git 或 external mapping。

`MarkdownLink` 属性为 `label`、`target`、文档顺序 `order`。`DoctidexDocument` 属性为
`path`、round-trip `data`、Markdown `body`、原换行风格 `newline`；`doctidex` 和 `is_root`
提供只读视图，`links()` 返回 link，`render()`/`write()` 保留 YAML 注释与原字段并以同目录
临时文件、`fsync`、`os.replace` 原子发布。YAML 禁止重复键；解析错误转换为结构化错误。

`tree_observations(context, excluded_roots=...)` 是供 protocol 以外消费者使用的只读解释入口。
它返回 `TreeObservations`：不跟随 directory symlink 的 filesystem paths、可读 Markdown raw content、
由 `MarkdownLink` 提取并以 `_resolve_link` 词法规范化的 `ObservedMarkdownLink`，以及由
`IndexInfo.entries` 得出的 responsible index、unsafe/boundary membership。`excluded_roots` 与
`excluded_configuration_fields` 只停止相应目录的递归枚举，仍保留其词法入口；external remove 因此不
读取 install payload、boundary-set 或 unsafe 内部。

Validation 与 observations 都由同一个 `_Validator` discovery/configuration pass 产生，后者不返回
protocol findings。`_validate_links` 直接消费 `TreeObservations.links`，再应用 annotation、boundary、
unsafe 与 reachability policy 生成 `LinkFact`。因此 CommonMark extraction、frontmatter stripping、URI
拆分、percent decode、root-relative resolution 和 directory-symlink scanning 没有第二套实现；external
service 只能对 observations 加其自身的删除扫描排除和 reference policy。

`ruamel.yaml` 使用 round-trip loader，`markdown-it-py` 使用 `commonmark` preset；filesystem
discovery 通过 `os.walk(..., followlinks=False)` 与 `.md` scanning 避免递归 directory symlink。
`urllib.parse.urlsplit/unquote` 完成当前 destination 拆分与 decode。这些 library/profile/decoder
选择属于 Python realization；Architecture 只约束最终 protocol path conclusion 不得越 root。

## [`protocol/root.py`](../../../../../impls/libs/python/whero/doctidex/protocol/root.py)

`RootContext(root, index)` 保存 exact 根和已解析根 index。`root_at` 只接受直接包含 root marker
的目录；`discover_roots` 从输入的词法父链返回全部根；`select_root` 实现显式 exact 选择、
包含约束以及 zero/multiple/mismatch 失败。`is_within` 使用平台绝对路径作词法包含判断，不
解析 doctidex link 或 external identity。

CLI 的显式 validate root 复用 `select_root`：index 缺失、不可解析或 root marker 无效时在选择
阶段以 `root_not_found` blocked。`RootContext` 创建后，validator 才处理扫描期间观察到的 root
structure finding。

## [`protocol/validation.py`](../../../../../impls/libs/python/whero/doctidex/protocol/validation.py)

公共入口 `validate_protocol(context, scopes, limit, cursor)`；`normalize_scopes` 校验根绝对
目录、词法规范化、去重并消除已覆盖后代。内部 `IndexInfo` 保存目录、document 和三个局部
配置的规范化 `Path` 列表；`LinkFact` 保存 target 与是否可作为可达边。

`_Validator` 的属性为 context/root、protocol findings、semantic candidates 和 `TreeObservations`；
其 discovery pass 填充 index map、Markdown 内容、已扫描路径和 `scan_complete`。执行顺序固定为：

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
candidate 不改变 protocol pass/fail。当前以空 body index 触发 `index_description_review`，并为
effective unsafe entry 产生 `unsafe_scope_review`。Support discovery、Finding suppression 与
`LinkFact` 等中间对象由 `_Validator` control flow 实现，不提升为 Architecture 模型。

Fingerprint 由已扫描路径的 root-relative name、mode/size/mtime-nanoseconds 构成，路径集合或
这些 metadata 变化使 cursor blocked。

并发边界：validation 不加锁且只读；扫描中变化可能形成一个已完成但 fingerprint 不连续的
观察，后续 cursor 会拒绝已检测到的 state mismatch。Scoped fingerprint 只覆盖 scope 与必要
支持路径；它由 relative name、mode、size 与 nanosecond mtime 构成，不读取 content digest。
这是一致性检测机制而不是 content-addressed snapshot 保证；调用方需要强一致观察时从第一页
重新运行 validation。

证据：[tests/test_protocol.py](../../../../../impls/libs/python/tests/test_protocol.py) 的
`test_boundary_unsafe_annotation_and_reachability`、
`test_invalid_annotation_and_unreachable_path_are_separate_findings`、
`test_index_log_and_atomic_rules`、`test_reference_link_annotation_is_associated_with_the_link`、
`test_scoped_validation_does_not_read_unrelated_subtree` 和
`test_scoped_validation_filters_output_and_cursor_is_state_bound` 分别覆盖上述边界；完整语义候选
仍由 agent 判断。
