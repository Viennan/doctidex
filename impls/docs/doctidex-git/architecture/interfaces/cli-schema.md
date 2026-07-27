# CLI 结果与字段契约

本篇定义 CLI 的 JSON、人读格式和全部公共字段。字段不是每次都出现；每个命令的精确
字段集合在后半部分列出。序列化、预算和渲染如何实现见
[Python CLI 与 rendering](../../details/python/cli-and-rendering.md)。

## 1. JSON 格式

`--json` 输出一个 JSON object，并遵循：

- 输出是一个 JSON object；
- key 按字典序排列，不按本文表格顺序；
- Unicode 保持原字符；
- 缩进为 2；
- 未知或不适用的显式值使用 `null`，布尔值保持 JSON boolean；
- 空数组和空 object 仍保留，除非某段代码本身不添加该字段。

Agent 需要稳定读取字段时应使用 `--json`。人读输出适合快速查看，但 blocked 时只
展示第一个 finding，且始终隐藏 `details`。

## 2. 人读格式

非 blocked payload 先按以下优先顺序输出存在且非 `null`/空列表/空 object 的字段：

```text
status, operation, root, result,
protocol_structure, semantic_review, plugin_readiness,
mount_state, mount_path, source, declared_revision,
effective_commit, readable,
maintenance_root, base_commit, target_branch,
changed, planned_changes, findings, semantic_candidates,
items, collection, next_actions
```

剩余字段按 key 排序输出，但 `details` 永远省略。label 把下划线替换为空格并仅将首
字符大写。object/array 被压成一行 JSON，boolean 显示为 `yes`/`no`。

blocked payload 使用固定格式：

```text
Cannot continue: <operation>
Reason: <first finding message>
Still available: <result>
Changes made: <changed items or none>
Next actions:
1. <first finding action>
Need from user: <requires_user or none>
```

它不显示第二个及后续 findings、`affected`、`details` 或 batch items。因此 agent 在
失败处理、批量操作和审阅中应优先使用 JSON。

## 3. 退出码

| 退出码 | 条件 |
|---:|---|
| `0` | payload 不 blocked，且 `protocol_structure` 不是 `fail`。`status: warning` 通常仍为 0。 |
| `1` | payload 顶层 `protocol_structure: fail`。当前主要是 `check`。 |
| `2` | payload 顶层 `status: blocked`。命令行语法错误通常也为 2，但不保证结构化 payload。 |
| `130` | 执行期间被调用者中断。 |

不要仅凭退出码把 warning 当作完全通过：`plugin_readiness: blocked` 或
`semantic_review: required` 当前可以退出 0。

## 4. 公共顶层字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `status` | string | 操作级状态：`ok`、`warning`、`blocked`。它不是协议符合性字段。 |
| `operation` | string | 产生 payload 的稳定操作名，例如 `mount_prepare`、`maintenance_handoff`。 |
| `root` | string/null | 当前命令选中的 doctidex 根；mount 操作中它是宿主根。resolve 使用 `--from` 时可能与 `link_root` 不同。无法建立根上下文的失败通常为 `null`；batch 子结果可能有 root。 |
| `result` | string | 对已完成或仍保留结果的简短说明，不是完整诊断。 |
| `changed` | array 或 boolean | 多数命令为实际改变的文件路径数组；batch/prepare/close 常为空数组。`mount_sync` 特例为 old/new commit 是否不同的 boolean。必须按 operation 解读。 |
| `planned_changes` | array[string] | dry-run 与 apply 共同展示计划涉及的文件；当前只由 `init` 返回。 |
| `items` | array[object] | list、status、scope、changes 或 batch 的项目。项目 schema 由 operation 决定。 |
| `findings` | array[object] | 确定性问题或 batch 汇总的问题；元素见“Finding”。 |
| `semantic_candidates` | array[object] | 需 agent 阅读判断的候选；不是 confirmed finding。 |
| `next_actions` | array[string] | 成功或 warning 后建议的有序后续动作。与 blocked finding 内 `actions` 不同。 |
| `collection` | object | 输出预算产生的列表统计和 cursor；没有列表被截断且 offset 为 0 时字段缺失。 |
| `affected` | array[string] | blocked 原因影响的路径、逻辑 mount 或其他对象。 |
| `requires_user` | string/null | blocked 操作是否需要某类用户输入或授权；`null` 表示 agent 可按 actions 自行处理。 |
| `details` | object | 仅 JSON 可见的有限诊断补充；人读输出隐藏。它不应成为正常流程前置。 |

