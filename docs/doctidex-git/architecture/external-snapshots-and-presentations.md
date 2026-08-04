# 外部快照、呈现与 checkout 接手

本页拥有 Git external snapshot、durable presentation、manifest/runtime、host integration 和
checkout hook 的共同语义。它定义一个已有 owner root 如何被另一 variant 正确解释和接手；
Python 的 JSON bytes、source canonicalization、file mode、Git invocation、write order 和 hook
script quoting 仍由 Python Impls 说明。

## 1. 用户问题与共同生命周期

external workflow 把一个 Git source 的固定 commit 变成 owner root 内逻辑只读、可恢复的内容，再由
用户选择 root 内可追踪的 presentation symlink。它处理已安装 snapshot 的 restore、path mapping、
reference-protected remove 和 checkout 后的离线 reconciliation；不替代 native Git、自动跟随 moving ref
或递归 checkout。

| 概念 | identity / allowed state | user-visible effect |
|---|---|---|
| Install | owner root + opaque Install ID；role `direct` 或 `dependency`。 | 一个固定 source/commit 的 managed payload；direct 可恢复，dependency 只表达 outer parent relation。 |
| Revision request | `{kind: commit|tag|branch, value}` + fixed `resolved_commit`。 | selector 是请求/provenance；commit 才是读取/恢复的 exact snapshot。 |
| Payload | `complete`、`missing`、`damaged`；dependency 还可为 `hidden`。 | complete 可读；missing direct 可 restore；damaged/hidden 保留而不猜测或覆盖。 |
| Durable link | root 内 target + Install ID + repository-relative path。 | user-selected relative symlink；link/manifest 可由 host Git track。 |
| Recovery manifest | direct installs + durable links 的 portable record。 | clone/clean 后按 exact commit/path 恢复，不重写 link。 |
| Runtime record | host-local install/link/worktree record。 | 支撑当前 owner mapping、dependency edges、hidden state 与 maintenance ownership。 |
| Hook registration | owner root + host Git repository + `post-checkout` trigger。 | checkout 后对已存在 managed snapshot 做离线 reconciliation。 |
| InstallReference | selected owner root + one current runtime install record 的只读查询视图。 | 让 human/agent 以可读 source repository path、host、fixed revision、role、state 和 recorded presentation 查找、比较及消歧，不把 opaque Install ID 当作对话名称。 |

不同 fixed selector 一般是不同 install identity；省略 selector 的 default provenance 只参与相同
intent 的 lookup，不授权以后刷新 branch/tag。dependency install 不在 install 内递归 materialize；
它仅增加一个去重 parent edge。普通 install 可将同 identity 的 dependency 提升为 direct，不能降级。

## 2. 主机归属与受管命名空间

owner root 下的 managed namespace 为 `/.doctidex/git/`。它不是 protocol configuration；它是产品工作
现场，故其已经存在的文件必须可由本页解释。

