# Agent 解读指南

本篇说明 agent 应如何使用 `doctidex-git` 提供的客观信息。它不要求 agent 放弃自身的
文件读取、目录浏览、搜索、编辑或 Git 工具；CLI 只补充 doctidex 感知的范围、路径、
mount 和校验事实。

## 1. 基本心智模型

一次任务同时存在三类信息：

1. **文件现场**：文件内容、目录结构、Git diff，由 agent 使用原生工具直接观察；
2. **doctidex 客观结构**：根、负责 index、过滤边界、mount、有效 commit，由 CLI
   按固定规则计算；
3. **语义判断**：内容是否正确、index prose 是否充分、log 是否要更新、维护顺序，
   必须由 agent 阅读后形成。

CLI 不使用 AI。不要把 `semantic_candidates` 当成 CLI 已经作出的语义结论，也不要
因为 CLI 未返回候选就跳过任务所需的内容审阅。

## 2. 每次读取 payload 的顺序

建议按以下顺序理解 JSON：

1. 看 `status` 和进程退出码，判断操作是否完成；
2. 看 `operation`，选择对应 schema，尤其确定 `changed` 的类型；
3. 看 `result`，确认哪些结果仍可使用；
4. 对 `check`/`handoff` 分别读 `protocol_structure`、`semantic_review`、
   `plugin_readiness`；
5. 读 `findings` 和 `semantic_candidates`，不要混为一类；
6. 查看 `collection`，确认列表是否截断；
7. blocked 时读 `affected`、第一个 finding 的 `code/actions` 和 `requires_user`。

字段缺失、`null`、空数组含义不同：

- **缺失**：该 operation 没有该字段或条件未触发，例如普通 inspect 没有 `mount`；
- **`null`**：字段适用但当前未知/不存在，例如首次 prepare 前 effective commit；
- **空数组**：已计算且没有元素，或被 cursor 移到当前页之外；必须结合 collection。

## 3. 选择根

任务开始可运行：

```bash
doctidex-git context PATH --json
```

- `status: ok`：使用返回的 `root/index`；
- `status: warning, root: null`：当前位置没有 doctidex 根。只有任务要求创建/接管时才
  进入 init；普通读取仍可使用原生工具；
- `root_ambiguous`：不要猜最近根。根据用户任务或明确路径重试；信息不足时询问用户。

`context.mode` 只是路径提示，不是访问权限。实际 mount 来源和边界以 `inspect` 的
PathContext 为准。

## 4. 自由读取与结构辅助

普通文件读取不需要先调用 CLI。建议在以下场景调用 `inspect`：

- 需要知道哪个 index 负责当前路径；
- 需要找最近 log 或确认 protected/excluded/atomic；
- 不确定路径是否已进入 mount；
- 需要读取负责 index 的 machine-parsable links 或语义候选。

理解 `path_context`：

- `host_scope: included`：路径属于宿主的协议与维护范围；
- `host_scope: excluded`：不由宿主 index/log 维护。它仍可为理解仓库而读取；
- `source: mount`：host 视角下只读，内容维护应转到 maintenance root；
- `attributes` 是集合而非单一状态；`protected` 表示写入需要明确用户方向，不妨碍
  读取；`atomic` 表示整体索引单元，不禁止检查内部文件。

`responsible_index`/`applicable_log` 是推荐导航事实。agent 可以先读它们缩小范围，也
可以在内容不足时直接扩大原生搜索，不需要 CLI 授权。

## 5. 内部路径与 mount 路径

`resolve` 接受 doctidex 绝对内部路径，不接受任意文件系统绝对路径。返回的：

- `internal_path`：已处理 `.`、`..` 和不可嵌套 namespace；
- `link_root`：当前所选宿主根；
- `working_path`：交给原生文件工具的路径；
- `crosses_mount/mount`：是否需要 lazy mount。

当文档路径含 mounted source 内的第二个 `/.doctidex/mounts` 时，不要按物理目录层层
拼接猜测；先用 `resolve` 得到规范路径。

## 6. Lazy mount 决策

| mount state | 含义 | Agent 动作 |
|---|---|---|
| `not_prepared`, effective null | 声明存在，尚未解析 source commit。 | 只有任务必须读取时运行 prepare；可能需要网络/凭据。 |
| `not_prepared`, effective 非 null | 已知读取 commit，但 presentation 不在现场。 | 运行 prepare 恢复同一 commit，然后重试原生工具。 |
| `ready`, readable true | 当前有效 commit 已在逻辑路径可读。 | 直接使用原生工具。不要为了读取而 sync。 |
| `ready` 但目标文件不存在 | mount 本身可读，具体目标可能确实不在 source。 | 用原生工具调查 source 内容和 revision。 |

prepare 不是同步。branch/tag mount 即使远端有新 commit，普通读取仍使用当前
effective commit。只有用户明确要求检查或更新 revision 时才运行 sync。

## 7. 声明 revision 与有效 commit

始终区分：

- `declared_revision.kind/value`：根 index 的用户配置；
- `effective_commit`：当前可读快照；
- `remote_commit`：online check 刚解析出的 selector；
- `old_effective_commit/new_effective_commit`：sync 计划。

`mount list` 不访问远端，所以不能根据 list 宣称 branch/tag 已是最新。online check 的
`update_available: false` 在 effective commit 为 null 时只表示“没有可比较的当前
commit”，不表示远端不存在内容。

sync dry-run 可能联网，但不切换读取结果。apply 前向用户说明 old/new commit 和受影响
mount。失败时先看 `result`：有旧 commit 时应继续使用保留结果，而不是盲目重新 clone。