## 5. 状态字段和值

| 字段 | 可能值 | Agent 解读 |
|---|---|---|
| `status` | `ok` | 当前操作完成；仍需查看独立结果域。 |
| `status` | `warning` | 结果可用，但存在协议失败、插件未就绪或语义候选。 |
| `status` | `blocked` | 当前请求未完成；按 finding actions 或询问用户。 |
| `protocol_structure` | `pass`/`fail` | 当前确定性协议检查是否有 error。 |
| `semantic_review` | `clear`/`required` | 是否存在需 agent 阅读判断的候选。`required` 不等于内容错误。 |
| `plugin_readiness` | `ready`/`blocked`/`not_applicable` | Git mount 使用前置是否满足。它不改变协议结构结论。 |
| `mount_state` 或 mount item `state` | `ready`/`not_prepared` | 当前逻辑 mount 是否有有效 commit 且可读路径存在。 |
| maintenance item `state` | `ready`/`has_changes` | maintenance root 的 Git porcelain 是否为空。 |
| `mode` | `host_read`/`mount_read` | `context` 对输入路径的字符串级读取模式提示。 |
| `source`（PathContext） | `local`/`mount` | 路径来自宿主本地内容还是声明 mount。 |
| `host_scope` | `included`/`excluded` | 路径是否属于宿主 doctidex 的索引/维护范围。 |
| scope item `kind` | `host_root`/`mounted_source` | maintenance scope 的独立维护单位类型。 |

## 6. Finding

Finding object 当前使用以下字段：

| 字段 | 类型/是否必有 | 含义 |
|---|---|---|
| `domain` | string，可选 | `protocol_structure`、`semantic_review` 或 `plugin_readiness`。通用 blocked error finding 通常没有 domain。 |
| `severity` | string，必有 | 当前使用 `error` 或 `info`。 |
| `code` | string，必有 | 稳定机器标识；用于分支处理，不应只匹配英文 message。 |
| `message` | string，必有 | 用户层原因或候选说明。 |
| `actions` | array[string]，必有 | 可执行下一步；blocked 时按顺序处理。 |
| `path` | string，可选 | finding 对应文件、内部路径或配置位置。通用 error 可能只在顶层 `affected` 给路径。 |
| `index` | string，可选 | 语义候选由哪个 `index.md` 负责。`init` 产生的候选当前没有该字段。 |

协议结构 finding 通常同时有 `domain/path`；通用 blocked finding 可能只有
severity/code/message/actions，受影响对象位于顶层 `affected`。

## 7. Semantic candidate

语义候选沿用 finding 的基本字段，并总是：

```json
{
  "domain": "semantic_review",
  "severity": "info",
  "code": "...",
  "path": "...",
  "message": "...",
  "actions": ["..."]
}
```

`index_reference_candidate` 在完整 protocol validation 中另有 `index`；`init` 的根直接
子项候选没有 `index`。`git_change_review` 的 path 是 Git porcelain 相对路径，不一定
是绝对文件系统路径。

当前 candidate codes：

| code | 含义 |
|---|---|
| `index_reference_candidate` | 没有机器可解析的 Markdown link 精确指向负责范围中的路径；需阅读现有 prose。 |
| `git_change_review` | 非 index/log Git change 可能需要 index 或 log 跟进；需结合内容判断。 |

## 8. Revision selector

`declared_revision` 使用：

| 字段 | 类型 | 含义 |
|---|---|---|
| `kind` | string | `commit`、`tag` 或 `branch`。 |
| `value` | string | index 声明中的原值。它不保证当前能从远端解析。 |

