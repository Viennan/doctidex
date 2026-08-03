# 工作现场与跨变体接手

本页定义一个 variant 留给下一个 variant 的 **工作现场**，并是 Architecture-only reader 的
入口。工作现场不是某次 CLI 输出的摘要，而是 user surface 已写入、保留或明确暴露的 selected
root、host repository、installed content、cache 和 diagnostic 中的配置与 artifact。reader 只能使用
该现场、user-visible transcript 和本 Architecture，仍必须说明每一个实际存在的 doctidex-git
配置文件、每个出现 option 和每个 artifact 的用途、使用方法、lifecycle 与安全处置。

本页只盘点并路由；每项的 field/state semantics 由所链接的唯一 authority 定义。它不要求 reader
复现 Python 的 JSON encoding、hash、lock primitive、Git argv 或调用顺序。

## 1. 发现与解释规则

1. 从 transcript 得到 selected root、host repository、operation、apply/dry-run、result、affected、
   preserved state 和 `requires_user`，但不把未列出的路径直接视为无关。
2. 递归盘点 selected root、host repository 的相关 hook/ignore、install payload、worktree 和本次
   operation 暴露的 cache/diagnostic；将每个文件归入下表的 configuration、artifact、third-party
   Git data 或未知数据。
3. 对每个 configuration option，读取其 authority 的约束、影响和 incoming-variant rule；对每个
   artifact，说明 producer、consumer、可用方式和保留/清理/恢复边界。
4. 不能由本 Architecture 直接支持的解释是 gap，不得用 Impls/source、名称猜测或 verifier 的全知
   推断补足。未知 schema/version、foreign hook 或无法证明 identity 的 payload 必须保留或 blocked，
   而不是被当成可安全删除的 private data。

正常、partial success、blocked、recovery、migration/compatibility、damaged、hidden 和 interruption
都是语义不同的现场类别。等价场景只有在文件、option、artifact、状态和 user-visible effect 都相同
时才可合并。

## 2. 配置与产物盘点

