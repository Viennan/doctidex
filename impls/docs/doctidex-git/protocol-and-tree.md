# 协议解析与目录树判断

本篇说明 `whero.doctidex.protocol` 当前如何读取 Markdown、规范化路径、匹配过滤条件、
计算路径上下文并生成协议与语义结果。它描述代码行为，不扩展协议要求。

## 1. `DoctidexDocument`

`DoctidexDocument` 是 `index.md` 和 `log.md` 的 round-trip 表示：

| 属性 | 含义 |
|---|---|
| `path` | 文档文件系统路径。 |
| `data` | `ruamel.yaml.comments.CommentedMap`，即 frontmatter 顶层 mapping。 |
| `body` | closing `---` 后的原始 Markdown 正文。 |
| `newline` | 从 frontmatter 检测到的 `\n` 或 `\r\n`，写回时继续使用。 |
| `doctidex` | `data["doctidex"]` 为 mapping 时返回该 mapping，否则为 `None`。 |
| `is_root` | 仅当 `doctidex.root is True` 时为真。字符串 `"true"` 不算。 |

### 1.1 读取

`load(path)` 要求文件为 UTF-8，并且第一个字符开始就是：

```text
---
<YAML mapping>
---
```

YAML 使用 round-trip 模式、禁止重复 key、保留引号和未知字段。frontmatter 缺失、YAML
无效或顶层不是 mapping 都转换为带动作的 `DoctidexError`。

### 1.2 新建根

`new_root(path)` 产生最小结构：

```yaml
type: index
doctidex:
  type: index
  root: true
  excludes:
    - path: .doctidex/mounts
```

正文初始为空。`init` 后续可能再加入 `.git` exclude。

### 1.3 写回

`write()` 在目标目录创建临时文件，写入并 `fsync` 后使用 `os.replace`。已有文件的
mode 会复制给新文件。它保持未修改正文和 round-trip YAML 信息，但重新序列化整个
frontmatter，因此不能假设字节完全不变。

### 1.4 Markdown links

`markdown_links(content)` 使用 `markdown-it-py` 的 CommonMark 模式，只提取解析器产生
的 `link_open` token。每个 `MarkdownLink` 字段为：

| 字段 | 含义 |
|---|---|
| `label` | link 内 text 与 inline code 拼接出的标签；其他 inline token 不加入。 |
| `target` | 原始 `href` 字符串。 |
| `order` | 在该正文中从 0 开始的发现顺序。 |

非标准 Markdown 扩展、裸路径和普通文本中的路径不进入该列表。图片也不是
`link_open`，当前不会作为文档 link 返回。

## 2. 内部路径

### 2.1 `normalize_internal_path`

输入必须以 `/` 开头。函数按 `/` 分段：

- 忽略空段和 `.`；
- `..` 弹出上一段，若已经没有上一段则报 `internal_path_escape`；
- 遇到 `.doctidex/mounts` 两段时，将此前累计路径替换为该 namespace；
- 输出始终为 `/` 加规范化分段。

因此：

```text
/.doctidex/mounts/a/guide/.doctidex/mounts/b/index.md
```

会变为：

```text
/.doctidex/mounts/b/index.md
```

实现按路径段处理 namespace，不依赖物理符号链接。

### 2.2 Mount path

`validate_mount_path` 先规范化，再要求：

- 是 `/.doctidex/mounts` 的严格后代；
- 输入本身已经是规范形式；
- 不等于 namespace 根。

不同声明之间的重复、祖先/后代重叠由 `read_mounts` 或 Git add 再检查。

### 2.3 文件系统转换

`internal_to_filesystem(root, value)` 把规范化内部路径的各段追加到 `root`。
`filesystem_to_internal(root, path)` 使用绝对但不解析符号链接的路径，要求目标在 root
内，然后返回 `/` 开头的 POSIX 路径。它使用 `abspath` 而不是 `resolve`，因此不会
以实际 symlink target 改写逻辑路径。

`mount_for_path(value, mount_paths)` 返回包含目标的最长 mount path；没有命中时为
`None`。

## 3. 根发现

