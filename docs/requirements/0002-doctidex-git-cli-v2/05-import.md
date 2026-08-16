# 需求 0002-05：`import` 命令簇工作流与生命周期设计

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-05` |
| 状态 | `implemented` |
| 日期 | 2026-08-09 |
| 来源 | 用户要求按命令簇设计 import 背后的模型交互工作流及生命周期 |
| 父需求 | [需求 0002：设计 doctidex-git 命令行工具 v2.x.x](overview.md) |
| 关联子需求 | [需求 0002-01：CLI 命令行参数及返回结果结构设计](01-cli-arguments-results.md)、[需求 0002-02：设计 doctidex-git 工作模型](02-working-model.md)、[`boundary-set` 命令簇工作流与生命周期设计](03-boundary-set.md) |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 影响范围 | `Installation`、`Ref`、`CacheStore`、`RuntimeStore`、import 文件和派生 `BoundaryPoint` |
| 文档性质 | 子 Requirement；仅记录工作流与生命周期设计，不授权实现 |

## 1. 需求意图

定义 `import` 命令簇如何操作 `Installation` 和 `Ref`，以及如何通过 `CacheStore`、`RuntimeStore`
维护 tracked/untracked 状态、安装文件、受管理引用和派生边界点。

## 2. 设计依据

- 子命令、参数、revision selector 和返回结构以 [需求 0002-01](01-cli-arguments-results.md) 为准。
- `Installation`、`Ref`、`CacheItem`、状态文件和事务规则以 [需求 0002-02](02-working-model.md) 为准。
- `install-path` 和受管理引用目标自动形成 `import`、`import-ref` 类型的 `BoundaryPoint`，其
  重建规则以 [需求 0002-03](03-boundary-set.md) 为准。

## 3. 状态和持久化交互

| 数据 | tracked 状态 | 权威持久化来源 | 派生边界点 |
|---|---|---|---|
| `Installation.tracked: true` | Git tracked 元信息；实际仓库文件可以不存在 | `imports.json` | `install-path` 派生 `import` 点 |
| `Installation.tracked: false` | Git ignored 运行时数据 | `runtime.json` | `install-path` 派生 `import` 点 |
| `Ref` | 全部 Git tracked | `import-refs.json` | `target-dir` 派生 `import-ref` 点 |
| 安装仓库文件 | Git ignored | `install-path` 对应文件系统目录 | 不单独持久化边界记录 |

所有会修改 Installation 或 Ref 的子命令都在 `RuntimeStore` 事务中完成；需要访问或恢复外部
Git object 时，通过 `GitCache` 提供的只读或写事务访问缓存。`GitCache` 事务内部协调
`CacheStore` 状态和 bare repository 的加载；tracked 文件仅保存其负责的部分，`runtime.json`
不重复保存已投影数据。CacheStore/GitCache 事务不是数据库事务，不对 Git object 的追加写入提供
回滚保证。`import install` 与 `import restore` 选择到 cache repository 后，revision 同步/解析和
install-path 的 Git worktree 操作都在同一个 GitCache 事务内完成；需要同时修改 RuntimeStore 时，
在该 GitCache 事务内再打开 RuntimeStore 写事务，锁顺序固定为 `GitCache -> RuntimeStore`。

`import install` 使用 branch 或 tag 时，在进入其 RuntimeStore 写操作前，将本次选择解析为一个具体
`commit-hash`。如果该 RuntimeStore 操作报告需求 0002-08 的 `repair-required`，命令协调器在当前
GitCache Write 事务内运行 repair 后重试该操作。若当前为 GitCache ReadOnly 事务，必须先退出后再以
GitCache Write 事务运行 repair，随后重新取得缓存。无论哪种缓存路径，重试复用已解析的 `commit-hash`，
不得重新同步远程或重新解析 branch/tag。`--commit` 直接提供固定 hash；`restore` 固定使用 Installation 已记录的
`commit-hash`，两者同样不发生重新选择。

### 3.1 install-path 统一准备流程

`import install` 和 `import restore` 对目标 `install-path` 使用同一套准备流程。该流程在持有当前
GitCache 事务并已确定目标 Git URL、目标 commit 后执行；它负责判断目标路径的既有物理状态和 Git
worktree 状态，并返回“可直接复用”或“需要重新创建”的结果。两个命令不得分别实现一套路径占用和
worktree 判断逻辑。

1. 目标路径不存在时，返回“新建”结果，由调用方创建目标 commit 的 Git worktree。
2. 目标路径存在时，先判断其是否为 Git 控制的 worktree，并读取该 worktree 对应的 Git URL。
3. 目标路径不受 Git 控制时，按不完整或未完成的安装状态处理：删除该路径，再返回“重新创建”结果。
   该分支包含空目录以及已留下但尚未成功建立 Git worktree 的残缺目录。
4. 目标路径受 Git 控制但对应 Git URL 与目标 URL 不同，返回
   `installation.target.unavailable`；不得删除或覆盖该 worktree。
5. 目标路径受 Git 控制且对应 Git URL 相同时，继续检查 worktree 是否处于 detached 状态，以及是否
   没有新增改动：
   - 两项均满足时，返回“复用”结果；调用方在现有 worktree 上切换到目标 commit，继续完成本次
     Installation 操作，不删除并重新创建目录。
   - 任一项不满足时，删除现有 worktree，再返回“重新创建”结果。
6. “新增改动”以 Git worktree 当前工作状态为准；存在未提交内容或其他使工作区不再干净的状态时，
   不得复用该 worktree。
7. 对“重新创建”结果，调用方仅在既有 worktree 已被移除后创建目标 commit 的新 worktree；对“复用”
   结果，不重复创建同一路径的 worktree。

该流程只决定既有 install-path 的物理处理方式，不改变 `install` 的 revision selector 解析、
`restore` 对已记录 commit 的严格使用、Installation 元信息更新或 Ref 关系保留规则。

### 3.2 Git worktree 目标 commit 准备

`install` 创建 install-path 的 Git worktree，以及 `restore` 创建或复用 install-path 前，均遵守
[需求 0002-08](08-store-transactions.md) 定义的目标 commit 可用性流程。`install` 的 branch、tag 或
commit selector 解析会取得目标 object；`restore` 则必须先检查 bare repository 是否已有 Installation
记录的 `commit-hash`，缺失时仅按该 hash 获取并复验，不重新同步或解析 Installation 的 branch/tag。

目标 commit 无法取得或复验时，`install` 按 revision selector 的 `revision.unresolvable` 失败；`restore`
使用 `installation.restore.unavailable`，并提供 Installation 的 `install-id`、`install-path` 与保存的
`commit-hash`。不得将此情形转换为 install-path 路径占用或 worktree 创建冲突。

## 4. 命令工作流

### 4.1 `import install`

1. 按 `--url` 在 GitCache ReadOnly 事务中查询 bare Git repository。命中时保持该 ReadOnly 事务；
   未命中时先退出，再在 GitCache Write 事务中 `load` repository，并保持该 Write 事务。后续步骤
   均在所选 GitCache 事务内执行。
2. `--branch`、`--tag`、`--commit` 是恰好选择一种的 revision selector。branch 安装先从远程同步
   指定 branch，tag 安装先从远程同步指定 tag，并分别解析当前指向的 commit hash；commit 安装按给定
   hash 获取所需 Git object。
3. 对 branch 或 tag selector，若已有同一 Git URL、同一 selector 且记录 commit hash 与当前 commit
   相同的 Installation，保留该 Installation 元信息；当前 commit 不同时，后续以新 Installation 替换
   旧记录。对 commit selector，若已有同一 Git URL、同一 commit hash 的 Installation，同样保留其
   元信息；否则继续安装。上述元信息复用不跳过第 3.1 节的 install-path 准备流程。
4. 在仍持有 GitCache 事务时打开 RuntimeStore 写事务，根据 Git URL 和 selector 派生语义化
   `install-path`，并调用第 3.1 节的统一 install-path 准备流程。若结果为“复用”，在现有
   worktree 上切换到指定 commit；若结果为“新建”或“重新创建”，使用 bare Git repository 在该路径
   创建指定 commit 的 Git worktree。路径位于 `/.doctidex-git/imports/<Domain>/<Name>/<selector-value>`；
   branch 或 tag 值中的 `/` 保留为路径层级。
5. 若第 3 步保留既有 Installation，则直接返回该记录；否则创建新的 Installation，填充 tracked
   状态、Git URL、最终 commit hash、selector 对应的 branch 或 tag、`install-id`、`install-path` 和
   query keys。统一 install-path 流程不改变 Installation 元信息的保留或替换语义。
6. 将 tracked install 的元信息写入 `imports.json`，untracked install
   写入 `runtime.json`。
7. 由 `install-path` 派生 `import` 类型的 `BoundaryPoint`，不在边界文件中另行记录。
8. 提交事务并返回需求 0002-01 定义的安装结果。

### 4.2 `import restore`

1. 在 RuntimeStore 中按 `install-id` 查找 tracked `Installation`；该查询在继续前结束，untracked
   install 不适用本命令。
2. 按 Installation 中保存的 Git URL 选择 GitCache ReadOnly 或 Write 事务。若 ReadOnly 未命中，
   必须先退出并在 Write 事务中加载；严格使用记录的 `commit-hash`，不重新同步或解析 branch、tag。
3. 在持有 GitCache 事务时打开 RuntimeStore 写事务，重新读取 Installation，按第 3.2 节确保其记录的
   `commit-hash` 在 bare repository 中可用，再调用第 3.1 节的统一 install-path 准备流程。目标 commit
   使用已记录的 `commit-hash`：若结果为“复用”，在现有 worktree 上切换到该 commit；若结果为“新建”
   或“重新创建”，按该 commit 重新创建 install-path 对应的 worktree。Installation 元信息保持不变。
4. 重新由 install-path 派生 `import` BoundaryPoint，并提交 RuntimeStore 事务。
5. 返回与 `import install` 一致的安装结果。

`restore` 解决 tracked install 只跟踪元信息而实际 install-path 不存在的情况，不创建新的
Installation 或 install-id。

### 4.3 `import track`

1. 在 RuntimeStore 中按 `install-id` 查找 Installation。
2. 若 Installation 已为 tracked，不修改 Installation、状态文件、安装文件或 BoundaryPoint，直接
   返回与 `import install` 一致的成功结果。
3. 若 Installation 为 untracked，将其 `tracked` 改为 `true`；提交时写入 `imports.json`，并从
   `runtime.json` 的未跟踪 Installation 集合移出。
4. 安装文件和 install-path 不因 track 操作被重新安装或移动；其 `import` BoundaryPoint 继续由
   Installation 派生。
5. 返回与 `import install` 一致的安装结果。

### 4.4 `import remove`

1. 在 RuntimeStore 中依据 `--install-id`、`--untracked` 或 `--auto` 解析移除选择器。指定的
   `install-id` 不存在或选择器未选中任何 Installation 时，成功 no-op。
2. 对每个选中的 tracked Installation，使用父需求定义的共享领域工具，以完整 boundary-set 视图扫描
   当前 doctidex 目录树范围内的 Markdown 文件，找出直接跨越 Installation 的 `import` BoundaryPoint，
   或跨越其关联 Ref 的 `import-ref` BoundaryPoint 的 link；两类 link 都关联到该 Installation。
3. 对每个选中的 tracked Installation，校验不存在上述 Markdown link，且不存在 `Ref.install-id` 等于该
   Installation 的 Ref；Ref 的实际符号链接是否存在不影响该关系校验。
4. 任何阻塞项存在时，命令以 `installation.remove.blocked` 失败，不删除任何已选择的 Installation、
   Ref、安装目录或状态记录。
5. 通过校验后，从对应的权威状态来源移除选中的 Installation：tracked install 从 `imports.json`
   移除，untracked install 从 `runtime.json` 移除。
6. 移除安装产物对应的实际文件和 install-path；由该 Installation 派生的 `import` BoundaryPoint
   随状态重建消失。
7. 提交 RuntimeStore 事务并返回通用成功结果。

`--auto` 选择所有 untracked install，以及所有未被仓库内文件建立受管理引用的 install；具体
选择规则以需求 0002-01 为准。

### 4.5 `import ref`

1. 在 RuntimeStore 中按 `install-id` 查找 Installation；若其为 untracked，先将其提升为 tracked。
2. 根据 Installation 的 install-path 和可选 `src-sub-dir` 确定引用源。
3. 在 `target-dir` 创建受管理引用（文件系统符号链接）。符号链接文本必须是从 `target-dir` 的父目录
   到已验证 source 的相对路径；创建 `Ref` 并写入 `import-refs.json`。
4. 由 `target-dir` 派生 `import-ref` 类型的 `BoundaryPoint`。
5. 提交 RuntimeStore 事务并返回通用成功结果。

### 4.6 `import unref`

1. 在 RuntimeStore 中按 `target-dir` 查找对应 Ref。若不存在，则成功 no-op，不扫描 Markdown link、
   不修改文件系统或 RuntimeStore。
2. 若 Ref 存在，使用共享领域工具扫描当前 doctidex 目录树范围内的 Markdown 文件。若任一 link 的第一个跨越点是
   该 Ref 的 `import-ref` BoundaryPoint，命令以 `ref.remove.blocked` 失败，不修改符号链接或 Ref 记录。
3. 移除目标位置的受管理引用和 `Ref` 记录。
4. 提交时更新 `import-refs.json`；对应的 `import-ref` BoundaryPoint 随状态重建消失。
5. 返回通用成功结果。

### 4.7 `import query`

1. 在 RuntimeStore 中读取 tracked 文件与 `runtime.json`，重建完整 Installation 和 Ref 集合。
2. 按唯一选择器 `install-id`、`install-path`、`ref-path` 或一个或多个 query key 筛选候选项。按 key
   查询是该命令私有的用户模糊搜索：任一 Installation key 包含任一输入 key 即匹配；结果先按匹配 key
   数量、再按精确匹配 key 数量降序排列，同分时保持工作模型稳定顺序。
3. 查询不修改 CacheStore、RuntimeStore、安装文件或边界集合。
4. 返回需求 0002-01 定义的 `candidates` 结果；候选项字段和 Ref 内容以该返回结构为准。

## 5. 模型生命周期

### 5.1 `Installation`

| 阶段 | 进入方式 | 退出或转换 |
|---|---|---|
| 不存在 | 尚未安装或已移除 | `import install` 创建 |
| untracked | `install --untracked` 创建，或由运行时恢复 | `import track` 或 `import ref` 提升为 tracked；`remove` 移除 |
| tracked | `install --tracked` 创建，或由 `track`/`ref` 提升 | `track` 再次执行 no-op；`restore` 恢复实际文件；`remove` 移除 |
| 文件待恢复 | tracked 元信息存在但 install-path 不存在 | `restore` 重新安装文件；元信息保持不变 |
| 已移除 | `remove` 成功提交 | 不再由 RuntimeStore 恢复或派生边界点 |

branch 或 tag selector 再次安装时，当前远程 commit 与同 selector Installation 的记录相同则保持其
生命周期状态；不同则删除旧 Installation 并重新进入相应的 untracked 或 tracked 状态。commit selector
再次安装命中同一 Git URL、同一 commit hash 的 Installation 时保持其生命周期状态。

### 5.2 `Ref`

`Ref` 在 `import ref` 成功提交后进入活动状态，由 `import-refs.json` 权威保存；`import unref`
成功提交后移除其记录、受管理引用和派生 `import-ref` BoundaryPoint。

### 5.3 关联约束

- `Ref.install-id` 必须对应当前 RuntimeStore 中的 Installation。
- 受管理引用创建会将对应 Installation 提升为 tracked；该转换不改变其 install-id、install-path
  或 commit hash。
- Installation、Ref 的边界点均为派生数据，不通过 `boundary-set add/remove` 直接管理。

## 6. 前置校验与错误处理

本节定义 `import` 命令簇在修改模型或文件系统前必须完成的校验，以及失败时使用的语义化错误。
错误码、`message.subject` 和 `message.details` 的公共结构以 [需求 0002-01](01-cli-arguments-results.md)
第 9.3 节为准。本节不直接返回未经解释的 Git、文件系统或 JSON 解析错误。

### 6.1 共同前提和失败边界

所有 `import` 子命令先解析 Git root 并读取 RuntimeStore。工作模型未初始化、无法建立事务或
重建时发现模型违规，分别返回 `work-model.uninitialized`、`store.transaction.unavailable` 或
`work-model.invalid`，且不继续执行该子命令的业务操作。

需要写入 Installation 或 Ref 的子命令，在所有可预先判断的选择、关系、来源和目标校验通过前，
不得写入 `imports.json`、`import-refs.json` 或 `runtime.json`，也不得创建、移除或替换受管路径。
校验失败后不提交本次状态变更。命令运行中出现的外部 Git、缓存或文件系统故障，必须转换为
本节相应的领域错误；只有 Store 的状态读取、写入或事务锁无法使用时，才使用
`store.transaction.unavailable`。

`import query` 只读取模型。任何选择器没有候选项都是成功结果，返回空 `candidates`；它不使用
`installation.not-found`。

### 6.2 Installation、revision 和来源校验

| 子命令 | 必须成立的前提 | 不满足时的错误 |
|---|---|---|
| `install` | 必须恰好提供一种 revision selector。branch 或 tag 必须能从远程同步并解析为当前 commit；commit 必须能获取为指定 Git object。 | selector 不存在或无法解析为 `revision.unresolvable`。 |
| `install` | CacheStore 能取得或恢复该 Git URL 对应的 bare repository；按 Git URL 和 selector 派生的安装路径可用于本次 Installation；既有 install-path 按第 3.1 节统一流程可复用、移除重建或明确拒绝。 | 缓存不可用为 `cache.repository.unavailable`；既有路径由不同 Git URL 控制为 `installation.target.unavailable`；统一流程无法完成所选复用或重建操作时，使用对应的 Installation 目标错误。 |
| `restore` | 指定 `install-id` 存在且为 tracked Installation；恢复严格使用其保存的 `commit-hash`，并按第 3.2 节确保 bare repository 包含该 commit；既有 install-path 按第 3.1 节统一流程可复用、移除重建或明确拒绝。 | Installation 不存在为 `installation.not-found`；状态不是 tracked 为 `installation.tracking-state.invalid`；无法取得对应 bare repository 为 `cache.repository.unavailable`；保存的 commit 无法获取或复验、不同 Git URL 控制既有路径或统一流程无法完成目标操作为 `installation.restore.unavailable`。 |
| `track` | 指定 `install-id` 存在。untracked Installation 被提升为 tracked；已 tracked Installation 成功完成 no-op。 | Installation 不存在为 `installation.not-found`。 |
| `ref` | 指定 `install-id` 存在。若其为 untracked，只有在后续来源与目标校验均可通过时，才在同一提交中提升为 tracked。 | Installation 不存在为 `installation.not-found`。 |

对 `install` 而言，branch 或 tag selector 必须先同步远程引用，并以其当前 commit 与同一 Git URL、
同一 selector 的 Installation 比较。commit 相同时保留 Installation 元信息；不同则以新的 Installation
替换旧记录。commit selector 命中同一 Git URL、同一 commit hash 的 Installation 时同样保留其元信息；
未命中时获取 Git object 并安装。无论 Installation 元信息是否复用，目标路径统一按第 3.1 节判断：
非 Git 控制路径删除后重建；不同 Git URL 控制的 worktree 返回
`installation.target.unavailable`；同源且 detached、无新增改动的 worktree 复用并切换到目标 commit，
其他同源 worktree 删除后重建。对 `restore` 而言，tracked Installation 缺少实际 `install-path` 是
预期的恢复场景，不构成错误；已有路径同样按第 3.1 节处理。对 `ref`
而言，Installation 的 `install-path` 和可选 `src-sub-dir` 必须已经是可用的实际引用源。tracked
Installation 尚未 restore 时，`ref` 不隐式恢复它，而是返回 `ref.source.unavailable`。

### 6.3 Ref、目标路径和移除校验

| 子命令 | 必须成立的前提 | 不满足时的错误 |
|---|---|---|
| `ref` | `target-dir` 不包含不相容内容，且能够建立指向已验证源的受管符号链接。 | `ref.target.unavailable`。 |
| `unref` | Ref 记录不存在时成功 no-op；存在时，目标位置仍是该 Ref 所记录的受管符号链接，且当前 doctidex 目录树没有 Markdown link 跨越该 Ref 的 `import-ref` BoundaryPoint。 | 链接不存在、不是预期符号链接或指向错误源为 `ref.target.inconsistent`；存在阻塞 link 为 `ref.remove.blocked`。 |
| `remove --install-id` | 指定 Installation 不存在时成功 no-op。 | 无。 |
| `remove` 选中的 tracked Installation | 不存在阻塞 link，且不存在关联 Ref。 | `installation.remove.blocked`。 |

移除 tracked Installation 或任意 Ref 前，工具通过共享领域工具基于完整 `boundary-set` 视图枚举当前
doctidex 目录树有效范围内的 Markdown 源文件，不进入任何 BoundaryPoint 后代。对每个本地 link，根据
其第一个跨越的 BoundaryPoint 关联模型对象：`import` 类型点关联其 Installation，`import-ref` 类型点
先关联 Ref，再关联该 Ref 的 Installation。即使 Installation 尚未 restore，也依据模型中的
`install-id`、`install-path` 和 Ref 记录完成关联，不恢复仓库文件或依赖实际 link 目标存在。指向
tracked Installation 的直接 link、通过其 Ref 的 link，均阻塞该 Installation 删除；指向 Ref 的 link
阻塞该 Ref 删除。

同时，任何 `Ref.install-id` 等于待移除 tracked Installation 的 Ref 都会阻塞移除，无论其受管符号链接
的实际工作目录是否存在。若同一命令选择多个 Installation，只要其中任一个存在阻塞项，命令不移除
任何选中 Installation，并在一次 `installation.remove.blocked` 错误中返回所有已发现的阻塞项。

该错误的 `details` 使用以下信息：

```jsonc
{
  "blocked-installations": [
    {
      "install-id": "<INSTALL-ID>",
      "install-path": "/<INSTALL-PATH>",
      "blocking-links": [
        {
          "path": "/<SOURCE-MARKDOWN-PATH>",
          "line": 42,
          "link-path": "<LINK-PATH>"
        }
      ],
      "blocking-ref-target-dirs": ["/<TARGET-DIR>"]
    }
  ]
}
```

`blocked-installations` 非空；其中每项的 `blocking-links` 和 `blocking-ref-target-dirs` 至少一个
非空。`blocking-links` 同时包含直接指向 Installation 和经其 Ref 指向的 link；其中 `path` 和
`blocking-ref-target-dirs` 均为仓库内部绝对路径，`line` 是 link 在源 Markdown 文件中的起始行号。
单个 `--install-id` 选择器的 `subject` 为该 Installation；`--untracked` 或 `--auto` 选择多个对象时，
`subject.kind` 为 `installation-selection`，具体被阻塞对象全部由 `details.blocked-installations` 表达。

`unref` 的 `ref.remove.blocked` 使用 `subject.kind: "ref"`、`subject.target-dir` 和
`details.blocking-links`。`blocking-links` 的每个元素同样包含仓库内部绝对 `path`、`line` 和
`link-path`；该数组非空时命令不得删除 Ref 记录或其受管符号链接。

`--untracked` 和 `--auto` 的选择语义以需求 0002-01 为准。它们选中的 tracked Installation 同样
使用本节阻塞检查；untracked Installation 不经过该 tracked 前置校验。物理 `install-path` 已缺失
的 tracked Installation 可以被移除，前提是不存在上述逻辑 link 或 Ref 关系。

### 6.4 完成移除和查询

通过第 6.3 节校验后，`remove` 才从各自权威状态来源删除 Installation，并移除仍存在的实际安装
文件。没有选中 Installation 时，`remove` 成功返回且不修改状态。tracked Installation 的实际
`install-path` 已缺失时，跳过文件删除但继续删除元信息和派生 `import` BoundaryPoint。`unref` 仅在
受管符号链接与 Ref 记录一致时才删除两者，避免删除用户已替换的路径。

`query` 的选择器没有匹配记录时不改变 Store 或文件系统，也不构成错误。选择器、路径格式或参数
互斥关系本身不成立时，仍按 CLI 契约返回 `argument.invalid` 或 `repository-path.invalid`。

## 7. 受影响的产品表面

| 表面 | 需要定义的内容 | 当前状态 |
|---|---|---|
| `import install/restore` | CacheStore、Installation 和 install-path 交互 | 已定义；revision、缓存、tracked 状态与目标冲突的错误映射已明确 |
| `import track` | untracked 到 tracked 的状态迁移、投影和已 tracked no-op | 已定义 |
| `import remove` | Installation、Ref、文件和 BoundaryPoint 的移除关系 | Installation 直接/经 Ref 的逻辑 link、关联 Ref 阻塞校验、错误详情和缺失路径处理已定义 |
| `import ref/unref` | Ref、符号链接和 `import-ref` 边界点 | 来源、目标与一致性前置校验、Ref link 阻塞和错误映射已定义 |
| `import query` | RuntimeStore 重建、筛选和只读返回 | 已定义 |
| Installation 生命周期 | 创建、tracked 转换、恢复和移除 | 已定义 |

## 8. 依赖与验收标准

- 父需求：[需求 0002](overview.md)。
- CLI 契约：[需求 0002-01](01-cli-arguments-results.md)。
- 工作模型：[需求 0002-02](02-working-model.md)。
- `boundary-set`：[需求 0002-03](03-boundary-set.md)。
- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。

- [x] 所有 import 子命令的 Store 交互、状态来源和派生边界点已记录。
- [x] `Installation`、`Ref` 的主要生命周期和 tracked 转换已记录。
- [x] `restore` 对 tracked 元信息与实际安装文件的关系已记录。
- [x] tracked Installation 的 link/Ref 移除前置校验和路径冲突处理已明确。
- [x] 各 import 子命令的 Installation、revision、来源、目标和关系校验及错误处理已展开。
- [x] `install` 与 `restore` 对 install-path 的 Git worktree 识别、同源复用、异源拒绝和重建规则已统一记录。
- [x] Git worktree 创建或切换前的目标 commit 检查、按 hash 获取及命令簇错误转换规则已与共享缓存事务设计对齐。
- [x] 设计与 CLI 契约、工作模型及 Architecture 的一致性已完成审阅。
- [x] Installation 直接/经 Ref 的 link 阻塞及 Ref 自身的 link 阻塞规则已补充，并与共享领域工具要求对齐。

## 9. 实施与状态

本子需求为 `implemented`。Installation、Ref、缓存协作、revision 固定和移除阻塞规则已实现，并由
phase 7 集成验收；当前行为以 user 与 Architecture 文档为权威说明。
