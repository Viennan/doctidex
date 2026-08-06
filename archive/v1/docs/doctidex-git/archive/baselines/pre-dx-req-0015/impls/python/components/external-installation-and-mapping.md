# External 实现

> 归档状态：`format-illegal`。本页是 DX-REQ-0015 前的历史文档基线，不定义当前产品。

[`git/external.py::ExternalService`](../../../../../../../../impls/libs/python/whero/doctidex/git/external.py)
由 CLI 以一个 `RootContext` 构造，属性为 context、owner
`root`、`RootStorage` 和唯一宿主 Git repository。它组合 source/storage/protocol，不能递归
读取依赖文档，也不决定 agent 是否采用受管方案。

## Install

`install(url, selector, dependency_of, apply, cwd)` 先从 runtime 查找相同 canonical source 与
normalized selector；省略 revision 优先匹配已记录的 `requested_default` install。Install ID 对
root/source/fixed selector 求 hash，因此 default intent 与显式 commit 解析到同一 fixed selector
时使用同一 physical key；`requested_default` 仍保留 lookup provenance。该 ID 决定
`/.doctidex/git/installs/<id>`。Parent 必须是
当前 root 的 complete install；role 只允许 dependency 提升为 direct。

dry-run 解析并验证 source/commit、manifest trackability 与计划路径，但不写持久 cache/root。
apply 在 source lock 中保证 exact objects，再在 root lock 中核对 payload untracked、写
frontmatter/ignore、创建 detached readonly worktree、发布 runtime；direct 另原子写 manifest。
既有 path 要求 `HEAD` 仍是记录 commit；不会以 `git status --porcelain` 阻止幂等重用，因此
logical read-only 不是修改检测或 security boundary。
重试既有 branch/tag 使用 record 和 exact commit，不 fetch moving ref。公开 `network` 合并解析
与 object 获取的实际访问。

## Link

`link(source_directory, target_value, apply)` 只接受可读目录和最内层完整 current mapping。
`_mapping_for_source` 先匹配 durable link 再匹配 install 并保留 repository suffix；dependency
source blocked，要求先提升 direct。target 经纯 POSIX 检查，拒绝 occupied、ignored 和任何
ancestor/descendant presentation overlap。

`_safe_state` 仅当 source directory 自身是 full-pass doctidex root 时返回 safe。负责 index
由 target parent 最近有效 index 决定。apply 在任何持久改动前复查 manifest trackability、
portable source、既有 mapping/symlink target，并在目标文件系统探测相对 symlink 能力；随后
在 root lock 中 round-trip 更新该 index、创建相对目录 symlink、发布 current mapping 和
portable link manifest。平台 symlink 失败不回退 copy/junction。幂等只接受完全相同
target/mapping 与 symlink target。

Python publication 顺序是 frontmatter -> symlink -> runtime -> manifest。Capability preflight 令
常规 platform failure 在持久改动前发生，但 process interruption 仍可能留下已建 symlink、mapping
未发布的窗口；后续解析把不自洽现场作为 damaged 保留，并要求以同 mapping 重试或人工修复。
Link result 不重复提示通用 Markdown navigation；Published Skill/human workflow 负责语义导航编辑。

## Restore

`restore(filters, apply, limit, cursor)` 只枚举 manifest direct installs。manifest identity、
规范 filter、limit 和 mode 构成 query identity；未知 filter 变成 item blocked。`_restore_item`
对匹配 path 返回 unchanged，对占用 path 保留并 blocked；dry-run 用 `verify_exact_commit`，apply
用 exact-commit cache 在原稳定 path 重建 readonly worktree，并从 manifest 重建必要 direct/
link runtime mapping。它不更改 manifest、frontmatter、symlink 或 Git index。

Restore 沿用 portable `source_relation` 作为原安装 provenance，并从 portable
`default_branch` 重建 Python runtime 的请求来源标记：non-null 写入
`requested_default: true`，null 写入 `false`。因此恢复后的 direct install record 可立即通过
`RootStorage.read_runtime()` 校验；default-intent lookup 继续复用原 selector/commit，不重新解析
已经移动的 default branch。

单项失败不撤销其他项；page 中任一 blocked 令顶层 warning。后续页只在 manifest identity
未变时继续，恢复 payload 本身不使 cursor 失效。

## Remove

`remove(install_id, apply)` 只接受 selected owner root runtime 中的 exact ID，direct 与 dependency
record 都可作为 target。它先取得 payload path/role 与 direct manifest inclusion，再调用
`tree_observations` 并排除 `install_directory`、`boundary-set` 与 `unsafe`。`_remove_references` 只检查 safe、
non-boundary、non-install Markdown documents 的 normalized file links 和同范围 symlink；它再读取
runtime/portable durable link mapping 以及其他 install 的 `parents`。reference evidence 去重后作为
`install_referenced` blocked finding/affected 返回，不改写它所指的 Markdown、symlink 或 mapping。

