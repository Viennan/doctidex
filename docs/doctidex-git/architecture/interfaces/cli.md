# CLI 用户接口

本文是 doctidex-git `v1.0.0` 命令、参数、省略行为和副作用的权威说明。结果字段见
[JSON Schema](cli-schema.md)，共同任务语义分别见 [树与 validation](../tree-and-validation.md)、
[external snapshot](../external-snapshots-and-presentations.md)、[worktree/cache](../worktrees-and-cache.md)
与 [operation safety](../operation-safety-and-recovery.md)。本篇不重复 JSON 字段类型或内部发布算法。
当前 `1.0.0` 可执行程序实现本篇命令 surface。

`external` 与 `worktree` 命令定义可选受管工作流；`validate` 直接检查可观察目录树，不以
任何管理记录为前提。受管命令也不是 agent 的唯一读取或维护入口，原生 Git、手工
worktree、submodule、symlink 和其他工具保持可选；本篇的路径、恢复和 close 承诺只适用于
CLI 创建或登记的对象。

## 1. 命令总览

```text
doctidex-git validate [ROOT] [--scope INTERNAL_DIRECTORY]...
  [--limit N] [--cursor TOKEN] [--json]

doctidex-git external install --url URL [--root ROOT]
  [--commit COMMIT | --tag TAG | --branch BRANCH]
  [--dependency-of INSTALL_ID]
  [--dry-run | --apply] [--json]

doctidex-git external link SOURCE_DIRECTORY TARGET_PATH [--root ROOT]
  [--dry-run | --apply] [--json]

doctidex-git external restore [--root ROOT] [--install INSTALL_ID]...
  [--limit N] [--cursor TOKEN]
  [--dry-run | --apply] [--json]

doctidex-git external remove INSTALL_ID [--root ROOT]
  [--dry-run | --apply] [--json]

doctidex-git hook (--install | --run) [--root ROOT] [--json]

doctidex-git external link-parse PATH [--root ROOT] [--json]

doctidex-git worktree open SOURCE [--root ROOT]
  (--commit COMMIT | --tag TAG | --branch BRANCH) [--json]

doctidex-git worktree list [--root ROOT]
  [--source SOURCE | --worktree WORKTREE]
  [--limit N] [--cursor TOKEN] [--json]

doctidex-git worktree close WORKTREE [--json]

doctidex-git cache clean (--url URL | --auto) [--dry-run | --apply] [--json]
```

`context`、`inspect`、`resolve`、`init`、`changes`、`check`、整个 `mount` 与旧
`maintenance` 命令族不属于该 surface。普通文件与 Git 操作使用原生工具；`check` 的
协议职责由 `validate` 取代。

## 2. 通用选项

| 选项 | 缺省 | 契约 |
|---|---|---|
| `--json` | 人读输出 | 输出一个符合 `schema_version: "1.0"` 的 UTF-8 JSON object。可在顶层命令前或最终 subcommand 后出现一次；Skills 统一放在末尾。 |
| `--limit N` | 100 | 只用于 validate/external restore/worktree list；整数 1..1000，分别限制当前页每个顶层列表。 |
| `--cursor TOKEN` | 首页 | 只用于 validate/external restore/worktree list；必须原样回传，且 operation、root、规范化 scope/filter、limit 与模式必须符合对应命令的 cursor identity。 |
| `--dry-run` | 写命令默认值 | install/link/restore/remove/cache clean 计划完整结果，可联网条件见各命令，但不持久写入。 |
| `--apply` | false | install/link/restore/remove/cache clean 才执行各自契约内写入；与 `--dry-run` 互斥。 |

不接受无实际效果的 option。parser 在识别 `--json` 后遇到语法错误也返回 JSON blocked
envelope；未请求 JSON 时可以使用标准 stderr usage，但退出码仍为 2。

## 3. 路径类型与根选择

