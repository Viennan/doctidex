# 需求 0002-08：`CacheStore` 与 `RuntimeStore` 事务机制实现设计要求

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-08` |
| 状态 | `draft` |
| 日期 | 2026-08-10 |
| 来源 | 用户要求将 `CacheStore`、`RuntimeStore` 事务机制的技术选型与实现方案独立记录 |
| 父需求 | [需求 0002：设计 doctidex-git 命令行工具 v2.x.x](overview.md) |
| 关联子需求 | [需求 0002-01：CLI 命令行参数及返回结果结构设计](01-cli-arguments-results.md)、[需求 0002-02：设计 doctidex-git 工作模型](02-working-model.md)、[需求 0002-05：`import` 命令簇工作流与生命周期设计](05-import.md)、[需求 0002-06：`worktree` 命令簇工作流与生命周期设计](06-worktree.md) |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 影响范围 | Python CLI、`CacheStore`、`RuntimeStore`、状态文件、缓存仓库和命令级文件系统操作 |
| 文档性质 | 子 Requirement；记录实现约束与持久化协议，不授权实现 |

## 1. 需求意图

为 `CacheStore` 和 `RuntimeStore` 定义可在 Python CLI 中实现的事务机制，确保多个
`doctidex-git` 进程不会同时修改同一份状态，并确保命令在进程中断后不会留下无法识别的状态文件
组合。

本需求采用文件系统事务模拟 Store 事务，不引入数据库作为状态权威来源。

## 2. 适用范围与保证边界

### 2.1 必须提供的保证

- 同一个 `CacheStore` 或 `RuntimeStore` 的 doctidex-git 进程间写操作互斥。
- 事务中的读取发生在获得锁之后，并使用一次完整状态快照作为内存工作副本。
- 单个状态文件通过临时文件和原子替换发布，不出现半写 JSON。
- `RuntimeStore` 的多文件发布具有可恢复的提交协议；进程中断后，下一次访问可以完成提交或恢复旧状态。
- 提交前发现状态文件被事务外修改时，不覆盖外部修改。

### 2.2 不提供的保证

- 不把多个普通工作区文件变成操作系统级的整体原子修改；`install-path` 和 `work-path` 的文件
  操作需要由命令工作流提供暂存和补偿清理。
- 不回滚已经写入 bare Git repository 的追加式 Git object。缓存中的未登记 object 可以保留，
  后续由缓存维护流程清理。
- 不阻止不遵守 doctidex-git 锁约定的外部程序直接修改状态文件；这类修改通过提交前 hash 检查
  或后续 `validate` 发现。
- 不通过 `threading.Lock` 或其他仅限当前 Python 进程的锁模拟跨进程互斥。

## 3. 技术选型

### 3.1 文件锁

当前 Linux/macOS 运行范围使用 Python 标准库 `fcntl.flock` 实现 advisory lock：

| Store | 锁文件 | 锁范围 |
|---|---|---|
| `CacheStore` | `cache-path/.lock` | 该用户级缓存及其 `status.json` |
| `RuntimeStore` | `<git-root>/.doctidex-git/.lock` | 当前 Git root 的全部 RuntimeStore 状态 |

锁文件可以持久存在；进程退出或异常终止时由操作系统释放锁。所有会读取或写入对应 Store 的
doctidex-git 命令都必须遵守该锁约定。

第一版可以让只读事务也获取排他锁，以减少读写锁实现和恢复路径的复杂度；后续如有性能需要，
再增加共享锁模式。

### 3.2 Python 事务抽象

Store 应提供统一的上下文接口：

```python
with runtime_store.transaction() as tx:
    tx.imports.replace(imports)
    tx.runtime.replace(runtime)