它与 `effective_commit` 不同：selector 是意图，effective commit 是当前读取快照。

## 9. Mount item

`mount list`、`inspect.mount` 和 `resolve.mount` 使用相同 object：

| 字段 | 类型 | 含义 |
|---|---|---|
| `mount_path` | string | 根声明的规范化逻辑路径。 |
| `source` | string | 清理 userinfo 后的 Git URL 或本地路径。 |
| `declared_revision` | object | `{kind, value}` selector。 |
| `effective_commit` | string/null | 当前 source 与 selector 对应的 40 位读取 commit；首次 prepare 前通常为 null。 |
| `state` | string | `ready` 或 `not_prepared`。 |
| `readable` | boolean | effective commit 存在且逻辑 destination 当前存在/是 symlink 时为 true。 |
| `next_action` | string/null | ready 时 null；否则是精确 `doctidex-git mount prepare ...` 命令。 |

`effective_commit` 非 null 但可读路径丢失时仍返回 `not_prepared/readable: false`，
prepare 会尝试复用该 commit 恢复读取。

## 10. PathContext

`inspect.path_context` 与 `inspect.source_context` 字段完全相同：

| 字段 | 类型 | 含义 |
|---|---|---|
| `host_root` | string | 该上下文计算所基于的 doctidex 根。source_context 中是 mounted source 的呈现根。 |
| `path` | string | 被检查路径的绝对文件系统路径。 |
| `internal_path` | string | 相对于该 host_root 的绝对内部路径。 |
| `source` | string | `local` 或 `mount`。 |
| `host_scope` | string | `included` 或 `excluded`。 |
| `attributes` | array[string] | 去重排序的 `atomic`、`excluded`、`protected`、`mount`。多属性可同时存在。 |
| `responsible_index` | string/null | included 本地路径的负责 index。 |
| `applicable_log` | string/null | 最近 `log.md`。 |
| `boundary_index` | string/null | 建立 excluded 边界的 index。 |
| `boundary_condition` | object/null | 命中的单字段 `{path: string}` 或 `{regex: string}`。 |
| `mount_path` | string/null | 所属声明 mount path。 |

`source_context` 的出现条件是宿主 path_context 为 mount 且 mount item `readable: true`。

## 11. MarkdownLink

`inspect.links[]`：

| 字段 | 类型 | 含义 |
|---|---|---|
| `label` | string | CommonMark link 的 text/inline-code 标签拼接。 |
| `target` | string | 原始 href。可能是相对路径、绝对内部路径、外部 URL 或 anchor。 |
| `order` | integer | 当前 index 正文中的零基发现顺序。 |

这些字段不表示 target 已存在或符合推荐路径形式。

## 12. Git change

`changes.items[]`、maintenance `changes[]`：

| 字段 | 类型 | 含义 |
|---|---|---|
| `status` | string | Git porcelain v1 的两个状态字符；第一个是 index，第二个是 worktree。 |
| `path` | string | 相对于相应 Git worktree 的路径。 |
| `original_path` | string，可选 | rename/copy 时的原路径；只有 status 第一个字符为 `R`/`C` 时添加。 |

常见值包括 ` M`（worktree 修改）、`M `（staged 修改）、`A `、`D `、`R `、`??`。CLI
不展开 diff，不把 status 转换成自然语言。

## 13. Output collection

某个列表被截断或当前请求从后续页开始时，`collection` 以字段路径为 key 给出：

| 字段 | 类型 | 含义 |
|---|---|---|
| `total` | integer | 预算前列表长度。 |
| `returned` | integer | 当前页实际返回数。 |
| `collapsed_directories` | integer | 列表 object 中 `path`/`internal_path` 所涉及的不同父目录数。 |
| `groups` | object | 最多 limit 个按父目录名排序的 `parent -> count` 摘要；无可分组路径时为空。 |
| `truncated` | boolean | 当前页之后是否还有项目。 |
| `next_cursor` | string/null | 仅顶层列表且还有后续项时给出 opaque cursor；嵌套列表永远 null。 |