| 占位符 | 类型与约束 |
|---|---|
| `ROOT` | 现有、可读取且直接包含 `doctidex.root: true` index 的文件系统目录；相对值以 cwd 为基准。必须是根本身，不接受任意子路径。 |
| `INTERNAL_DIRECTORY` | `/` 或 `/docs/api` 形式的 doctidex 根绝对 POSIX 目录路径，不是宿主文件系统路径，也不接受 anchor；重复 `/`、`.` 与可在 root 内消去的 `..` 先词法规范化，结果不得越 root 且必须是现有可读目录。 |
| `TARGET_PATH` | 只用于 external link；所选根下的非空 POSIX relative path，不得以 `/` 开头，不得含空段、`.` 或 `..`，最终目标是 symlink。 |
| `SOURCE_DIRECTORY` | 现有可读文件系统目录，必须位于所选 root 及其完整受管 external mapping 内；相对值以 cwd 为基准。 |
| `PATH` | external link-parse 的现有可读目录或 symlink；symlink target 可以不存在。相对值以 cwd 为基准；其他不存在路径不接受。 |
| `INSTALL_ID` | external install 返回的稳定不透明标识；作为 filter 时可重复，重复值去重。 |
| `WORKTREE` | `worktree open` 返回的 exact filesystem path；close 不接受其子目录、等价 symlink 或手工 worktree。 |

| 命令 | 显式根 | 省略根 |
|---|---|---|
| validate | positional `ROOT` | 从 cwd 选择唯一包含根。 |
| external install/link/restore/remove | `--root ROOT`；link 时还必须包含 SOURCE_DIRECTORY | 从 cwd 选择唯一包含根，link 的 source 必须属于该根。dependency parent 也必须属于该根。 |
| hook | `--root ROOT` | 从 cwd 选择唯一包含根；`--install` 所得 hook 只协调该 root。 |
| external link-parse | `--root ROOT`，必须包含 PATH 或拥有其外层受管 presentation | PATH 位于受管 install/link 时恢复其 owner root；否则从 PATH 或其可读父目录选择唯一包含根。 |
| worktree open managed path | `--root ROOT`，必须包含 SOURCE | 从 SOURCE 选择唯一 mapping owner root。 |
| worktree open 其他 source | `--root ROOT` | 从 cwd 选择唯一包含根。 |
| worktree list | `--root ROOT` | 从 cwd 选择唯一包含根。 |
| worktree close | 不接受；从 exact WORKTREE 恢复 owner root | WORKTREE 必须归属唯一受管 root。 |
| cache clean | 不接受，也不选择 root | cwd 与 doctidex root 均不参与 source identity 或清理范围。 |

没有候选返回 `root_not_found`；多个候选返回 `root_ambiguous` 和候选路径，不采用“最近
祖先”猜测。显式 ROOT 与操作路径不匹配返回 `root_mismatch`。显式或自动选择都只接受有效
root；初始 index/marker 不可用时返回 `root_not_found` blocked。已经选中的 root 在扫描期间变得
不可读或结构失效时，validation 通过 finding 与 `scan_complete` 表达观察结果。

## 4. 修订选择（revision）

`--commit`、`--tag`、`--branch` 互斥：

- COMMIT 必须是 repository object format 的完整 object ID，不能是缩写；
- TAG/BRANCH 必须是单一合法 Git ref name，不接受 `..`、reflog、range 或其他 revspec；
- tag peel 后、branch tip 和 commit object 都必须唯一解析为 commit；
- 输出的 selector 保留显式 kind/value，读取或维护基准另以完整 commit 返回。

install identity 使用 selected root、canonical source 与 normalized fixed selector，而不是只使用
resolved commit：commit value 规范为 full object ID；tag/branch 保留各自 kind 和规范化 ref name；
省略 revision 在首次解析后固定为 commit selector，并另存 default provenance 供后续省略调用
优先复用。Default provenance 是否形成额外 physical key 维度由 Impls 定义。