```

事务上下文负责获取锁、恢复未完成事务、读取快照、暂存变更、提交或回滚。业务命令只能通过
事务对象修改 Store，不得直接写入正式状态文件。

事务无异常退出时提交；业务校验失败必须抛出领域异常或显式调用回滚，使上下文不发布暂存内容。

## 4. `CacheStore` 事务要求

`CacheStore` 的结构化状态只有 `status.json`，因此其状态提交采用单文件原子写入：

1. 获取 `cache-path/.lock`。
2. 读取并解析 `status.json`，重建 `CacheItem` 集合。
3. 在内存副本上完成缓存条目的增删改。
4. 将新 JSON 写入同目录临时文件，执行 `flush`、`os.fsync`，再使用 `os.replace` 发布。
5. 对缓存目录执行目录级 `fsync`，释放锁。

bare Git repository 的 fetch 和 object 写入属于追加式外部操作。事务失败时不要求删除新产生的
object；只有 `status.json` 的原子发布成功后，该缓存条目才对模型可见。

恢复或替换不匹配的 bare repository 时，应先在同一缓存目录下准备临时 repository，完成基本校验
后再发布目录；不得在未准备新 repository 前直接删除唯一可用的旧 repository。

## 5. `RuntimeStore` 多文件事务要求

### 5.1 事务目录与 Journal

事务目录位于 `<git-root>/.doctidex-git/.transactions/<transaction-id>/`，至少包含：

```text
<transaction-id>/
├── journal.json
├── stage/      # 待发布文件
└── backup/     # 提交前的旧文件副本
```

`journal.json` 使用原子临时文件写入，并记录事务阶段和每个目标文件的 hash：

```jsonc
{
  "version": 1,
  "transaction-id": "<TRANSACTION-ID>",
  "store": "runtime",
  "state": "prepared",
  "entries": [
    {
      "target": "imports.json",
      "old-sha256": "<OLD-HASH>",
      "new-sha256": "<NEW-HASH>",
      "stage": "stage/imports.json",
      "backup": "backup/imports.json"
    }
  ]
}
```

`target` 必须是 RuntimeStore 允许的固定相对路径；journal 不接受由用户输入直接拼接出的任意路径。
不存在的旧文件使用 `old-sha256: null`，不创建对应 backup。

### 5.2 提交协议

事务提交分为准备、发布和完成三个阶段：

```text
读取快照
  ↓
生成 stage 与 backup，并写入 prepared journal
  ↓
校验目标文件仍匹配 old-sha256
  ↓
写入 publishing journal
  ↓
逐个 os.replace(stage, target)
  ↓
校验全部 new-sha256
  ↓
写入 committed journal
  ↓
