# 需求 0002-09：`repair` 命令簇工作流与生命周期设计

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-09` |
| 状态 | `draft` |
| 日期 | 2026-08-10 |
| 来源 | 用户要求新增 `repair` 命令簇，使物理仓库状态与 doctidex 配置描述相容 |
| 父需求 | [需求 0002：设计 doctidex-git 命令行工具 v2.x.x](overview.md) |
| 关联子需求 | [需求 0002-01：CLI 命令行参数及返回结果结构设计](01-cli-arguments-results.md)、[需求 0002-02：设计 doctidex-git 工作模型](02-working-model.md)、[需求 0002-03：`boundary-set` 命令簇工作流与生命周期设计](03-boundary-set.md)、[需求 0002-04：`init` 命令簇工作流与生命周期设计](04-init.md)、[需求 0002-05：`import` 命令簇工作流与生命周期设计](05-import.md)、[需求 0002-06：`worktree` 命令簇工作流与生命周期设计](06-worktree.md)、[需求 0002-07：`validate` 命令簇工作流与校验设计](07-validate.md)、[需求 0002-08：`CacheStore` 与 `RuntimeStore` 事务机制实现设计要求](08-store-transactions.md) |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 影响范围 | `Installation`、`Ref`、`Worktree`、派生 `BoundaryPoint`、Git ignore、受管理符号链接和物理工作目录 |
| 文档性质 | 子 Requirement；仅记录修复工作流与生命周期设计，不授权实现 |

## 1. 需求意图

定义 `repair` 如何以当前 `.doctidex-git/` 配置文件和状态文件为基准，使其描述的
Installation、Ref、Worktree、派生 `boundary-set` 和 Git ignore 约束与仓库当前可观察的物理状态
相容。

`repair` 的目标是建立一个可继续工作的有效环境，不是从备份、journal 或 Git 历史恢复到某个
失效前版本。对 JSON 未描述的物理 install-path，repair 按本需求明确的忽略规则处理。

## 2. 命令格式与通用约束

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] repair
```

该命令只接受通用 `--repos-path` 参数，不接受 `--subdir` 或对象选择器。修复范围始终为当前
Git root 的完整 doctidex 工作模型和其相关物理对象。

`repair` 是写操作，必须使用需求 0002-08 定义的 Store 事务、文件锁、暂存和补偿提交规则。
命令成功后返回需求 0002-01 的通用成功结构；具体修复项不改变公共成功返回结构。

## 3. 修复基准与不变量

### 3.1 JSON 描述优先

- `imports.json`、`import-refs.json`、`runtime.json` 和 `boundary-set.json` 中能够成功解析的
  记录构成修复基准。
- JSON 没有记录但物理上存在的 `install-path` 不加入 Installation，不因本命令自动登记或删除。
- JSON 记录无法解析、字段缺失或关系冲突时，不把原始解析错误转化为物理修复动作；命令按通用
  工作模型错误返回并停止相关修复。
- `custom` BoundaryPoint 由用户状态保留；`import`、`import-ref` 和 `worktree` 类型点依据
  Installation、Ref、Worktree 记录重新派生。

### 3.2 幂等性

相同 JSON 状态和相同物理状态重复执行 `repair` 不应产生额外状态变化。修复过程中已经与描述
相容的对象必须保持不变。

## 4. 修复工作流

### 4.1 启动和事务恢复

1. 根据通用 `--repos-path` 解析 Git root；解析失败返回 `git-root.unresolved`。
2. 检查 `.doctidex-git/` 工作模型是否已初始化；未初始化返回 `work-model.uninitialized`。
3. 按 `CacheStore -> RuntimeStore` 顺序获取所需锁，并检查 RuntimeStore 未完成事务 journal。
4. 若发现上一次事务已经回滚到旧状态，`repair` 在本次命令中继续执行一次自身的修复流程；不递归
   调用 `repair`。`validate` 和 `init` 不执行该自动修复规则。
5. 读取并解析当前 JSON 状态，建立 Installation、Ref、Worktree 和 BoundaryPoint 的内存视图。

### 4.2 Installation 对齐

对每条 JSON 中的 Installation：

1. 检查其记录的 `install-path` 是否存在实际安装目录。
2. 若实际安装目录存在，以 JSON 中该 Installation 的字段为目标，校正实际安装目录的 Git 状态；
   不修改 `tracked`、`install-id`、`keys`、`install-path` 或其他 Installation 描述字段，也不得把
   JSON 中没有的物理 install-path 反向登记为新的 Installation。
3. JSON 中存在 Installation、但对应物理 install-path 缺失时，不因 repair 自动创建新的
   Installation 记录；缺失的 tracked install 文件由 `import restore` 重新安装。
4. JSON 中没有记录而物理上存在的 install-path 忽略，不删除、不登记，也不改变其内容。

### 4.3 Import Ref 对齐

对每条 `import-refs.json` 中的 Ref：

1. 根据其 `install-id`、Installation 的 `install-path` 和 `src-sub-dir` 计算预期源路径。
2. 检查 `target-dir` 对应的受管理符号链接是否存在。
3. 受管理符号链接不存在时，按照 Ref 记录创建该链接，并保留原 Ref 记录；已存在的受管理符号
   链接保持不变。