`discover_roots(path)` 从目标目录向文件系统祖先逐级查找 `index.md`。若输入看起来是
文件（已存在文件，或不存在但具有 suffix），从父目录开始。候选 index 必须成功解析
且 `is_root` 为真；解析失败的祖先会被跳过。

返回顺序从最近祖先到更远祖先。`require_root` 的选择规则为：

1. 没有根：`root_not_found`；
2. 参数恰好是某个根目录：选择该精确根，即使外层还有根；
3. 否则命中多个根：`root_ambiguous`，要求提供精确根；
4. 只有一个：选择它。

`RootContext` 只有两个字段：

| 字段 | 含义 |
|---|---|
| `root` | 所选根的文件系统路径。 |
| `index` | 已加载的根 `DoctidexDocument`。 |

## 4. 路径上下文

`inspect_path(context, path)` 生成 `PathContext`。其公开字段也由 `inspect` 返回：

| 字段 | 计算方式 |
|---|---|
| `host_root` | `RootContext.root` 的绝对路径。 |
| `path` | 被检查目标的绝对路径。路径可以尚不存在。 |
| `internal_path` | 目标相对于宿主根的绝对内部路径。 |
| `source` | `local` 或 `mount`。只要内部路径命中声明就为 `mount`。 |
| `host_scope` | `included` 或 `excluded`。mount 在宿主语义中始终 excluded。 |
| `attributes` | 去重排序后的 `atomic`、`excluded`、`protected`、`mount` 组合。excluded 匹配会压制同一步的其他过滤属性。 |
| `responsible_index` | included 本地路径的最近有效负责索引；其他情况为 `null`。 |
| `applicable_log` | 从目标所在目录向宿主根找到的最近 `log.md`；不存在时为 `null`。 |
| `boundary_index` | 导致 excluded 边界的 index；mount 使用根 index。 |
| `boundary_condition` | 命中的单个 `{path: ...}` 或 `{regex: ...}`；mount 为 `{path: ".doctidex/mounts"}`。 |
| `mount_path` | 命中的声明 mount path；本地路径为 `null`。 |

遍历目标各路径段时，当前负责 index 从根开始。目录存在有效子 `index.md` 且此前未
进入 atomic 时，责任转移到子 index。子 index 无法解析时，代码暂时保留父 index，
具体格式问题由完整 validation 报告。

## 5. 过滤条件

当前实现读取 `doctidex.atomic_entries`、`excludes`、`protected`，并映射为属性
`atomic`、`excluded`、`protected`。

每个条件必须是只含一个 key 的 mapping：

- `path`：非空相对路径，不得包含越过根的 `..`；
- `regex`：非空 `regex` VERSION1 pattern。

### 5.1 实际匹配基准

对于负责 index 到目标的相对路径 `a/b/file.md`，代码生成以下前缀：

```text
a
a/b
a/b/file.md
```

`path` 条件与任一前缀完整相等即命中，所以 `{path: a}` 同时覆盖 `a` 及其后代。
`regex` 对每个前缀执行 `search`，不自动加 `^` 或 `$`。默认区分大小写，目录名后不
追加 `/`，路径分隔符为 `/`。

atomic 只对目录参与 `inspect_path` 匹配；文件本身不会得到 atomic 属性。excluded
命中时，该次返回只保留 excluded 条件，并停止沿该路径继续切换负责 index。

### 5.2 Regex 编译

`DoctidexPattern` 固定使用依赖中的 `regex==2026.7.19`，flags 为
`VERSION1 | UNICODE`。编译失败保存错误消息与可用时的字符位置。该方言是当前 Git
实现约定，不是协议当前规定的统一方言。

## 6. 基础 mount 解析

`read_mounts(root_document)` 只负责基础字段：

| 字段 | 要求 |
|---|---|
| `type` | 非空字符串；基础层不限制具体值。 |
| `url` | 非空字符串；基础层不解释其传输语义。 |
| `mount_path` | 非空、规范化且位于 namespace 下的绝对内部路径。 |