字段路径示例：`items`、`findings`、`semantic_candidates`、`items[].findings`、
`findings[].actions`。同一个 cursor 当前会推进所有顶层列表，因此包含多个顶层列表的
payload 不能把它理解为只属于某一个 collection key。Cursor 是 opaque token；调用方
只能原样回传 `next_cursor`，不能解析或自行构造。

## 14. Blocked error payload

所有预期的操作失败使用：

| 字段 | 类型 | 含义 |
|---|---|---|
| `status` | string | 固定 `blocked`。 |
| `operation` | string | 被阻止的操作。 |
| `root` | string/null | 已能明确选择根时为该根；在建立上下文前失败时通常为 null。 |
| `affected` | array[string] | 受影响对象。 |
| `changed` | array | 固定空数组；若异常前已产生其他独立结果，batch items/result 另行说明。 |
| `result` | string | 明确哪些结果仍保留；默认 `No changes were made.`。 |
| `findings` | array | 当前恰好一个 error finding。 |
| `requires_user` | string/null | 所需用户输入类别。 |
| `details` | object，可选 | 有限补充信息。 |

`requires_user` 当前值：

| 值 | 需要什么 |
|---|---|
| `doctidex_root` | 用户选择精确根。 |
| `repository_access` | Git 凭据或仓库访问。 |
| `network_access` | 允许或恢复网络。 |
| `revision` | 确认 commit/tag/branch。 |
| `external_references` | 决定并更新仍指向 mount 的文档。 |
| `mount_path` | 处理已占用逻辑路径。 |
| `source_url` | 选择或修正完整 doctidex source。 |
| `git_index` | 决定如何处理 tracked mount 内容。 |
| `git_action` | 决定 commit/交付后再关闭维护根。 |

`details` 当前 shape：

- `plugin_not_ready`：`ignored_by_root_gitignore` boolean、`tracked_count` integer；
- `unexpected_failure`：`diagnostic_id` string。

## 15. `context` 字段

### 15.1 找到根

| 字段 | 含义 |
|---|---|
| `status` | `ok`。 |
| `operation` | `context`。 |
| `git_worktree` | Git top-level 绝对路径。 |
| `root` | doctidex 根绝对路径。 |
| `index` | 根 `index.md` 绝对路径。 |
| `mode` | `host_read` 或 `mount_read`。 |
| `result` | 固定语义为 context 已选择。 |

### 15.2 未找到根

| 字段 | 含义 |
|---|---|
| `status` | `warning`。 |
| `operation` | `context`。 |
| `git_worktree` | Git top-level 或 null。 |
| `root` | null。 |
| `result` | 说明没有根。 |
| `next_actions` | 当前只包含 init dry-run 建议。 |

## 16. `init` 字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `status` | string | `ok`。 |
| `operation` | string | `init`。 |
| `root` | string | 选择或计划创建的根。 |
| `index` | string | 根 index 路径。 |
| `applied` | boolean | 是否传入 `--apply`。 |
| `network` | boolean | 当前固定 false。 |
| `changed` | array[string] | apply 时实际计划写入的 index/.gitignore；dry-run 为空。 |
| `planned_changes` | array[string] | 需要创建或修正的文件，无论 apply 与否都返回。 |
| `semantic_review` | string | 有根直接子项候选时 `required`，否则 `clear`。 |
| `semantic_candidates` | array | 根直接子项候选。 |
| `plugin_readiness` | string | apply 时直接为 `ready`；dry-run 有 planned changes 时 `blocked`，否则 `ready`。它不重新读取 apply 后 Git index。 |
| `result` | string | plan ready 或结构已初始化且下一步为 agent 语义复核。 |

## 17. `inspect` 字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `status` | string | `ok`。 |
| `operation` | string | `inspect`。 |
| `root` | string | 宿主根。 |
| `path_context` | object | 必有，见 PathContext。 |
| `links` | array，可选 | 有 responsible index 时，该 index 的 MarkdownLink 列表。 |
| `mount` | object，可选 | 目标属于 mount 时的 Mount item。 |
| `source_context` | object，可选 | mount 可读时从 source root 重新计算的 PathContext。 |
| `semantic_candidates` | array | 当前负责 index 的候选；可以为空。 |
| `result` | string | 路径上下文已检查。 |

