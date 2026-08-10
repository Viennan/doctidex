# 需求 0002-05：`import` 命令簇工作流与生命周期设计

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-05` |
| 状态 | `draft` |
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

- 子命令、参数、revision 组合和返回结构以 [需求 0002-01](01-cli-arguments-results.md) 为准。
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
Git object 时，在 `CacheStore` 事务中取得对应缓存。事务提交后，tracked 文件仅保存其负责的
部分，`runtime.json` 不重复保存已投影数据。

## 4. 命令工作流

### 4.1 `import install`

1. 根据通用 `--repos-path` 恢复 Git root 的 `RuntimeStore`，并按 `--url` 访问 `CacheStore` 中的 bare Git repository。
2. 按需求 0002-01 的 revision 选择规则解析 branch、tag 和 commit，得到最终 commit hash 及
   `is-auto-resolved-hash`。未指定 `--commit` 时，必须先从远程同步所指定的 branch 或 tag
   到本地 CacheStore，才能确定并写入最终 commit hash；此时将 `is-auto-resolved-hash` 设为
   `true`。显式指定 `--commit` 时该标记为 `false`。
3. 使用 CacheStore 的 bare Git repository，在 `install-path` 创建指定 revision 的 Git worktree；
   自动解析 hash 且相同 Git URL、未指定 revision 条件已有 Installation 时，覆盖其原安装文件。
4. 创建或更新 `Installation`，填充 tracked 状态、Git URL、revision、`install-id`、`install-path` 和 query keys。
5. 当同一 Git URL 使用相同的未指定 revision 条件再次安装，按覆盖处理已有 Installation 及其
   `install-path`：重新解析 commit hash，覆盖安装文件，并以新的 revision 更新安装结果。该情形
   不因已有 `install-path` 返回 `installation.target.unavailable`。
6. 将 tracked install 的元信息写入 `imports.json`，untracked install
   写入 `runtime.json`。
7. 由 `install-path` 派生 `import` 类型的 `BoundaryPoint`，不在边界文件中另行记录。
8. 提交事务并返回需求 0002-01 定义的安装结果。

### 4.2 `import restore`

1. 在 RuntimeStore 中按 `install-id` 查找 tracked `Installation`；untracked install 不适用本命令。
2. 严格根据 Installation 中已保存的 `commit-hash`、`branch` 和 `tag` 访问或恢复 CacheStore
   中的 bare Git repository，不因 `is-auto-resolved-hash` 重新解析 revision。
3. 按已记录的 install-path 重新安装仓库文件；Installation 元信息保持不变。
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

1. 在 RuntimeStore 中依据 `--install-id`、`--untracked` 或 `--auto` 解析移除选择器。
2. 对选中的 tracked Installation，校验 boundary-set 内的 Markdown 文件不存在指向该 Installation
   的 link，且不存在基于该 Installation 的 Ref；校验范围使用 boundary-set 过滤，修改内容优先
   通过 Git 感知方式确定。
3. 任何冲突或必需数据、路径缺失时，命令报错并不得完成移除。
4. 从对应的权威状态来源移除选中的 Installation：tracked install 从 `imports.json` 移除，
   untracked install 从 `runtime.json` 移除。
5. 移除安装产物对应的实际文件和 install-path；由该 Installation 派生的 `import` BoundaryPoint
   随状态重建消失。
6. 提交 RuntimeStore 事务并返回通用成功结果。

`--auto` 选择所有 untracked install，以及所有未被仓库内文件建立受管理引用的 install；具体
选择规则以需求 0002-01 为准。

### 4.5 `import ref`

1. 在 RuntimeStore 中按 `install-id` 查找 Installation；若其为 untracked，先将其提升为 tracked。
2. 根据 Installation 的 install-path 和可选 `src-sub-dir` 确定引用源。
3. 在 `target-dir` 创建受管理引用（文件系统符号链接），创建 `Ref` 并写入 `import-refs.json`。
4. 由 `target-dir` 派生 `import-ref` 类型的 `BoundaryPoint`。
5. 提交 RuntimeStore 事务并返回通用成功结果。

### 4.6 `import unref`

1. 在 RuntimeStore 中按 `target-dir` 查找对应 Ref。
2. 移除目标位置的受管理引用和 `Ref` 记录。
3. 提交时更新 `import-refs.json`；对应的 `import-ref` BoundaryPoint 随状态重建消失。
4. 返回通用成功结果。

### 4.7 `import query`

1. 在 RuntimeStore 中读取 tracked 文件与 `runtime.json`，重建完整 Installation 和 Ref 集合。
2. 按唯一选择器 `install-id`、`install-path`、`ref-path` 或一个或多个 query key 筛选候选项。
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
`installation.not-found` 或 `ref.not-found`。

### 6.2 Installation、revision 和来源校验

| 子命令 | 必须成立的前提 | 不满足时的错误 |
|---|---|---|
| `install` | Git URL 与 branch、tag、commit 能解析出符合参数组合的 revision。 | revision 无法解析为 `revision.unresolvable`；tag 与显式 commit 不一致为 `revision.inconsistent`。 |
| `install` | CacheStore 能取得或恢复该 Git URL 对应的 bare repository；安装路径可用于本次 Installation。未指定 `--commit` 时，先同步远程 branch 或 tag 并自动解析 commit hash；若相同 Git URL、未指定 revision 条件已有 Installation 及其 `install-path`，则按覆盖更新处理。 | 缓存不可用为 `cache.repository.unavailable`；显式指定 `--commit` 时，或目标路径已由其他内容或不相容 Installation 占用为 `installation.target.unavailable`。 |
| `restore` | 指定 `install-id` 存在且为 tracked Installation；恢复使用其已保存的 revision，不重新解析 branch 或 tag。 | Installation 不存在为 `installation.not-found`；状态不是 tracked 为 `installation.tracking-state.invalid`；无法取得对应 bare repository 为 `cache.repository.unavailable`；已保存 revision 无法恢复为 `installation.restore.unavailable`。 |
| `track` | 指定 `install-id` 存在。untracked Installation 被提升为 tracked；已 tracked Installation 成功完成 no-op。 | Installation 不存在为 `installation.not-found`。 |
| `ref` | 指定 `install-id` 存在。若其为 untracked，只有在后续来源与目标校验均可通过时，才在同一提交中提升为 tracked。 | Installation 不存在为 `installation.not-found`。 |

对 `install` 而言，未指定 `--commit` 的自动解析 hash 场景必须先同步远程 branch 或 tag；
相同 Git URL、未指定 revision 条件已有 Installation 时，即使其 `install-path` 已存在，也覆盖
其安装文件和 Installation 元信息，不报告 `installation.target.unavailable`。显式指定 `--commit`
时，或目标路径属于其他内容或不相容 Installation 时，仍须通过目标占用校验。对 `restore` 而言，
tracked Installation 缺少实际 `install-path` 是预期的恢复场景，不构成错误；
但已存在的安装路径不能被本次恢复安全使用时，返回 `installation.target.unavailable`。对 `ref`
而言，Installation 的 `install-path` 和可选 `src-sub-dir` 必须已经是可用的实际引用源。tracked
Installation 尚未 restore 时，`ref` 不隐式恢复它，而是返回 `ref.source.unavailable`。

### 6.3 Ref、目标路径和移除校验

| 子命令 | 必须成立的前提 | 不满足时的错误 |
|---|---|---|
| `ref` | `target-dir` 不包含不相容内容，且能够建立指向已验证源的受管符号链接。 | `ref.target.unavailable`。 |
| `unref` | `target-dir` 有对应 Ref，且目标位置仍是该 Ref 所记录的受管符号链接。 | Ref 记录不存在为 `ref.not-found`；链接不存在、不是预期符号链接或指向错误源为 `ref.target.inconsistent`。 |
| `remove --install-id` | 指定 Installation 存在。 | `installation.not-found`。 |
| `remove` 选中的 tracked Installation | 不存在阻塞 link，且不存在关联 Ref。 | `installation.remove.blocked`。 |

移除 tracked Installation 前，工具基于完整 `boundary-set` 视图枚举当前 doctidex 目录树有效范围内的
Markdown 源文件，不进入任何 BoundaryPoint 后代。对每个本地 link，根据其第一个跨越的
`import` 类型 BoundaryPoint 关联到 Installation；即使该 tracked Installation 尚未 restore，也
依据模型中的 `install-id` 和 `install-path` 完成这项逻辑关联，不恢复仓库文件或依赖实际 link
目标存在。指向该 Installation 的每个 link 都会阻塞移除。

同时，任何 `Ref.install-id` 等于待移除 Installation 的 Ref 都会阻塞移除，无论其受管符号链接的
实际工作目录是否存在。若同一命令选择多个 Installation，只要其中任一个存在阻塞项，命令不移除
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
非空。前者中的 `path` 和后者均为仓库内部绝对路径，`line` 是 link 在源 Markdown 文件中的
起始行号。单个 `--install-id` 选择器的 `subject` 为该 Installation；`--untracked` 或 `--auto`
选择多个对象时，`subject.kind` 为 `installation-selection`，具体被阻塞对象全部由
`details.blocked-installations` 表达。

`--untracked` 和 `--auto` 的选择语义以需求 0002-01 为准。它们选中的 tracked Installation 同样
使用本节阻塞检查；untracked Installation 不经过该 tracked 前置校验。物理 `install-path` 已缺失
的 tracked Installation 可以被移除，前提是不存在上述逻辑 link 或 Ref 关系。

### 6.4 完成移除和查询

通过第 6.3 节校验后，`remove` 才从各自权威状态来源删除 Installation，并移除仍存在的实际安装
文件。tracked Installation 的实际 `install-path` 已缺失时，跳过文件删除但继续删除元信息和派生
`import` BoundaryPoint。`unref` 仅在受管符号链接与 Ref 记录一致时才删除两者，避免删除用户已
替换的路径。

`query` 的选择器没有匹配记录时不改变 Store 或文件系统，也不构成错误。选择器、路径格式或参数
互斥关系本身不成立时，仍按 CLI 契约返回 `argument.invalid` 或 `repository-path.invalid`。

## 7. 受影响的产品表面

| 表面 | 需要定义的内容 | 当前状态 |
|---|---|---|
| `import install/restore` | CacheStore、Installation 和 install-path 交互 | 已定义；revision、缓存、tracked 状态与目标冲突的错误映射已明确 |
| `import track` | untracked 到 tracked 的状态迁移、投影和已 tracked no-op | 已定义 |
| `import remove` | Installation、Ref、文件和 BoundaryPoint 的移除关系 | tracked Installation 的逻辑 link/Ref 阻塞校验、错误详情和缺失路径处理已定义 |
| `import ref/unref` | Ref、符号链接和 `import-ref` 边界点 | 来源、目标与一致性前置校验及错误映射已定义 |
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
- [x] 设计与 CLI 契约、工作模型及 Architecture 的一致性已完成审阅。

## 9. 实施与状态

本子需求目前为 `draft`。设计内容已与 CLI 契约、工作模型及相关命令簇完成一次同步；获得明确
批准前，不授权修改 CLI 实现、测试或相关 Architecture 文档。
