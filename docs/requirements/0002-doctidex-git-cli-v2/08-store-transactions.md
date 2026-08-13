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

为 `CacheStore`、`GitCache` 和 `RuntimeStore` 定义可在 Python CLI 中实现的事务机制，确保多个
`doctidex-git` 进程不会同时修改同一份状态，并确保命令在进程中断后不会留下无法识别的状态文件
或缓存记录组合。

本需求采用文件系统事务模拟 Store 事务，不引入数据库作为状态权威来源。

## 2. 适用范围与保证边界

### 2.1 必须提供的保证

- 同一个 `CacheStore` 或 `RuntimeStore` 的 doctidex-git 进程间写操作互斥。
- 事务中的读取发生在获得锁之后，并使用一次完整状态快照作为内存工作副本。
- 单个状态文件通过临时文件和原子替换发布，不出现半写 JSON。
- `RuntimeStore` 的多文件发布具有可恢复的提交协议；进程中断后，下一次访问可以完成已判定的提交，
  或将 JSON 状态收敛到可由 repair 继续处理的安全状态。

### 2.2 不提供的保证

- 不把多个普通工作区文件变成操作系统级的整体原子修改；`install-path` 和 `work-path` 的文件
  操作需要由命令工作流提供暂存和补偿清理。
- 不回滚已经写入 bare Git repository 的追加式 Git object。缓存中的未登记 object 可以保留，
  后续由缓存维护流程清理。
- 不对用户、编辑器或其他非 doctidex-git 程序直接修改状态文件或物理目录所形成的 race 提供
  防御性保证；Store 不以提交前 snapshot hash 对比等局部检查伪装为能够解决这类问题。
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

`RuntimeStore` 将事务分为两个明确的上下文接口：

```python
with runtime_store.read_only_transaction() as tx:
    state = tx.state

with runtime_store.write_transaction() as tx:
    tx.replace_state(state)
```

两类事务都会获取 RuntimeStore 锁、恢复遗留 journal 并读取一次完整状态快照。只读事务不提供
`replace_state()`，也不创建事务目录。写事务在 `__enter__()` 完成上述恢复和快照后，立即创建
事务目录、`stage/`、`backup/` 及初始 `journal.json`；因此进程在上下文中异常终止时，下一次
命令能够感知遗留事务并按恢复协议处理。写事务正常退出时才根据 `replace_state()` 的结果发布
变更；上下文内抛出异常或没有变更时清理该初始事务目录。

业务命令只能通过写事务修改 Store，不得直接写入正式状态文件。

## 4. `CacheStore` 与 `GitCache` 事务要求

### 4.1 CacheStore 的内部记录

`CacheItem` 不是用户级领域模型，而是 `CacheStore` 对特定 Git 仓库缓存的内部记录：

```python
@dataclass(frozen=True, slots=True)
class CacheItem:
    status: CacheItemStatus  # preparing | published
    git_url: str              # 在当前 CacheStore 中唯一
    path: str                 # 相对于 cache-path 的 bare repository 路径
```

`status` 仅在 CacheStore/GitCache 内部使用，不出现在 doctidex-git 的命令返回结果中，也不参与
RuntimeStore 的工作模型。`status.json` 的结构保持为 `records` 数组；每个 URL 至多有一条记录。

`preparing` 表示记录已经登记，但其对应的 bare repository 尚未完成加载；`published` 表示该记录
可供 GitCache 的后续操作使用。该状态机不是数据库提交状态，而是进程中断后让下一次 CacheStore
事务能够识别并清理未完成加载的恢复标记。

### 4.2 CacheStore 事务接口

CacheStore 同样区分只读和写两类事务：

```python
with cache_store.read_only_transaction() as tx:
    records = tx.records
    item = tx.find(git_url)

with cache_store.write_transaction() as tx:
    records = tx.records
    tx.replace_records(records)
```

两类事务在进入上下文时获取 `cache-path/.lock` 并读取 `status.json`。只读事务只提供记录查询，
不提供 `replace_records`；写事务提供 `replace_records`。`replace_records` 不是退出时暂存的
变更，而是在调用时立即通过临时文件、`flush`、`os.fsync`、`os.replace` 和目录级 `fsync` 写入
`status.json`。事务退出时只负责释放锁，不再隐式提交或回滚另一次状态。

事务进入时必须先处理所有 `preparing` 记录：对每条记录按其 `path` 定位缓存目录，直接删除对应
的 bare repository（不检查仓库内容、不尝试恢复），再从当前记录集合中移除该记录，并立即发布清理
后的 `status.json`。该恢复动作是 CacheStore 事务启动协议的一部分，因此只读事务也会执行；它不
构成对用户级缓存提供的完整一致性保证。

