# Python 工作现场清单与构造

本页是 Python 变体实际物化的工作现场唯一的物理权威说明。它将每个文件、配置选项和 artifact 映射到 [Architecture 工作现场交接](../../architecture/worksite-handoff.md)的直接语义权威，并说明 Python 如何构造、验证和保留它们。component 页面可以链接本页，但不能重新定义布局或清单。

<a id="1-physical-layout-与-ownership"></a>
## 1. 物理布局与责任归属

对于选定的 owner root，Python 使用下列布局：

```text
<owner-root>/.doctidex/git/
|-- installs/
|   |-- <install-id>/
|   `-- .hidden/<install-id>/
|-- worktrees/<worktree-id>/
|-- manifest.json
|-- runtime.json
`-- .mutation.lock/

<user-cache>/
|-- sources/<source-id>.git/
|-- locks/<source-id>.lock/
`-- diagnostics/<diagnostic-id>.log
```

`RootStorage` 负责 owner-root 路径和 [`git/storage.py`](../../../../impls/libs/python/whero/doctidex/git/storage.py)中的 JSON 验证。`cache_root()` 负责平台 cache 的选择；source ID/hash、lock directory 名称、JSON key 顺序和 atomic-write 实现属于私有机制。下表是完整的用户界面工作现场清单：

| 对象与物理形式 | Python 生产者与责任方 | Architecture 语义 | Python 构造与证据 |
|---|---|---|---|
| 根或负责的 `index.md` frontmatter、关联 doctidex annotation 与 Markdown | `protocol.document`、`RootStorage`、`ExternalService.link`；只更新相关声明。 | [树配置](../../architecture/tree-and-validation.md#2-索引配置与根观察) | [`protocol/document.py`](../../../../impls/libs/python/whero/doctidex/protocol/document.py)、[`external.py`](../../../../impls/libs/python/whero/doctidex/git/external.py)；protocol/link 测试。 |
| host `.gitignore` 的受管条目 | `RootStorage.ensure_host_layout`。 | [host namespace](../../architecture/external-snapshots-and-presentations.md#2-主机归属与受管命名空间) | [`storage.py`](../../../../impls/libs/python/whero/doctidex/git/storage.py)；install/restore/worktree 测试断言 tracking boundary。 |
| `manifest.json` | `RootStorage.read_manifest/write_manifest`；`ExternalService` 更新直接 install/link 记录。 | [portable manifest](../../architecture/external-snapshots-and-presentations.md#3-可移植恢复清单) | [`storage.py`](../../../../impls/libs/python/whero/doctidex/git/storage.py)、[`external.py`](../../../../impls/libs/python/whero/doctidex/git/external.py)；install/link/restore 测试。 |
| `runtime.json` 的 install/link 记录 | `RootStorage.read_runtime/update_runtime`；external/hook 服务。 | [runtime install/link](../../architecture/external-snapshots-and-presentations.md#4-运行时安装与链接记录) | [`storage.py`](../../../../impls/libs/python/whero/doctidex/git/storage.py)、[`external.py`](../../../../impls/libs/python/whero/doctidex/git/external.py)、[`hooks.py`](../../../../impls/libs/python/whero/doctidex/git/hooks.py)。 |
| 普通 install payload | `ExternalService.install/restore`、Git detached worktree。 | [payload 状态](../../architecture/external-snapshots-and-presentations.md#5-安装载荷隐藏状态与持久呈现) | [`external.py`](../../../../impls/libs/python/whero/doctidex/git/external.py)、[`source.py`](../../../../impls/libs/python/whero/doctidex/git/source.py)。 |
| hidden install payload | `HookService` 将无法证实的 dependency payload 移入 `.hidden`。 | [hidden 生命周期](../../architecture/external-snapshots-and-presentations.md#5-安装载荷隐藏状态与持久呈现) | [`hooks.py`](../../../../impls/libs/python/whero/doctidex/git/hooks.py)；hidden/unhide 测试。 |
| 持久的相对 symlink | `ExternalService.link`；source 是完整的直接 payload suffix。 | [持久呈现](../../architecture/external-snapshots-and-presentations.md#5-安装载荷隐藏状态与持久呈现) | [`external.py`](../../../../impls/libs/python/whero/doctidex/git/external.py)；link/retry/safe-state 测试。 |
| host `post-checkout` executable | `HookService.install`；路径由 host Git 解析。 | [受管 hook](../../architecture/external-snapshots-and-presentations.md#6-受管-checkout-hook) | [`hooks.py`](../../../../impls/libs/python/whero/doctidex/git/hooks.py)；install/foreign-hook 测试。 |
| `worktrees/<id>` 与 runtime record | `WorktreeService.open/list/close`。 | [worktree 记录/生命周期](../../architecture/worktrees-and-cache.md#2-运行时工作树记录) | [`worktrees.py`](../../../../impls/libs/python/whero/doctidex/git/worktrees.py)；clean/changed/unavailable/orphan 测试。 |
| `sources/<id>.git` bare cache | source resolver 与 `CacheService`。 | [共享 cache](../../architecture/worktrees-and-cache.md#4-共享来源缓存与清理) | [`source.py`](../../../../impls/libs/python/whero/doctidex/git/source.py)、[`worktrees.py`](../../../../impls/libs/python/whero/doctidex/git/worktrees.py)；cleanup 测试。 |
| opaque diagnostic log | 意外失败时由 `git.diagnostics` 产生。 | [diagnostic artifact](../../architecture/operation-safety-and-recovery.md#4-诊断锁与临时产物) | [`diagnostics.py`](../../../../impls/libs/python/whero/doctidex/git/diagnostics.py)。 |
| root/source/hook locks、cache-private lock container、temp files 与原生 Git metadata | `storage`/source/hook 服务和 Git。 | [瞬态证据](../../architecture/operation-safety-and-recovery.md#4-诊断锁与临时产物) | [`storage.py`](../../../../impls/libs/python/whero/doctidex/git/storage.py)、component recovery 页面。 |

<a id="2-configuration-representations"></a>
## 2. 配置表示

Python 接受并产生 `schema_version: "1.0"`。`RootStorage` 在使用记录前拒绝无效类型、ID/path 关系、revision 形式和引用不一致。它有意让读写共用同一组 validators，因此不会发布随后无法读取的状态。Architecture 负责语义含义；下表标识物理实现和具体的验证边界。

| 文件或记录 | Python 物理表示 | 验证与转换边界 |
|---|---|---|
| `index.md` 与关联 doctidex annotation | YAML frontmatter 保留顶层 `type: index`、`doctidex` root/local configuration，以及链接需要时相邻的 `<!-- doctidex: {...} -->` comment。 | `protocol.document` 在应用负责声明时保留无关 frontmatter/comments/Markdown；annotation 仍与其链接关联。 |
| `manifest.json` 顶层 | 含有 `schema_version`、对象 `installs`、对象 `links` 的 JSON object。 | `read_manifest(required=...)` 拒绝非 `1.0`、无效记录或缺失的必需 manifest。 |
| portable install | 以相同的 `install_id` 为键的 object；仅含直接记录。 | `install_path` 必须是正常 namespace path；selector/commit/value/source 字段写入前均会验证。 |
| portable link | 以相同的规范化 `target_path` 为键的 object。 | 被引用的直接 install、root-relative target、repository suffix、`safe_state`、负责的 `index.md` 均会验证。 |
| `runtime.json` 顶层 | JSON object 额外包含对象 `worktrees`。 | 仅当文件不存在时，`read_runtime` 才返回空的有效 runtime；现存无效文件会被 blocked/damaged。 |
| runtime install | portable fields 加上 `canonical_source`、`requested_default`、`role`、`parents`、`managed_state`。 | hidden path/state 仅允许用于 dependency；parents 必须唯一；restore 重建 runtime 时会重新计算本地字段。 |
| runtime link | 与 portable link 相同的记录形状。 | target key 与 install reference 必须和当前 runtime installs 一致。 |
| runtime worktree | 键相同的 `worktree_id`、source/revision/paths 字段。 | 验证 source-kind enum、selector/base commit、root-internal path 和 repository suffix。 |

精确的 JSON serializer（`sort_keys`、separators、ASCII escaping）、manifest hash 和 file replacement primitive 不属于 Architecture contract。它们作为本地机制见[源码/状态存储](components/source-and-state-storage.md)和[发布/恢复](publication-recovery-and-private-mechanics.md)。接手的变体仍必须先从 Architecture 理解字段语义，再转换或保留此表示。

<a id="3-scenario-construction-matrix"></a>
## 3. 场景构造矩阵

工作现场验证使用隔离的本地 Git fixture：临时 owner root/host repository、source repositories、隔离的 `DOCTIDEX_GIT_CACHE` 和捕获到的 `--json` transcript。它从不使用用户 credential、既有 host repositories 或真实用户 cache。执行者会在每个场景后保留完整 fixture，包括 hidden files、hook location、cache 和操作暴露的 diagnostic path。

| 场景类别 | 构造方式与可观察的物化结果 | Python 证据与 reader 必须覆盖的内容 |
|---|---|---|
| 空 root 与 dry-run | 创建有效 root，运行 validate/install/link dry-run；不产生持久变更。 | `test_valid_tree_and_scopes`；reader 应解释缺失状态，而不是编造 runtime state。 |
| 直接 install 变体 | 具有省略 default、显式 commit/tag/branch 和 host/other source relation 的本地 source。 | install/default-selector 测试；各行共同覆盖 manifest/runtime/payload/cache/ignore/index 选项。 |
| dependency 与 promotion | 先安装带 parent 的 dependency，再以相同 identity 正常安装。 | dependency/self-cycle/promotion 测试；覆盖 `role`、`parents` 和 manifest inclusion。 |
| 安全/不安全的持久 link | 将完整直接 install 链接到安全 root 和不安全 scope。 | link/safe-state 测试；覆盖 symlink、两类 link record 与负责的 index 选项。 |
| 缺失的直接 restore | 仅移除 payload，观察 `owner_install_missing`，再 dry-run/apply restore。 | restore 测试；覆盖 broken presentation、`planned/restored/unchanged/blocked`。 |
| portable 的损坏 dependency link | 检查 outer dependency 缺失的已安装 repository link，再物化它。 | portable mapping 测试；`dependency_not_installed` 属于正常结果。 |
| hook 注册与直接对齐 | 安装 hook、重复安装、加入 foreign hook 情形，并 checkout 已有 payload 的变更 manifest。 | hook install/alignment 测试；覆盖 hook artifact、直接 runtime 和 transcript。 |
| hidden dependency / unhide | checkout 无法证明 dependency metadata 的状态，再重新引入已对齐的 parent metadata。 | hidden/unhide 测试；覆盖 `.hidden`、`managed_state` 和 parent evidence。 |
| remove 保护 | 无引用、被 Markdown/symlink/mapping/parent-edge 阻止，以及 hidden 保留。 | remove 测试；覆盖 artifact 和 record 的保留。 |
| worktree source 与状态 | managed path、URL、working tree、bare/gitfile；clean、changed、unavailable 与未记录 orphan。 | worktree/orphan 测试；覆盖 record option 和保留行为。 |
| cache 清理 | active/preserved、eligible/removed、prunable、damaged/blocked 和自动枚举。 | cache 测试；覆盖 cache item 状态和计数。 |
| interruption/damage | 无效 manifest/runtime、lock conflict、orphan/partial publication 和意外 diagnostic。 | recovery/lock 测试；保留并重观测，而不是重建 source 细节。 |

只有当源码/测试证据证明物化文件、选项值、artifact、状态和可观察用户效果相同，矩阵才可以合并场景。每次配对 reader/verifier 轮次都在活动 Requirement 中记录精确 fixture path、变体标识和 transcript，而不记录在已发布的 Architecture/Impls 页面中。

<a id="4-construction-boundaries"></a>
## 4. 构造边界

Python test suite 是多数行的主要确定性构造器：[`test_git_plugin.py`](../../../../impls/libs/python/tests/test_git_plugin.py)覆盖 external、hook、worktree/cache 和 recovery fixture；[`test_protocol.py`](../../../../impls/libs/python/tests/test_protocol.py)覆盖树和验证。配对验证运行已安装的 console script，并针对独立本地 fixture，而不直接调用 service，因此 Architecture reader 只能看到变体/用户界面实际留下的内容。

runtime/cache/lock path 的发现必须从 fixture 或其 public result 捕获；任何场景都不暴露真实 credential、不使用外部 network source，也不复用用户的 `DOCTIDEX_GIT_CACHE`。私有 source algorithms 是证明 fixture 等价的证据，而不是提供给 Architecture-only reader 的输入。
