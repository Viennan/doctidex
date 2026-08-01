# doctidex-git 0.1.0 CLI 用户接口

本篇描述 `doctidex-git` 0.1.0 当前接受的命令和副作用。返回字段的逐字段说明见
[CLI 结果契约](cli-schema.md)。Python 参考实现如何完成参数分发和渲染见
[CLI 与 rendering](../../impls/python/cli-and-rendering.md)。

## 1. 命令总览

```text
doctidex-git context [PATH]
doctidex-git inspect [PATH]
doctidex-git resolve INTERNAL_PATH [--from LINK_DOCUMENT]
doctidex-git init [PATH] [--dry-run | --apply]

doctidex-git mount list
doctidex-git mount add --url URL (--commit SHA | --tag TAG | --branch BRANCH) \
  --mount-path INTERNAL_PATH [--dry-run | --apply]
doctidex-git mount remove MOUNT_PATH [--dry-run | --apply]
doctidex-git mount prepare [MOUNT_PATH]
doctidex-git mount sync [MOUNT_PATH] [--dry-run | --apply]

doctidex-git maintenance scope [PATH ...]
doctidex-git maintenance open MOUNT_PATH
doctidex-git maintenance status [MAINTENANCE_ROOT]
doctidex-git maintenance handoff [MAINTENANCE_ROOT]
doctidex-git maintenance close [MAINTENANCE_ROOT]

doctidex-git check [PATH] [--online]
doctidex-git changes [PATH]
```

## 2. 全局选项

以下全局选项可以出现在子命令之前或之后：

| 选项 | 默认值 | 当前行为 |
|---|---:|---|
| `--json` | false | 输出 indent 2、Unicode 不转义、key 排序的 JSON。否则输出人读 key/value。 |
| `--limit N` | 100 | 每个列表最多返回 N 项；最小 1，最大 1000。该限制分别作用于每个列表，不是整个 payload 的总项目数。 |
| `--cursor TOKEN` | 无 | 继续读取上一结果给出的下一页；必须原样使用 `next_cursor`，不能自行构造。当前同一页位置会作用于结果中的每个顶层列表。 |
| `--depth N` | 4 | 解析并限制到 0..32，但当前版本没有将其用于遍历或输出裁剪，因此目前没有可观察效果。 |

全局选项可以放在子命令之前或之后，例如以下两种形式等价：

```bash
doctidex-git --json mount list
doctidex-git mount list --json
```

无效 `--cursor` 会成为结构化 `cursor_invalid` blocked 结果。`--limit`/`--depth` 的非整数
值属于命令行语法错误，不保证产生 JSON 结果。

## 3. 根与路径选择

命令对 `PATH` 的解释不是完全一致的：

| 命令 | 用于选择 doctidex 根的路径 | 实际操作目标 |
|---|---|---|
| `context [PATH]` | PATH，默认 cwd | 同一 PATH。 |
| `init [PATH]` | 自己决定已有根或新根 | 选择出的 root。 |
| `inspect [PATH]` | cwd 已选出且包含 PATH 时保留 cwd 宿主；否则由 PATH 选择。PATH 默认 cwd。 | PATH。 |
| `resolve INTERNAL_PATH` | 默认 cwd；有 `--from` 时结合 cwd 和 LINK_DOCUMENT。 | INTERNAL_PATH 相对于实际 link root。 |
| 所有 `mount` | cwd | 所选宿主根。 |
| `maintenance scope/open` | cwd | scope 的 PATH 只用于 scope 分类，不改变宿主根选择；open 作用于当前宿主声明。 |
| `maintenance status/handoff/close` | 显式 MAINTENANCE_ROOT 对应的宿主；省略时为 cwd | 一个已登记维护根，或当前宿主的登记集合。 |
| `check [PATH]` | PATH，默认 cwd | 所选根整棵目录树。 |
| `changes [PATH]` | PATH，默认所选根 | 对 PATH 执行 Git status，但结果中的 `root` 仍是所选 doctidex 根。 |

除 `context` 和 `init` 外，命令通常通过 `require_root` 要求唯一根。路径恰好是一个根
目录时优先选择该根；路径位于嵌套根之间且没有精确指定时返回 `root_ambiguous`。

cwd 是默认命令上下文，而不是通用访问限制。命令没有统一 `--root` 参数。短暂从
宿主检查 mount 文件时，`inspect PATH` 会保留宿主上下文；解释该文件中的内部 link
时可使用 `resolve --from LINK_DOCUMENT`。集中在一个根内的连续操作可以先进入精确根，
从而简化后续参数。显式 MAINTENANCE_ROOT 是 `maintenance open` 的返回值，可从其他
cwd 继续传给 status/handoff/close。

## 4. 写模式