install 可以省略 selector。首次创建时读取 remote default branch，将分支名保存为 provenance，
同时把有效 selector 归一化为 full commit。后续省略调用复用该 commit。worktree open
始终要求显式 selector。

## 5. `validate`

```text
doctidex-git validate [ROOT] [--scope INTERNAL_DIRECTORY]...
  [--limit N] [--cursor TOKEN] [--json]
```

- 离线、只读、不调用 AI；无 dry-run/apply。
- `--scope` 可重复；省略等价于 `/`。所有值先词法规范化并按规范路径排序、去重；祖先
  已覆盖的后代从有效集合移除。输入次序及冗余写法不改变有效集合；有效集合为 `["/"]`
  时 coverage 为 full，否则为 scoped。
- 任一 scope 不满足路径语法、越根、不是现有目录或不可读时返回 `scope_invalid` blocked，
  不扫描其余 scope，也不降级为全根。
- 不带 scope 时扫描协议要求的整个 safe 范围；带 scope 时扫描所选目录，并读取保证判断
  正确所需的支持闭包：root 和祖先负责 index、适用局部配置、可达性所需负责 index/导航
  文档，以及所选范围内 link 的必要目标。unsafe 内部始终只按协议保留的外部责任检查。
- 分开返回 deterministic findings 和 semantic candidates。scoped 输出只含所选目录内事项，
  以及直接阻止解释或验证所选目录的支持路径事项；collection total 在过滤后计算。
- 结果以 `coverage: full|scoped` 和规范化 `scopes` 回显覆盖范围。scoped
  `protocol_structure: pass` 只表示该范围及其必要支持闭包未发现协议 error，不表示整个
  root 符合；需要全根结论时省略 `--scope` 重新运行。
- 不读取 plugin registry，不检查 remote、Git status 或 presentation ownership。
- protocol fail 是已完成的 validation，status 为 warning、退出码为 1；root 无法选择或
  scope 非法才是 blocked、退出码 2。

## 6. `external install`

```text
doctidex-git external install --url URL [--root ROOT]
  [--commit COMMIT | --tag TAG | --branch BRANCH]
  [--dependency-of INSTALL_ID]
  [--dry-run | --apply] [--json]
```

- URL 必须是完整 repository locator；允许凭据只作为调用期输入，禁止写入 mapping 或输出。
- dry-run 可以访问 network，并只能使用可丢弃的调用期 Git 数据；持久 objects、恢复清单、
  root index、`.gitignore` 和 install path 均不改变。
- 每个 selected root/canonical source identity/normalized fixed selector 只有一个稳定 install key。工具
  分配稳定不透明 `install_id`，并由它确定 `/.doctidex` 下的稳定 `install_path`；调用方不
  提供 target。同 source 的不同 normalized selector 通常不共用路径；default provenance 的 key
  处理见对应 Impls。
- apply 持久取得 fixed commit，维护内部受管命名空间的边界/unsafe 结构、精确宿主
  `.gitignore` 规则和不被忽略的恢复清单，再发布逻辑只读 install。它不生成 prose 或
  Markdown link，也不执行 Git stage/commit/`rm --cached`。
- result 分别报告 `.gitignore` 和恢复清单的 `absent|tracked|modified|untracked` 状态；
  `absent` 只用于 dry-run 中尚不存在的 planned path。
- 安装载荷必须未被宿主 Git 追踪；恢复清单必须可追踪。宿主 repository 无法唯一确定、
  载荷已有 tracked entry 或有效 ignore 规则破坏该边界时 blocked，不自动改写无关规则。
- 同 install key 重试只幂等核对并复用记录 commit，不重新解析 branch/tag；新 selector
  创建新 install。命令不提供 replace。
- 省略 `--dependency-of` 创建或提升为 `direct` 并写恢复清单。提供该参数时，ID 必须属于
  selected root 的完整 install；结果建立/复用 `dependency`，只更新运行期 parent edge，
  不写恢复清单。direct 不降级，dependency-only 可由后续普通调用原地提升。