| 可出现对象 | 类别与发现位置 | 直接 authority | incoming variant 的最低责任 |
|---|---|---|---|
| `index.md` 与关联的 doctidex link annotation | doctidex configuration；root 或 responsible index。 | [树与验证](tree-and-validation.md#2-索引配置与根观察) | 解释 top-level `type`、`doctidex` options 与 `unsafe`/boundary annotation，并仅按 protocol 修改/保留。 |
| host `.gitignore` | host configuration；包含 owner root 的 Git repository。 | [外部快照](external-snapshots-and-presentations.md#2-主机归属与受管命名空间) | 保持 managed payload/runtime/worktree/lock 不被 track，同时不得隐藏 manifest 或 durable presentation。 |
| `/.doctidex/git/manifest.json` | versioned portable configuration；owner root。 | [外部快照](external-snapshots-and-presentations.md#3-可移植恢复清单) | 读取每个 entry，按 exact snapshot restore/link；未知 version preserve/reject。 |
| `/.doctidex/git/runtime.json` | host-local handoff configuration；owner root。 | [外部快照](external-snapshots-and-presentations.md#4-运行时安装与链接记录) 和 [工作树](worktrees-and-cache.md#2-运行时工作树记录) | 解释 install/link/worktree record；读取、转换或保留，不能静默猜测或丢弃。 |
| `/.doctidex/git/installs/<id>/` | logical read-only fixed snapshot artifact。 | [外部快照](external-snapshots-and-presentations.md#5-安装载荷隐藏状态与持久呈现) | 根据 runtime/manifest 验证 identity，作为 source/read target，或按 restore/preserve 处置。 |
| `/.doctidex/git/installs/.hidden/<id>/` | hidden dependency artifact。 | [外部快照](external-snapshots-and-presentations.md#5-安装载荷隐藏状态与持久呈现) | 解释 hidden 原因；不得把它作为 durable presentation source 或直接删除。 |
| durable presentation symlink | root 内、trackable user-selected path。 | [外部快照](external-snapshots-and-presentations.md#5-安装载荷隐藏状态与持久呈现) | 以 mapping 解释 target；broken 时 link-parse/restore/installation，而非盲目重写。 |
| host `post-checkout` | host-side registration artifact。 | [外部快照](external-snapshots-and-presentations.md#6-受管-checkout-hook) | 识别 managed/foreign/unknown，按 compatible takeover、preserve 或 conflict rule 处理。 |
| `/.doctidex/git/worktrees/<id>/` | writable managed worktree artifact。 | [工作树](worktrees-and-cache.md#3-可写工作树生命周期) | 通过 runtime record 解释 source/revision/status；changed/unavailable 时保留。 |
| shared source cache | user-cache 的 bare Git artifact；可能由 install/URL worktree 暴露。 | [工作树](worktrees-and-cache.md#4-共享来源缓存与清理) | 作为 shared cache 而非 root state；只经 cache cleanup 判断，不能因单个 root 删除。 |
| diagnostic | user-cache 中由 opaque diagnostic ID 指向的 failure artifact。 | [操作安全](operation-safety-and-recovery.md#4-诊断锁与临时产物) | 将 ID 与 operation 一起交给 maintainer；不解析 traceback 来重定义产品 state。 |
| root/source/hook lock、temp、cache-private coordination container 或 Git registration | active/incomplete evidence、private cache organization，或 Git 自己的 metadata。 | [操作安全](operation-safety-and-recovery.md#4-诊断锁与临时产物) | active evidence 等待、重观测或有限重试；空 private container 不表示可删 cache；两者都不擅自删除。 |

普通 host `.git/`、bare repository internals、installed content 自己的 source files 和没有 doctidex-git
identity 的 files 不是本产品 configuration。它们仍可能是可读 artifact，但只能按 native Git、
doctidex protocol 或用户上下文解释；不得伪称为已知 managed state。

## 3. 配置文件的选项覆盖

下列是 Architecture reader 在现场遇到配置文件时必须能解释的完整 option 集。`schema_version`
为当前支持 schema 的 discriminator；未知或无法验证的 version 不允许兼容猜测。

| 文件 | options | 语义、影响与安全处置 |
|---|---|---|
| `index.md` | top-level `type`、`doctidex.type`、`root`、`boundary-set[].path`、`atomic-indexing[].path`、`unsafe[].path` | 定义 interoperable index kind、protocol root、responsibility、reachability 和 strict-rule exception；详见 [树与验证](tree-and-validation.md#2-索引配置与根观察)。 |
| 与 file-path link 关联的 doctidex annotation | `unsafe`、`cross-boundary-point` | 把 unsafe 或首次 cross-boundary fact 绑定到该 link；必须保留其关联而不是把 HTML comment 视为无意义文本；详见 [树与验证](tree-and-validation.md#2-索引配置与根观察)。 |
| `.gitignore` | managed namespace entries | 标识哪个 root-internal payload/runtime/worktree/lock 不进入 host Git；manifest 与 presentation 必须保持 trackable；详见 [主机归属](external-snapshots-and-presentations.md#2-主机归属与受管命名空间)。 |
| `manifest.json` | `schema_version`、`installs`、`links`；每个 install 的 `install_id`、`install_path`、`source_url`、`source_relation`、`revision_selector.kind/value`、`default_branch`、`resolved_commit`；每个 link 的 `target_path`、`install_id`、`repository_relative_path`、`safe_state`、`responsible_index` | direct snapshot 的 portable recovery/presentation contract；每个 field 的 identity、effect 和 version/unknown rule 见 [manifest](external-snapshots-and-presentations.md#3-可移植恢复清单)。 |
| `runtime.json` install/link | `schema_version`、`installs`、`links`；install 还包括 `canonical_source`、`requested_default`、`role`、`parents`、`managed_state` | host-local lookup、dependency/hide state 与 current mapping；value 可以为 opaque matching fact，但不是无意义字段。完整含义和 convert/preserve/reject rule 见 [runtime install/link](external-snapshots-and-presentations.md#4-运行时安装与链接记录)。 |
| `runtime.json` worktree | `worktrees`；每个 record 的 `worktree_id`、`source_kind`、`source_identity`、`source_url`、`gitdir`、`revision_selector`、`base_commit`、`root_internal_path`、`worktree_path`、`repository_relative_path` | writable artifact 的 owner、source/revision、working path 和 close safety；完整约束见 [运行时工作树](worktrees-and-cache.md#2-运行时工作树记录)。 |

这些表定义语义，不要求当前或未来 variant 共用 JSON library、key order、hash、absolute-path encoding
或 atomic write implementation。一个 variant 如采用不同 physical format，必须仍能解释已经出现的
`1.0` 文件，或安全 preserve/reject 并给出可行动 result。

## 4. 接手决策

| 现场结论 | 必须保持的 observable semantics | 允许的动作 |
|---|---|---|
| known complete direct install + valid manifest/runtime | exact commit、durable link、logical read-only、restore identity。 | 直接使用，或转换为 own representation 后保持 mapping。 |
| missing direct payload + valid manifest | broken presentation 不被重写；restore 只补 exact snapshot。 | `restore` 或报告 owner-install-missing。 |
| dependency-only / portable dependency link | 不递归 materialize；`dependency_not_installed` 是合法状态。 | 保持，或经显式 dependency install 后重新解析。 |
| hidden dependency | 不猜 revision、不供 durable link、保留 parent evidence。 | 在可证明 aligned ancestor 后 unhide；否则 preserve/blocked。 |
| clean worktree | ownership、base commit、writable path。 | 使用或显式 close。 |
| changed/unavailable worktree | user changes 或损坏 evidence 不丢失。 | 保留，返回 `worktree_changed` / `worktree_unavailable`，由 native Git/用户决定。 |
| shared cache with valid/unknown registrations | 不因当前 owner root 推断可删除。 | 仅按 cache clean 的 eligibility/preserve rule 操作。 |
| managed compatible hook | checkout 后离线 reconciliation、foreign hook 不被覆盖。 | 保持 compatible registration 或按 versioned migration 接手。 |
| foreign/unknown hook、schema、payload 或 lock | 用户/其他工具的 state 不被破坏。 | preserve、block、diagnose 或要求显式 migration authority。 |

## 5. 概念提升边界

一个 Impls/source concept 只要是解释上表某个已存在 configuration/artifact 的 identity、option、
state transition、use、recovery、handoff 或 safety boundary 所必需，就必须在 Architecture 的相应
authority 中出现。反之，局部 algorithm、parser intermediate、hashing、lock acquisition、temp name、
call graph、module boundary 和 performance tuning 若不改变这些行为，可仅留在 Impls/source。

因此 Architecture-only reader 的目标不是复述当前 execution，而是足以让独立 variant 正确处理
user surface：输入与默认、配置/artifact、结果、failure、recovery、handoff 与 safety。未复现
source 的内部 mechanics 本身不是 gap。