仓库当前 doctidex 目录树有效范围内，凡是指向某个 Installation 的 `install-path` 或其子目录、
但没有对应 `import-refs.json` 记录的符号链接，均视为未登记链接并删除。该扫描必须复用父需求定义的
共享领域工具，不得自行实现与 `import` 或 `validate` 不同的 BoundaryPoint 过滤或 Installation/Ref
关联规则；扫描不得进入 `/.doctidex-git` 或任何 BoundaryPoint 后代。

### 4.4 Worktree 对齐

对每条 `runtime.json` 中的 Worktree：

1. 检查记录的 `work-path` 是否存在并仍是对应 Git worktree。
2. `work-path` 缺失时，使用 Worktree 记录的 `base-commit-hash` 重建该 worktree：URL 来源直接以其
   `url` 和 `base-commit-hash` 创建；Installation 来源仍按其 `install-id` 关联的 Installation 创建。保留原
   Worktree 记录和 `work-path`。
3. 不在 `.doctidex-git/worktrees/` 下的 `work-path` 必须继续满足其记录对应的 Git ignore 规则。

Worktree 创建所需的缓存和远程访问由 `CacheStore` 自身负责；repair 不重复设计该服务的访问
边界。

### 4.5 BoundaryPoint 和 Git ignore 修复

1. 保留 JSON 中所有有效的 `custom` BoundaryPoint，不根据物理目录树新增 custom 点。
2. 根据当前有效 Installation、Ref 和 Worktree 记录重新派生 `import`、`import-ref` 和
   `worktree` BoundaryPoint；不在 `boundary-set.json` 中重复写入派生点。
3. 删除已不存在或已不再由模型记录派生的旧 managed BoundaryPoint；不删除 custom 点。
4. 确保 `runtime.json`、`.transactions/`、`imports/`、`worktrees/` 和自定义 work-path 的
   必要 Git ignore 规则存在。
5. 只移除能够确认由 doctidex-git 自动加入、且已不再由当前模型需要的 Git ignore 规则；保留用户
   手工维护的其他规则。

BoundaryPoint 和 Git ignore 的修复与同一 RuntimeStore 事务提交，不能在模型提交成功前留下新的
派生状态。

## 5. 提交、失败和生命周期

### 5.1 提交边界

`repair` 在完成所有可预先判断的模型关系、目标路径和 Git ignore 检查后，才发布符号链接、
worktree、状态文件和派生边界变化。任一不可恢复的修复失败时，不提交尚未完成的 RuntimeStore
模型变更；已经执行的物理动作必须按命令级 journal 或补偿操作恢复到 repair 开始前的相容状态。

### 5.2 生命周期影响

| 对象 | repair 的作用 | 不发生的转换 |
|---|---|---|
| `Installation` | 以 JSON 记录为基准对齐已存在的安装目录和可观察状态 | 不因未知 install-path 创建 Installation；不自动改变 install-id |
| `Ref` | 创建缺失的受管理符号链接，清理未登记的 import link | 不根据未知符号链接创建 Ref |
| `Worktree` | 为已有记录补建缺失的 work-path | 不改变 Worktree 记录本身 |
| `BoundaryPoint` | 重建派生点并保留 custom 点 | 不允许 repair 删除 custom BoundaryPoint |
| Git ignore | 补齐模型要求的自动规则，移除不再需要的工具生成规则 | 不覆盖用户维护的无关规则 |

### 5.3 事务遗留后的内部调用

可写 RuntimeStore 事务从写入 `prepared` journal 起，即允许命令执行真实文件系统操作。因此存在
残留事务时，只有 `committed` journal 且全部目标文件均已是 `new-sha256`，才可以直接清理并跳过
修复。`prepared` 或 `publishing` 残留事务只要能够完成恢复处理，就必须报告 `repair-required`。

除 `validate` 和 `init` 外，其他命令在启动时收到 `repair-required` 后，必须在继续执行业务工作流前
内部执行一次 `repair`。该内部调用以当前 JSON 状态为基准，只执行一次，不对外产生嵌套命令输出；
repair 本身不递归触发 repair。无法安全处理残留事务时，保留 journal 并停止命令，不尝试 repair。

## 6. 受影响的错误与返回

`repair` 成功返回需求 0002-01 的通用成功结构。无法修复时沿用对应操作已有的错误码和
`message.details` 结构；不建立独立的 `repair.*` 错误目录。底层文件系统或 Git 错误仍须转换为已有
的领域错误，不直接暴露原始文本。

## 7. 验收标准

- [x] `repair` 命令格式和 `--repos-path` 语义已定义。
- [x] JSON 描述优先及未知物理 install-path 不自动登记的规则已定义。
- [x] Installation、Ref、Worktree、BoundaryPoint 和 Git ignore 的修复范围已定义。
- [x] import-ref 缺失链接的创建和未登记 import 链接的删除边界已定义。
- [x] 缺失 Worktree 的补建流程及其事务边界已定义。
- [x] 非 `committed` 残留事务处理后各非 `validate`、非 `init` 命令的内部 repair 行为已定义。
- [x] repair 的幂等性、失败回滚和用户内容保护要求已定义。
- [x] repair 沿用需求 0002-01 已定义的错误码，不建立独立错误目录。

## 8. 实施与状态

本子需求目前为 `draft`。修复范围、生命周期和错误复用规则已完成一次同步；获得明确批准前，
不授权修改 CLI 实现、测试或相关 Architecture 文档。