`init`、`mount add`、`mount remove`、`mount sync` 接受互斥的 `--dry-run`/`--apply`。
- 有 `--apply` 才进行公开写操作；
- `--dry-run` 和两个 flag 都不写的行为相同；
- CLI 不要求必须显式给出其中一个。

不能根据命令名推断是否联网。尤其 `mount sync --dry-run` 为获得 new commit，可能
访问远端；它只是不会切换当前可读快照。

## 5. `context`

```bash
doctidex-git context [PATH] [--json]
```

用途：发现 PATH 所在 Git 工作目录和 doctidex root，不要求已有根。

无根时返回 `status: warning`、可选 Git 工作目录、`root: null` 和 init 下一步，退出码
仍为 0。找到一个根时返回根、根 index 和 mode。

`mode` 当前通过 PATH 字符串是否包含 `/.doctidex/mounts/` 判断：

- `host_read`：没有该片段；
- `mount_read`：含该片段。

该判断不检查 mount 声明，且 namespace 目录本身没有结尾 `/` 时仍是 `host_read`。

副作用：无文件写入，无网络访问。

## 6. `init`

```bash
doctidex-git init [PATH] [--dry-run | --apply] [--json]
```

用途：在 Git working tree 内创建或接管一个 doctidex 根。

根选择：如果 requested PATH 向上只发现一个已有 doctidex 根，使用该根；没有时以
requested 目录为新根；发现多个时 blocked。目标必须处于 Git 工作目录。

计划内容：

- 新建或修正根 `index.md` 的 `type: index`、`doctidex.type: index`、
  `doctidex.root: true`；
- 确保 `excludes` 是列表并包含 `.doctidex/mounts`；
- 仅当 `<root>/.git` 存在时再加入 `.git` exclude；
- 确保根 `.gitignore` 有精确行 `/.doctidex/mounts/`；
- 把根当前直接子项列为语义候选，跳过 `index.md`、`.git`、`.doctidex`。

注意：existing `doctidex.excludes` 不是列表时，当前行为会替换为新列表，而不是保留
原非法值。apply 会写整个 frontmatter 和 `.gitignore`；不会生成 index 正文、commit
或访问网络。

## 7. `inspect`

```bash
doctidex-git inspect [PATH] [--json]
```

用途：解释一个文件系统路径相对于宿主 doctidex 根的范围和导航信息。

若 cwd 已经唯一选中一个 doctidex 根且 PATH 位于该根下，命令保留这个根作为宿主
上下文。这使宿主 cwd 下对 mount 文件的 inspect 同时返回宿主 `path_context` 和源
`source_context`。PATH 位于当前根之外，或 cwd 不在根中时，改由 PATH 选择根。嵌套
根仍可能要求把 cwd 或 PATH 明确到精确根。

始终返回 `path_context`。本地 included 路径有负责 index 时，还返回该 index 的
CommonMark `links`。mount 路径额外返回对应 mount 状态；若 mount 已可读，再从 source
root 角度返回 `source_context`。

`semantic_candidates` 只保留 `index` 字段恰好等于当前 `responsible_index` 的候选。
excluded/mount 路径没有负责 index，因此通常为空。

副作用：无写入、无网络。它会遍历并校验宿主目录树来生成候选，目录很大时成本可能
高于单纯路径判断。

## 8. `resolve`

```bash
doctidex-git resolve INTERNAL_PATH [--from LINK_DOCUMENT] [--json]
```

用途：规范化 `/` 开头的 doctidex 内部路径，并给出原生文件工具可使用的
`working_path`。

不传 `--from` 时，cwd 选择的根同时是命令 root 和 link root。`--from` 接受包含该
link 的现有可读文件系统文件；相对值相对于 cwd。它不接受目录、不读取目标文件，也
不验证 INTERNAL_PATH 是否真的出现在该文档中。该参数只提供 link 来源上下文：

- LINK_DOCUMENT 是宿主本地文档时，普通 `/...` 以宿主根解析；
- LINK_DOCUMENT 位于已准备 mount 时，普通 `/...` 以该挂载源根解析，working path
  仍通过宿主可访问 mount path 表达；
- 同一挂载文档中的 `/.doctidex/mounts/...` 按不可嵌套规则回到原宿主 namespace；
- 普通嵌套 doctidex 根不能仅凭文件位置静默选择；cwd 未精确选择时返回
  `root_ambiguous`。

INTERNAL_PATH 只接受 link 的路径部分，不包含 anchor。调用方已经知道普通同根 link
的 link root 时，可以直接按规则推导文件系统路径，无需为每个 link 调用 resolve。

