# CLI JSON Schema 契约

本文是 doctidex-git `v1.0.0` 稳定 JSON surface 的权威说明。调用语法和副作用见
[CLI](cli.md)，概念关系从 [Architecture models](../index.md#模型层)进入。本篇只定义可观察数据结构，
不重复用户步骤或内部 storage。未知 optional field 可以忽略；本篇标为 required 的字段
缺失或类型变化是兼容失败。

## 1. 公共结果结构

每次 `--json` 调用在 stdout 输出一个 object，不混入日志或进度文本。公共字段全部
required；空值使用 null 或空 collection，不依赖 key 缺失表达状态。

| 字段 | 类型 | 含义 |
|---|---|---|
| `schema_version` | string | 固定 `1.0`；不是 doctidex 协议版本。 |
| `operation` | string | 本篇定义的 operation discriminator；在 command/subcommand 尚未成功解析时固定为 `command`。 |
| `status` | `ok`/`warning`/`blocked` | 当前请求完成、完成但有需关注结果，或请求未完成。 |
| `result` | string | 已完成与已保留结果的简短说明。 |
| `root` | absolute path/null | 已选择的 doctidex 根；link-parse 为拥有外层安装/依赖的 owner root，cache clean 固定为 null，选择前 blocked 时也为 null。 |
| `changed` | array[absolute path] | 本次可可靠确定的公开路径 effects；dry-run/只读以及 publication 前 blocked 为空。Blocked 无法完整重建 effects 时可为空，调用方再依据 `affected` 重读现场。 |
| `network` | boolean | 本次是否实际访问 network。 |
| `findings` | array[Finding] | 客观问题、warning 或保留原因；默认空。 |
| `next_actions` | array[string] | 已完成结果的建议后续；默认空。 |
| `affected` | array[string] | blocked/partial result 影响对象；默认空。 |
| `requires_user` | string/null | 继续所需的用户输入类别；无需用户时 null。 |
| `collection` | Collection/null | validate/external restore/worktree list 的分页事实；其他 operation 为 null。 |

Blocked unexpected failure 可额外提供 `details: {"diagnostic_id": string}`；其他 details fields
不是 stable public contract。Diagnostic ID 只用于报告内部诊断，不是 path、authorization 或 cursor。

`status` 不替代 operation domain：validate 的 `protocol_structure: fail` 是已完成的 warning，
worktree dirty 是 list item state，只有当前请求无法按契约完成时才是 blocked。

## 2. Finding 与候选项

### 2.1 Finding

| 字段 | 类型 | 含义 |
|---|---|---|
| `domain` | `protocol`/`command`/`external`/`worktree`/`cache` | 问题所属的用户层领域。 |
| `severity` | `error`/`warning`/`info` | error 影响操作或协议结果；warning 表示可用但需处理；info 是客观提示。 |
| `code` | string | 稳定机器分支标识，不匹配 message。 |
| `message` | string | 不依赖内部 cache、lock、module 或 traceback 的说明。 |
| `path` | absolute path/null | 能定位时统一给出 normalized filesystem absolute path；validation 也不返回 root-relative spelling。不能公开 internal cache/lock path 的 domain 固定为 null。 |
| `actions` | array[string] | 有序、可执行恢复动作；不能以无限重试代替用户决定。 |

### 2.2 语义候选项

| 字段 | 类型 | 含义 |
|---|---|---|
| `code` | string | `index_description_review` 或 `unsafe_scope_review`。 |
| `path` | absolute path | 需要阅读的目标。 |
| `responsible_index` | absolute path | 判断所需的负责 index。 |
| `message` | string | 为什么需要语义判断，不声称 defect。 |
| `actions` | array[string] | 建议读取和决定步骤。 |

candidate 不进入 `findings`，也不改变 `protocol_structure`。

## 3. 集合与分页

| 字段 | 类型 | 含义 |
|---|---|---|
| `limit` | integer | 本页每个顶层列表的预算。 |
| `lists` | object | `field -> {total, returned, truncated}`；validate 使用 findings/semantic_candidates，external restore 与 worktree list 使用 items。 |
| `truncated` | boolean | 任一列表还有后续项时 true。 |
| `next_cursor` | string/null | 同时恢复所有列表位置的 opaque token；没有下一页时 null。 |

cursor 与 operation、root、规范化 scope/filter、limit 及命令定义的模式绑定。validate 的 scope 输入次序、
重复项或被祖先覆盖的后代不同，只要规范化后集合相同，就属于同一 cursor identity。
无效、过期或上下文不同返回 `cursor_invalid` blocked；不能静默回到第一页。排序 key 固定为：

| Collection | Ascending key |
|---|---|
| validate findings | `(path-or-empty, code, message)`。 |
| semantic candidates | `(path, code, message)`。 |
| restore items | `install_id`。 |
| worktree items | `worktree_path`。 |

同 key item 必须保持 deterministic order。Observed-state identity 由 Impls 根据该 operation 可
可靠观察的 query/state facts 形成，用于拒绝明显不属于同一结果现场的 continuation；它不是跨实现
wire identity，也不要求特定 canonical JSON/hash。Restore 使用 recovery manifest identity 与
normalized filter/install-ID selection，不包含 invocation 时观察到的 payload state，因此前页
apply 不使后页 cursor 失效。Cursor encoding 可以因实现而异。

## 4. RevisionSelector

```json
{"kind": "commit|tag|branch", "value": "string"}
```

显式 selector 保留调用输入。install 省略 revision 时返回 kind `commit` 和首次解析的
full object ID；`default_branch` 单独记录来源。`resolved_commit`/`base_commit` 始终是
repository object format 的完整 commit ID。

## 5. `validate`

非 blocked result 的 operation-specific required fields：

| 字段 | 类型 | 含义 |
|---|---|---|
| `operation` | `validate` | 操作判别字段。 |
| `coverage` | `full`/`scoped` | 结论覆盖整个 root，或仅覆盖调用方选择的目录集合及必要支持闭包。 |
| `scopes` | array[root-absolute POSIX directory path] | 规范化、排序、去重并删除已被祖先覆盖的目录；full 时固定为 `["/"]`。 |
| `protocol_structure` | `pass`/`fail` | 当前 coverage 及其必要支持闭包内是否存在 protocol error finding；scoped pass 不是全根符合结论。 |
| `scan_complete` | boolean | 当前 coverage 及其必要支持闭包的所有应检查 safe 内容是否完成读取和判断。 |
| `semantic_review` | `clear`/`required` | candidate 是否非空。 |
| `semantic_candidates` | array[SemanticCandidate] | 需要人或 agent 判断的候选。 |

`coverage: scoped` 的支持闭包按 [tree model](../models/doctidex-tree-and-configuration.md#5-reachability-与-scope)
包含 scopes 外的 root/祖先负责 index、适用局部配置、必要 navigation support 和 scopes 内 link
的必要目标。`findings` 与 `semantic_candidates` 只包含 scope
内事项，或直接阻止解释/验证 scope 的支持路径事项；collection totals 对该结果集合计数，
不是对整个根计数。

协议 finding code：

| code | 覆盖事实 |
|---|---|
| `root_invalid` | 根名、root index 存在性或 root marker。 |
| `document_unreadable` | 必查 Markdown 不存在、不可读、非 UTF-8。 |
| `frontmatter_invalid` | YAML、重复键、type 或 doctidex mapping/field 类型。 |
| `index_continuity_invalid` | index 接管链不连续。 |
| `log_continuity_invalid` | safe log 接管链不连续或 frontmatter 无效。 |
| `local_config_invalid` | boundary-set、atomic-indexing、unsafe 的 list/item/path/target kind。 |
| `local_config_scope_invalid` | 条目越根或越过下级 index 后声明其内部目标。 |
| `atomic_indexing_invalid` | atomic 目录内部出现协议 index/log 或接管边界。 |
| `unsafe_declaration_invalid` | unsafe 入口、外部责任或必须 link 注释不成立。 |
| `path_unreachable` | 负责 index 无有效 Markdown link path 到达必达目标。 |
| `link_path_invalid` | doctidex 文件路径 link 越根、目标不可读或无法形成有效路径边。 |
| `link_annotation_invalid` | doctidex 注释结构、重复、必需字段、boundary point 或 unsafe 值错误。 |
| `reserved_name_conflict` | 仅供显式启用且提供 machine-readable reserved-name contract 的 protocol extension；base `v1.0.0` 没有这类 registry，当前 validation 不得靠内容语义猜测或发射此 code。 |

同一 code 可通过 path/message 区分多个位置；实现不为每个 YAML 子错误发明不稳定 code。

## 6. 外部来源字段

DependencyParents：

```json
{"total": 1, "returned": 1, "truncated": false, "items": ["opaque-install-id"]}
```

`items` 按 install ID 排序，最多返回 100 项；`total` 是完整 parent 数量。该摘要不提供
pagination，因为 agent 建立或判断当前 edge 不需要枚举整个依赖图；`truncated: true` 时不得
把 items 当作完整集合。

### 6.1 `external_install`

非 blocked result 的 fields：

| 字段 | 类型 | 含义 |
|---|---|---|
| `operation` | `external_install` | 操作判别字段。 |
| `applied` | boolean | 是否实际 apply；dry-run 为 false。 |
| `install_id` | opaque string | 在 selected root 内稳定标识该 source install。 |
| `install_role` | `direct`/`dependency` | 是否进入恢复清单；direct 也可以具有 parent edges。 |
| `dependency_of` | DependencyParents | parent install IDs 的有界摘要。 |
| `manifest_included` | boolean | direct 为 true，dependency-only 为 false。 |
| `install_path` | root-absolute POSIX path | 工具分配的稳定内部路径，位于 `/.doctidex`；不公开具体命名算法。 |
| `working_path` | absolute path | 原生文件工具读取 repository 根的当前路径。 |
| `source_url` | sanitized string | 无 credentials 的 source identity。 |
| `source_relation` | `host_repository`/`other`/`unknown` | 能否可靠确认 source 就是 selected root 的宿主 Git repository。 |
| `revision_selector` | RevisionSelector | 显式 selector 或默认解析后的 commit selector。 |
| `default_branch` | string/null | 仅省略首次 install revision 时记录 remote default branch。 |
| `resolved_commit` | full commit ID | install 固定对应的 immutable commit。 |
| `host_repository` | absolute path | 包含 selected root 且负责 Git 追踪边界的 repository 根。 |
| `payload_tracking` | `ignored_untracked` | 安装载荷被精确 ignore 且没有 tracked entry。 |
| `git_exclusion_file` | absolute path | 宿主 repository 根 `.gitignore`。 |
| `git_exclusion_state` | `absent`/`tracked`/`modified`/`untracked` | 精确规则所在文件的 Git 状态；absent 只用于 dry-run 的 planned path。 |
| `recovery_manifest` | absolute path | 可版本化恢复清单的公开路径。 |
| `recovery_manifest_state` | `absent`/`tracked`/`modified`/`untracked` | 清单的 Git 状态；absent 只用于 dry-run 的 planned path，CLI 不代为 stage/commit。 |
| `responsible_index` | absolute path | 负责内部受管命名空间边界/unsafe 声明的 index。 |
| `frontmatter_changes` | FrontmatterChanges | 对内部命名空间 planned 或 actual structured changes。 |
| `planned_changes` | array[absolute path] | 可能修改的 index、`.gitignore`、install path 与受管记录；只有 direct/提升操作包含恢复清单。 |

首次省略 revision 的 `revision_selector.kind` 必须为 commit，且 value 等于
`resolved_commit`。remote default branch 后续移动不能改变任何现有 result。install identity
由 root、canonical source 和 normalized fixed selector 构成；default provenance 用于后续省略
selector 的 lookup，是否形成额外 physical key 维度由 Impls 定义。同 key 重试保持
`install_id`/`install_path`，dependency-only 可提升为 direct。

### 6.2 `external_link`

非 blocked result 的 fields：

| 字段 | 类型 | 含义 |
|---|---|---|
| `operation` | `external_link` | 操作判别字段。 |
| `applied` | boolean | 是否实际 apply；dry-run 为 false。 |
| `install_id` | opaque string | source 最终所属安装。 |
| `install_path` | root-absolute POSIX path | symlink 最终指向的稳定内部安装根。 |
| `source_path` | absolute path | 调用方传入并规范化后的受管 source directory。 |
| `target_path` | POSIX relative path | symlink 相对 selected root 的调用输入。 |
| `presentation_path` | absolute path | target 的文件系统入口，即使 dry-run 尚不存在也给出计划路径。 |
| `working_path` | absolute path | 原生文件工具读取 source directory 的路径。 |
| `repository_relative_path` | POSIX path | link 入口对应 repository 内的起始路径；根为 `.`。 |
| `source_url` | sanitized string | 从 install 继承的 source identity。 |
| `source_relation` | `host_repository`/`other`/`unknown` | 从 install 继承的宿主 source 关系。 |
| `revision_selector` | RevisionSelector | 从 install 继承的 selector provenance。 |
| `default_branch` | string/null | 从 install 继承的 default branch provenance。 |
| `resolved_commit` | full commit ID | symlink 当前指向 install 的固定 commit。 |
| `safe_state` | `safe`/`unsafe` | 该 link 入口的产品接入分类。 |
| `symlink_tracking` | `trackable` | symlink 未被宿主 Git ignore；CLI 不保证用户已 stage/commit。 |
| `responsible_index` | absolute path | 接收该 link boundary/unsafe 条目的最近负责 index。 |
| `frontmatter_changes` | FrontmatterChanges | 该 link planned 或 actual structured changes。 |
| `recovery_manifest` | absolute path | 同步记录 link mapping 的恢复清单。 |
| `recovery_manifest_state` | `tracked`/`modified`/`untracked` | 更新后的清单 Git 状态；link 的 source manifest 已存在。 |
| `planned_changes` | array[absolute path] | 可能修改的 index、symlink、恢复清单与 link mapping。 |

FrontmatterChanges：

```json
{
  "boundary_set": "add|existing",
  "unsafe": "add|existing|remove|not_required"
}
```

### 6.3 `external_restore`

RestoreItem：

| 字段 | 类型 | 含义 |
|---|---|---|
| `install_id` | opaque string | 恢复清单中的稳定安装标识。 |
| `install_path` | root-absolute POSIX path/null | 必须恢复到的原内部路径；未知 filter ID 为 null。 |
| `source_url` | sanitized string/null | 获取缺失 objects 的 portable source identity；未知 filter ID 为 null。 |
| `revision_selector` | RevisionSelector/null | 原安装的 selector provenance；不用于重新解析 moving ref；未知 filter ID 为 null。 |
| `default_branch` | string/null | 原安装省略 revision 时的来源信息。 |
| `resolved_commit` | full commit ID/null | 唯一允许恢复的 exact commit；未知 filter ID 为 null。 |
| `state` | `planned`/`restored`/`unchanged`/`blocked` | dry-run 可重建、apply 已重建、原内容已匹配，或该项未完成。 |
| `findings` | array[Finding] | item-level 阻塞与恢复动作；正常为空。 |

非整体 blocked result 的 fields：

| 字段 | 类型 | 含义 |
|---|---|---|
| `operation` | `external_restore` | 操作判别字段。 |
| `applied` | boolean | 是否实际 apply；dry-run 为 false，缺失且可重建的 item 使用 `planned`。 |
| `recovery_manifest` | absolute path | 本次读取的恢复清单。 |
| `recovery_manifest_identity` | opaque string | 用于 cursor 一致性判断，不泄漏内部 storage。 |
| `install_filter` | array[opaque string] | 规范化、排序并去重后的 filter；省略时为空。 |
| `items` | array[RestoreItem] | 当前有界页。 |

省略 filter 时 items 只来自 manifest 中的 direct installs。提供 filter 时，每个 normalized ID
在排序与 pagination 中占一项；未知 ID 产生字段为 null、`state: blocked`、code
`install_not_found` 的 RestoreItem，因此 total 与请求集合一致。Dependency-only install 和
dependency edges 不在无 filter 集合中。任一 item blocked 令顶层 status 至少为 warning，但其他 item 可以成功。整体清单缺失、schema
不可识别或无法选择宿主 repository 时，operation blocked。`collection.lists.items` 对 filter
后的记录计数；恢复载荷不改变 manifest identity，也不使后续 cursor 失效。

## 7. `external_link_parse`

非 blocked result 的 fields：

| 字段 | 类型 | 含义 |
|---|---|---|
| `operation` | `external_link_parse` | 操作判别字段。 |
| `managed` | boolean | 是否识别到 PATH 的 current-owner 或 installed-repository 受管 mapping 身份；不表示 target 可用或 mapping 完整。 |
| `mapping_origin` | `owner_root`/`installed_repository`/null | mapping 由当前 owner root 的受管记录提供，还是由 install 内 portable manifest 提供。 |
| `created_by` | `install`/`link`/null | 最内层 mapping 的创建 operation；portable external symlink 为 link。 |
| `content_root` | absolute path/null | 可确定时用于解释 repository-relative suffix 的 content root。Current-owner mapping 没有更内层 doctidex root 时可回退 owner root；portable/unmanaged input 无法确定时可为 null。 |
| `input_path` | absolute path | 规范化 PATH；broken symlink 保留 symlink 自身路径。 |
| `input_kind` | `directory`/`symlink` | 输入路径自身的种类，不跟随 symlink target 分类。 |
| `presentation_path` | absolute path/null | 命中的 install/link presentation；portable mapping 时为 install 内 symlink。 |
| `install_id` | opaque string/null | 当前 owner root 中实际提供 target 的 install；尚未安装时为 null。 |
| `install_path` | root-absolute POSIX path/null | 当前 owner root 中 target install 的稳定内部路径。 |
| `install_role` | `direct`/`dependency`/null | 当前 target install 是否进入恢复清单；尚未安装时为 null。 |
| `dependency_of` | DependencyParents | 当前 target install 的 parent 摘要；尚未安装或未受管时为空摘要。 |
| `dependency_parent_install_id` | opaque string/null | portable mapping 所在的当前外层 parent install；其他 origin 为 null。 |
| `target_state` | `available`/`owner_install_missing`/`dependency_not_installed`/`unavailable`/`not_applicable` | target 在当前 owner root 中的解析状态。 |
| `source_url` | sanitized string/null | target source identity；portable mapping 从版本化 manifest 恢复。 |
| `source_relation` | `host_repository`/`other`/`unknown`/null | source 与宿主 repository 的可靠关系。 |
| `revision_selector` | RevisionSelector/null | 固定 presentation 的 selector provenance。 |
| `default_branch` | string/null | 省略 install revision 时的初次来源。 |
| `resolved_commit` | full commit ID/null | target source 固定 commit。 |
| `repository_relative_path` | POSIX path/null | input 对应 target repository 内的位置，根为 `.`。 |
| `working_path` | absolute path/null | 当前 owner root 已有匹配 install 时可交给原生工具的 target 路径。 |
| `safe_state` | `safe`/`unsafe`/null | 该 presentation 入口分类。 |
| `responsible_index` | absolute path/null | 在 content root 中拥有 link boundary/unsafe 条目的 index。 |

顶层 `root` 始终是 owner root。`mapping_origin: installed_repository` 时，`content_root` 优先是
正在解释的 doctidex root；实现无法从当前 facts 可靠恢复 repository root 时可以为 null。
`dependency_parent_install_id` 是包含它的当前 install。

`target_state: dependency_not_installed` 是正常 `ok`：portable mapping 完整，但匹配依赖尚未
在 owner root 扁平安装；`install_id`、`install_path`、`install_role` 和 `working_path` 为
null，source/selector/commit/repository-relative path 仍完整。匹配 install 已存在时 state
为 available 并返回外层 working path，不能返回 install 内 broken symlink target。
调用方决定安装时，以 `source_url`、`resolved_commit` 和 `dependency_parent_install_id`
构造 `external install --commit ... --dependency-of ...`；`revision_selector` 中的 branch/tag
只是 provenance。

current-owner durable link 的目标 install 缺失时 state 为 `owner_install_missing`，status 为
warning，并提供 restore next action。managed false 时 mapping origin 为 null、target state
为 `not_applicable`，mapping/source/install fields 为 null，`content_root` 在可确定时仍可
返回，status 为 ok。已识别但损坏的 current-owner/portable mapping 保持 managed true：identity/
record/path 仍自洽、只是当前 target/working path 不可用时，以 `unavailable` + warning 完成诊断；
schema、identity、path containment、record reference 或 owner 证据不自洽，无法安全形成 mapping
时才 blocked。两者都使用 `mapping_damaged` finding 并保留仍可靠字段，不能伪装成 unmanaged 或
dependency_not_installed。

## 8. WorktreeItem

| 字段 | 类型 | 含义 |
|---|---|---|
| `source_kind` | `managed_path`/`url`/`working_tree`/`bare_gitdir`/`gitfile` | open 时的 source 分类。 |
| `owner_root` | absolute path | CLI-created worktree 所属的 selected doctidex root。 |
| `source_url` | sanitized string/null | 可公开 remote identity；纯本地且没有可公开 remote 时 null。 |
| `revision_selector` | RevisionSelector | open 输入。 |
| `base_commit` | full commit ID | detached worktree 基准。 |
| `root_internal_path` | root-absolute POSIX path | owner root 的 `/.doctidex` 下扁平受管路径。 |
| `worktree_path` | absolute path | repository 根的 writable worktree。 |
| `repository_relative_path` | POSIX path | 最初 SOURCE 对应位置，根为 `.`。 |
| `working_path` | absolute path | `worktree_path` 加 repository-relative suffix。 |
| `state` | `clean`/`changed`/`unavailable` | 当前客观 Git/文件系统状态。 |
| `findings` | array[Finding] | item-level 问题；正常为空。 |

Worktree ID 是 runtime-internal；public identity 是 `(owner_root, root_internal_path,
worktree_path)`，list/close filter 使用 exact worktree path。Local source 的 `source_url: null` 不
丢失 CLI identity：同一 item 仍由 source kind、repository-relative suffix 和 public worktree
paths 描述；跨调用按 source 过滤时调用方再次提供原 local path/gitdir，由实现规范化后比较
internal source identity，JSON 不承诺公开该 host-internal value。

### 8.1 `worktree_open`

非 blocked result：

| 字段 | 类型 | 含义 |
|---|---|---|
| `operation` | `worktree_open` | 操作判别字段。 |
| `worktree` | WorktreeItem | 新建且 state 为 clean 的现场。 |
| `reuse_candidate_count` | integer | 同 canonical source/base commit 的其他受管现场数。 |

candidate count 大于零时 status 为 warning，但 open 已完成且新现场保持独立。

### 8.2 `worktree_list`

| 字段 | 类型 | 含义 |
|---|---|---|
| `operation` | `worktree_list` | 操作判别字段。 |
| `items` | array[WorktreeItem] | 当前有界页；无匹配为空。 |

顶层 `root` 是 list 选择的 owner root，items 不跨 root。任一 unavailable item 令顶层
status warning，不阻断其他 items。

### 8.3 `worktree_close`

| 字段 | 类型 | 含义 |
|---|---|---|
| `operation` | `worktree_close` | 操作判别字段。 |
| `worktree` | WorktreeItem/null | 能识别时为关闭前/被保留状态；无法识别 exact path 时 null。 |

普通 clean close 成功时 `changed` 包含已实际移除的 worktree path；dirty/unavailable blocked 时
changed 为空且 worktree 保留。Path 或 exact Git registration 已 absent 时，当前操作返回
unavailable/blocked 并保留 ownership record；实现不从“path 不存在”推导删除授权。

## 9. `cache_clean`

非 blocked result 的 required fields：

| 字段 | 类型 | 含义 |
|---|---|---|
| `operation` | `cache_clean` | 操作判别字段。 |
| `applied` | boolean | 是否请求并完成 apply；dry-run 和 preserved 均为 false。 |
| `source_url` | sanitized string | 调用 URL 解析出的无 credentials source identity。 |
| `cache_source_id` | opaque string | 目标 shared bare source cache 的稳定不透明标识；不得据此构造 storage path。 |
| `linked_worktree_count` | integer | Git metadata 中全部 linked worktree registrations 数量；source bare repository 自身不是 linked worktree，不计入。 |
| `valid_worktree_count` | integer | Git 判为仍有效、因而阻止删除的 registrations 数量。 |
| `prunable_worktree_count` | integer | Git 明确判为 prunable 的 registrations 数量。 |
| `state` | `planned`/`removed`/`preserved` | dry-run 已证明可清理、apply 已删除 bare cache，或有效 worktree 令 cache 保留。 |

非 blocked result 中，三个计数均为非负整数，且
`linked_worktree_count = valid_worktree_count + prunable_worktree_count`；存在无法归入后两类
的 registration 时 operation 必须 blocked，不能用第三种隐含分类继续。`state: planned`
要求 `applied: false`、valid count 为零；`state: removed` 要求 `applied: true`、valid count
为零；`state: preserved` 要求 `applied: false`、valid count 大于零且 status 为 warning。

cache clean 的顶层 `root`、`collection` 固定为 null，`network` 固定为 false。内部 cache
path 不公开，因此包括 `removed` 在内的 `changed` 都为空。`cache_source_not_found`、metadata
损坏/无法分类或并发复查冲突是 blocked；blocked envelope 可以保留已可靠确定的上述字段，
但调用方不得假定 operation-specific fields 完整。删除后的重复调用返回
`cache_source_not_found`，而不是再次返回 `removed`。cache-domain Finding 的 `path` 固定为
null，不能用该字段泄漏内部 cache 或 Git metadata 路径。

## 10. `requires_user`

| 值 | 所需决定 |
|---|---|
| `doctidex_root` | 选择 exact root。 |
| `network_access` | 允许或恢复网络。 |
| `repository_access` | 提供 credentials 或 repository permission。 |
| `revision` | 选择有效 commit/tag/branch。 |
| `target_path` | 处理占用、overlap 或选择新路径。 |
| `install_parent` | 提供 selected root 中有效的 parent install ID，或改用普通 direct install。 |
| `git_tracking` | 处理已 tracked payload、冲突 ignore 规则，或 stage/commit 恢复清单与 symlink。 |
| `recovery_manifest` | 恢复、修复或选择有效的版本化清单。 |
| `git_action` | 处理 dirty worktree 的 commit、交付或保留。 |

## 11. 通用失败代码

| code | 典型恢复 |
|---|---|
| `argument_invalid` | 按 CLI contract 修正参数。 |
| `root_not_found` / `root_ambiguous` / `root_mismatch` | 传 exact ROOT。 |
| `path_invalid` / `path_not_directory` / `path_type_unsupported` | 传符合命令类型与根边界的路径；link-parse 只接受目录或 symlink。 |
| `target_occupied` / `presentation_overlap` | 选择新 target 或由用户处理现有内容。 |
| `host_git_not_found` / `host_git_ambiguous` | 让 selected root 位于唯一宿主 Git repository 后重试。 |
| `install_payload_tracked` | 用户用原生 Git 明确移除 payload 的 tracked entries；CLI 不运行 `git rm --cached`。 |
| `git_exclusion_conflict` | 审阅并修正冲突 ignore 规则，保持 payload ignored、manifest/link trackable。 |
| `link_target_ignored` | 调整 target 或 ignore 规则，使 symlink 可被宿主 Git 追踪。 |
| `symlink_unsupported` | 在支持 symlink 的文件系统/平台执行；不回退为目录复制。 |
| `source_invalid` / `source_unmanaged` | 修正 source locator 或先 install。 |
| `source_access_failed` | 处理 network/credentials/repository access。 |
| `default_branch_unavailable` | 显式提供 revision。 |
| `revision_invalid` / `revision_not_found` / `revision_not_commit` | 提供可唯一解析的 selector。 |
| `dependency_parent_invalid` | 传 selected root 中现有且完整的 parent install ID。 |
| `dependency_not_recoverable` | 以同 source/selector 运行普通 install，提升为 direct 后再建立 durable link。 |
| `mapping_damaged` | 保留可读内容，修复或重建精确 mapping。 |
| `owner_install_missing` | 按当前 owner root 的恢复清单 dry-run/apply restore；不要重写 durable link。 |
| `recovery_manifest_missing` / `recovery_manifest_invalid` | 恢复版本化清单或修复其 schema/portable facts。 |
| `install_not_found` | 修正 `--install` ID 或不带 filter 重新列出。 |
| `install_path_conflict` / `install_damaged` | 保留占用内容并人工判断；确认后再恢复 exact path/commit。 |
| `index_update_conflict` | 重新 dry-run，审阅并重试 apply。 |
| `partial_success` | 按 changed/affected/next actions 只补齐缺失步骤。 |
| `worktree_unmanaged` / `worktree_unavailable` | 传 exact managed path 或保留现场排查。 |
| `worktree_changed` | 原生 Git 审阅并由用户决定交付/保留。 |
| `cache_source_not_found` | 检查 URL；目标 source cache 已删除时无需继续 apply。 |
| `cache_source_damaged` | 完整保留 cache 和 linked paths；用原生 Git 检查或修复 bare repository/worktree metadata 后重新 dry-run。 |
| `cache_worktree_active` | cache 已保留；只有确认所有有效 linked worktree 生命周期结束后才重新 dry-run。 |
| `cache_cleanup_conflict` | cache 已保留；并发 source/worktree mutation 完成后重新 dry-run。 |
| `cursor_invalid` | 从第一页重新查询，不自行解析 token。 |
| `scope_invalid` | 提供根绝对、根内且指向现有可读目录的 scope；非法 scope 不会回退到全根。 |
| `interrupted` | 检查 changed 与现存路径后有限重试。 |
| `unexpected_failure` | 保存 diagnostic ID；安全重试一次后报告。 |

## 12. 退出码

| code | 条件 |
|---:|---|
| 0 | ok，或不含 protocol fail 的 warning。 |
| 1 | validate 完成且 `protocol_structure: fail`。 |
| 2 | blocked 或调用语法无效。 |
| 130 | 调用者中断；已完成状态保留。 |