## 18. `resolve` 字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `status` | string | `ok`。 |
| `operation` | string | `resolve`。 |
| `root` | string | 选中的命令上下文根；使用 mounted LINK_DOCUMENT 时通常是原宿主根。 |
| `input` | string | 用户原始 INTERNAL_PATH。 |
| `internal_path` | string | 规范化后路径。 |
| `link_document` | string，可选 | 传给 `--from` 的现有文件的绝对可访问路径；省略 `--from` 时字段缺失。 |
| `link_root` | string | 本次解析实际使用的文件系统 link root。它可以是命令 root，也可以是宿主 mount 下的 source root。 |
| `link_root_kind` | string | `host_root` 表示命令/宿主根语义；`mounted_source` 表示普通绝对 link 从 `link_document` 所属挂载源根解析。 |
| `working_path` | string | 原生文件工具可尝试访问的路径；mounted source 结果仍位于宿主可访问 mount path 下。 |
| `crosses_mount` | boolean | 本次解析是否依赖一个宿主 mount；既包括目标命中宿主 mount，也包括从 mounted source 解析普通绝对 link。 |
| `mount` | object/null | 与本次解析相关的 Mount item；未涉及 mount 时为 null。 |
| `result` | string | 普通 resolved，或提示 mount 尚未准备。 |

`--from` 只提供 link 来源，不解析文档内容。源文档中的普通 `/...` 会产生
`link_root_kind: mounted_source`；源文档中的 `/.doctidex/mounts/...` 按 namespace
回边产生 `host_root`。因此 agent 不应假设 `root == link_root`。

## 19. Mount 命令字段

### 19.1 `mount_list`

| 字段 | 含义 |
|---|---|
| `status` | `ok`。 |
| `operation` | `mount_list`。 |
| `root` | 宿主根。 |
| `items` | Mount item 数组。 |
| `result` | 找到的 Git mount 数量。 |

### 19.2 `mount_add`

| 字段 | 类型/含义 |
|---|---|
| `status` | `ok`。 |
| `operation` | `mount_add`。 |
| `root` | 宿主根。 |
| `mount_path` | 已校验逻辑路径。 |
| `source` | 清理后的 URL。 |
| `declared_revision` | selector。 |
| `network` | 固定 false。 |
| `changed` | apply 时为根 index 单元素数组；dry-run 为空。 |
| `result` | 声明可添加或已添加。 |
| `mount_state` | 固定 `not_prepared`。 |

当前没有 `applied` 字段，需从 `changed`、result 或调用参数判断。

### 19.3 `mount_remove`

| 字段 | 含义 |
|---|---|
| `status` | `ok`。 |
| `operation` | `mount_remove`。 |
| `root` | 宿主根。 |
| `mount_path` | 被移除或计划移除的声明。 |
| `changed` | apply 时根 index 路径数组；dry-run 为空。 |
| `result` | 可安全移除或已移除。 |

当前没有 `applied` 字段。

### 19.4 单项 `mount_prepare`

| 字段 | 含义 |
|---|---|
| `status` | `ok`。 |
| `operation` | `mount_prepare`。 |
| `root` | 宿主根。 |
| `mount_path` | 准备的逻辑路径。 |
| `source` | 清理后的 URL。 |
| `declared_revision` | selector。 |
| `effective_commit` | 已准备的完整 commit。 |
| `mount_state` | 固定 `ready`；未完成时使用 blocked 结果。 |
| `readable` | true。 |
| `changed` | 空数组；prepare 不改变用户维护的公开文件，但会使 mount 可读。 |
| `result` | 外部目录树可读。 |

### 19.5 单项 `mount_sync`

