# 需求 0002-06：`worktree` 命令簇工作流与生命周期设计

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-06` |
| 状态 | `draft` |
| 日期 | 2026-08-09 |
| 来源 | 用户要求按命令簇设计 worktree 背后的模型交互工作流及生命周期 |
| 父需求 | [需求 0002：设计 doctidex-git 命令行工具 v2.x.x](overview.md) |
| 关联子需求 | [需求 0002-01：CLI 命令行参数及返回结果结构设计](01-cli-arguments-results.md)、[需求 0002-02：设计 doctidex-git 工作模型](02-working-model.md)、[`boundary-set` 命令簇工作流与生命周期设计](03-boundary-set.md) |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 影响范围 | `Worktree`、`CacheStore`、`RuntimeStore`、work-path 和派生 `BoundaryPoint` |
| 文档性质 | 子 Requirement；仅记录工作流与生命周期设计，不授权实现 |

## 1. 需求意图

定义 `worktree` 命令簇如何创建、移除和查询多仓库工作区，明确 `Worktree` 与 Installation、
CacheStore、RuntimeStore 及 `worktree` 类型 BoundaryPoint 的交互关系。

## 2. 设计依据

- 子命令、参数和返回结构以 [需求 0002-01](01-cli-arguments-results.md) 为准。
- `Worktree`、`CacheItem`、RuntimeStore 事务和工作区目录以 [需求 0002-02](02-working-model.md) 为准。
- `work-path` 派生 `worktree` 类型 BoundaryPoint，且不单独写入 tracked 文件；规则以
  [需求 0002-03](03-boundary-set.md) 为准。

## 3. 状态和持久化交互

| 数据 | 状态 | 权威持久化来源 | 派生边界点 |
|---|---|---|---|
| `Worktree` | 始终 untracked | `runtime.json` | `work-path` 派生 `worktree` 点 |
| worktree 工作文件 | Git ignored 目录中的实际工作区 | `work-path` 对应文件系统目录 | 不单独持久化边界记录 |
| `Installation` | 仅在使用 `--install-id` 时被读取 | `imports.json` 或 `runtime.json` | 不因 worktree 创建额外安装记录 |
| `CacheItem` | 全局缓存记录 | CacheStore 的 `status.json` | 无 |

`Worktree` 的 `url` 始终记录其外部 Git 仓库 URL，`base-commit-hash` 记录创建时实际使用的基准
commit。使用已有 Installation 创建时，同时记录对应的 `install-id`，并使用该 Installation 已记录的
commit；直接使用 `--url` 创建时不创建 Installation，`install-id` 省略。该基准不跟踪 worktree 内后续的
提交变化。

## 4. 命令工作流

### 4.1 `worktree create`

1. 根据通用 `--repos-path` 恢复当前 Git root 的 RuntimeStore。
2. `--install-id` 与 `--url` 必须且只能选择一个：
   - 使用 `--install-id` 时，从 RuntimeStore 查找 Installation，并以其 Git URL 和已记录的
     `commit-hash` 创建 Worktree，写入同值的 `base-commit-hash`；在创建前按
     [需求 0002-08](08-store-transactions.md) 确保该 commit 在 bare repository 中可用，缺失时仅按
     该 hash 获取并复验；
   - 使用 `--url` 时，`--branch`、`--tag` 与 `--commit` 必须且只能选择一个。通过 CacheStore
     获取或恢复该 Git URL 的 bare repository；branch 或 tag 先与远程同步并解析为 commit，commit
     则获取并确认所指定的 Git object。创建前仍按需求 0002-08 的目标 commit 流程复验。
3. 确定 `work-path`：显式 `--work-path` 直接作为工作路径；否则以来源 Git URL 派生默认根目录
   `/.doctidex-git/worktrees/<domain>/<repository-path-without-.git>/`，再追加 `--tree-name`。未提供
   `--tree-name` 时，以长度近似 GitHub 展示 commit hash 的短随机标识作为末级目录名；仅在此未提供
   `--tree-name` 和 `--work-path` 的随机命名情形，若该随机路径已被工作模型记录或对应物理路径已存在，
   则重新生成，直至取得未冲突的路径。`--tree-name` 可包含 `\`，其中的 `\` 按目录分隔符解释；它
   只参与默认路径的派生。
4. 用户提供的 `--work-path` 或 `--tree-name` 所确定的 work-path 已存在、发生路径冲突或无法创建时，
   命令直接报错，不自动重命名。
5. 如果 `work-path` 不位于 `.doctidex-git/worktrees/` 下，将该 `work-path` 加入当前 Git root 的
   `.gitignore`。
6. 在仍持有 GitCache transaction 时，以已确认可用的最终 commit 创建 detached Git worktree 工作区。
7. 创建并写入 `Worktree`，保存 Git URL、基准 commit、可选 install-id 及 work-path；由 work-path
   派生 `worktree` 类型 BoundaryPoint，该边界点不单独写入文件。
8. 提交 RuntimeStore 事务并返回需求 0002-01 定义的成功结果。

创建的 Worktree 始终为 untracked，不能通过 `boundary-set remove` 或其他 tracked 投影改变其
状态。

### 4.2 `worktree remove`

1. 根据 `--work-path` 在 RuntimeStore 中查找 Worktree；没有对应记录时不报错，直接返回成功。
2. 若已有记录的 worktree 工作目录已缺失，不报错，继续清理对应的模型状态；否则尝试移除 Git
   worktree 工作区。
3. worktree 存在未提交修改或 Git worktree 状态异常时，未提供 `--force` 则报错；提供 `--force`
   时强制移除。
4. 如果该 `work-path` 不位于 `.doctidex-git/worktrees/` 下，从当前 Git root 的 `.gitignore` 中
   删除由本命令加入的 `work-path` 规则。
5. 从 `runtime.json` 的 Worktree 集合移除该记录。
6. `worktree` 类型 BoundaryPoint 随状态重建消失。
7. 提交事务并返回通用成功结果。

### 4.3 `worktree query`

1. 根据 `--work-path` 读取并重建 RuntimeStore。
2. 查询对应的 Worktree 元信息，不修改任何 Store、工作文件或 BoundaryPoint。
3. 返回需求 0002-01 定义的查询结果；由 Installation 创建的 Worktree 返回 `install-id`，
   由 URL 直接创建的 Worktree 省略该字段。

## 5. `Worktree` 生命周期

| 阶段 | 进入方式 | 状态来源 | 退出或转换 |
|---|---|---|---|
| 不存在 | 尚未创建或已移除 | 无 | `worktree create` 创建 |
| 已创建 | `create` 成功建立工作区并提交记录 | `runtime.json` 和 work-path | `query` 读取；`remove` 移除 |
| 工作目录缺失 | Worktree 记录存在但 work-path 已不存在 | `runtime.json` 仍是记录来源 | `remove` 可无错误清理记录、边界点和自定义 ignore 规则 |
| 脏工作区或状态异常 | worktree 存在未提交修改或 Git worktree 状态异常 | `runtime.json` 和 Git worktree 状态 | `remove` 默认报错；`remove --force` 强制移除 |
| 已移除 | `remove` 成功提交 | 无 Worktree 记录 | 不再派生 BoundaryPoint |

Worktree 的生命周期不改变其关联 Installation 的生命周期；移除 Worktree 不移除或修改关联的
Installation。

## 6. 与其他模型的交互

- 使用 `--install-id` 创建时，Worktree 读取 Installation 的 `git-url` 和 install-id，但不复制或
  移动 Installation 的 install-path，并以其已记录的 commit 创建 Worktree。bare repository 缺少该
  commit 时，按共享目标 commit 流程仅以该 hash 获取；不重新解释 Installation 的 branch/tag。
- 使用 `--url` 创建时，Worktree 通过 CacheStore 使用缓存对象，将选定的 branch、tag 或 commit
  解析为最终 commit 后创建；缓存记录不因 Worktree 的创建或移除自动删除。
- `work-path` 创建成功后自动形成 `worktree` 类型 BoundaryPoint；移除 Worktree 后该派生点消失。
- 默认 `work-path` 位于 `/.doctidex-git/worktrees/<domain>/<repository-path-without-.git>/<tree-name>`；
  该目录按工作模型规定被 Git ignore。每一层保留 Git URL 的 repository path，避免不同仓库路径产生
  相同的默认位置；不在默认目录下的 `work-path` 在创建时加入 `.gitignore`，并在移除时删除由本命令
  加入的规则。

## 7. 已确认的通用处理规则

URL 来源的 `worktree create` 必须提供且只能提供一种 revision selector；branch、tag 和 commit 不能与
`--install-id` 一起使用。branch 或 tag 的选择仅用于本次创建时解析基准 commit，Worktree 记录保存该
base commit 供后续 repair 使用，而不保存会随远程变化的 selector，也不跟踪 worktree 后续提交。仅未指定
`--tree-name` 和 `--work-path` 的随机默认路径可在冲突时重试；用户指定的 `--tree-name` 或 `--work-path`
发生路径冲突或无法创建时，`worktree create` 直接报错。`worktree remove` 的未记录路径或工作目录缺失不构成错误；未提交修改
或 Git worktree 状态异常时，只有指定 `--force` 才可以强制移除。所有 `worktree create` 来源均在创建
Git worktree 前遵守需求 0002-08 的目标 commit 可用性流程；`--install-id` 已记录的 commit 无法获取或
复验时，返回 `worktree.source.unavailable`；`--url` 的 selector 无法取得目标 commit 时仍返回
`revision.unresolvable`。实现中，`--install-id` 也作为 `install-id` 类型的来源 selector 传递到该检查和
诊断构建流程，因此两类来源均不会出现空 selector。两者均不误报为 work-path 冲突。

URL 来源的 branch/tag 在当前 GitCache 事务中只解析一次，得到本次 `base-commit-hash` 后才进入可重试的
RuntimeStore 创建操作。该操作报告 `repair-required` 时，协调器复用当前 GitCache Write 事务运行 repair，随后以
同一个 `base-commit-hash` 重试。若当前为 GitCache ReadOnly 事务，必须先退出后再以 GitCache Write 事务运行
repair，并在重试时重新取得缓存；不得重新同步远程或重新解析 selector。Installation 来源本就以记录的
`commit-hash` 作为固定的 `base-commit-hash`。

## 8. 受影响的产品表面

| 表面 | 需要定义的内容 | 当前状态 |
|---|---|---|
| `worktree create` | Installation/CacheStore 来源选择、revision 解析、默认路径派生、工作区创建和 BoundaryPoint 派生 | 已定义；冲突或无法创建时报错 |
| `worktree remove` | 工作区删除、RuntimeStore 更新和边界点移除 | 已定义；缺失清理与 `--force` 规则已明确 |
| `worktree query` | RuntimeStore 查询和可选 install-id 返回 | 已定义 |
| Worktree 生命周期 | 创建、运行、失效和移除 | 已定义 |

## 9. 依赖与验收标准

- 父需求：[需求 0002](overview.md)。
- CLI 契约：[需求 0002-01](01-cli-arguments-results.md)。
- 工作模型：[需求 0002-02](02-working-model.md)。
- `boundary-set`：[需求 0002-03](03-boundary-set.md)。
- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。

- [x] `create`、`remove`、`query` 的 Store 交互和 BoundaryPoint 派生规则已记录。
- [x] Worktree 的 untracked 状态、持久化来源和主要生命周期已记录。
- [x] `--install-id` 与 `--url` 两种来源路径、URL revision selector 和最终 commit 的模型交互已记录。
- [x] 默认及自定义 `work-path` 的 Git ignore 创建、移除规则已记录。
- [x] URL 层级默认 work-path 和 `--tree-name` 的派生规则已记录。
- [x] 工作区冲突、缺失清理和异常移除规则已明确。
- [x] URL 与 Installation 两类创建来源的目标 commit 检查、按 hash 获取和错误转换规则已统一记录。
- [x] 设计与 CLI 契约、工作模型及 Architecture 的一致性已完成审阅。

## 10. 实施与状态

本子需求目前为 `draft`。设计内容已与 CLI 契约、工作模型及相关命令簇完成一次同步；获得明确
批准前，不授权修改 CLI 实现、测试或相关 Architecture 文档。
