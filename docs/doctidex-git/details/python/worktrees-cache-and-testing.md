# Worktree、清理与测试

## `git/worktrees.py`

`WorktreeSource` 属性为 `kind`、common `gitdir`、canonical `identity`、可公开 `source_url`、
`repository_relative_path`、实际 `network` 和可选 `ResolvedSource`。`WorktreeService` 属性为
owner context/root/storage。

`_classify` 的顺序是 managed presentation、gitfile、bare/working tree、URL；目录/文件类型
互斥，因此与公开 managed -> working/bare -> gitfile -> URL 语义一致。gitfile 会解析为
common gitdir，避免从 linked-worktree private gitdir 再创建现场。managed subdirectory
保留 suffix，所有结果 path 仍在 owner root 的扁平 worktree namespace。

`open` 在 source mutation boundary 中解析 selector/base commit，每次生成随机 ID/path，统计
同 source/base 的 reuse candidates，创建 detached writable worktree后才发布 record；它不建
branch 或进入 external manifest。创建与 record publication 间中断可由 Git metadata 和受管
namespace留下客观 orphan 证据，当前实现只保留，不自动 adopt/delete。

`list` 从 runtime 选 root 内 items，再用原生 `git status --porcelain` 重算
clean/changed/unavailable，按 exact source/worktree filter、稳定 path 顺序分页。WorktreeItem
包含 Architecture 定义的全部 source/owner/selector/base/root-internal/worktree/suffix/working
path/state/findings 属性。

`close` 只匹配 exact record path；unavailable/changed 以顶层 WorktreeItem blocked 并保留。
clean path 在 source/root lock 中调用 `git worktree remove`，成功后删除 record；不触碰其他
presentation。

## `CacheService`

`clean(url, apply)` 不选择 root。locator 必须是 remote 或绝对 local path；canonical identity
只定位一个 bare source。`_classify_linked_worktrees` 解析 `git worktree list --porcelain`，跳过
bare 本身，把每个登记唯一分成 valid 或 Git `prunable`；语法/metadata异常 blocked。

source lock 内有任一 valid 时返回 preserved warning。否则 dry-run 返回 planned；apply 立即
重查相同计数后只删除 bare source directory，公开 changed 仍为空。它不清理 root payload、
manifest、runtime 或其他来源。该 operator command不进入 Published Skills。

## 平台与测试

平台机制使用 `pathlib`、`tempfile`、`os.replace`、`subprocess`、`chmod` 和 mkdir lock；不在
import 时依赖 POSIX-only module。cache root 分平台选择；symlink capability不足由
`symlink_unsupported` 表达而不复制。Git path 输出通过 `--path-format=absolute` 获取。

`tests/test_protocol.py` 使用纯目录 fixture；`tests/test_git_plugin.py` 使用调用真实 console
module 的本地 Git repositories。当前场景覆盖 parser/schema、nested root、ignore、selector
固定、自/cycle edge、restore/mapping、manifest damage、symlink capability/篡改、gitfile、
dirty/unmanaged orphan 保留、active/prunable clean、protocol scope、reference link 与 cursor。
Ruff 负责 Python 3.11 语法和静态规则。

跨平台 CI 在 Linux、macOS 与 Windows 的 Python 3.11/3.12 运行 editable install、Ruff 和
pytest。无法创建 symlink 的 runner 跳过需要成功 symlink 的端到端场景；独立的错误路径由
实现捕获 OSError 并保持 Architecture failure contract。

已知实现边界：没有稳定 Python import API；逻辑只读是普通权限的尽力约束而非 sandbox；
外部 Git/network 错误依赖 Git 可观察消息分类；中断发生在 worktree 创建与 record 发布之间
时，孤立现场只作为 namespace/Git metadata 证据保留，不自动 adopt 或删除。