`preparing` 记录的路径必须是 CacheStore 根据内部规则生成且位于 `cache-path` 下的相对路径。GitCache
使用 `<domain>/<repository-path>`：`domain` 为 Git URL 的仓库域名，`repository-path` 为
URL 路径移除末尾 `.git` 后的分层目录。例如 `git@github.com:Viennan/doctidex.git` 对应
`github.com/Viennan/doctidex`。本地路径或 `file` URL 使用 `local` 作为 `domain`。清理操作
不得把用户输入直接当作任意文件系统删除目标。`published` 记录对应的 repository 不存在或不可用时，
CacheStore 不负责恢复；由 GitCache 的写事务通过 `load` 决定是否重新加载。

### 4.3 GitCache 对外事务封装

外部模块不得直接操作 CacheStore，也不得绕过 GitCache 事务访问缓存。GitCache 在 CacheStore
事务之上提供面向调用方的两类事务，负责缓存查询和本地 bare repository 的获取：

| GitCache 事务 | 能力 |
|---|---|
| ReadOnly | 查询 URL 对应的 `published` CacheItem，并取得其本地 bare repository；不修改 `status.json`，也不提供 `load` 或删除缓存接口。 |
| Write | 提供 ReadOnly 的查询和 repository 获取，并额外提供 `load(git_url)`；`load` 在需要时登记/准备 CacheItem、加载本地不存在的 bare repository，完成后将记录发布为 `published`。 |

`GitCache` 应提供 `with_repository(git_url, operation)` 作为其他模块访问缓存的通用 helper。
它统一执行“先读、未命中后加载”的事务选择；选择到可用 repository 后，依赖该 repository 的完整
命令操作必须仍在所选 GitCache 事务内执行：

```python
def with_repository(git_url, operation):
    with self.read_only_transaction() as transaction:
        repository = transaction.find(git_url)
        if repository is not None:
            return operation(repository)

    with self.write_transaction() as transaction:
        repository = transaction.load(git_url)
        return operation(repository)
```

只读事务未找到可用的 `published` repository 时，调用方必须先退出只读事务，再重新打开写事务并
调用 `load`；不得在只读事务内执行加载，也不得嵌套打开写事务。这样可以保持事务类型与锁的边界
清晰，并让 `load` 在新的 CacheStore 快照上处理残留 `preparing` 记录或不可用缓存。`operation` 包含
revision 的同步和解析，以及使用该 bare repository 创建、替换或移除 install/worktree 等外部 Git
操作；这些操作不得在只取得 `Path` 后关闭 GitCache 事务再执行。

`GitCache` 不负责 revision 选择、fetch、worktree 创建或移除等命令簇工作流。后续 `import` 和
`worktree` 阶段在 GitCache 事务提供的 bare repository 上自行实现这些操作及其领域错误转换；事务
生命周期由 `with_repository` 的 callback 保持，不能因此把命令簇工作流移入 `GitCache`。

`GitCache` 的 Write 事务执行 `load` 时，必须先在当前 CacheStore 快照中检查 URL 和记录路径：

1. 已存在 `published` 记录且对应 repository 可用时，直接复用该记录，不重复 clone。
2. 记录不存在，或记录为 `published` 但对应 repository 不可用时，生成受 CacheStore 管理的路径，
   先以 `preparing` 状态调用 `replace_records` 立即登记，再执行 bare repository 的 clone/恢复。
3. repository 准备成功后，将同一记录改为 `published`，再次调用 `replace_records` 立即发布。
4. repository 准备失败或进程中断时，保留 `preparing` 记录；下一次任意 CacheStore 事务进入时按
   4.2 节直接删除该 repository 并移除记录，之后由新的 Write 事务重新执行 `load`。

GitCache 的事务不提供 `remove` 缓存接口。`import remove`、worktree remove 或其他外部模块的
移除操作只删除其自身创建的安装目录、worktree 或引用，不删除 CacheStore 中的 published cache。
缓存清理不属于本需求范围。

### 4.4 事务语义与保证边界

CacheStore/GitCache 事务不是严格意义上的数据库事务。它们只在遵守锁和事务接口的
doctidex-git 进程之间提供一定程度的并发协调，并在进程崩溃后把缓存状态清理到可重新开始的
合法状态；不承诺恢复到崩溃前的精确状态。

CacheStore 只保护 `status.json` 中的记录与本地 cache repository 目录之间的对应关系。bare
repository 中的 fetch、clone、object 写入等 Git 操作不纳入可回滚范围；失败后产生的 Git object
可以保留。该边界不改变 RuntimeStore 多文件事务及其 journal 协议。

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