- dependency 始终与 parent 并列位于 selected root 的 `/.doctidex`；CLI 不读取依赖文档、
  不自动递归。命中既有 install key 即停止，因此 self/cycle 有界。
- source 指回 host repository 时也返回独立 fixed-commit install，不返回当前 working tree。
  source/commit 可可靠匹配且 objects 已存在时可以离线复用宿主 Git objects。

## 7. `external link`

```text
doctidex-git external link SOURCE_DIRECTORY TARGET_PATH [--root ROOT]
  [--dry-run | --apply] [--json]
```

- 全程离线，不 fetch、不重解析 revision、不写 source Git objects。
- SOURCE_DIRECTORY 可位于 direct install 或另一个 link 内；以最内层完整 mapping 为准。
- apply 创建指向稳定 install path 或其子目录的相对 symlink，并更新恢复清单；禁止绝对
  symlink 和目录复制 fallback。平台不支持 symlink 或 target 被有效 Git ignore 时 blocked。
- target 独立获得 boundary/unsafe frontmatter 与 link mapping，不继承 source 入口状态；
  只有 SOURCE_DIRECTORY 本身可作为完整 doctidex 根通过 validation 时才标为 safe，否则
  按 unsafe 接入。
- 同 target/同 mapping 幂等；不同 mapping 或任何占用/overlap blocked。
- 没有 replace。工具不删除或移动旧 link，也不 stage/commit symlink 或相关文档。
- dependency-only source 返回 `dependency_not_recoverable`；调用方以相同 source/selector 运行
  普通 install 提升为 direct 后重试。

## 8. `external restore`

```text
doctidex-git external restore [--root ROOT] [--install INSTALL_ID]...
  [--limit N] [--cursor TOKEN]
  [--dry-run | --apply] [--json]
```

- 读取可版本化恢复清单中的 portable facts，只按记录的 source、exact resolved commit 和
  stable install path 恢复；不发现 default branch、不解析移动 ref。
- 省略 `--install` 时分页处理全部记录；指定时按稳定 install ID 排序、去重和过滤。未知
  ID 返回 item-level blocked，不把它当作空匹配。
- dry-run 可检查本地对象并按需访问记录的 source，但不写入。apply 在对象不足时可以联网
  获取 exact commit，并把缺失 install 重建到原路径。
- 每项返回 `planned|restored|unchanged|blocked`；`planned` 只用于 dry-run 中可重建的缺失项。
  单项失败不撤销其他项。路径被未受管内容占用、清单损坏或 Git 排除边界不成立时保留
  现场并给出恢复动作。
- 从 manifest 重建必要的内部 install/link mapping，但不重写、重建或 stage 已有 external
  link symlink。恢复成功后 symlink 因固定目标路径重新可用。
- cursor 绑定 root、恢复清单 identity、规范化 install filter、排序后的 install-ID selection、limit
  和 dry-run/apply mode；清单变化令 cursor invalid，恢复载荷本身不令 cursor 失效。每次调用只
  dry-run/apply 当前页，调用方以 next cursor 继续后续项。

## 9. `external remove`

```text
doctidex-git external remove INSTALL_ID [--root ROOT]
  [--dry-run | --apply] [--json]
```

- `INSTALL_ID` 是 selected owner root 内一个 complete 或 hidden dependency managed install 的唯一 target；命令不接受
  multiple IDs、source URL、revision、payload path、cursor 或 pagination。未知、损坏或不属于该 root
  的 ID 返回 blocked 并保留现场。
- 调用者只有 managed path 而不知道 ID 时，先运行 `external link-parse PATH [--root ROOT]`，只使用
  结果的 current `install_id`；`dependency_parent_install_id` 不是可删除 target，unmanaged 或
  `dependency_not_installed` 没有 current install 可删除。
