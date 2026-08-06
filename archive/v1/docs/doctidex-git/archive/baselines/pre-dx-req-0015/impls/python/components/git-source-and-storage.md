# Git 来源与状态

> 归档状态：`format-illegal`。本页是 DX-REQ-0015 前的历史文档基线，不定义当前产品。

## [`git/runner.py`](../../../../../../../../impls/libs/python/whero/doctidex/git/runner.py)

`GitResult(stdout, stderr, returncode)` 是内部 subprocess 结果。`git(arguments, cwd, operation,
check)` 使用参数数组和 `GIT_TERMINAL_PROMPT=0`，不经 shell；`check=False` 供调用者客观分类，
否则 `_git_error` 把认证/网络/revision/其他失败清理为 user-level Finding。stderr 和含凭据的
argv 不进入正常结果。

## [`git/source.py`](../../../../../../../../impls/libs/python/whero/doctidex/git/source.py)

调用者为 External/Worktree coordinator；它不读取 doctidex frontmatter 或分配 root path。

`RevisionSelector` 属性为 `kind` 与 `value`；`ResolvedSource` 属性为调用期 `input_url`、已
清理 `public_url`、内部 `canonical` identity、规范 selector、`default_branch`、full
`commit` 和本次解析是否实际使用 `network`。

主要函数：

- `sanitize_url` 移除 scheme URL userinfo；`canonical_source` 对 local/file URL 使用
  `Path.resolve(strict=False)`，对 scheme URL lower-case scheme/host、移除 fragment/trailing slash，
  对 SCP-like 只移除 trailing slash；query 与其他未归一化 spelling 保持 identity 的一部分，
  不推断 mirror/fork；
- `resolve_source` 校验 selector，首次省略时读取 HEAD/default branch 并转为 commit selector；
  remote full commit 以临时 bare fetch 验证，tag/branch 以 remote ref 解析；
- `ensure_source_cache` 创建/更新用户级 bare repository；`ensure_exact_commit_cache` 为既有
  key/restore 只保证已记录 commit，不解析 moving ref；`verify_exact_commit` 为 dry-run 使用
  现有 objects 或调用期临时 bare repository，不写持久 cache；
- `add_detached_worktree` prune 明确失效登记后从 bare/common gitdir 直接创建 detached path；
  `move_detached_worktree` 先临时恢复 owner-write permission，再以 `git worktree move` 保持 linked-worktree
  registration 后重设 logical read-only；`make_logically_read_only` 清除普通写权限，失败时尽力而为且不构成
  sandbox；
- `source_relation` 只在 common gitdir 或 canonical origin 足以证明时报告宿主关系。

## [`git/storage.py`](../../../../../../../../impls/libs/python/whero/doctidex/git/storage.py)

`cache_root()` 按 `DOCTIDEX_GIT_CACHE`、Windows `LOCALAPPDATA`、macOS Caches 或 Linux
`XDG_CACHE_HOME` 选择用户 cache。`source_id` 是 opaque hash；`source_cache` 只返回 bare
repository 路径。`source_mutation` 从 canonical source 得到 ID；`source_mutation_id` 是其底层
lock primitive，供 `cache clean --auto` 对已枚举的 opaque ID 使用，因此不会因缺少 canonical URL
另建一个 lock namespace。

`RootStorage` 的属性为 `root`、内部 namespace、normal install/hidden/worktree 目录、ignored runtime
JSON、trackable manifest JSON 和 root mutation lock。方法负责拒绝 duplicate JSON key、逐项
校验 schema/identity/path/reference 自洽性、atomic update、
manifest identity、root lock，以及维护 root index 的 install boundary/unsafe 和宿主根
`.gitignore` 精确规则。manifest 只含 direct installs/links；runtime 另含 dependency edges 和
worktree ownership。正常结果不公开 runtime、cache 或 lock path。

`directory_lock` 使用原子 `mkdir`，支持 POSIX/Windows，不依赖 `fcntl`；超时转换为 conflict。
`source_mutation` 按 canonical source 串行 object/worktree mutation；调用者先取 source，再取
root lock。`_atomic_text` 在同目录写临时文件、fsync 后 `os.replace`。Git objects、frontmatter、
ignore、manifest、payload 与 record 不构成总事务，失败必须按 changed/affected 恢复。

manifest/runtime schema 当前只接受 `1.0`；未知或损坏文件 blocked，不自动迁移 v0。
JSON 使用排序键和结尾换行，manifest identity 对完整规范 JSON 求摘要；写入前使用同一校验器，
避免发布 CLI 自身无法重新读取的 portable facts。

`manifest_identity` 使用 Python `json.dumps(sort_keys=True, separators=(",", ":"))` 的完整 logical
object 摘要；validator 要求 known fields 自洽并允许 unknown fields 保留为无本版本语义的数据。

`HookService` 用 `git rev-parse --git-path hooks/post-checkout` 取得 linked host worktree 对应的 hook
path，以内容标识自己管理的 executable shell entrypoint；它不会覆盖或组合其他 hook。`run()` 只在现有
linked worktree/common Git objects 上执行 detached checkout，不 fetch 或重新解析 moving ref；随后在
source -> root lock order 中同步 runtime revision provenance，或在没有 parent manifest metadata 时调用
`move_detached_worktree` 隐藏 dependency subtree。

Host Git Coordinator 的其余 ownership 分布为：`git.external._host_repository` 用
`git rev-parse --show-toplevel` 选择唯一 host；`RootStorage.ensure_host_layout` 再验证 host、更新
root index 与 exact `.gitignore` entries；`git.storage.git_file_state` 产生 tracked/modified/untracked；
`git.external._assert_payload_untracked`、`_assert_manifest_trackable`、`_git_ignored` 与 link target
checks 执行 tracking/ignore preflight。`ExternalService.install/link/restore` 是这些 helpers 的唯一
产品 coordinator，并在 root lock 内重新读取相关 facts。

证据：[tests/test_git_plugin.py](../../../../../../../../impls/libs/python/tests/test_git_plugin.py) 中
`test_default_revision_is_fixed_and_self_dependency_is_bounded`、
`test_explicit_branch_retry_stays_fixed_and_root_is_part_of_identity`、
`test_install_blocks_an_ignored_recovery_manifest`、
`test_cache_cleanup_accepts_prunable_registration` 与
`test_manifest_rejects_duplicate_and_inconsistent_portable_facts`。网络认证场景依赖 Git 错误分类，
CI 不需要真实远端凭据。