返回输入、可选 link document、规范化路径、命令 root、实际 link root 及其种类、
文件系统路径、是否跨 mount 和完整 mount 状态。涉及 mount 时还返回
`root_relation` 与 `maintenance_reuse`：前者只在可可靠确认时标明当前根自引用及 commit
是否相同；后者说明后续写入是否可复用 host 或已开放 maintenance scope。两者都不改变
`working_path`，自引用读取仍位于 `/.doctidex/mounts/...`。mount 未准备时命令本身仍
`status: ok`，通过 `result` 和 mount 的 `next_action` 提示 prepare；resolve 不自动
恢复 mount。

副作用：无写入、无网络。

## 9. `mount list`

```bash
doctidex-git mount list [--json]
```

用途：列出根 index 中所有 `type: git` 声明及其本地有效状态。

每项包含 mount path、清理后的 source URL、声明 selector、有效 commit、state、
readable 和下一步。list 不访问远端；`ready` 只表示已有有效 commit 且逻辑路径当前
存在，不表示 branch/tag 与远端最新值相同。

副作用：无写入、无网络。

## 10. `mount add`

```bash
doctidex-git mount add --url URL \
  (--commit SHA | --tag TAG | --branch BRANCH) \
  --mount-path /.doctidex/mounts/NAME \
  [--dry-run | --apply] [--json]
```

用途：在根 index 声明完整 Git doctidex source。

前置条件：mount path 规范化且不重叠；URL 合法；根 `.gitignore` 直接覆盖 namespace；
namespace 下没有 tracked 内容。apply 只修改根 index，返回 `mount_state: not_prepared`。

副作用：dry-run 无写入；apply 写根 `index.md`。两者都不访问网络、不解析 selector、
不创建可读路径。

## 11. `mount remove`

```bash
doctidex-git mount remove MOUNT_PATH [--dry-run | --apply] [--json]
```

用途：删除一个精确 Git mount 声明。

命令先扫描宿主 Markdown 中可解析的 link。仍有引用时返回
`mount_still_referenced`。dry-run 只说明是否可移除；apply 修改根 index，并移除该声明
当前受管理的可读路径和有效选择记录。

副作用：不访问网络。apply 不承诺回收可被其他 mount 复用的本地 Git 数据。

## 12. `mount prepare`

```bash
doctidex-git mount prepare [MOUNT_PATH] [--json]
```

用途：把 lazy mount 恢复为原生文件工具可读路径。

指定路径时只处理该 mount；省略时处理所有 Git mounts。只有一个目标时直接返回单项
schema；零个或多个目标时返回 batch schema。

已有 effective commit 且所需 Git 数据在本地时可完全离线。首次准备或本地数据不足时
可能访问 source。成功会建立宿主 mount 的可读路径并保存有效选择，但不修改 tracked
文件、根 index 或 Git index。

## 13. `mount sync`

```bash
doctidex-git mount sync [MOUNT_PATH] [--dry-run | --apply] [--json]
```

用途：显式检查 selector 当前解析到的 commit，并可切换有效读取结果。

不指定路径时顺序处理所有 Git mounts。branch/tag 通常 fetch；commit 在已有 effective
commit 时不重新解析。dry-run 返回 old/new commit 和布尔 `changed`，但不切换当前
可读快照。apply 在 commit 不同时切换该 mount；其他指向旧 commit 的 mount 不变。

注意：该命令的 `changed` 是“commit 是否不同”的布尔值，不是其他命令常用的路径
数组。单 mount 结果与 batch 结果 shape 也不同。

## 14. `maintenance scope`

```bash
doctidex-git maintenance scope [PATH ...] [--json]
```

用途：观察本次输入路径所属的宿主根和挂载源，并给出同 revision scope 复用事实。

没有 PATH 时使用宿主根。每个 mount 和宿主根各只返回一次。mounted source 返回
只读路径、declared revision、base commit、`target_branch`、`root_relation` 与
`maintenance_reuse`；host root 返回直接可写路径、当前 HEAD、当前 branch 提示和指向
自身的复用建议。同一 `source`、相同 `base_commit` 的 items 是合并候选，最终是否兼容
仍由 agent 根据写入权限和交付目标决定。

一个 item 只表示该次调用观察到的对象，不表示它尚未或已经分配到写入范围。
scope 不记录 agent 的计划；当新路径进入任务、已有 maintenance root 变化或需要复核边界时，
可以再次运行它。每次结果都是当时的客观事实，由 agent 自己制定或调整最终写入范围。