- preflight 复用 validate 的 tree observation 层，对 safe Markdown navigation link、filesystem
  symlink、runtime/manifest durable mapping 和指向 target 的 dependency parent edge 检查引用；不递归
  扫描 install payload、boundary-set 或 unsafe 内部。这个 external policy 不改变 validation 的 protocol
  scope 或 findings。
- 任一 target reference 都返回 `install_referenced` blocked，并在 affected/findings 中提供可定位的
  document、symlink 或 managed-record evidence。命令不自动删除或改写引用。
- hidden dependency install 不执行删除 preflight 或物理 mutation；dry-run 和 apply 都以 completed
  `preserved_hidden` result 保留 payload、runtime parent edge 与所有其他 state。它不是 reference block，
  也不要求调用方解除 hidden 才能安全重试。
- 其他 target 的 dry-run 执行完整 preflight、回显 planned deletion，但不写入。apply 在 source -> root mutation
  boundary 内重查 target/reference；只有 reference-free 时才移除 exact payload、runtime install
  record，且对 direct install 移除 manifest install record。它不改写 presentation、frontmatter、
  `.gitignore` 或 shared Git cache，不运行 cache clean。

## 10. `hook`

```text
doctidex-git hook (--install | --run) [--root ROOT] [--json]
```

- `--install` 与 `--run` 恰好提供一个；两者都不接受 dry-run/apply、source、selector、install filter、
  scope、cursor 或 pagination。
- `--install` 为 selected root 所在 Host Git Repository 的 `post-checkout` hook 建立 entrypoint。已有
  相同 managed entrypoint 返回 unchanged；已有不属于 doctidex-git 的 hook 返回 `hook_occupied` blocked，
  并保留该文件。命令不覆盖、迁移或组合用户 hook，不修改 Git config、index 或 manifest。
- `--run` 是安装脚本在 checkout 后调用的 root-scoped reconciliation entrypoint，也可由 human/program
  显式诊断性调用。它离线运行，不 fetch、不重新解析 moving branch/tag/default branch，也不创建、
  restore 或删除未安装 direct install。
- run 先处理 current manifest 中 physical payload 存在的 direct install：其 Git `HEAD` 必须变为
  `resolved_commit`，runtime 的 selector/default-branch provenance 尽力与 manifest 同步。commit 或
  metadata 无法安全对齐时保留该 item、报告 field-level outcome，不能以 commit 相同冒充 complete。
- 然后从已完成 direct install 遍历 runtime dependency parent edges。parent content 是 doctidex root、
  有合法 manifest 且包含 child metadata 时，按同一 commit/provenance contract 处理 child 并递归；
  否则 child subtree 为 hidden。所有 existing hidden nodes 每次都重新判定，不能被忽略。
- hook run 可以移动 complete/hidden dependency payload 以更新其受管 visibility 与 runtime state，但不
  改写 portable manifest、durable symlink、Markdown/frontmatter、`.gitignore`、Git index 或 shared cache。
  dirty、damaged、object 缺失、manifest/runtime 损坏和 concurrent state change 保留现场并以 item finding
  返回；checkout 已完成，不因 hook warning 回滚。

## 11. `external link-parse`

```text
doctidex-git external link-parse PATH [--root ROOT] [--json]
```

- 离线、只读、单结果、无 pagination 或 dry-run/apply。
- PATH 可以是可读目录或 symlink 本身；broken symlink 按路径自身的文件系统事实识别，
  不要求 target 存在。命令不接受其他任意不存在路径，也不沿 broken symlink 猜测后续
  suffix。
- PATH 位于当前 owner root 的 install/link 时，解析最内层 current-owner mapping。PATH
  位于受管 install 的 doctidex content root 中且自身是 external symlink 时，还读取该
  content root 随 Git 版本化的 portable manifest/link mapping。
- 外层受管 presentation 的 owner root 始终是结果 `root` 和依赖安装位置；实际解释 repository
  suffix 的 installed repository root（或 mapping 指向的其中 doctidex root）单独返回为
  `content_root`，不能成为递归 install/restore 位置。
