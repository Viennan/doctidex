# External 实现

`git/external.py::ExternalService` 由 CLI 以一个 `RootContext` 构造，属性为 context、owner
`root`、`RootStorage` 和唯一宿主 Git repository。它组合 source/storage/protocol，不能递归
读取依赖文档，也不决定 agent 是否采用受管方案。

## Install

`install(url, selector, dependency_of, apply, cwd)` 先从 runtime 查找相同 canonical source 与
normalized selector；省略 revision 只匹配首次已记录的 default key。install ID 对
root/source/selector 求 hash，决定 `/.doctidex/git/installs/<id>`。parent 必须是当前 root 的
complete install；role 只允许 dependency 提升为 direct。

dry-run 解析并验证 source/commit、manifest trackability 与计划路径，但不写持久 cache/root。
apply 在 source lock 中保证 exact objects，再在 root lock 中核对 payload untracked、写
frontmatter/ignore、创建 detached readonly worktree、发布 runtime；direct 另原子写 manifest。
既有 path 必须仍是记录 commit。重试既有 branch/tag 使用 record 和 exact commit，不 fetch
moving ref。公开 `network` 合并解析与 object 获取的实际访问。

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

## Restore

`restore(filters, apply, limit, cursor)` 只枚举 manifest direct installs。manifest identity、
规范 filter、limit 和 mode 构成 query identity；未知 filter 变成 item blocked。`_restore_item`
对匹配 path 返回 unchanged，对占用 path 保留并 blocked；dry-run 用 `verify_exact_commit`，apply
用 exact-commit cache 在原稳定 path 重建 readonly worktree，并从 manifest 重建必要 direct/
link runtime mapping。它不更改 manifest、frontmatter、symlink 或 Git index。

单项失败不撤销其他项；page 中任一 blocked 令顶层 warning。后续页只在 manifest identity
未变时继续，恢复 payload 本身不使 cursor 失效。

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

证据：端到端测试覆盖 direct/dependency、default/branch 固定、self edge、相对 link、missing
install restore、portable broken link 的缺失/展开、wrong content root、broad ignore 冲突、
manifest 重复/路径损坏、symlink 篡改和 capability preflight。
