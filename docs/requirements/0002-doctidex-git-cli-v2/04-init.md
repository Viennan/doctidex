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

定义 `init` 如何在当前 Git root 建立 doctidex-git 工作模型和 doctidex 根入口，使后续
`boundary-set`、`import`、`worktree` 和 `validate` 能够恢复并访问一致的仓库级状态。

本子需求只定义工作模型初始化，不定义其他命令簇在已初始化状态下的具体业务操作。

## 2. 设计依据

- `init` 仅接受通用 `--repos-path` 参数，调用格式以 [需求 0002-01](01-cli-arguments-results.md) 为准。
- 仓库级工作空间和状态文件以 [需求 0002-02](02-working-model.md) 为准。
- `RuntimeStore` 的事务恢复和写入规则以 [需求 0002-08](08-store-transactions.md) 为准。
- `boundary-set` 的 custom 持久化规则以 [需求 0002-03](03-boundary-set.md) 为准。

## 3. 初始化目标

`init` 面向通用 `--repos-path` 确定的 Git root，建立根 `index.md` 及以下仓库级工作空间：

```text
<git-root>/
├── index.md
└── .doctidex-git/
    ├── config.toml
    ├── imports.json
    ├── boundary-set.json
    ├── import-refs.json
    └── runtime.json
```

根 `index.md` 是工作模型结构的一部分。初始化时不存在该文件则创建它，并写入配套 Architecture
第 2.3 节规定的基础 frontmatter：

```yaml
---
type: index
doctidex:
  type: index
  root: true
---
```

初始化实际执行时，若根 `index.md` 已存在，`init` 保留正文和不相关的 frontmatter 字段，并补充缺少的
`type`、`doctidex.type` 或 `doctidex.root`。任一必需字段已存在但类型或值不等于 Architecture 的固定值时，
命令以 `root-index.frontmatter.conflict` 失败且不创建工作空间。已有 frontmatter 不是有效 YAML 映射时，
无法安全补充字段，命令以 `root-index.frontmatter.invalid` 失败且不覆盖该文件。

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

初始化还必须为 `.command.lock`、`runtime.json`、`.transactions/`、`imports/` 和 `worktrees/` 保持
[需求 0002-02](02-working-model.md) 规定的 Git ignore 约束。

## 4. 初始化工作流

1. 按通用 `--repos-path` 确定 Git root；无法确定 Git root 时命令不进入工作模型初始化。
2. 检查 `.doctidex-git/` 工作空间是不存在、为空还是非空。
3. 若 `.doctidex-git/` 已存在且非空，直接返回“已运行过初始化，可以使用 `validate --model-structure` 校验工作模型”
   的成功信息；不读取、覆盖、修复或恢复已有状态文件、根 `index.md`、仓库配置、Git ignore 规则或残留
   RuntimeStore journal。
4. 若工作空间不存在或已存在但为空，先读取根 `index.md` 并确定其创建或补充后的内容。必需字段冲突或
   frontmatter 无法解析时立即失败，不创建或修改工作空间。
5. 写入已确定的根 `index.md`，创建工作空间目录、配置文件和空状态文件，并建立运行时目录的 Git ignore
   约束。
6. 对本次创建的工作空间，通过 `RuntimeStore` 读取并重建初始状态，确认后续命令可以访问模型。
7. 按需求 0002-01 的通用成功返回结构返回结果。

`init` 不创建 custom `BoundaryPoint`，也不改变用户级 `CacheStore` 中的缓存条目。

工作空间文件先在系统临时目录中直接写入，完成完整的 `.doctidex-git/` 工作空间后，再一次性
同步到 Git root 的目标路径；临时目录内的单个文件不需要分别使用原子写入。Git root 下不创建
形如 `.doctidex-git.initializing-*` 的初始化临时目录；初始化临时目录也不使用 RuntimeStore 的
`.transactions/` journal 进行恢复。同步失败时仅清理本次尚未完成的初始化产物，不改变已有工作空间。

## 5. 工作模型生命周期

| 阶段 | 进入方式 | 状态特征 |
|---|---|---|
| 未初始化 | Git root 中不存在可用的 `.doctidex-git/` 工作空间 | 工作模型不能被正常恢复 |
| 已初始化 | `init` 成功创建工作空间和初始状态文件 | 可创建 Store 事务，所有已定义命令簇可以访问模型；再次执行 `init` 返回已初始化提示 |
| 已使用 | `import`、`worktree` 或 `boundary-set` 修改状态 | 状态由 RuntimeStore 及其 tracked 投影共同维护 |
| 已失效 | 状态文件、tracked 投影或 Git ignore 约束不满足模型不变量 | 由 `validate` 的 `work-model.valid` 规则报告；由 `repair` 按需求 0002-09 对齐物理状态 |

重复执行 `init` 不得覆盖已有模型数据。只要 `.doctidex-git/` 非空，命令直接返回已运行过初始化的
信息，并建议用户执行 `validate --model-structure`；`init` 不负责校验已有状态，也不触发 repair。

## 6. 已确认的通用处理规则

目标 Git root 已存在非空 `.doctidex-git/` 工作空间时，`init` 不执行部分补建或覆盖，也不执行任何
工作模型校验；它直接返回已运行过初始化的信息，并建议使用 `validate --model-structure`。若该目录为空，`init` 继续
完成初始化。

## 7. 受影响的产品表面

| 表面 | 需要定义的内容 | 当前状态 |
|---|---|---|
| 根入口 | Git root 的 `index.md` 及基础 frontmatter | 新建、缺失字段补充和冲突拒绝已定义 |
| 工作空间 | `.doctidex-git/` 及初始状态文件 | 新建初始化、空目录继续初始化和非空目录提示已定义 |
| RuntimeStore | 初始空状态和可恢复性 | 已定义 |
| Git ignore | runtime、transactions、imports 和 worktrees 的忽略约束 | 新建时建立；已有工作空间由 `validate --model-structure` 显式校验 |
| 工作模型生命周期 | 未初始化、已初始化、已使用和失效阶段 | 已定义 |

## 8. 依赖与验收标准

- 父需求：[需求 0002](overview.md)。
- CLI 契约：[需求 0002-01](01-cli-arguments-results.md)。
- 工作模型：[需求 0002-02](02-working-model.md)。
- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。

- [x] `init` 的根入口、初始化目标、初始状态和工作模型生命周期已记录。
- [x] `init` 与 RuntimeStore、tracked 文件和 Git ignore 的交互已记录。
- [x] 空工作空间继续初始化、非空工作空间提示并建议执行 `validate --model-structure` 的规则已明确。
- [x] 设计与 CLI 契约、工作模型及 Architecture 的一致性已完成审阅。

## 9. 实施与状态

本子需求目前为 `draft`。设计内容已与 CLI 契约、工作模型及相关命令簇完成一次同步；获得明确
批准前，不授权修改 CLI 实现、测试或相关 Architecture 文档。