- 显式 `--root` 必须选择该 owner root；把 install 内 `content_root` 作为 `--root` 返回
  `root_mismatch` 和 owner root candidate，不在只读嵌套根建立新的受管 namespace。
- portable mapping 完整但 target 尚未在 owner root 安装时，返回正常
  `target_state: dependency_not_installed`、固定 source/selector/commit 和
  `dependency_parent_install_id`。这不是 mapping damage；agent 可以把这些字段交给可选的
  Maintenance 工作流。若决定安装，必须以 `source_url`、`--commit resolved_commit` 和
  `--dependency-of dependency_parent_install_id` 建立 exact dependency；原 branch/tag 只作
  provenance，不能在此重新解析。
- owner root 已有由当前 parent edge 指向、且 source 与 exact resolved commit 匹配的 dependency
  install 时，命令把 portable link 的 repository-relative base 映射到该 install，并返回外层
  可读 `working_path`。该 dependency install 使用 commit selector；portable branch/tag 仍只
  是原快照的 provenance。安装仓库内的原 symlink 保持不变，即使其物理 target 仍不存在。
- current-owner durable link 的 install path 缺失时返回 `owner_install_missing`，引导调用
  `external restore`；它与 installed-repository dependency 未展开是不同状态。
- 没有 current-owner 或 portable mapping 时返回 unmanaged ok。已识别 mapping 的 source、
  manifest/link 对应关系或 repository-relative path 损坏时保持 managed，并返回
  warning/blocked 与仍可证明字段。
- 不判断协议符合性、内容信任、写入授权或 remote 更新。

## 12. `worktree open`

```text
doctidex-git worktree open SOURCE [--root ROOT]
  (--commit COMMIT | --tag TAG | --branch BRANCH) [--json]
```

SOURCE 分类顺序：

1. 现有路径位于受管 presentation：`managed_path`；
2. 现有目录位于 Git working tree 内，或自身是 bare gitdir：对应 kind；working-tree subdirectory
   保留相对 Git top-level 的 suffix；
3. 现有文件是有效 gitdir pointer：`gitfile`；
4. 其他字符串是有效 Git URL：`url`；
5. 否则 `source_invalid`。

如果任务维护 selected root 的当前宿主 working tree，且基准 selector 等于当前 commit，
agent 可以直接使用当前路径；open 不是前置要求。需要隔离时仍可显式调用。

open 解析显式 selector，在 selected root 的 `/.doctidex` 下创建一个新 detached managed
worktree。managed path 保留请求目录相对 repository 的 suffix；其他 source suffix 为 `.`。
即使 SOURCE 位于 install 或 worktree，结果也与它们扁平并列，不递归创建。payload 被宿主
Git ignore，但不进入 external 恢复清单。URL 在 objects 不足时可联网；其他 kind 离线。
open 没有 dry-run/apply，不 checkout 用户 branch、不 commit/push/merge。
相同 source/base commit 的候选不会阻止创建，只令成功 result 为 warning。

## 13. `worktree list`

```text
doctidex-git worktree list [--root ROOT]
  [--source SOURCE | --worktree WORKTREE]
  [--limit N] [--cursor TOKEN] [--json]
```

离线、只读。显式 `--root` 或 cwd 选择 owner root；两个 filter 互斥，无 filter 列出该 root
第一页。`--source` 使用 open 的同一分类和
canonical identity，`--worktree` 要求 exact managed path。无匹配返回空 ok collection。
列表只给 clean/changed/unavailable 概要；具体 diff 使用原生 Git。

## 14. `worktree close`

```text
doctidex-git worktree close WORKTREE [--json]
```

close 是显式 destructive lifecycle action，但只允许移除可证明归属且 Git-clean 的受管
worktree。changed、unavailable、路径不 exact、归属不明或 Git 检查失败均 blocked 并保留。
它不回收 shared objects、不影响 presentation，也不处理手工 worktree。