| 字段 | 类型/含义 |
|---|---|
| `status` | `ok`。 |
| `operation` | `mount_sync`。 |
| `root` | 宿主根。 |
| `mount_path` | 同步目标。 |
| `source` | 清理后的 URL。 |
| `declared_revision` | selector。 |
| `old_effective_commit` | string/null，调用前有效 commit。 |
| `new_effective_commit` | string，新解析 commit。 |
| `changed` | boolean，old/new 是否不同。 |
| `applied` | boolean，是否传入 apply；old==new 时 true 也不会重建。 |
| `result` | already current、new available 或 synchronized。 |

### 19.6 Mount batch

当 prepare/sync 目标数不是 1 时：

| 字段 | 含义 |
|---|---|
| `status` | 有任一子项 blocked 时 `blocked`，否则 `ok`。 |
| `operation` | `mount_prepare` 或 `mount_sync`。 |
| `root` | 宿主根。 |
| `items` | 每个目标的完整成功 payload 或 blocked error payload；blocked item 额外补 `mount_path`。 |
| `findings` | 所有 blocked item findings 的扁平汇总。 |
| `completed_count` | 成功 callback 数。 |
| `total_count` | 目标总数。 |
| `changed` | 固定空数组；真实逐项 changed 位于 items。 |
| `result` | completed/total 摘要并说明已完成结果保留。 |

## 20. Maintenance 命令字段

### 20.1 `maintenance_scope`

顶层为 `status: ok`、`operation: maintenance_scope`、`root`、`items`、`result`。

`host_root` item：

| 字段 | 含义 |
|---|---|
| `kind` | `host_root`。 |
| `root` | 宿主 doctidex 根。 |
| `base_commit` | 当前 HEAD 或 null。 |
| `write_path` | agent 可直接维护的宿主根路径。 |

`mounted_source` item：

| 字段 | 含义 |
|---|---|
| `kind` | `mounted_source`。 |
| `mount_path` | 宿主逻辑 mount。 |
| `source` | 清理后的 source URL。 |
| `base_commit` | effective commit 或 null。 |
| `read_only_path` | 宿主 mount 的文件系统路径。未准备时也会返回该计划路径。 |
| `write_action` | 精确 maintenance open 命令。 |

### 20.2 `maintenance_open`

| 字段 | 含义 |
|---|---|
| `status` | `ok`。 |
| `operation` | `maintenance_open`。 |
| `root` | 宿主根。 |
| `maintenance_root` | 新 maintenance root 的绝对路径。 |
| `mount_path` | 来源 mount。 |
| `source` | 清理后的 URL。 |
| `base_commit` | open 的有效 commit。 |
| `target_branch` | branch selector 值，否则 null。仅为交付提示。 |
| `writable_root` | 当前与 maintenance_root 相同。 |
| `boundaries` | `{writable: <path>, host_mount: "read_only"}`。`writable` 是允许写入根；`host_mount` 是宿主路径边界状态。 |
| `next_actions` | 使用源 index 维护、check、handoff 三个提示。 |
| `changed` | 空数组；open 不改变用户维护的公开文件，但会创建维护现场。 |
| `result` | 独立维护根已就绪。 |

### 20.3 `maintenance_status`

顶层为 `status: ok`、`operation: maintenance_status`、`root`、`items`、`result`。

每个 item：

| 字段 | 含义 |
|---|---|
| `maintenance_root` | 登记路径。 |
| `mount_path` | 来源 mount。 |
| `source` | 清理后的 URL。 |
| `base_commit` | open 时 commit。 |
| `target_branch` | branch 提示或 null。 |
| `state` | 有 changes 时 `has_changes`，否则 `ready`。 |
| `change_count` | 预算前 Git change 数。 |
| `changes` | Git change 数组，可能被 limit 截断；用 change_count/collection 判断完整性。 |

### 20.4 `maintenance_handoff`