| 位置 / host artifact | owner 与 trackability | variant 接手规则 |
|---|---|---|
| `/.doctidex/git/manifest.json` | versioned、host Git 必须可 track。 | 作为 portable recovery contract 读写或安全转换。 |
| `/.doctidex/git/runtime.json` | host-local，host Git 必须忽略。 | 解释 current mapping/state；无法转换时保留并报告。 |
| `/.doctidex/git/installs/<id>/`、`.hidden/<id>/` | managed payload，host Git 忽略。 | 按 record 身份、role/state 使用、restore 或 preserve。 |
| `/.doctidex/git/worktrees/<id>/` | managed writable artifact，host Git 忽略。 | 按 worktree record 判断 clean/changed/unavailable，不能无条件删除。 |
| root mutation lock / temporary publication evidence | managed transient state，host Git 忽略。 | 见 [操作安全](operation-safety-and-recovery.md#4-诊断锁与临时产物)。 |
| host `.gitignore` | host configuration，不等于 owner-root config。 | 忽略上述 private namespace classes，但不得忽略 manifest 或 durable symlink；其它用户条目保持原样。 |

install、restore、link、worktree 和 hook 只能在 selected owner root/host relationship 已证明时改变这些
state。一个 incoming variant 可以采用不同 own namespace，却必须先读或安全迁移该 v1 namespace；
它不得通过删除 `runtime.json`、payload 或 ignore entry 来伪造接手成功。

## 3. 可移植恢复清单

`/.doctidex/git/manifest.json` 是跨 clone/clean、跨 host 以及跨 variant 都必须可解释的 portable
configuration。schema `1.0` 的 top-level fields 是：

| Option | meaning / constraint | effect |
|---|---|---|
| `schema_version` | string，当前为 `1.0`。 | unknown version 不可猜测；保留并 blocked/migrate。 |
| `installs` | object，key 是 non-empty opaque Install ID，value 是 PortableInstall。 | 只记录 `direct` install；是 restore 的 complete inventory。 |
| `links` | object，key 是 normalized root-relative POSIX target path，value 是 PortableLink。 | 把 durable presentation 绑定到 install，供 restore/link-parse/remove 保护。 |

每个 PortableInstall 的 key 和 `install_id` 必须相同：

| Option | meaning / allowed value | effect / handoff rule |
|---|---|---|
| `install_id` | opaque stable ID。 | 不从其值推断 source；link 与 runtime 用它引用同一 logical install。 |
| `install_path` | `/.doctidex/git/installs/<install_id>`。 | direct payload 的 normal location；不同 layout 的 variant 必须映射或保留。 |
| `source_url` | non-empty sanitized public locator，不含 credential。 | source recovery input；local locator 的环境可用性可能 blocked，不是授权重写。 |
| `source_relation` | `host_repository`、`other` 或 `unknown` 的原安装 provenance。 | 解释 source 与当时 host 的关系；不表示当前 host permission/trust。 |
| `revision_selector` | object `{kind: commit|tag|branch, value: non-empty string}`。 | 记录请求/provenance；不得取代 exact commit。 |
| `default_branch` | string 或 `null`。 | 只记录 omitted-selector 当时观察的 default provenance；不用于 refresh。 |
| `resolved_commit` | 40 或 64 lowercase hexadecimal commit ID。 | restore、payload verification 和 handoff 的 hard revision fact。 |

每个 PortableLink 的 object key 和 `target_path` 必须相同：

| Option | meaning / allowed value | effect / handoff rule |
|---|---|---|
| `target_path` | non-empty normalized root-relative POSIX path。 | user-selected presentation location；不能与 managed payload overlap。 |
| `install_id` | 同 `installs` 内的 direct install ID。 | 决定 link source、remove reference protection 和 restore relation。 |
| `repository_relative_path` | `.` 或 normalized source-repository relative POSIX path。 | 从 payload 得到 symlink source 与 link-parse suffix。 |
| `safe_state` | `safe` 或 `unsafe`。 | 决定 responsible index 的 protocol declaration；不表示 trust/permission。 |
| `responsible_index` | normalized root-relative `index.md` path。 | 说明哪个 index 负责 presentation 的 boundary/unsafe state。 |
| `frontmatter_ownership` | 可选 object；新建记录包含 `boundary_set` 与 `unsafe` 的受管/保留事实。 | `unlink` 据此只撤回本 link 引入的 declaration，或恢复 link 曾临时移除的原有 `unsafe` entry；缺失代表旧记录，解绑时保守保留配置。 |

Duplicate key、invalid required field、unresolvable install reference 或 unknown schema version 使 manifest
不能作为自动 restore input。未知 additional field 可以保留，但不能改变 required semantics。logical
manifest identity 必须随 semantic content 改变，以支持 cursor/concurrent detection；canonical JSON order、
hash 和 encoding 不属于 Architecture。

Restore 只从 manifest 重建 missing **direct** payload 的 exact path/commit，保持 manifest 和 existing
presentation 不变；它不 materialize dependency-only node、follow moving ref、覆盖 damaged payload 或清理
shared cache。

## 4. 运行时安装与链接记录

`/.doctidex/git/runtime.json` 是 v1 owner-local configuration。它让当前工作现场的 install/link/worktree
状态可由另一 variant 解释，即使该 variant 选择转换到不同 local storage。top-level `schema_version`
仍为 `1.0`；`installs`、`links`、`worktrees` 都是 object。`worktrees` 的 fields 由
[工作树权威页面](worktrees-and-cache.md#2-运行时工作树记录) 定义。

Runtime Install 包含 PortableInstall 的所有 fields，另外包含：

| Option | meaning / allowed value | effect / incoming rule |
|---|---|---|
| `canonical_source` | non-empty variant-normalized source equality identity。 | 用于 same-source lookup/lock scope；其它 variant 可重新计算或映射，不能把它当公开 URL。 |
| `requested_default` | boolean。 | true 表示调用者省略 revision；影响 idempotent lookup/provenance，而不是 resolved commit。 |
| `role` | `direct` 或 `dependency`。 | direct 应出现在 manifest；dependency 只保留 outer parent relation，除 promotion 外不进入 manifest。 |
| `parents` | unique non-empty Install ID array。 | dependency 的 explicit outer parents；用于 forest/hide/remove protection，不能凭 payload directory 推断。 |
| `managed_state` | `complete`；或仅 dependency 可为 `hidden`。 | hidden payload 不作为 normal mapping/presentation source，必须保留到 hook 重判。 |

Runtime Link 使用与 PortableLink 相同的 `target_path`、`install_id`、`repository_relative_path`、
`safe_state`、`responsible_index` 和可选的 `frontmatter_ownership`。它是 current owner mapping；manifest link 是 portable recovery
mapping。两者已知不一致、target/symlink identity 不能证明或 record 无法验证时是 `mapping_damaged`，
不是自动修复或删除的理由。

当前 `schema_version: 1.0` 读者必须逐项解释上述 option。无法安全读取当前 runtime 的 variant 可以
保留该文件、从 manifest 处理 portable direct state，并对需要 current mapping/hidden/worktree 的操作
返回 blocked/migration diagnostic；不能以空 runtime 覆盖它。

### 4.1 Managed install reference 与只读发现

`InstallReference` 是 `external list` 在一个 selected owner root 内对 current runtime install record 形成的
瞬时公开视图，不是 manifest/runtime 新字段、install 的第二 identity 或可变 alias。其精确 target 始终是
`(owner root, install_id)`；可读字段只用于人和 agent 在对话中重新发现或比较该 target，不能跨 root 复用，也
不能令 fixed snapshot 跟随 branch/tag。

每个 reference 至少公开 sanitized `source_url`、由 source 可读呈现得到的 `repository_path`、可为 null 的
`source_host`、`revision_selector`、`resolved_commit`、`install_role`、`managed_state`、opaque `install_id`，以及
该 owner root 当前 runtime link record 中关联此 ID 的 root-relative `presentation_paths`。`repository_path` 是
source repository 的路径线索，例如 `git@github.com:Viennan/wiki.git` 的 `Viennan/wiki`；它不是完整 URL、
credential、payload path 或跨 host 的全局名。不同 host 的相同 repository path 必须保持为不同 reference 候选。
没有 host 的 local source 公开 null `source_host`；没有 durable presentation 的 `presentation_paths` 为空。

`external list` 只读取该 owner root 的 current managed install/link records，包含 direct、complete dependency 和
hidden dependency；它不枚举 filesystem 中普通 repository、remote source、未展开的 portable dependency 或其它
owner root。它不验证、restore、install、删除或刷新 payload，也不把 recorded presentation path 当成已被 native
filesystem 读取成功的保证。agent 以完整实际 path 解释 external link 时，仍按需调用 `link-parse`；不完整 path 的
context-first 补全是 agent responsibility，不是本命令或 runtime 的搜索行为。

查询的 repository path、host、revision 和 role filters 只在已记录 facts 上比较：tag/branch 只匹配 selector
provenance，commit 只匹配 fixed resolved commit，绝不访问 network 或重新解析 moving ref。空集和多项都是成功的
读结果；只有 agent 能结合用户上下文选择唯一项。运行时 schema/record 无法安全读取时 operation 返回 existing
diagnostic/blocked result，不伪造部分 reference。

## 5. 安装载荷、隐藏状态与持久呈现

`complete` payload 位于 normal `installs/<id>/`，表示 record、exact Git HEAD、resolved commit 与
source/revision provenance 足以相互证明。它是 logical read-only content：用户可以原生读取，维护写入
应选择 current repository 或 explicitly opened worktree。permission hardening、Git worktree mechanics
和 exact layout 由 Impls 说明。

| 状态 / artifact | producer / consumer | 使用、恢复与交接 |
|---|---|---|
| complete direct payload | install/restore；link/read/hook 消费。 | 可作为 durable link source；missing 时 manifest exact restore。 |
| complete dependency payload | dependency install；outer mapping/hook 消费。 | 不进入 manifest；可读但不得递归 materialize 或直接成为 durable link source。 |
| missing direct payload | clean/clone/physical loss；restore/link-parse 观察。 | existing link 保持；返回 `owner_install_missing`，只 restore exact manifest entry。 |
| damaged payload | identity/path/record 无法证明。 | 完整保留并诊断；不得用 restore 覆盖。 |
| hidden dependency payload | hook 不能从 aligned direct ancestor 证明 child revision metadata。 | 移出 normal mapping namespace，保留 parent/Git evidence；每次 hook 重判，只有可证明时 unhide。 |
| durable symlink | link apply 产生；human/agent/native tool 消费。 | target 由用户选择、source 由 mapping 证明；broken 时 `link-parse` 区分 missing direct、uninstalled dependency、damage 或 unmanaged。 |

Link apply 只有在 source 属于 complete direct install、target 空闲且不 overlap managed payload、host Git
能 track link/manifest、symlink capability 可用时才可进行。`safe_state: safe` 还要求 source directory 是
selected root 且 full validation structural pass/scan complete；否则为 `unsafe` 并维护对应 protocol entry。

一个 durable link 以 root-relative `target_path` 为 presentation identity；它不是 install 的可变别名。
install 仍是固定 source/commit snapshot。用户或 agent 想引用新版本时，先建立和审阅新的 direct install，
再在相同 target 上使用 `external rebind SOURCE_DIRECTORY TARGET_PATH`。rebind 只接受一个已经完整、可证明的
direct durable link：runtime、manifest、旧 symlink、payload 和负责 index declaration 必须相互一致；新 source
也必须按 link 的 direct-source 规则可证明。它把 target 的 mapping 改为新 install/repository-relative path，
保持 target spelling 不变，因此兼容目录结构中的既有 Markdown link 不需要改写。它不判断内容语义或目录结构
兼容性，也不改写 Markdown、navigation prose、annotation、Git index 或旧 install。

rebind 的 dry-run 给出 old/new fixed snapshot、index configuration 和计划效果；apply 在 root mutation boundary
内重新验证上述事实。实现必须先准备新的 sibling symlink，再以单次 publication 替换 live target，不能先删除
旧 symlink 形成可观察的 temporary broken presentation。manifest/runtime 或 index publication 不是跨文件 transaction：
interruption 仍须保留可诊断的实际文件和旧/新可读 target，下一次操作不得猜测或覆盖不一致 mapping。
同 target/同 source mapping 的 rebind 是 completed no-op；占用、overlap、损坏、缺失 payload、tracking 或 source
问题都保持旧 presentation 并返回可定位 blocked evidence。

`external unlink TARGET_PATH` 是删除一个 durable presentation 的独立 lifecycle，不是 `external remove` 的
简写。它先证明 target 的 runtime/manifest/symlink/index 状态，再对 safe Markdown navigation link、safe
filesystem symlink 及其它仍指向该 presentation 的 managed reference 做 preflight。任何 reference 都以
`presentation_referenced` blocked 返回定位 evidence；调用方先获得内容编辑授权并改写或删除 reference，apply
绝不留下一个因此失效的 link。reference-free apply 只移除精确 symlink、两种 link record 和该 link 可证明拥有
的 index declaration；它不删除 install payload、cache、其它 presentation、文章文字或未知归属的 frontmatter。
之后如需再呈现内容，使用已有 `external link` 或新的 install 加 `external link`。

新 link record 的 `frontmatter_ownership` 对每个 declaration 记录以下事实：`managed` 表示该 link 添加了
entry，`preserved` 表示 entry 原已存在并仍保留，`removed` 表示 safe presentation 为保持正确声明而暂时移除了
原有 `unsafe` entry，`absent` 表示没有该 entry。unlink 移除 `managed`、恢复 `removed`、保留 `preserved`/`absent`；
rebind 在同一 target 上更新此事实而不删除 boundary identity。v1 旧 record 没有该可选 field 时，变体必须把其
配置视为未知归属并保留，不能以“可推测是 link 所加”为由删除用户 state。

`external remove INSTALL_ID` 先扫描 Markdown navigation、filesystem symlink、runtime/manifest durable
mapping 和其它 runtime install 的 parent edge。任一 reference 都返回 `install_referenced` 并保留 payload、
metadata、link 和 configuration。reference-free 时只移除 exact payload 与 per-install metadata；不删
`.gitignore` namespace、root configuration、shared cache 或其它 root state。hidden dependency 仍是保留
状态，不能借 remove 取消下一次 reconciliation 的证据。

## 6. 受管 checkout hook

Hook Registration 的 identity 是 `(owner root, host Git repository, post-checkout trigger)`。`hook --install`
在 Git 解析出的 host hook location 写入 executable managed entrypoint；当前 v1 entrypoint 以
`doctidex-git managed post-checkout hook` marker 表示 owner，并启动 `doctidex-git hook --run --root <owner-root>`。
它是工作现场 artifact，不是 Published Skill 默认操作。

| hook condition | common result / next action |
|---|---|
| no entrypoint | 未安装；只有 human/program 显式选择 `hook --install` 后才创建。 |
| compatible managed entrypoint | install 返回 installed/unchanged；checkout run 消费当前 manifest/runtime。 |
| foreign or unknown entrypoint | `hook_occupied`；保留 entrypoint，不覆盖、不串联、不假定 owner。 |
| incoming variant can reproduce v1 compatibility | 可按 same owner/trigger contract 接手；必须保持 foreign protection 和离线 scope。 |
| incoming variant cannot prove compatibility | preserve entrypoint 并报告 interoperability/migration boundary；不得以 different launcher 覆盖。 |

run 只处理当前 manifest 声明且当前 runtime/payload 已存在的 direct install；它校验 exact commit，离线
切换可用 payload，尽力同步 selector/default provenance。缺失 direct payload 保留并报告，绝不自动
restore。dependency forest 只在一个 aligned direct ancestor 的 content manifest 提供足够 child metadata
时对齐；否则隐藏或保留 dependency，而不猜 revision。manifest fixed commit 永不由 hook 改写。

host hook bytes、exact string comparison、shell quoting、file mode、lock 和 Git worktree move 是
realization mechanics。它们不需要在 Architecture 中复现，但这不减弱上表的 managed identity、conflict、
offline scope、hidden lifecycle 和 incoming preserve/replace boundary。

## 7. 失败、发布与接手

install/link/rebind/unlink/restore/remove/hook 各自可能留下部分已完成的 payload、runtime、manifest、frontmatter、
ignore、link 或 hook effect。它们没有跨资源 transaction。调用方按 result 的 `changed`、`affected`、
finding 和 action 重观测；`index_update_conflict`、mapping/manifest damage、source access failure、hook
occupancy 或 interruption 不授权强制覆盖。

另一 variant 接手时，优先使用 manifest 的 portable direct contract，再读取 runtime 的 current mapping /
hidden state，最后检查 payload/link/hook/worktree 的可证明一致性。能转换时保持所有 observable semantics；
不能转换时保留现场并给出具体 identity/path 与用户下一决策。局部 JSON writer、source hash、lock、
temp path 或 hook-script implementation 的不同不构成 Architecture gap。
