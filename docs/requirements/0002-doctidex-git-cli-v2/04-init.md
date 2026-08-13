# 需求 0002-04：`init` 命令簇工作流与生命周期设计

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-04` |
| 状态 | `draft` |
| 日期 | 2026-08-09 |
| 来源 | 用户要求按命令簇设计 doctidex-git 工作模型初始化工作流 |
| 父需求 | [需求 0002：设计 doctidex-git 命令行工具 v2.x.x](overview.md) |
| 关联子需求 | [需求 0002-01：CLI 命令行参数及返回结果结构设计](01-cli-arguments-results.md)、[需求 0002-02：设计 doctidex-git 工作模型](02-working-model.md)、[`boundary-set` 命令簇工作流与生命周期设计](03-boundary-set.md) |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 影响范围 | Git root 工作空间、RuntimeStore 初始状态、tracked 文件和 Git ignore 约束 |
| 文档性质 | 子 Requirement；仅记录工作流与生命周期设计，不授权实现 |

## 1. 需求意图

定义 `init` 如何在当前 Git root 建立 doctidex-git 工作模型，使后续 `boundary-set`、`import`、
`worktree` 和 `validate` 能够恢复并访问一致的仓库级状态。

本子需求只定义工作模型初始化，不定义其他命令簇在已初始化状态下的具体业务操作。

## 2. 设计依据

- `init` 仅接受通用 `--repos-path` 参数，调用格式以 [需求 0002-01](01-cli-arguments-results.md) 为准。
- 仓库级工作空间和状态文件以 [需求 0002-02](02-working-model.md) 为准。
- `RuntimeStore` 的事务恢复和写入规则以 [需求 0002-08](08-store-transactions.md) 为准。
- `boundary-set` 的 custom 持久化规则以 [需求 0002-03](03-boundary-set.md) 为准。

## 3. 初始化目标

`init` 面向通用 `--repos-path` 确定的 Git root，建立以下仓库级工作空间：

```text
<git-root>/.doctidex-git/
├── config.toml
├── imports.json
├── boundary-set.json
├── import-refs.json
└── runtime.json
```

各状态文件建立为空集合的初始状态：

| 文件 | 初始内容 | 所属状态 |
|---|---|---|
| `imports.json` | 空的 tracked `Installation` 集合 | Git tracked |
| `boundary-set.json` | 空的 custom `BoundaryPoint` 集合 | Git tracked |
| `import-refs.json` | 空的 `Ref` 集合 | Git tracked |
| `runtime.json` | 空的 untracked `Installation` 集合和空的 `Worktree` 集合 | Git ignored |
| `config.toml` | 仓库级配置文件 | 配置 |

`imports/` 与 `worktrees/` 是按需创建的路径空间，不在初始化阶段产生任何 `Installation`、
`Ref` 或 `Worktree`，也不因此产生派生 `BoundaryPoint`。

初始化还必须为 `runtime.json`、`.transactions/`、`imports/` 和 `worktrees/` 保持
[需求 0002-02](02-working-model.md) 规定的 Git ignore 约束。

## 4. 初始化工作流

1. 按通用 `--repos-path` 确定 Git root；无法确定 Git root 时命令不进入工作模型初始化。
2. 检查 `.doctidex-git/` 工作空间及其状态文件。
3. 若 `.doctidex-git/` 已存在，内部转入 `validate` 流程，检查已有工作模型；不覆盖或修复
   已有状态文件、仓库配置或 Git ignore 规则。
4. 若工作空间不存在，创建工作空间目录、配置文件和空状态文件，并建立运行时目录的 Git ignore
   约束。
5. 对新建工作空间，通过 `RuntimeStore` 读取并重建初始状态，确认后续命令可以访问模型。
6. 按需求 0002-01 的通用成功返回结构返回结果。

`init` 不创建 custom `BoundaryPoint`，也不改变用户级 `CacheStore` 中的缓存条目。

工作空间文件先在系统临时目录中直接写入，完成完整的 `.doctidex-git/` 工作空间后，再一次性
同步到 Git root 的目标路径；临时目录内的单个文件不需要分别使用原子写入。Git root 下不创建
形如 `.doctidex-git.initializing-*` 的初始化临时目录；初始化临时目录也不使用 RuntimeStore 的
`.transactions/` journal 进行恢复。同步失败时仅清理本次尚未完成的初始化产物，不改变已有工作空间。

## 5. 工作模型生命周期

| 阶段 | 进入方式 | 状态特征 |
|---|---|---|
| 未初始化 | Git root 中不存在可用的 `.doctidex-git/` 工作空间 | 工作模型不能被正常恢复 |
| 已初始化 | `init` 成功创建工作空间和初始状态文件 | 可创建 Store 事务，所有已定义命令簇可以访问模型；再次执行 `init` 转入内部 validate 流程 |
| 已使用 | `import`、`worktree` 或 `boundary-set` 修改状态 | 状态由 RuntimeStore 及其 tracked 投影共同维护 |
| 已失效 | 状态文件、tracked 投影或 Git ignore 约束不满足模型不变量 | 由 `validate` 的 `work-model.valid` 规则报告；由 `repair` 按需求 0002-09 对齐物理状态 |

重复执行 `init` 不得覆盖已有模型数据，而是转入内部 validate 流程。已有状态文件、非法 JSON、
仓库配置和 Git ignore 规则的有效性由该流程判断。

## 6. 已确认的通用处理规则

目标 Git root 已存在 `.doctidex-git/` 工作空间时，`init` 不执行部分补建或覆盖；它内部转入
validate 流程，由工作模型有效性校验处理现有状态。

## 7. 受影响的产品表面

| 表面 | 需要定义的内容 | 当前状态 |
|---|---|---|
| 工作空间 | `.doctidex-git/` 及初始状态文件 | 新建初始化与已存在工作空间的 validate 分支已定义 |
| RuntimeStore | 初始空状态和可恢复性 | 已定义 |
| Git ignore | runtime、transactions、imports 和 worktrees 的忽略约束 | 新建时建立；已有工作空间由内部 validate 流程校验 |
| 工作模型生命周期 | 未初始化、已初始化、已使用和失效阶段 | 已定义 |

## 8. 依赖与验收标准

- 父需求：[需求 0002](overview.md)。
- CLI 契约：[需求 0002-01](01-cli-arguments-results.md)。
- 工作模型：[需求 0002-02](02-working-model.md)。
- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。

- [x] `init` 的初始化目标、初始状态和工作模型生命周期已记录。
- [x] `init` 与 RuntimeStore、tracked 文件和 Git ignore 的交互已记录。
- [x] 已有状态、配置错误、ignore 冲突和重复执行时转入内部 validate 流程的规则已明确。
- [x] 设计与 CLI 契约、工作模型及 Architecture 的一致性已完成审阅。

## 9. 实施与状态

本子需求目前为 `draft`。设计内容已与 CLI 契约、工作模型及相关命令簇完成一次同步；获得明确
批准前，不授权修改 CLI 实现、测试或相关 Architecture 文档。
