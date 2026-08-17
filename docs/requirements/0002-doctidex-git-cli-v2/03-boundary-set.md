# 需求 0002-03：`boundary-set` 命令簇工作流与生命周期设计

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-03` |
| 状态 | `approved` |
| 日期 | 2026-08-09 |
| 来源 | 用户要求按命令簇设计模型交互工作流及生命周期，并优先审阅 `boundary-set` 命令簇 |
| 父需求 | [需求 0002：设计 doctidex-git 命令行工具 v2.x.x](overview.md) |
| 关联子需求 | [需求 0002-01：CLI 命令行参数及返回结果结构设计](01-cli-arguments-results.md)、[需求 0002-02：设计 doctidex-git 工作模型](02-working-model.md) |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 影响范围 | `boundary-set`、`BoundaryPoint`、`RuntimeStore`、Git root 目录边界和路径解析 |
| 文档性质 | 子 Requirement；仅记录工作流与生命周期设计，不授权实现 |

## 1. 需求意图

定义 `boundary-set` 命令簇与工作模型之间的交互方式，明确 `BoundaryPoint` 的来源、重建、
查询和生命周期，使路径解析能够使用完整的边界集合，并与需求 0002-01 的命令参数及返回
结构保持一致。

本子需求只设计 `boundary-set` 命令簇及其与其他模型的交互，不重新设计 `import`、`worktree`
或 `validate` 命令簇的内部行为。

## 2. 设计依据

- `boundary-set add`、`boundary-set remove` 和 `boundary-set parse` 的调用格式及返回结构以
  [需求 0002-01](01-cli-arguments-results.md) 为准。
- `BoundaryPoint` 的字段和类型以 [需求 0002-02](02-working-model.md) 为准：

  ```jsonc
  {
    "type": "<custom | import | import-ref | worktree>",
    "path": "<REPOSITORY-INTERNAL-ABSOLUTE-PATH>"
  }
  ```

- `RuntimeStore` 在事务中读取各 tracked 文件与 `runtime.json`，合并形成内存中的完整运行时
  数据；`boundary-set` 的派生点不单独持久化。
- `boundary-set.json` 只保存 `custom` 类型的 `BoundaryPoint`，并由 Git tracked。
- `--repos-path` 是所有命令通用的 Git root 指定方式；省略时使用当前路径向上搜索到的 Git root。

## 3. 边界点来源与状态

内存中的 `boundary-set` 是四类 `BoundaryPoint` 的集合。其持久化来源和产生命令如下：

| 类型 | 来源 | 持久化来源 | 可由 `boundary-set remove` 移除 |
|---|---|---|---|
| `custom` | 用户执行 `boundary-set add` | `boundary-set.json` | 是 |
| `import` | `Installation.install-path` | `imports.json` 或 `runtime.json` 中对应的 Installation | 否 |
| `import-ref` | `Ref.target-dir` | `import-refs.json` 中对应的 Ref | 否 |
| `worktree` | `Worktree.work-path` | `runtime.json` 中对应的 Worktree | 否 |

状态重建时，`custom` 点从 `boundary-set.json` 读取；`import`、`import-ref` 和 `worktree` 点
分别从 `Installation`、`Ref` 和 `Worktree` 派生。命令不额外维护一份边界点记录。

## 4. 命令工作流

### 4.1 `boundary-set add`

1. 按通用 `--repos-path` 确定 Git root，并初始化 `RuntimeStore` 事务。
2. 事务读取 `boundary-set.json`、`imports.json`、`import-refs.json` 和 `runtime.json`，重建当前完整的 `boundary-set`。
3. 对每个输入 `--path` 创建 `type: custom` 的 `BoundaryPoint`，并加入内存中的边界集合。
4. 事务提交时仅将 `custom` 边界点写入 `boundary-set.json`；其他类型的边界点保持由其所属模型提供。
5. 按需求 0002-01 的通用成功返回结构返回结果。

`--path` 可以重复提供，每个输入值都作为一个待处理的 custom 边界点。参数格式、路径类型和
失败返回遵循需求 0002-01；本子需求不新增参数或错误结构。

### 4.2 `boundary-set remove`

1. 按通用 `--repos-path` 确定 Git root，并初始化 `RuntimeStore` 事务。
2. 事务重建当前完整的 `boundary-set`。
3. 按输入 `--path` 定位 `type: custom` 的 `BoundaryPoint` 并移除；没有对应 custom 记录的输入成功
   no-op。
4. 事务提交时更新 `boundary-set.json`；由 `Installation`、`Ref` 或 `Worktree` 派生的边界点不受影响。
5. 按需求 0002-01 的通用成功返回结构返回结果。

`remove` 只能移除由 `boundary-set add` 创建的 custom 边界点；不存在的 custom 记录不构成错误。
不能通过该命令移除 `import`、`import-ref` 或 `worktree` 类型的边界点；这些派生点仍存在且受其来源
模型管理时，命令返回禁止删除错误。

### 4.3 `boundary-set parse`

1. 按通用 `--repos-path` 确定 Git root，并读取 `RuntimeStore` 重建完整的 `boundary-set`。
2. 对每个输入 `--path` 按仓库内部路径的层级前缀进行解析。
3. 命中路径中遇到的第一个 `BoundaryPoint` 后停止继续解析该输入路径。
4. 为每个输入路径生成一个解析结果；未命中边界点时返回 `has-boundary: false`。
5. 成功结果使用需求 0002-01 定义的 `results` 结构，并通过 `boundary-type` 返回命中点的类型。

`parse` 是只读操作，不改变 `RuntimeStore` 或任何 tracked 文件。

### 4.4 路径输入与边界合并规则

`add`、`remove` 和 `parse` 的所有 `--path` 值都必须是仓库内部绝对路径：以 `/` 开头，路径根
对应 `--repos-path` 指定的 Git root，而不是宿主文件系统根目录。

路径先进行规范化处理；路径中允许出现 `..`，但规范化后的结果不得越过仓库根目录。目标路径
可以不存在，路径是否存在不影响上述三个命令对参数的接受。

多个 `BoundaryPoint` 的路径相同，或一个路径是另一个路径的祖先/后代时，按路径前缀进行合并：
从仓库根目录向输入路径解析，只保留首先命中的 `BoundaryPoint` 及其路径前缀，不继续保留或
匹配该点之后的后代边界点。

## 5. `BoundaryPoint` 生命周期

### 5.1 `custom`

| 阶段 | 触发操作 | 状态来源 |
|---|---|---|
| 不存在 | 尚未执行 `add`，或已执行 `remove` | 无 |
| 已登记 | `boundary-set add` 成功提交 | `boundary-set.json`，并在内存集合中可用 |
| 已恢复 | 命令启动或事务创建时读取 tracked 文件 | 从 `boundary-set.json` 重建 |
| 已移除 | `boundary-set remove` 成功提交 | 从 `boundary-set.json` 和内存集合删除 |

### 5.2 派生边界点

`import`、`import-ref` 和 `worktree` 类型没有独立的 `boundary-set` 增删操作。它们随来源模型
的生命周期变化：

- `Installation` 创建或保留其 `install-path` 时，派生 `import` 边界点；Installation 被移除后，不再派生该点。
- `Ref` 创建或保留其 `target-dir` 时，派生 `import-ref` 边界点；Ref 被移除后，不再派生该点。
- `Worktree` 创建或保留其 `work-path` 时，派生 `worktree` 边界点；Worktree 被移除后，不再派生该点。

上述来源模型的具体创建、恢复、提升 tracked 和移除命令，分别以需求 0002-05 和 0002-06 的
工作流设计为准；参数与返回结构仍以需求 0002-01 为准。

## 6. 设计备注

当前没有针对 `boundary-set` 命令簇新增的待确认事项。

## 7. 受影响的产品表面

| 表面 | 需要定义的内容 | 当前状态 |
|---|---|---|
| `boundary-set add` | custom 边界点的创建、持久化和重复输入处理 | 已定义 |
| `boundary-set remove` | custom 边界点的移除及对派生边界点的保护 | 已定义 |
| `boundary-set parse` | 完整边界集合重建、前缀匹配和解析结果 | 已定义 |
| `RuntimeStore` | tracked 来源、runtime 来源和派生边界点的合并 | 已定义 |
| `BoundaryPoint` 生命周期 | custom 与派生类型的创建、恢复和移除 | 已定义 |

## 8. 依赖与验收标准

- 父需求：[需求 0002](overview.md)。
- CLI 契约：[需求 0002-01](01-cli-arguments-results.md)。
- 工作模型：[需求 0002-02](02-working-model.md)。
- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。

- [x] `BoundaryPoint` 四类来源、持久化来源和可移除边界已明确。
- [x] `add`、`remove`、`parse` 的模型交互工作流已记录。
- [x] custom 与派生边界点的生命周期已记录。
- [x] 重叠路径、重复输入和路径参数校验规则已明确。
- [x] 设计与 CLI 契约、工作模型及 Architecture 的一致性已完成审阅。

## 9. 实施与状态

本子需求为 `approved`，其实施已完成。custom 与派生 BoundaryPoint 的命令工作流、生命周期和路径解析已实现，
并由 phase 7 集成验收；当前行为以 user 与 Architecture 文档为权威说明。