`MountDeclaration.raw` 保留原始 `CommentedMap`，供 Git 层读取 `revision` 或 round-trip
删除。非根 index 只要包含非空 mounts 就报错。所有 mount path 必须互不重复且不互为
祖先/后代。

Git 层只消费 `type: git`，并额外验证 URL、禁止 `src_path`、要求唯一 revision
selector；详见 [Git 运行时](git-runtime.md)。

## 7. 协议校验

`validate_protocol(RootContext)` 返回：

| 字段 | 含义 |
|---|---|
| `protocol_structure` | 有任一 error finding 时为 `fail`，否则 `pass`。 |
| `semantic_review` | 有任一语义候选时为 `required`，否则 `clear`。 |
| `findings` | 确定性协议结构问题。 |
| `semantic_candidates` | 需要 agent 阅读判断的候选。 |
| `mount_count` | 基础 mount 声明数量；Git CLI 的 `check` 当前不把该字段透传到顶层。 |

检查内容包括：

- 根和普通 index/log 的顶层 `type` 与 `doctidex.type`；
- 根 `doctidex.root: true` 与 `.doctidex/mounts` exclude；
- index/log 祖先连续性；
- 过滤条件 shape、path 和 regex；
- atomic 目录内不得出现 `index.md` 或 `log.md`；
- 非根 index 不得声明 mounts；
- CommonMark 文档 link 规范化时不得越过链接根。

### 7.1 遍历和剪枝

`walk_content` 使用 `os.walk(..., followlinks=False)`：

- 不跟随目录 symlink，也不返回 symlink 目录；
- excluded 目录不进入；
- atomic 目录不进入普通递归校验；
- atomic 由单独遍历检查内部是否出现禁止的 index/log；
- 普通 `.md` 文件只进行 link 越界检查；
- `index.md`/`log.md` 还进行 frontmatter、marker、连续性检查。

当前 link 校验不检查目标是否存在、不校验 anchor、不验证普通链接是否必须使用推荐
的相对/绝对形式，也不解析非 CommonMark 扩展。这些属于当前实现限制，而不是“检查
通过即证明所有链接有效”。

## 8. 语义候选

对每个有效 index，代码计算其负责路径：

- 跳过 index 自身、symlink 和 excluded；
- 收集直接子项并继续递归普通目录；
- 遇到 atomic 或具有自身 `index.md` 的目录后停止向内递归；
- 将 index 中可解析 Markdown link 解析为文件系统目标；
- 未被这些 link 精确指向的负责路径产生 `index_reference_candidate`。

候选字段包括 `domain`、`severity`、`code`、`index`、`path`、`message`、`actions`。
它只表示“没有机器可解析的 link 精确命中”，不能证明正文没有自然语言索引说明。
agent 必须阅读 index 正文后决定保留现状还是补写 link。

CLI `check` 和 `maintenance handoff` 还会为非 index/log 的 Git change 添加
`git_change_review`，提示 agent 判断是否需要 index/log 跟进。

## 9. 结构 finding codes

协议层当前可能产生：

- 文档读取：`invalid_utf8`、`document_unreadable`、`frontmatter_missing`、
  `frontmatter_invalid`、`frontmatter_not_mapping`；
- 根与 marker：`root_marker`、`top_level_type`、`doctidex_type`；
- 连续性：`index_continuity`、`log_continuity`；
- mount 基础结构：`mount_exclude`、`mounts_not_list`、`mounts_on_non_root`、
  `mount_not_mapping`、`mount_field_invalid`、`mount_path_invalid`、
  `mount_path_not_normalized`、`mount_paths_overlap`；
- 过滤：`filter_not_list`、`filter_shape`、`filter_value`、`filter_path`、
  `filter_regex`；
- 内容边界：`link_path_escape`、`atomic_document`；
- 路径/根选择异常：`internal_path_not_absolute`、`internal_path_escape`、
  `filesystem_path_outside_root`、`root_not_found`、`root_ambiguous`。

每个 code 的通用字段结构和 agent 处理方式见 [CLI 输出字段参考](cli-output.md) 与
[Agent 解读指南](agent-interpretation.md)。
