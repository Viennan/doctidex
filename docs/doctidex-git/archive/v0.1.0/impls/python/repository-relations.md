# doctidex-git 0.1.0 Git Repository Relation 与 Scope 复用

`git/relations.py` 为 [root relation 与 maintenance reuse](../../architecture/domain-model.md#44-root-relation)
提供离线、确定性的 Python 实现。它只生产供上层决策的客观事实，不改变 mount 路径、
创建 worktree、选择交付目标或判断任务是否应当合并。本模块落实
[DXG-REQ-0002](../../../../../requirements/0002-root-self-reference-and-maintenance.md)。

## 1. 模块责任

| 负责 | 不负责 |
|---|---|
| 读取当前 Git HEAD、symbolic branch 和 checkout 根。 | 联网验证 remote、mirror 或 fork 身份。 |
| 保守确认 mount source 是否对应当前 checkout root。 | 规范化所有 Git URL 或改变 source cache identity。 |
| 比较已确认同源两侧的 commit。 | 因 commit 相同而推断仓库相同。 |
| 从开放 records 中找同 source/base commit scope，并排除已知 branch 冲突。 | 判断写入权限、未知 branch 或其他交付动作是否兼容。 |
| 返回固定、有界的 relation/reuse object。 | 创建、选择、关闭或删除 maintenance root。 |

调用者是 `MaintenanceService.scope()`、`guidance()` 和 `open()`；`cli._resolve()` 通过
`guidance()` 使用同一逻辑。模块依赖 `git.runner.git`，不依赖 CLI 或协议解析层。

## 2. 公开给上层的函数

### 2.1 `git_head(path, operation)`

运行 `git rev-parse HEAD`，成功返回完整 commit，非 Git、unborn 或其他非零结果返回
`None`。`operation` 只用于 Git error context；函数不写入、不联网。

### 2.2 `git_branch(path, operation)`

运行 `git symbolic-ref --quiet --short HEAD`，成功返回当前 symbolic branch；detached
HEAD 或其他非零结果返回 `None`；unborn branch 仍可成功返回名称。它只提供交付提示，
不切换 branch。

### 2.3 `repository_relation(root, source, effective_commit, root_head=None)`

返回固定 object：

| 属性 | 值 |
|---|---|
| `source` | `same_repository` 或 `unknown`。 |
| `revision` | `same_commit`、`different_commit` 或 `unknown`。 |

`root_head` 允许 scope 在多个 mount 间复用一次 HEAD 读取；省略时函数自己读取。确认
source 的顺序为：

1. `root` 必须恰好等于 Git `--show-toplevel`，nested doctidex root 不参与自引用复用；
2. 本地 source path 或 `file://` path 与 root 的 Git common directory 相同时确认；
3. source 文本与 root 任一配置 remote URL 精确相同时确认；
4. source 与配置 remote 都能解释为存在的本地路径且解析后相同时确认；
5. 其他情况返回 unknown。

第 4 步不会把 `git@example.com:repo.git` 一类 SCP-style remote 当作相对路径；显式
`./...`、`../...` 和绝对路径仍按本地路径解析。这样 remote 文本与同名本地目录不会
产生错误的仓库同一性结论。

确认 source 后才比较 HEAD 与 effective commit。任何一侧缺失时 revision 为 unknown。
所有探测使用 `check=False`，无法读取的 Git 元数据收敛为 unknown，不阻断 resolve/scope。

### 2.4 `maintenance_reuse(..., *, target_branch, root_branch)`

`records` 是当前宿主 state 中已过滤为 mapping 的 maintenance records。函数返回固定
object 的全部属性：

| 属性 | 计算方式 |
|---|---|
| `status` | 唯一首选为 `recommended`；多个已有根为 `selection_required`；没有为 `not_available`。 |
| `scope_kind` | recommended host 为 `host_root`；recommended/selection-required 开放根为 `maintenance_root`；not-available 为 `None`。 |
| `write_path` | 唯一建议路径；无唯一建议时 `None`。 |
| `target_branch` | 唯一建议根的 branch 提示；无唯一建议时 `None`。 |
| `candidate_count` | 已知兼容 scope 数量，不返回候选路径数组。 |
| `reason` | 公共 schema 定义的稳定原因枚举。 |

兼容 maintenance record 必须满足原始 `url` 文本相同、`base_commit` 等于 effective commit、
登记 path 仍是目录，并且 record `target_branch` 与输入 target branch 不存在已知冲突。
只有两侧都是非 null 字符串且不同才视为冲突；任一侧未知时保留候选。自引用且同 commit
且 root branch 兼容时 host root 优先于所有开放根；否则一个开放根可直接复用，多个开放
根只返回数量并要求上层引导 status 选择。存在同 source/base commit 候选但均因已知 branch
冲突被排除时，reason 为 `delivery_target_conflict`。

### 2.5 `current_root_reuse(root, target_branch)`

为 `host_root` scope item 构造固定推荐：kind 为 host、write path 为 root、候选数为 1、
reason 为 `current_root`，并透传调用者已读取的 branch。它不调用 Git。

## 3. 内部辅助函数

| 函数 | 作用与返回 |
|---|---|
| `_same_repository(root, source)` | 组合 checkout-root、common-directory、remote 和本地路径检查；只返回确认成功/未确认。 |
| `_git_worktree_root(path)` | 宽容读取绝对 checkout root，失败为 `None`。 |
| `_git_common_directory(path)` | 宽容读取并解析 Git common directory，支持 linked worktree。 |
| `_remote_urls(root)` | 读取所有 `remote.*.url`；结果是去重 set，失败为空。 |
| `_local_source_path(value, root)` | 解析存在的普通/file 本地路径；相对值以 doctidex root 为基准，非本地 scheme 或不存在返回 `None`。 |
| `_is_scp_like_remote(value)` | 按 colon 前缀是否含路径分隔符区分 SCP-style remote 与显式本地路径。 |
| `_delivery_targets_compatible(first, second)` | 只有两个已知且不同的字符串 branch 才返回 false。 |
| `_branch_hint(value)` | 将 record 中的字符串 branch 透传，缺失或非字符串值规范化为 `None`。 |

这些函数不对外承诺兼容性。特别是 `_remote_urls` 的结果只用于保守肯定，URL 不相等
不会产生“不同仓库”结论。

## 4. 副作用、失败与并发

- 只执行本地、非交互 Git 读取和文件存在性检查；不写文件、state 或 Git index。
- 不获取模块自己的锁。relation 是调用时刻快照；并发 commit/open 可能在下一命令改变
  结果，上层不得把建议当作长期租约。
- Git probe 非零不会抛业务失败，而是 unknown；这保证提示增强不会阻断原有工作流。
- `records` 的读取和锁由 `MaintenanceService`/`StateStore` 负责；本模块不扫描全局 state。
- remote URL 读取可能继承本地 Git 配置，但不会访问 remote 或凭据提供器。

## 5. 典型调用

```python
from pathlib import Path

from whero.doctidex.git.relations import maintenance_reuse, repository_relation

root = Path("/workspace/docs")
commit = "a" * 40
relation = repository_relation(root, "/workspace/docs", commit)
reuse = maintenance_reuse(
    root,
    "/workspace/docs",
    commit,
    relation,
    records=[],
    target_branch="main",
    root_branch="main",
)
```

上层只消费返回 object，不应调用内部 helper 或向 Skills 暴露判断证据。

## 6. 测试证据与限制

`tests/test_git_plugin.py` 覆盖本地路径自引用的同/different commit、SCP remote 与显式
本地路径歧义、nested root 保守 unknown、普通外部 source unknown、已有同 source/base
commit maintenance root 的复用建议，以及已知 branch 冲突。当前不会识别语义等价但
文本不同的 remote URL、镜像或 fork；详见
[当前限制](known-limitations.md#3-git-就绪与-source)。
