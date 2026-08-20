# 需求 0003：规范 doctidex-git 在作为 import installation 仓库内的行为

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0003` |
| 状态 | `approved` |
| 日期 | 2026-08-17 |
| 来源 | 用户补充 import installation 行为的草稿信息，并要求细化目标、需求、方案、细节处理和验收标准 |
| 影响范围 | `--repos-path` 语义、owner 识别、Installation 只读边界、间接 import 的恢复与查询、`import-by-installations` 关系、Installation 目录组织、`import remove` 语义、CLI 错误码，以及 Installation 上下文命令运行环境 |
| 文档性质 | 大型 Requirement；记录总体设计、子需求导航与阶段状态 |

## 1. 需求意图

本需求定义 `doctidex-git` 在作为 import installation 的仓库内应遵循的行为。核心目标：当命令
作用于某个已安装仓库时，不得把它当作普通可写工作空间；应识别 owner，把可变状态写到 owner，
同时保持 Installation 作为只读参考目录树。

## 2. 子需求

| 子需求 | 状态 |
|---|---|
| [0003-02 owner 识别与命令路由](02-owner-identification-command-routing.md) | `approved` |
| [0003-03 拆分 model_view 与事务/视图构造](03-model-view-refactor.md) | `approved` |
| [0003-04 重实现 Installation Store/Transaction/ModelView](04-installation-runtime-store-modelview.md) | `approved` |

暂不实现的子需求：

- [0003-01 扩展 RuntimeStore 模型](01-runtime-store-model.md)：`暂不实现`
- [0003-05 Installation 目录组织与 remove 语义](05-directory-organization-remove.md)：`暂不实现`

## 3. 依赖与相关记录

- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。
- 产品 Architecture：[doctidex-git v2 Architecture](../../architecture/doctidex-git-v2.md)。
- CLI 参数与返回结构：[需求 0002-01](../0002-doctidex-git-cli-v2/01-cli-arguments-results.md)。
- 工作模型：[需求 0002-02](../0002-doctidex-git-cli-v2/02-working-model.md)。
- `import` 命令簇：[需求 0002-05](../0002-doctidex-git-cli-v2/05-import.md)。
- Store 事务与恢复：[需求 0002-08](../0002-doctidex-git-cli-v2/08-store-transactions.md)。

## 4. 实施与状态

需求 0003 已获用户批准。当前 active 子需求 0003-02、0003-03、0003-04 均已批准；
0003-01、0003-05 暂不实现，文档保留。具体实现细节和验收标准以对应子需求为准。
