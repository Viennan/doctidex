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

`repair` 的目标是尝试解决当前可修复的问题，使工作模型回归可继续工作的合法状态；常规 repair 不从
备份、journal 或 Git 历史恢复到某个失效前版本。唯一例外是处理残留 RuntimeStore journal：repair 可以
使用该 journal 的 `backup/` 将混合发布的 JSON 收敛到旧状态，再以收敛后的 JSON 为基准继续 repair。对
JSON 未描述的物理 install-path，repair 按本需求明确的忽略规则处理。

`repair` 只处理工作模型及其受管物理对象的可修复问题，不读取、诊断或修改 Markdown 文件中的
link。Markdown link 问题由 `validate` 单独报告，不能作为 repair 的修复目标。

## 2. 命令格式与通用约束

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] repair
```

该命令只接受通用 `--repos-path` 参数，不接受 `--subdir` 或对象选择器。修复范围始终为当前
Git root 的完整 doctidex 工作模型和其相关物理对象。

`repair` 是特殊的维护写操作，必须使用需求 0002-08 定义的命令级协调锁、GitCache 事务和与 `validate`
相同的 RuntimeStore 诊断锁定访问。该访问不创建自己的 RuntimeStore 暂存目录、journal 或 backup；只有
repair 工作流处理已有残留 journal 时才可使用该 journal 的 backup 恢复 JSON。命令成功后返回需求 0002-01
的通用成功结构；具体修复项不改变公共成功返回结构。

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
3. 按 `GitCache -> RuntimeStore` 顺序获取所需锁。repair 使用与 `validate` 相同的 RuntimeStore 诊断
   锁定访问：它不创建自己的 `.transactions/` 目录或 journal，只提供 repair 执行期间的锁定状态浏览。
4. repair 在该锁定访问内先检查所有残留 journal，并按需求 0002-08 第 5.3 节分类处理。已确认 `committed` 的 journal
   可以直接判定为无需物理修复，但其清理必须延后到本次 repair 的其他 journal 和全部物理修复成功之后；
   其余可自动恢复的 journal 必要时先用原 journal 的 backup 恢复 JSON，但必须保留该 journal，继续以
   收敛后的 JSON 和当前物理状态执行 repair。repair 不调用 `validate`，不消费诊断中间结果，也不递归调用
   repair。
5. 读取并解析可用 JSON 状态，建立 Installation、Ref、Worktree 和 BoundaryPoint 的内存视图，运行本需求
   定义的 repair 核心。所有 JSON 恢复和物理修复成功后，才删除本次处理的残留 journal；无法安全恢复的
   情况保留 journal 并停止命令。

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

1. 使用当前 ModelView 按 `install-id` 查询 Installation，不得自行重建 Installation 索引。若没有
   对应 Installation，直接移除该 Ref 记录及其 `target-dir` 物理对象；不扫描 Markdown link，也不以
   link 阻塞该维护动作。多个此类无效 Ref 必须作为一次 `import-refs.json` 原子更新删除。
2. 对存在关联 Installation 的 Ref，根据 Installation 的 `install-path` 和 `src-sub-dir` 计算预期源路径，
   并检查 `target-dir`。
3. `target-dir` 缺失时，按照 Ref 记录创建相对符号链接；已存在且解析结果等于预期源的受管理
   符号链接保持不变。存在但不是该记录所描述目标的文件、目录或符号链接时，删除后重新创建，
   不返回目标冲突错误。

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

Worktree 创建所需的 bare repository 访问经 GitCache 事务完成；目标 commit 的可用性检查和 Git worktree
创建复用 import/worktree 的共享仓库操作。repair 不在本需求中重复定义缓存或 Git 命令簇的访问边界。

### 4.5 BoundaryPoint 和 Git ignore 修复

1. 保留 JSON 中所有有效的 `custom` BoundaryPoint，不根据物理目录树新增 custom 点。
2. 根据当前有效 Installation、Ref 和 Worktree 记录重新派生 `import`、`import-ref` 和
   `worktree` BoundaryPoint；不在 `boundary-set.json` 中重复写入派生点。
3. 删除已不存在或已不再由模型记录派生的旧 managed BoundaryPoint；不删除 custom 点。
4. 确保 `runtime.json`、`.transactions/`、`imports/`、`worktrees/` 和自定义 work-path 的
   必要 Git ignore 规则存在。
5. 只移除能够确认由 doctidex-git 自动加入、且已不再由当前模型需要的 Git ignore 规则；保留用户
   手工维护的其他规则。

BoundaryPoint 和 Git ignore 的修复在同一 RuntimeStore 诊断锁定访问及命令级协调锁保护下完成。除清理
无关联 Ref 所需的 `import-refs.json` 原子更新外，repair 不发布新的业务 RuntimeStore 状态；若它正处理
残留 journal，只有完成 JSON 收敛及全部相关物理修复后，才删除该 journal。

## 5. 提交、失败和生命周期

### 5.1 提交边界

`repair` 在完成所有可预先判断的模型关系、目标路径和 Git ignore 检查后，才创建或替换受管理符号链接、
worktree 和派生边界相关物理状态。残留 journal 要求的 JSON 收敛在物理修复之前完成，并只使用该 journal
已保存的 backup。repair 不创建自己的事务 journal；任一修复失败时保留尚未完成处理的残留 journal
（若本次由残留事务触发），并停止命令。已经执行的物理动作不要求回滚到 repair 开始前，而由下一次 repair
继续尝试使其与 JSON 描述相容。

### 5.2 生命周期影响

| 对象 | repair 的作用 | 不发生的转换 |
|---|---|---|
| `Installation` | 以 JSON 记录为基准对齐已存在的安装目录和可观察状态 | 不因未知 install-path 创建 Installation；不自动改变 install-id |
| `Ref` | 创建缺失引用，重建与记录不一致的目标，清理未登记链接和没有 Installation 的 Ref | 不根据未知符号链接创建 Ref |
| `Worktree` | 为已有记录补建缺失的 work-path | 不改变 Worktree 记录本身 |
| `BoundaryPoint` | 重建派生点并保留 custom 点 | 不允许 repair 删除 custom BoundaryPoint |
| Git ignore | 补齐模型要求的自动规则，移除不再需要的工具生成规则 | 不覆盖用户维护的无关规则 |

### 5.3 事务遗留后的内部调用

可写 RuntimeStore 事务从写入 `prepared` journal 起，即允许命令执行真实文件系统操作。因此只有
`committed` journal 且全部目标文件均已是 `new-sha256` 的残留事务，才可以由 repair 在诊断锁定访问内判定
为已完成并跳过物理修复，但其 journal 仍须等本次 repair 的全部处理完成后统一清理。`prepared` 或 `publishing`
残留事务必须由 repair 在该锁定访问内按需求 0002-08 第 5.3 节分类、收敛 JSON 并执行本需求的物理 repair；不能由普通
事务报告后自行清理。

普通 RuntimeStore 事务在 `__enter__()` 的准备阶段只检测残留 journal。检测到后，它释放当前 RuntimeStore
锁并报告仅供命令协调器使用的 `repair-required` 信号；此时业务事务未建立状态快照或 journal，也不持有
repair 回调、GitCache 或重试循环。协调器捕获该信号后运行 repair，并重试发生该信号的 RuntimeStore 操作
闭包，最多 3 次；第三次 repair 后再次检测到残留 journal 时，以 `store.transaction.unavailable` 停止，
返回 `attempts: 3` 和最后一次残留 transaction ID，并提示用户排查环境或重试。显式 `repair` 直接运行本节的
repair 工作流，不通过普通事务委派自身。

repair 以收敛后的 JSON 和当前物理状态为输入，不调用 `validate`，也不消费诊断中间结果。对于两者共同
涉及的模型关系和物理对象事实，repair 与 validate 必须复用同一组底层状态判定逻辑；前者决定修复动作，
后者生成只读诊断。除显式 `validate` 与已有工作空间的 `init` 外，所有使用普通 RuntimeStore 事务的命令
均适用上述协调循环。命令已经持有 GitCache Write 事务时，repair 核心复用该事务进入诊断锁定访问；当前仅持有
GitCache ReadOnly 事务时，必须先退出该事务，再打开 GitCache Write 事务执行 repair；当前尚未访问 GitCache
时，协调器只在需要 repair 时打开一个 GitCache Write 事务。不得在同一个 ReadOnly 事务内嵌套升级为 Write。
`GitCache -> RuntimeStore` 只适用于这类同时持有两种锁的工作流。`.command.lock` 覆盖检测、repair 和重试，
避免 RuntimeStore 锁释放后另一条 doctidex-git 命令进入工作模型业务工作流。repair 自身中断时，尚未删除的
残留 journal 使下一次命令能够再次感知并处理；
它不创建自己的事务目录。

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
- [x] 残留事务由 repair 在诊断锁定访问内处理、普通事务的释放锁后 `repair-required` 协调与操作重试、显式
      `validate` 和 `init` 的只诊断边界，以及 repair 不创建自身事务目录的规则已定义。
- [x] repair 的幂等性、失败时保留 journal 以供后续继续尝试及用户内容保护要求已定义。
- [x] repair 沿用需求 0002-01 已定义的错误码，不建立独立错误目录。

## 8. 实施与状态

本子需求目前为 `draft`。修复范围、生命周期和错误复用规则已完成一次同步；获得明确批准前，
不授权修改 CLI 实现、测试或相关 Architecture 文档。