## 15. `cache clean`

```text
doctidex-git cache clean (--url URL | --auto) [--dry-run | --apply] [--json]
```

- `--url URL` 与 `--auto` 恰好提供一个。URL mode 采用 `external install` 相同的 repository
  locator、credential sanitization 与 canonical source identity 规则；结果公开 sanitized URL 和
  opaque cache source ID。`--auto` 没有调用者 URL，扫描本机 doctidex-git source-cache namespace，
  只公开 opaque cache source ID。
- 命令不接受 `--root`、scope、filter、limit 或 cursor；cwd 不影响结果。URL mode 是单结果，
  auto mode 返回调用开始时已发现 candidate 的稳定 source-ID 顺序；两种模式顶层 `root` 和
  `collection` 固定为 null。
- 命令离线、默认 dry-run。每个 candidate 在自身 source mutation boundary 中读取 Git worktree
  metadata；apply 在删除前重新分类，不能依赖先前 dry-run 或另一个 candidate 的计数。
- 任一 Git-valid linked worktree 都保留整个 bare source cache，不考虑 clean/dirty、
  doctidex ownership 或 runtime record。只有 valid count 为零且其余 linked registrations全由 Git
  判为 prunable 时，dry-run 才报告 planned，apply 才删除该 bare cache。
- URL mode 的 missing cache、damaged metadata、无法分类 registration 或复查冲突返回 top-level
  blocked。Auto mode 把同类 candidate failure 作为 item-level `blocked` 并继续其他 source；
  valid worktree 为 item-level `preserved`。auto mode 的顶层 status 在任一 preserved 或 blocked
  item 存在时为 warning，但请求仍完成且不因这些 item 使用退出码 2。
- 自动扫描不是全局 transaction 或持续 watcher。未识别 namespace entry、扫描外/后新增的 cache 和
  cache root 外 repository 不在本次删除范围；并发移除后才取得 source lock 的 candidate 作为 blocked
  item 保留。调用方可在审阅结果后再次显式运行命令。
- 删除范围只有每个 eligible bare source cache。命令不删除或修改 linked worktree filesystem path、
  install/worktree payload、恢复清单、runtime record、其他非 candidate source cache，也不由 close、
  restore 或其他 operation 隐式触发。
- 内部 cache path 不进入 human/JSON 输出；即使 apply 成功，公共 `changed` 也为空。后续
  install/restore/worktree open 如缺 objects，仍按各自网络契约重新取得。

## 16. 读写与网络矩阵

| 命令 | 根/公开文件 | 持久 Git/state | Network |
|---|---|---|---|
| validate | 只读 | 无 | 从不使用 |
| install dry-run | 无 | 无；只允许可丢弃的调用期状态 | 可能使用 |
| install apply | 写入 index、`.gitignore`、恢复清单、install path | objects + install record | 可能使用 |
| link dry-run | 无 | 无 | 从不使用 |
| link apply | 写入 index、symlink、恢复清单 | link mapping | 从不使用 |
| restore dry-run | 无 | 只读清单；只允许可丢弃的调用期状态 | 可能使用 |
| restore apply | 重建 install path | objects + install state | 对象不足时可能使用 |
| remove dry-run | 无 | 只读 owner/tree/managed state | 从不使用 |
| remove apply | 移除 exact install payload | 移除 per-install runtime/manifest record | 从不使用 |
| link-parse | 只读 | 只读 | 从不使用 |
| worktree open | 新建受管 worktree | objects + record | URL source 可能使用 |
| worktree list | 无 | 只读 | 从不使用 |
| worktree close | 移除 clean 受管 worktree | 移除 record | 从不使用 |
| cache clean dry-run | 无 | 只读单个 bare source cache 的 Git metadata | 从不使用 |
| cache clean apply | 无 root-owned 变化 | 仅删除满足条件的单个 bare source cache | 从不使用 |
