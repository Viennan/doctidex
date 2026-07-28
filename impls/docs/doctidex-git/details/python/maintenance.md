# Maintenance 实现

`git/maintenance.py` 先为 host/mounted paths 提供可复用 scope 建议，再在明确需要隔离
时把 mounted source 的只读宿主入口转换成独立可写根，并聚合交付前事实。它落实
[mounted source 与多根工作流](../../architecture/workflows.md#8-维护-mounted-source)，
但不执行 commit、push、merge 或宿主 selector 更新。关系判断见
[Repository Relation](repository-relations.md)。

## 1. `MaintenanceService`

### 1.1 属性与依赖

| 属性 | 类型/含义 |
|---|---|
| `context` | 宿主 `RootContext`；所有 mount 分类以此为起点。 |
| `root` | 宿主 doctidex 根。 |
| `store` | 宿主 `StateStore`，保存开放维护根归属。 |
| `mounts` | 同一 context 的 `GitMountService`。 |

模块依赖 `inspect_path` 做 scope 分类，依赖 `git.relations` 生产 root/reuse facts，依赖
`SourceRepository` 建立/移除 worktree，并用 `git_status`、`validate_protocol` 和
`root_gitignore_status` 形成交付事实。

### 1.2 `scope(paths)`

输入是文件系统 `Path` 列表；空列表等价于宿主根。每个路径先由 `inspect_path` 分类：

- mounted path 以 `mount:<mount_path>` 去重，返回 `kind/mount_path/source/declared_revision/
  base_commit/target_branch/read_only_path/root_relation/maintenance_reuse/write_action`；
- 其他 path 统一以 `root:<host-root>` 去重，返回
  `kind/root/base_commit/target_branch/write_path/maintenance_reuse`。

宿主 base commit 与 branch 由 `relations.git_head/git_branch` 各宽容读取一次，失败为
`None`。mounted source base commit 来自与当前声明匹配的 effective record，也可以为
`None`；target branch 只在 selector 为 branch 时有值。recommended 时
`write_action=None`；多候选时为 status 命令；无兼容 scope 时为 open 命令。scope 不修改
用户内容、mount 选择或 `state.json`，也不联网；读取 state 时可能创建或使用内部目录与
lock 文件。它排除已知 branch 冲突，但不替 agent 判断权限、未知 branch 或完整交付意图。

`scope(paths)` 不保存调用者的维护计划，也不在 item 中记录待分配、已分配或完成状态。
同一工作流可以重复调用；每次都根据当时的输入、HEAD、effective record 和开放维护根
返回当前观察。调用者负责把一个或多个兼容 item 纳入最终写入范围，并在目标或现场变化
后复核该决定。

最终写入范围的执行边界不由 `MaintenanceService` 持久化或强制。调用模块必须把选定的
host root 或 maintenance root 作为编辑、校验、diff 和交付边界；通过其中的 mount 发现
其他 source 时，应重新调用 `scope`，不能把只读 mount path 当作写入范围的延伸。

### 1.3 `guidance(mount_path)`

读取 mount/effective commit、当前 root relation 和当前宿主开放 records，返回
`(root_relation, maintenance_reuse)`。`cli._resolve` 调用它，使 resolve、scope 和 open
使用完全相同的关系字段。方法不修改用户内容、mount 选择或 `state.json`，也不准备
mount、不联网；读取 records 时可能创建或使用内部 state 目录和 lock 文件。

### 1.4 `open(mount_path)`

要求 `GitMountService.effective()` 返回 commit，否则抛
`maintenance_source_not_prepared`。identifier 是秒级时间戳加 8 位随机 hex；
`SourceRepository.open_maintenance` 从 base commit 建立 detached worktree。

state record 的全部属性：

| 属性 | 含义 |
|---|---|
| `path` | worktree 绝对路径。 |
| `host_root` | 所属宿主；支持跨 cwd 反查。 |
| `mount_path` | 来源逻辑 mount。 |
| `url` | 原始 source identity。 |
| `base_commit` | 建立现场的 effective commit。 |
| `target_branch` | selector 为 branch 时的值，否则 `None`；只作交付提示。 |

open 在创建前计算 relation/reuse，随后仍建立新的公开 maintenance root。这使显式 open
保留隔离含义；若已有兼容 scope，结果为 warning 并在 next actions 中提示只保留一个
有意使用的 scope。state 保存失败发生在 worktree 创建之后时可能留下未登记现场，这是
当前非事务边界。

### 1.5 `status(maintenance_root)`

`_select` 从宿主 state 取 records；参数省略返回全部，提供时按 `absolute()` 精确匹配。
每项重新运行 Git porcelain，返回 record 字段以及 `state/change_count/changes`。

当前 path 已丢失时 `changes=[]` 且 state 显示 `ready`，属于已知限制。status 不验证
HEAD 是否仍等于 base commit，也不检查协议。

### 1.6 `handoff(maintenance_root)`

必须精确选中一项，否则 `maintenance_root_ambiguous`。它加载维护根自身 `index.md`，
构造新的 `RootContext` 并依次计算：完整协议 validation、Git changes、维护根 readiness、
语义候选。每个非 `index.md`/`log.md` change 追加 `git_change_review`。

handoff 返回独立的 `protocol_structure`、`semantic_review`、`plugin_readiness`，但当前
findings 只含协议 findings；readiness blocked 只体现在状态。它没有顶层 `root`，使用
`maintenance_root` 表示检查对象。

### 1.7 `close(maintenance_root)`

同样要求精确一项。任何 Git change 都抛 `maintenance_has_changes`，设置
`requires_user=git_action` 并保留路径。clean 时先调用 Git worktree remove，再删除 state
record；前者成功、后者失败会留下无效登记。

## 2. 典型模块调用

```python
from pathlib import Path
from whero.doctidex.git.maintenance import MaintenanceService
from whero.doctidex.protocol.tree import require_root

host = require_root(Path("/workspace/host"), operation="maintenance_scope")
service = MaintenanceService(host)
observations = service.scope([Path("/workspace/host/.doctidex/mounts/api/guide.md")])
item = observations[0]
reuse = item["maintenance_reuse"]
opened = service.open(item["mount_path"]) if reuse["status"] == "not_available" else None

# 编辑与 Git 动作由调用者完成。
if opened:
    handoff = service.handoff(Path(opened["maintenance_root"]))
```

包内调用应始终保存 open 返回的精确路径，不从内部目录命名推断 maintenance root。

## 3. 并发与生命周期

MaintenanceService 本身没有宿主级总锁。source worktree add/remove 由 source lock
串行，record update 由 state lock 串行；两步之间不是事务。不同 source 可以并行，
同一 source 会串行。relation/reuse、status/handoff 与外部编辑可能并发，因此它们只
表示命令观察时刻的 Git 现场，不构成 scope 租约。

关闭后不自动更新宿主 mount、branch 或 selector；调用者必须把 Git 交付和宿主同步
作为独立工作流。完整状态布局见 [Git Runtime](git-runtime.md#9-maintenance-root)。