`maintenance_reuse.status: recommended` 时，`write_action` 为 null，直接使用返回的
`write_path`；`selection_required` 时先运行 status 选择已有维护根；`not_available` 时
`write_action` 才是 open 命令。自引用 source 与当前 HEAD 相同时优先复用 host root。
比较 scope item 的 `target_branch` 与 `maintenance_reuse.target_branch`：两者都已知且
不同时 CLI 不会推荐该根；任一侧为 null 时仍需结合用户交付意图判断。选择已有根时以
scope item 的 `source/base_commit` 对齐 status item，并比较 status item 的
`target_branch`；无法唯一决定时请求用户选择。`delivery_target_conflict` 默认要求保持
独立；用户明确选择共同集成结果时，自引用可重新 scope `.` 取得 host write path，开放根
可运行 status 并按 source/base commit 查找，再选择有授权且符合共同交付意图的根。将具体 mounted
文件映射到写入根时，从目标路径移除 `read_only_path` 前缀并把其 source-relative suffix
接到所选写入根，不能从前缀下表达的目标不得猜测映射。选定写入根后，该根就是
本次执行边界；通过其 mount 发现的其他源目标必须重新进入 scope 决策。

副作用：无写入、无网络。输入 PATH 不改变 cwd 所选择的宿主根。

## 15. `maintenance open`

```bash
doctidex-git maintenance open MOUNT_PATH [--json]
```

用途：从 mount 有效 commit 创建独立可写维护根。

mount 尚无 effective commit 时返回 `maintenance_source_not_prepared` 和 prepare 命令。
成功返回 `maintenance_root`、base commit、可写边界、目标 branch 提示、
`root_relation` 和调用前的 `maintenance_reuse`。open 是显式隔离动作：即使调用前已有
兼容 scope，它仍创建新根，但返回 `status: warning` 和先合并 scope 的提示；调用者应
确认隔离是有意的，并关闭未使用的 clean 现场。

副作用：创建并登记 maintenance root；不访问远端，不切换调用者 cwd，不改变宿主
mount。

## 16. `maintenance status`

```bash
doctidex-git maintenance status [MAINTENANCE_ROOT] [--json]
```

用途：列出当前开放的 maintenance contexts 及 Git changes。

不传路径时列出全部；传入时按绝对路径过滤。没有匹配也返回 ok/空 items，而不是
blocked。每项 state 为 `ready` 或 `has_changes`。显式路径会查找登记该路径的宿主，
因此不要求 cwd 留在最初宿主；省略路径时仍从 cwd 选择宿主。

副作用：无写入、无网络。

## 17. `maintenance handoff`

```bash
doctidex-git maintenance handoff [MAINTENANCE_ROOT] [--json]
```

用途：为一个维护根产生交付前事实。

省略路径只在当前恰好登记一个 maintenance context 时成立；否则
`maintenance_root_ambiguous`。命令返回 Git changes、协议结构、语义候选、插件就绪
状态和用户 Git 动作提示。显式传入 open 返回的精确路径时，可从任意 cwd 找到其宿主。

副作用：无写入、无网络；不会 commit/push/merge。

## 18. `maintenance close`

```bash
doctidex-git maintenance close [MAINTENANCE_ROOT] [--json]
```

用途：移除一个已经 clean 的 maintenance root。

有任何 porcelain change 时返回 `maintenance_has_changes`，保留路径并要求先 handoff
和决定 Git 动作。clean 时关闭并移除该维护现场。显式维护根与 handoff 使用
相同的跨 cwd 选择规则；省略时使用当前宿主且必须恰好选中一个登记。

副作用：只关闭已登记且 Git 状态 clean 的 maintenance context；无网络。

## 19. `check`

```bash
doctidex-git check [PATH] [--online] [--json]
```

用途：把协议结构、语义候选和插件就绪状态分开检查。

默认离线。`--online` 对每个 Git mount 使用 refresh 解析 selector，返回当前 effective
commit、remote commit 和 update_available。online check 不切换可读快照或
effective commit，但会访问 source 并刷新本地 Git 信息。

check 还读取宿主 Git changes，为非 `index.md`/`log.md` change 添加
`git_change_review` 候选。任何语义候选、协议 fail 或插件 blocked 都令顶层 status 为
`warning`；只有 `protocol_structure: fail` 令进程退出码为 1。插件 blocked 本身当前
仍退出 0。

## 20. `changes`

```bash
doctidex-git changes [PATH] [--json]
```

用途：返回 `git status --porcelain=v1 -z` 的结构化列表。

每项有两字符 `status` 和 `path`；rename/copy 另有 `original_path`。第一个状态字符表示
index/staged 状态，第二个表示 worktree 状态；`??` 表示 untracked。CLI 不加入 diff
内容，也不判断变更是否合理。

副作用：无写入、无网络。

## 21. 参数与异常边界

未知命令、缺少必需参数、互斥 selector 冲突等命令行语法错误通常退出 2 并写
stderr，不保证 `--json`。命令开始执行后的预期问题使用统一 blocked schema。执行期间
Ctrl-C 返回 `interrupted` 和退出 130；未预期异常返回 `unexpected_failure`、
诊断 ID 和退出 2。