| 字段 | 含义 |
|---|---|
| `status` | 协议 fail、插件 blocked 或有语义候选时 `warning`，否则 `ok`。 |
| `operation` | `maintenance_handoff`。 |
| `maintenance_root` | 被交付路径。 |
| `mount_path` | 来源 mount。 |
| `source` | 清理后的 URL。 |
| `base_commit` | 维护基准 commit。 |
| `target_branch` | branch 提示或 null。 |
| `changes` | Git change 数组。 |
| `change_count` | 预算前 change 数。 |
| `protocol_structure` | `pass`/`fail`。 |
| `semantic_review` | 合并候选后的 `clear`/`required`。 |
| `plugin_readiness` | 维护根 `.gitignore`/tracked 状态。 |
| `findings` | 协议 structure findings。当前不额外加入 readiness finding。 |
| `semantic_candidates` | 协议候选加 Git change candidates。 |
| `result` | 维护结果已保留供 agent 审阅。 |
| `next_actions` | 审阅 diff/候选并向用户请求 Git 动作授权。 |

该 payload 当前没有顶层 `root` 字段；`maintenance_root` 是被检查的 source root。

### 20.5 `maintenance_close`

| 字段 | 含义 |
|---|---|
| `status` | `ok`。 |
| `operation` | `maintenance_close`。 |
| `maintenance_root` | 已关闭路径。 |
| `changed` | 空数组。 |
| `result` | clean maintenance context 已关闭。 |

有 changes 时返回通用 blocked schema，code 为 `maintenance_has_changes`，affected 和
result 明确保留的 maintenance path。

## 21. `check` 字段

| 字段 | 类型/含义 |
|---|---|
| `status` | `ok` 或 `warning`。 |
| `operation` | `check`。 |
| `root` | 被检查根。 |
| `protocol_structure` | 协议 validation 的 pass/fail。 |
| `semantic_review` | 合并协议与 Git change candidates 后的 clear/required。 |
| `plugin_readiness` | root Git ignore 与 Git mount 扩展状态。 |
| `findings` | 协议 findings，加 Git 扩展/readiness findings。 |
| `semantic_candidates` | 协议 candidates 加 Git change candidates。 |
| `remote` | offline 时空数组；online 时每个 Git mount 一项。 |
| `result` | 检查未改变文件或 mount 的 effective commit；online 仍可能刷新本地 Git 信息。 |

Online `remote[]`：

| 字段 | 含义 |
|---|---|
| `mount_path` | mount 逻辑路径。 |
| `effective_commit` | 当前本地有效 commit 或 null。 |
| `remote_commit` | refresh 后 selector 解析结果。 |
| `update_available` | 只有 effective commit 非 null 且与 remote 不同时为 true；首次未 prepare 时即使 remote 已解析也为 false。 |

`check` 不返回 `mount_count`，也不展开 readiness 的检查过程；blocked finding 提供
用户层动作。

## 22. `changes` 字段

| 字段 | 含义 |
|---|---|
| `status` | `ok`。 |
| `operation` | `changes`。 |
| `root` | 所选 doctidex 根，不一定等于传给 Git status 的 PATH。 |
| `items` | Git change 数组。 |
| `result` | 预算前发现的 change 数。 |

## 23. Code 目录

下表按当前代码分组列出可机器处理的 code。

### 23.1 文档、根和路径

| code | 含义 |
|---|---|
| `invalid_utf8` | doctidex 文档不是 UTF-8。 |
| `document_unreadable` | 文件系统读取失败。 |
| `frontmatter_missing` | 文档开头没有 YAML frontmatter。 |
| `frontmatter_invalid` | YAML 解析失败。 |
| `frontmatter_not_mapping` | YAML 顶层不是 mapping。 |
| `root_not_found` | PATH 不在任何可识别 doctidex 根内。 |
| `root_ambiguous` | 命中多个根且没有精确选择。 |
| `link_source_invalid` | `resolve --from` 没有指向一个现有文件。 |
| `git_worktree_required` | init 目标不在 Git worktree。 |
| `internal_path_not_absolute` | 内部路径不以 `/` 开头。 |
| `internal_path_escape` | `..` 越过 link root。 |
| `filesystem_path_outside_root` | 文件系统路径不在所选根内。 |
| `cursor_invalid` | pagination cursor 无法解码。 |