清理事务目录
```

具体要求：

1. 所有 stage、backup 和目标文件必须位于同一文件系统中。
2. stage 文件和 backup 文件写入后必须 `flush`、`fsync`；journal 写入后也必须 `fsync`，并对
   所在目录执行目录级 `fsync`。
3. 目标文件只能通过 `os.replace` 发布，不得直接以写模式打开正式文件。
4. 每次替换后允许其他 doctidex-git 进程继续等待锁；它们不得读取到未持有事务锁的中间状态。
5. 所有目标文件发布并校验成功后才写入 `committed`；提交完成后才删除 backup 和 journal。

只发生变化的状态文件可以不加入 `entries`，但重建结果和投影规则必须与未优化时一致。

### 5.3 恢复协议

每次建立 `RuntimeStore` 事务时，必须先在锁保护下扫描未完成的 journal：

| 观察结果 | 恢复动作 |
|---|---|
| 所有目标均为 `new-sha256` | 视为提交完成，标记完成并清理事务目录 |
| 所有目标均为旧状态 | 视为尚未发布，删除 stage、backup 和 journal |
| 目标处于新旧混合状态 | 使用 backup 恢复全部旧文件，再清理事务目录 |
| 某目标既不是新状态也不是旧状态 | 不自动覆盖，保留 journal，返回需要人工处理的存储恢复错误 |

恢复过程必须幂等。恢复中再次中断时，下一次事务可以根据同一 journal 继续判断，不得生成第二个
相互矛盾的恢复事务。

### 5.4 回滚后的内部修复

RuntimeStore 事务恢复必须向命令级协调器报告恢复结果至少为 `committed`、`rolled-back` 或
`recovery-required`。当本次启动发现遗留事务并完成 `rolled-back` 后：

- `validate` 和 `init` 不执行内部 `repair`；前者只报告待恢复事务，后者按初始化规则处理工作模型。
- 其他命令必须在继续其业务工作流前，以回滚后的 JSON 状态为基准执行一次内部 `repair`。
- 内部 `repair` 使用与显式 `repair` 相同的修复规则，但不递归触发自身，也不额外输出独立命令结果。
- 内部 `repair` 无法完成时，原命令停止其业务操作并返回相应的结构化错误。

若恢复结果为 `committed`，不执行该内部修复；若为 `recovery-required`，命令不得继续访问或修改
工作模型，直接返回 `store.transaction.unavailable`。

## 6. 跨 Store 与物理文件系统协调

`import` 和 `worktree` 可能同时使用 `CacheStore`、`RuntimeStore` 及实际工作目录。两个 Store
不得以各自独立的嵌套上下文随意加锁；命令级协调器必须：

1. 按固定顺序获取锁，统一采用 `CacheStore -> RuntimeStore`，避免不同命令形成死锁环。
2. 在两个 Store 锁都持有时完成来源、目标和模型校验。
3. 将 install/worktree 目录先创建在同一文件系统的暂存位置，成功后再发布到目标路径。
4. 将 RuntimeStore 元数据提交作为模型可见性的最终步骤；失败时删除暂存目录，必要时按命令
   journal 恢复已替换的目标目录。
5. 接受 CacheStore 中已写入但尚未登记的 Git object；该残留不构成 RuntimeStore 模型违规。

该协调机制是命令级补偿事务，不宣称对 Git worktree 文件和两个 Store 提供数据库式全局 ACID。

## 7. 并发修改与错误转换

Store 锁只约束遵守锁协议的 doctidex-git 进程。事务开始时必须保存各正式状态文件的旧 hash，
提交前重新计算并比较；若发现外部 Git 操作、编辑器或其他程序已经修改文件，事务必须终止并且
不得覆盖外部内容。

锁无法获取、journal 无法读写、暂存文件无法发布或恢复失败时，转换为需求 0002-01 定义的
`store.transaction.unavailable` 公共错误结构，并在 `details` 中说明 `store`、`phase`、状态路径
和恢复事务 ID。底层 `OSError`、JSON 异常或 Git 文本不得直接作为用户可见错误。

`validate` 必须以只读方式检查 `.transactions/`；目录不存在时视为空。发现一个或多个状态为
`prepared` 或 `publishing` 的 RuntimeStore journal 时，不得执行恢复，必须返回 `valid: false`，仅
报告这些事务待恢复，并立即结束本次校验；不得继续读取模型状态、检查根入口、扫描 Markdown 或检查
link。此时 `work-model.valid.details.content-scan` 固定为 `skipped`。可读取的每个待恢复 journal
以 `transaction.recovery.required` 违规表示；journal 无法读取或无法判定其状态时，命令返回
`store.transaction.unavailable`。状态为 `committed` 的 journal 仅待后续事务清理，不单独构成
待恢复违规。

## 8. 实现边界

推荐的内部组件职责如下：

| 组件 | 职责 |
|---|---|
| `FileLock` | 获取、保持和释放跨进程文件锁 |
| `AtomicFileWriter` | 临时文件、`fsync`、`os.replace` 和目录持久化 |
| `TransactionJournal` | journal 的创建、阶段更新、恢复判断和清理 |
| `StoreTransaction` | 快照、领域模型修改、暂存、提交和回滚 |
| `StoreCoordinator` | 跨 `CacheStore`、`RuntimeStore` 的固定锁顺序和命令级补偿 |

这些组件不改变 `CacheStore`、`RuntimeStore` 的领域模型和权威文件划分。

## 9. 验收标准

- [ ] 两个 doctidex-git 进程不能同时提交同一 `CacheStore` 或 `RuntimeStore`。
- [ ] 单个状态文件写入使用临时文件和原子替换，不产生半写 JSON。
- [ ] `RuntimeStore` 多文件事务具有 `prepared`、`publishing`、`committed` 阶段和可持久化 journal。
- [ ] 在每个提交阶段模拟进程中断后，下一次事务能够完成提交、恢复旧状态或明确报告不可自动恢复。
- [ ] `validate` 发现 `prepared` 或 `publishing` journal 时，仅报告待恢复事务并跳过其余校验。
- [ ] 提交前检测到外部状态文件 hash 改变时，不覆盖外部修改。
- [ ] CacheStore 的追加式 Git object 残留不会导致 RuntimeStore 状态错误。
- [ ] 涉及两个 Store 的命令统一遵守 `CacheStore -> RuntimeStore` 锁顺序。
- [ ] install/worktree 的物理目录失败时，模型状态不会发布为已完成状态。
- [ ] 事务实现不改变当前 JSON 文件的权威性、tracked/untracked 投影规则和模型生命周期。

## 10. 状态

本子需求目前为 `draft`，用于审阅事务实现边界和恢复协议；完成审阅并获得明确批准前，不授权
修改 CLI 实现、测试或 Architecture。