写事务刚进入上下文时尚未得知业务要发布的目标内容，因此初始 `prepared` journal 为每个
RuntimeStore 状态文件记录当前 `old-sha256`，并使用一个与旧 hash 不相等的保留 provisional
`new-sha256` 标记“尚未进入提交准备”。该 journal 只用于持久化写事务已经开启这一事实；正式
提交开始后，事务会用实际变更文件集合及其新 hash 原子替换该 `prepared` journal。若进程在此之前
终止，目标文件仍处于旧状态，下一次事务将其按回滚完成并清理。

### 5.2 提交协议

事务提交分为准备、发布和完成三个阶段：

```text
获取锁、恢复遗留事务并读取快照
  ↓
写事务目录及初始 prepared journal
  ↓
生成 stage 与 backup，并写入 prepared journal
  ↓
写入 publishing journal
  ↓
逐个 os.replace(stage, target)
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
5. 所有目标文件发布完成后才写入 `committed`；提交完成后才删除 backup 和 journal。

只发生变化的状态文件可以不加入 `entries`，但重建结果和投影规则必须与未优化时一致。

### 5.3 恢复协议

每次建立 `RuntimeStore` 事务时，必须先在锁保护下扫描未完成的 journal。是否可直接清理并跳过
内部 `repair` 同时取决于 journal 状态和目标文件状态：

| Journal 状态及观察结果 | 恢复动作 | 后续行为 |
|---|---|---|
| `committed`，且所有目标均为 `new-sha256` | 直接清理事务目录 | 报告 `committed`；可继续命令，不运行内部 `repair`。 |
| `prepared` 或 `publishing`，且所有目标均为 `new-sha256` | 清理事务目录，保留当前 JSON 状态 | 报告 `repair-required`；以当前 JSON 为基准运行内部 `repair`。 |
| `prepared` 或 `publishing`，且所有目标均为旧状态 | 清理 stage、backup 和 journal | 报告 `repair-required`；以当前 JSON 为基准运行内部 `repair`。 |
| `prepared` 或 `publishing`，且目标处于新旧混合状态 | 使用 backup 恢复全部旧文件，再清理事务目录 | 报告 `repair-required`；以已恢复的 JSON 为基准运行内部 `repair`。 |
| `committed` 但目标并非全部为 `new-sha256`，或任一目标既不是新状态也不是旧状态 | 不自动覆盖，保留 journal | 报告 `recovery-required`；命令停止，不运行 `repair`。 |

恢复过程必须幂等。恢复中再次中断时，下一次事务可以根据同一 journal 继续判断，不得生成第二个
相互矛盾的恢复事务。

恢复过程完成其 journal 所要求的旧状态写入后，不额外扫描目标文件是否再次匹配 `old-sha256`。
RuntimeStore 锁已经排除遵守锁协议的并发 doctidex-git 写入；写入或目录持久化失败仍按事务不可用
处理，journal 保留以供下一次恢复判断。

### 5.4 残留事务后的内部修复

可写事务从写入 `prepared` journal 起，就可能在其上下文中执行安装、符号链接、worktree 或 Git
ignore 等真实文件系统操作。因此残留事务只有在 journal 已为 `committed` 且全部目标文件均为
`new-sha256` 时，才可以直接清理并跳过修复。任何成功处理的 `prepared` 或 `publishing` 残留事务
都必须触发一次内部 `repair`，无论其 JSON 状态最终表现为全新、全旧还是由混合状态恢复为旧状态。

RuntimeStore 事务恢复必须向命令级协调器报告 `committed`、`repair-required` 或
`recovery-required`。当本次启动发现遗留事务并报告 `repair-required` 后：

- `validate` 和 `init` 不执行内部 `repair`；前者只报告待恢复事务，后者按初始化规则处理工作模型。
- 其他命令必须在继续其业务工作流前，以当前 JSON 状态为基准执行一次内部 `repair`。
- 内部 `repair` 使用与显式 `repair` 相同的修复规则，但不递归触发自身，也不额外输出独立命令结果。
- 内部 `repair` 无法完成时，原命令停止其业务操作并返回相应的结构化错误。

若恢复结果为 `committed`，不执行该内部修复；若为 `recovery-required`，命令不得继续访问或修改
工作模型，直接返回 `store.transaction.unavailable`。

## 6. 跨 Store 与物理文件系统协调

`import` 和 `worktree` 可能同时使用 `GitCache`、`RuntimeStore` 及实际工作目录。外部命令不得
直接嵌套 `CacheStore` 事务；对缓存的所有访问必须经由 GitCache 的 ReadOnly/Write 事务。命令级
协调器必须：

1. 按 `GitCache -> RuntimeStore` 的固定顺序获取两类事务所需的锁，避免不同命令形成死锁环；
   外部命令不直接管理 CacheStore 锁。命令需要同时操作 cache repository 和 RuntimeStore 时，必须在
   持有 GitCache 事务的回调内打开 RuntimeStore 事务，并在两者仍持有时完成相应的外部 Git 操作。
   仅为取得后续缓存 URL 而进行的、已经结束的 RuntimeStore 查询不构成嵌套锁。
2. 在完成必要的缓存查询、来源校验和 RuntimeStore 模型校验后，再创建或替换 install/worktree
   等实际目录；这些使用 cache repository 的目录操作必须仍由其 GitCache 事务覆盖。
3. 将 RuntimeStore 元数据提交作为命令工作模型可见性的最终步骤；物理目录操作失败时，不得把
   相应 Installation、Ref 或 Worktree 记录发布为完成状态。
4. 物理目录暂存、替换或补偿的具体策略由对应命令工作流确定；它们不得声称为 bare repository
   与 RuntimeStore 提供数据库式原子性。
5. 接受 CacheStore 中已写入但尚未登记的 Git object；该残留不构成 RuntimeStore 模型违规。

该协调机制是命令级补偿事务，不宣称对 Git worktree 文件和两个 Store 提供数据库式全局 ACID。

## 7. 内部并发与错误转换

Store 锁只协调遵守锁和事务协议的 doctidex-git 进程。事务保存正式状态文件的旧 hash，仅用于
RuntimeStore journal 的发布和恢复判断，不作为外部修改的并发防御机制。用户、编辑器或其他程序
直接修改文件所形成的 race 不在本需求的保证范围内。

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
| `CacheStoreTransaction` | 读取 `CacheItem`、清理 `preparing` 记录，以及立即发布 `status.json` 记录 |
| `GitCacheTransaction` | 对外提供 Git cache 的 ReadOnly/Write 接口，并通过 Write `load` 管理 CacheItem 生命周期和 bare repository 加载 |
| `TransactionJournal` | journal 的创建、阶段更新、恢复判断和清理 |
| `RuntimeStoreTransaction` | RuntimeStore 快照、领域模型修改、暂存、提交和恢复 |
| `StoreCoordinator` | 协调 GitCache、RuntimeStore 与物理目录的命令级副作用和补偿 |

这些组件不改变 `CacheStore`、`RuntimeStore` 的领域模型和权威文件划分。

## 9. 验收标准

- [ ] 两个 doctidex-git 进程不能同时提交同一 `CacheStore` 或 `RuntimeStore`。
- [ ] 单个状态文件写入使用临时文件和原子替换，不产生半写 JSON。
- [ ] `RuntimeStore` 多文件事务具有 `prepared`、`publishing`、`committed` 阶段和可持久化 journal。
- [ ] 在每个提交阶段模拟进程中断后，下一次事务能够完成提交、恢复旧状态或明确报告不可自动恢复。
- [ ] `validate` 发现 `prepared` 或 `publishing` journal 时，仅报告待恢复事务并跳过其余校验。
- [ ] CacheStore 的 `preparing` 记录及其 repository 在下一次事务进入时可直接清理，且追加式 Git object 残留不会导致 RuntimeStore 状态错误。
- [ ] GitCache 对外只提供 ReadOnly/Write 事务；Write 的 `load` 复用可用缓存、登记 `preparing` 并在加载完成后发布 `published`。
- [ ] 涉及两个 Store 的命令通过 GitCache 事务与 RuntimeStore 协调；需要嵌套时固定为
      `GitCache -> RuntimeStore`，并将使用 cache repository 的外部 Git 操作保持在 GitCache 事务内。
- [ ] install/worktree 的物理目录失败时，模型状态不会发布为已完成状态。
- [ ] 事务实现不改变当前 JSON 文件的权威性、tracked/untracked 投影规则和模型生命周期。

## 10. 状态

本子需求目前为 `draft`，用于审阅事务实现边界和恢复协议；本次补充已细化 CacheStore 的
`preparing`/`published` 状态、ReadOnly/Write 事务以及 GitCache 的对外事务封装。现有代码中的
CacheStore/GitCache 实现不因本次文档更新而视为已符合该协议；完成审阅并获得明确批准前，不授权
修改 CLI 实现、测试或 Architecture。后续实施计划需要单独安排该协议与现有实现的同步。