dry-run 与 apply 使用相同 preflight。apply 在 `source_mutation(canonical_source)` 后进入 root
`mutation()`，重新读取 record/observations/references；reference-free 时 `remove_detached_worktree`
先恢复 owner-write permission 并以 Git 删除 exact linked worktree，再删除 direct manifest install
entry，最后删除 runtime install record。缺失 payload 也允许同 ID retry 继续删除遗留 record，
但不接受 runtime/manifest identity 或 path 不能自洽的现场。它从不删除 cache、presentation symlink、
root frontmatter 或 shared layout。

result 固定回显 `applied`、`install_id`、`install_role`、`install_path`、`manifest_included`、
`state` 和 `planned_changes`；reference-free plan state 为 `planned`，apply state 为 `removed`。runtime
中的 hidden dependency 是这一流程的前置例外：`remove` 不读取 references、不删除 worktree/record，直接以
`hidden_install_preserved` finding 和 `preserved_hidden` state 完成，`applied` 为 false。
证据由 `test_external_remove_*` 系列覆盖 direct/dependency、mapping/Markdown/symlink/parent block、
exclusion、link-parse target 与 cache preservation。

## Link Parse

`link_parse(path)` 离线读取 owner runtime 和 content root。判定顺序为 current durable link、
install 内 portable symlink、current generic install、unmanaged。portable parser 从 content
root 随快照版本化的 manifest 取 source/link，外层 parent 则由 owner runtime 的 presentation
确定。

`_current_mapping_result` 区分 available 与可 restore 的 `owner_install_missing`。
`_portable_mapping_result` 只匹配同 parent edge、canonical source 与 exact commit 的外层
dependency；缺失是正常 `dependency_not_installed`，匹配但 repository suffix 不可用才是
damage。返回 working path 总是外层 dependency path，不跟随 install 内 broken symlink。

路径、manifest、symlink target 或 source facts 无法自洽时保留 managed 身份并产生
`mapping_damaged`；没有
mapping 返回 unmanaged ok。输入 content root 不获得 owner 写入权。

Generic current mapping 在没有可发现 doctidex root 时把 owner root 填入 `content_root`；portable
或 unmanaged input 无法可靠恢复 repository root 时可返回 null。该字段只表示当前实现可证明的
解释起点，不授予 owner authority。

Portable install 直接保存 `ResolvedSource.public_url`；relative/symlink-spelled local locator 的
跨 cwd/host 可恢复性有限，调用方应优先使用稳定 locator。Mapping damage 的 warning/blocked
分界由 current/portable helper 能否形成自洽 mapping 决定；当前 `requires_user` 只使用代码实际
产生的 root、revision、repository/network、target、tracking、manifest 与 Git-action categories。

证据：[tests/test_git_plugin.py](../../../../../../../../impls/libs/python/tests/test_git_plugin.py) 中
`test_link_restore_and_current_owner_parse`、
`test_restore_rebuilds_requested_default_provenance`、
`test_portable_broken_link_dependency_can_be_flattened`、
`test_restore_preserves_blocked_item_and_restores_other_item`、
`test_link_retry_rejects_a_changed_symlink_target`、
`test_link_classifies_only_a_complete_doctidex_root_as_safe` 与
`test_link_reports_symlink_unsupported_before_persistent_changes`。

## Checkout hook

[`git/hooks.py::HookService`](../../../../../../../../impls/libs/python/whero/doctidex/git/hooks.py)拥有 owner-root
scoped `post-checkout` registration 和 reconciliation。`install()` 用 Git 解析的 hook path 写入精确、
executable 的 `doctidex-git hook --run --root <root>` entrypoint；相同内容重复安装为 unchanged，任何其他
file 或 symlink 保留并返回 `hook_occupied`。

`run()` 先读取 current manifest/runtime。它仅对 manifest 与 runtime 都已知且 payload 存在的 direct
install 调用 `_checkout_exact`：dirty/damaged/missing object 保留为 item-level blocked；否则 detached HEAD
切到 manifest 的 exact commit，并把 selector/default-branch/source provenance 投影回 runtime，绝不 fetch
或重新解释 moving ref。未安装或当前 manifest 未声明的 direct install 作为 ignored item 返回。

成功 direct root 以 runtime `parents` 形成 bounded traversal。每个 parent payload 必须自身是 doctidex
root，且其 portable manifest 必须按 canonical source（有歧义时再按 selector）唯一定位 child metadata；
缺少此证据时，`_hide_subtree` 用 Git worktree move 将每个 dependency payload 移到 hidden namespace 并
更新 runtime。已有 hidden record 无论是否可达 direct root 都会进入本轮结果；具有有效 metadata 的 node
先在原 hidden path 对齐，再移动回 normal path，仅该 node 返回 `unhidden`，其 descendants 仍独立遍历。

Hook result 不分页，按 install ID 返回 item state/count；每个 blocked item 使整体 status 为 warning，但不会
撤销 host checkout。证据：`test_hook_install_is_idempotent_and_preserves_foreign_hook`、
`test_post_checkout_aligns_direct_commit_and_revision_provenance` 与
`test_hook_rechecks_hidden_dependencies_and_unhides_from_parent_manifest`。