### 23.2 协议结构

| code | 含义 |
|---|---|
| `root_marker` | 根缺少严格 boolean `doctidex.root: true`。 |
| `top_level_type` | 顶层 `type` 与 index/log 文件类型不符。 |
| `doctidex_type` | `doctidex.type` 与文件类型不符。 |
| `index_continuity` | index 祖先链缺少 index。 |
| `log_continuity` | log 祖先链缺少 log。 |
| `mount_exclude` | 根 excludes 缺 `.doctidex/mounts`。 |
| `atomic_document` | atomic 目录内出现 index/log。 |
| `link_path_escape` | 可解析 link 越过 link root。 |
| `filter_not_list` | 某过滤字段不是列表。 |
| `filter_shape` | 条件不是只含一个字段的 mapping。 |
| `filter_value` | 条件 key/value 不是合法 path/regex 非空字符串。 |
| `filter_path` | path 条件是绝对路径或含越界 `..`。 |
| `filter_regex` | VERSION1 regex 编译失败。 |

### 23.3 Mount 声明与就绪

| code | 含义 |
|---|---|
| `mounts_not_list` | `doctidex.mounts` 不是 list。 |
| `mounts_on_non_root` | 非根 index 声明 mounts。 |
| `mount_not_mapping` | 某声明不是 mapping。 |
| `mount_field_invalid` | type/url/mount_path 缺失或非空字符串要求不满足。 |
| `mount_path_invalid` | mount path 不在 namespace 严格子路径下。 |
| `mount_path_not_normalized` | 输入含可折叠段或 nested namespace，未使用规范形式。 |
| `mount_paths_overlap` | 声明重复或祖先/后代重叠。 |
| `mount_root_required` | add 时选中的 index 不是根。 |
| `mount_not_declared` | 精确路径没有 Git mount 声明。 |
| `mount_still_referenced` | remove 扫描到仍指向 mount 的 Markdown links。 |
| `git_mount_src_path` | Git 扩展不支持 `src_path`。 |
| `git_mount_revision` | revision 不是唯一合法 selector。 |
| `git_url_invalid` | URL/本地路径为空或多行。 |
| `git_url_credentials` | HTTP(S) URL 内嵌 credentials。 |
| `plugin_not_ready` | mount 写操作前根 ignore/tracked 状态不安全。 |
| `git_mount_not_ready` | check 对同一 readiness 问题生成的 finding code。 |
| `mount_path_occupied` | 逻辑路径含未识别内容或无法安全替换。 |
| `mount_unreadable` | 插件无法让 mount path 成为普通文件工具可读的目录。 |
| `source_root_missing` | source checkout 根没有 index.md。 |
| `source_root_invalid` | source index 不是 doctidex root。 |

### 23.4 Git source

| code | 含义 |
|---|---|
| `git_auth_required` | 远端需要 credentials/access。 |
| `git_network_unavailable` | 网络/DNS/连接不可用。 |
| `git_revision_unavailable` | Git 报告 ref/object 无法解析。 |
| `git_revision_not_commit` | rev-parse 结果不是预期完整 commit。 |
| `git_failed` | 未分类 Git 失败。 |
| `revision_view_unavailable` | 本地已有 commit 读取现场不可复用。 |

### 23.5 Maintenance、候选和运行时

| code | 含义 |
|---|---|
| `maintenance_source_not_prepared` | open 前 mount 没有 effective commit。 |
| `maintenance_root_ambiguous` | handoff/close 没有精确选中一个 context。 |
| `maintenance_has_changes` | close 时仍有 Git changes，结果已保留。 |
| `index_reference_candidate` | index link 候选。 |
| `git_change_review` | Git change 的 index/log 跟进候选。 |
| `interrupted` | 操作被 Ctrl-C 中断。 |
| `unexpected_failure` | 未预期异常；使用 details.diagnostic_id 报告。 |
| `doctidex_error` | 没有更具体分类时的通用 doctidex 操作失败。 |