## 8. 修改宿主与挂载源

对 included 本地内容，agent 可以在宿主 root 内按授权编辑。不要通过
`/.doctidex/mounts/...` 修改 source：该路径是只读读取结果。

修改挂载源时：

1. `maintenance scope` 确认独立根；
2. mount 没有 base commit 时先 prepare；
3. `maintenance open MOUNT_PATH`；
4. 只在返回的 `maintenance_root/writable_root` 下编辑；
5. 使用 source 自己的根 index 和过滤边界；
6. 在该路径运行 check/changes；
7. `maintenance handoff MAINTENANCE_ROOT`；
8. 将 commit/push/merge/selector 更新作为独立用户授权动作；
9. Git 状态 clean 后才 close。

`target_branch` 只是建议交付到哪个 branch；maintenance root 实际为 detached HEAD。
不要把它误解为已在目标 branch 上提交。

## 9. 多根与批量结果

`maintenance scope` 中每个 item 是独立交付单位，拥有自己的 base commit、diff、校验
和 Git 动作。不要把 host 与 mounted source 的结果合成一个假想原子事务。

无路径的 mount prepare/sync 可能返回 batch：

- `completed_count` 表示成功项；
- `total_count` 表示目标数；
- `items` 保留每个完整成功或 blocked payload；
- 顶层 `findings` 只汇总失败；
- 顶层 `status: blocked` 不代表成功 items 被撤销。

逐项报告已保留结果和失败下一步，不应因为一个 source 失败而丢弃其他 root 的工作。

## 10. Check 三个结果域

### 10.1 `protocol_structure`

只表示当前实现检查到的确定性结构。`fail` 应先修复对应 error finding；但 `pass` 不
证明 link 目标存在、非标准 link 可解析或正文语义正确。

### 10.2 `semantic_review`

`required` 要求 agent 打开 candidate path、负责 index、适用 log 和 Git diff：

- 已有 prose 足够清楚时可以确认无需改动；
- 需要索引时由 agent 自己撰写说明和 link；
- 需要 log 时由 agent判断变化是否重要并撰写记录。

不要机械地为每个 candidate 生成条目；候选算法只识别 CommonMark link 的精确目标。

### 10.3 `plugin_readiness`

`blocked` 表示 Git mount 操作现场不安全，常见为根 `.gitignore` 未直接覆盖 namespace
或已有 tracked mount 内容。它不是 doctidex 协议 failure。处理 tracked 内容会改变
Git index，必须根据 `requires_user` 请求用户决定，不能自动 `git rm --cached`。

## 11. `changed`、计划与内部副作用

按 `operation` 解读：

- init/add/remove：`changed` 是 apply 后公开文件路径；`planned_changes` 仅 init 有；
- prepare/open/close：`changed: []` 不表示没有内部 cache/state/worktree 变化；
- sync：`changed` 是 boolean；
- batch：顶层 `changed: []`，逐项结果才有实际含义；
- Git changes 列表位于 `items` 或 `changes`，不是顶层 `changed`。

`network: false` 当前只由 init 和 mount add 明确返回。其他 payload 缺少 `network` 时，
不能推断离线；prepare、sync、online check 都可能访问 source。

## 12. 有界输出

任何列表都可能受 `--limit` 截断，包括 findings、actions、changes 和 batch items。
agent 应：

1. 检查 `collection` 是否存在；
2. 优先通过更精确 PATH/单 mount/单 maintenance root 缩小请求；
3. 需要下一页时原样使用 `next_cursor`；
4. 不因当前页没有某项就断言全量没有；
5. 不把 `--limit 1000` 作为默认，以免占满上下文。

当前 cursor 对 payload 中每个顶层列表使用同一 offset。对 handoff/check 等含多个顶层
列表的命令，分页前应分别记录 collection 统计，避免把一个 cursor 当成某个单独列表
的专属游标。

## 13. Blocked 与用户升级

遇到 `status: blocked`：

1. 不盲目重复同一命令；
2. 先说明 `result` 中仍可使用或已保留的结果；
3. 用 `code` 选择处理分支；
4. 执行安全、明确且在任务授权内的 `actions`；
5. `requires_user` 非 null，或 action 涉及 credentials、网络、revision 选择、tracked
   Git index、commit/push/merge/reset/删除时，直接向用户说明所需决定；
6. `unexpected_failure` 重试一次仍失败时，向用户报告 `diagnostic_id`，不要要求用户
   阅读实现源码。

人读 blocked 输出只有第一个 finding。批量或复杂检查必须读取 JSON 后再作决定。

## 14. 典型工作流

### 14.1 读取一个外部文件

```text
原生工具报告路径不存在
  -> resolve 内部路径
  -> mount.state == not_prepared
  -> mount prepare 精确 mount
  -> 原生工具重试 working_path
  -> ready 仍不存在才作为真实缺失调查
```

### 14.2 审阅维护结果

```text
maintenance handoff --json
  -> protocol_structure: 修确定性结构
  -> semantic_candidates: 阅读后判断
  -> changes: 用原生 Git diff 检查内容
  -> plugin_readiness: 与协议结论分开
  -> 请求用户授权 Git 交付动作
```

### 14.3 更新 branch mount

```text
mount sync PATH --dry-run --json
  -> 比较 old/new
  -> old == new: 不需要 apply
  -> old != new: 解释变更并获得授权
  -> mount sync PATH --apply --json
  -> 用原生工具验证逻辑 mount path
```
