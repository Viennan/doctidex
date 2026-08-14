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

本需求只要求在遵守协议的 doctidex-git 进程之间协调 Store 访问。同一工作流需要同时持有两个 Store 的锁时，
必须按 `GitCache -> RuntimeStore` 获取；只操作 RuntimeStore 的工作流不因此预先打开 GitCache。残留
journal 的 repair 在 RuntimeStore 锁已经释放后发生：它复用当前 GitCache Write 事务，或按需打开一个，
因而不在已持有 RuntimeStore 锁时反向获取 GitCache 锁。

第一版可以让只读事务也获取排他锁，以减少读写锁实现和恢复路径的复杂度；后续如有性能需要，
再增加共享锁模式。

### 3.2 Python 事务抽象

`RuntimeStore` 将普通事务分为两个明确的上下文接口：

```python
with runtime_store.read_only_transaction() as tx:
    state = tx.state

with runtime_store.write_transaction() as tx:
    tx.replace_state(state)
```

两类普通事务都会获取 RuntimeStore 锁，并在 `__enter__()` 中只检查是否存在残留 journal。不存在残留
journal 时，事务读取一次完整状态快照；若发现残留 journal，则释放当前 RuntimeStore 锁并报告内部的
`repair-required` 信号。命令协调器捕获该信号、运行 repair，并重试触发信号的 RuntimeStore 操作；该信号
最多处理 3 次，仍有残留事务时返回结构化的 `store.transaction.unavailable`，提示用户排查环境或重试。
普通事务不保存 repair 回调或重试状态。只读事务不提供 `replace_state()`，也不创建事务目录。写事务只有在
某次操作成功建立无残留的快照后，才创建事务目录、`stage/`、`backup/` 及初始 `journal.json`；因此业务
事务自身异常终止时，下一次命令能够感知遗留事务并再次进入该流程。
写事务正常退出时才根据 `replace_state()` 的结果发布变更；上下文内抛出异常或没有变更时清理该初始事务目录。

业务命令只能通过写事务修改 Store，不得直接写入正式状态文件。

显式 `validate` 另使用只用于诊断的读取接口。该接口同样获取 RuntimeStore 锁并读取快照，但不恢复、
清理或创建 journal，也不修改 CacheStore；它不提供状态替换接口。它的唯一用途是在不改变当前工作模型的
前提下建立一致的诊断视图，不能替代普通事务供其他命令执行业务工作流。

`repair` 使用与 `validate` 相同的诊断锁定访问。该访问获取 RuntimeStore 锁但不为 repair 自身创建
`.transactions/<transaction-id>/`、journal、stage 或 backup；repair 在锁内显式处理残留 journal、恢复
JSON 和执行物理修复。只有在处理已有残留 journal 时，repair 才能依其 `backup/` 恢复旧 JSON。repair
使用的外层 GitCache 事务和 RuntimeStore 诊断锁定访问均由命令级协调器按 `GitCache -> RuntimeStore`
顺序建立；repair 完成所有修复后才清理其处理的残留 journal。

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

任何命令簇在 bare repository 上创建 Git worktree，或把可复用的 Git worktree 切换到目标 commit 前，
都必须先由命令簇工作流确保目标 commit 在该 bare repository 中可用。该固定流程属于 GitCache
transaction 覆盖的命令簇操作，而不是 GitCache 的公开能力：

1. 使用 `git cat-file -e <commit-hash>^{commit}` 验证目标对象是 commit；命中后继续创建或切换。
2. 未命中时，在仍持有当前 GitCache transaction 的条件下按该 commit hash 从 `origin` 获取 object，
   然后再次验证。已命中的 ReadOnly transaction 不因 object 缺失而调用 `load`；ReadOnly 约束的是
   CacheStore 状态，不妨碍命令簇在 callback 内追加 Git object。仅 bare repository 本身未命中时，才按
   本节既有规则退出 ReadOnly transaction、进入 Write transaction 并调用 `load`。
3. 获取或复验失败时，命令簇按自身的来源或恢复错误转换失败；不得把“bare repository 缺少目标
   commit”表述为普通 worktree 目标路径冲突。
4. 该流程不重新选择 revision。保存的 commit hash（例如 tracked Installation 的 `commit-hash`）始终是
   唯一目标；branch/tag selector 只由显式使用 selector 的创建工作流解析。

`import install`、`import restore` 和 `worktree create` 均适用该流程。前两者以及 URL 来源的
`worktree create` 在解析 selector 时通常已取得目标 object；流程仍作为所有 Git worktree 创建/切换
操作的共同前置条件。使用 `--install-id` 创建 Worktree 和 `import restore` 必须依靠该流程补齐可能
缺失的已记录 commit。

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
终止，目标文件仍处于旧状态；下一次普通事务报告 `repair-required` 后，由 repair 将其与当前物理状态
一并处理并在成功后清理。

### 5.2 提交协议

事务提交分为准备、发布和完成三个阶段：

```text
获取 RuntimeStore 锁、检查遗留事务
  ├─ 无残留：读取快照、完成事务准备
  └─ 有残留：释放 RuntimeStore 锁并报告内部的 repair-required 信号
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

每次建立普通 `RuntimeStore` 事务时，只在锁保护下检查是否存在残留 journal；它不负责根据 journal 状态
恢复 JSON，也不负责清理 journal。发现残留时，普通事务释放 RuntimeStore 锁并报告仅供命令协调器使用的
`repair-required` 内部信号；它不持有 repair 回调、不获取 GitCache、不进行重试，也不会向调用方提供状态
快照或创建自己的 journal。诊断读取接口不触发此信号。残留 journal 的分类、JSON 恢复、物理 repair 和最终
清理均由 repair 工作流负责。repair 与 `validate` 使用同一种只加 RuntimeStore 锁、不创建事务目录的诊断
读取访问；残留处理是 repair 在该锁定访问内部显式执行的工作，而不是该访问的进入、退出或其他准备阶段职责：

| Journal 状态及观察结果 | repair 在锁定访问内的动作 | 清理时机 |
|---|---|---|
| `committed`，且所有目标均为 `new-sha256` | 将该残留视为已提交；它没有待执行的恢复或物理修复 | 先标记该项已处理；待本次 maintenance repair 的其他 journal 和全部物理修复成功后统一清理。 |
| `prepared` 或 `publishing`，且所有目标均为 `new-sha256` | 保留当前 JSON，以当前 JSON 为基准执行物理 repair | 所有 repair 成功后才清理该事务目录。 |
| `prepared` 或 `publishing`，且所有目标均为旧状态 | 保留当前旧 JSON，以当前 JSON 为基准执行物理 repair | 所有 repair 成功后才清理该事务目录。 |
| `prepared` 或 `publishing`，且目标处于新旧混合状态 | 使用 backup 将 JSON 恢复为旧状态，保留 journal，再以恢复后的 JSON 执行物理 repair | 所有 repair 成功后才清理该事务目录。 |
| `committed` 但目标并非全部为 `new-sha256`，或任一目标既不是新状态也不是旧状态 | 不自动覆盖或清理，返回 `recovery-required` | 保留 journal，命令停止并提示用户排查。 |

repair 必须在其锁定访问内完成所有 JSON 恢复、残留 journal 分类、物理修复和必要的 Git ignore/符号链接/worktree
操作完成后，才删除本次处理的全部残留事务目录，包括已判定为 `committed` 的项。repair 自身在此之前
中断时，所有残留 journal 必须继续存在，使下一次普通事务能够再次报告 `repair-required`；重复处理必须幂等，
不得生成第二个相互矛盾的恢复事务。

repair 完成 journal 所要求的 JSON 恢复后，不额外扫描目标文件是否再次匹配 `old-sha256`；
同一 repair 过程的物理状态检查由 repair 规则完成。RuntimeStore 锁和命令级协调锁在本次 repair 内
排除遵守协议的并发 doctidex-git 写入；写入或目录持久化失败仍按事务不可用处理，journal 保留以供
下一次恢复判断。

### 5.4 残留事务的检测委派与 repair

可写事务从写入 `prepared` journal 起，就可能在其上下文中执行安装、符号链接、worktree 或 Git
ignore 等真实文件系统操作。因此任何残留事务均须由 repair 处理；`committed` 且全部目标文件均为
`new-sha256` 的项仅在 repair 锁定访问内被判定为已完成并跳过物理修复。普通事务不得自行清理或恢复
任何残留 journal。

`RuntimeTransaction.__enter__()` 发现残留 journal 时，业务事务尚未准备完成，也尚未向调用方提供状态
快照。它释放当前 RuntimeStore 锁并报告 `repair-required`，由命令级协调器围绕实际 RuntimeStore 操作执行
以下重试，而非在命令开始前打开一个空的普通读事务作为预检：

1. 运行一个以普通 RuntimeStore 事务开始的、尚未执行物理业务动作的操作闭包。若它未报告
   `repair-required`，该闭包正常完成。
2. 若报告该信号，RuntimeStore 锁已经释放。`.command.lock` 仍覆盖本次命令，其他遵守协议的命令不得
   在 repair 与重试之间进入工作模型业务流程。
3. 当前闭包已经持有 GitCache Write 事务时，协调器将该事务传给 repair 核心；repair 复用该访问并只在其
   内部打开 RuntimeStore 诊断锁定访问。当前闭包持有 GitCache ReadOnly 事务时，必须先退出该事务，再为
   repair 打开 GitCache Write 事务；不得嵌套或原地升级同一 GitCache 锁。当前闭包未持有 GitCache 事务时，
   协调器仅为 repair 打开一个 GitCache Write 事务，再调用同一 repair 核心。
4. repair 成功后，重试同一个操作闭包。需要重新取得 GitCache 的闭包仍按 ReadOnly 优先、cache miss 后
   Write `load` 的常规模式获取缓存；该闭包重新建立普通 RuntimeStore 事务并自然复检残留 journal。它不是
   通过恢复旧事务对象继续执行，也不重放任意整个 CLI 命令。
5. `repair-required` 最多允许出现 3 次。第三次 repair 后再次报告时，停止该命令并返回
   `store.transaction.unavailable`，其中 `details` 至少包含 `store: "runtime"`、
   `phase: "recovery-repair"`、`attempts: 3` 和最后一次检测到的 `transaction-ids`。`message.summary`
   必须提示用户排查当前环境或在问题消除后重试。

普通 RuntimeStore 事务只产生内部协调信号，不知道或保存 GitCache、repair 函数或命令级重试状态。repair
核心接收调用方提供的 GitCache Write 访问，不得再打开嵌套的 GitCache 事务；显式 `repair` 命令自行打开该
访问后调用核心。repair 自身是特殊维护过程，不创建自己的事务目录，且不能作为嵌套命令触发重试。对于已
确认的 `committed` 残留，它标记该项无需物理 repair，并在本次 repair 的全部处理完成后统一清理。显式
`validate` 从不打开普通 RuntimeStore 事务，只报告诊断读取中发现的待恢复 journal；已有工作空间上的
`init` 同样只执行诊断校验而不触发 repair。

`import install` 的 branch/tag 选择，以及 URL 来源 `worktree create` 的 branch/tag 选择，必须在其已持有的
GitCache 事务中先解析为本次操作的具体 commit hash。发生 repair/retry 时，该操作闭包复用当前 GitCache
Write 事务和这个已解析 hash；若原先使用 ReadOnly 事务而为 repair 退出，则在重试中重新取得缓存但仍复用
该 hash，不再次同步远程或解析 selector；`--commit` 与 Installation 来源本已提供固定 hash，不发生重新选择。

repair 与 `validate` 不通过诊断中间层传递数据。对于两者共同检查的模型关系和物理对象事实，实现必须
复用同一组底层模型浏览、关联和状态判定逻辑：`validate` 将这些事实转换为诊断，repair 将其转换为已
定义的修复动作；不得由两套相互独立的扫描规则产生偏离的判断。repair 无法完成或遇到
`recovery-required` 时，保留 journal，原命令停止其业务操作并返回相应的结构化错误。

## 6. 跨 Store 与物理文件系统协调

`import` 和 `worktree` 可能同时使用 `GitCache`、`RuntimeStore` 及实际工作目录。外部命令不得
直接嵌套 `CacheStore` 事务；对缓存的所有访问必须经由 GitCache 的 ReadOnly/Write 事务。命令级
协调器必须：

1. `GitCache -> RuntimeStore` 仅约束同一工作流需要同时持有两类锁的情形，以避免不同命令形成死锁环；
   它不是每条命令的预检或预先获取 GitCache 的要求。外部命令不直接管理 CacheStore 锁。命令需要同时
   操作 cache repository 和 RuntimeStore 时，必须在持有 GitCache 事务的回调内打开 RuntimeStore 事务，
   并在两者仍持有时完成相应的外部 Git 操作。
2. 普通 RuntimeStore 事务发现残留 journal 后已经释放 RuntimeStore 锁。命令协调器按第 5.4 节复用当前
   GitCache Write 事务，或按需新开一个，再使 repair 获取 RuntimeStore 诊断锁；不得在已持有 RuntimeStore
   锁时反向获取 GitCache，也不得以空 RuntimeStore 事务预先触发 repair。
3. 在完成必要的缓存查询、来源校验和 RuntimeStore 模型读取后，再创建或替换 install/worktree 等实际
   目录；这些使用 cache repository 的目录操作必须仍由其 GitCache 事务覆盖。
4. 将 RuntimeStore 元数据提交作为命令工作模型可见性的最终步骤；物理目录操作失败时，不得把
   相应 Installation、Ref 或 Worktree 记录发布为完成状态。
5. 物理目录暂存、替换或补偿的具体策略由对应命令工作流确定；它们不得声称为 bare repository
   与 RuntimeStore 提供数据库式原子性。
6. 接受 CacheStore 中已写入但尚未登记的 Git object；该残留不构成 RuntimeStore 模型违规。

该协调机制是命令级补偿事务，不宣称对 Git worktree 文件和两个 Store 提供数据库式全局 ACID。

## 7. 内部并发与错误转换

Store 锁只协调遵守锁和事务协议的 doctidex-git 进程。事务保存正式状态文件的旧 hash，仅用于
RuntimeStore journal 的发布和恢复判断，不作为外部修改的并发防御机制。用户、编辑器或其他程序
直接修改文件所形成的 race 不在本需求的保证范围内。

锁无法获取、journal 无法读写、暂存文件无法发布或恢复失败时，转换为需求 0002-01 定义的
`store.transaction.unavailable` 公共错误结构，并在 `details` 中说明 `store`、`phase`、状态路径
和恢复事务 ID。底层 `OSError`、JSON 异常或 Git 文本不得直接作为用户可见错误。

显式 `validate` 必须以诊断读取接口检查 `.transactions/`；目录不存在时视为空。它不得执行恢复，
也不得创建或清理事务记录。发现一个或多个状态为 `prepared` 或 `publishing` 的 RuntimeStore journal
时，必须返回 `valid: false`，仅报告这些事务待恢复，并立即结束本次校验；不得继续读取模型状态、
检查根入口、扫描 Markdown 或检查 link。此时 `work-model.valid.details.content-scan` 固定为 `skipped`。
可读取的每个待恢复 journal 以 `transaction.recovery.required` 违规表示；journal 无法读取或无法判定
状态时，命令返回 `store.transaction.unavailable`。仅当所有目标均为 `new-sha256` 的 `committed`
journal 不单独构成待恢复违规；其清理由后续 repair 负责。普通事务检测到任何残留 journal 后，均由
命令协调器处理内部 `repair-required` 信号。

## 8. 实现边界

推荐的内部组件职责如下：

| 组件 | 职责 |
|---|---|
| `FileLock` | 获取、保持和释放跨进程文件锁 |
| `AtomicFileWriter` | 临时文件、`fsync`、`os.replace` 和目录持久化 |
| `CacheStoreTransaction` | 读取 `CacheItem`、清理 `preparing` 记录，以及立即发布 `status.json` 记录 |
| `GitCacheTransaction` | 对外提供 Git cache 的 ReadOnly/Write 接口，并通过 Write `load` 管理 CacheItem 生命周期和 bare repository 加载 |
| `TransactionJournal` | journal 的创建、阶段更新、恢复判断和清理 |
| `RuntimeStoreTransaction` | RuntimeStore 残留事务检测、状态快照、领域模型修改、暂存和提交 |
| `RuntimeDiagnosticTransaction` | 提供与 validate 相同的只加锁读取访问；repair 在该访问内分类残留 journal、恢复 JSON、执行物理 repair，并在所有修复成功后清理残留 journal |
| `StoreCoordinator` | 协调 GitCache、RuntimeStore 与物理目录的命令级副作用和补偿 |

这些组件不改变 `CacheStore`、`RuntimeStore` 的领域模型和权威文件划分。

## 9. 验收标准

- [ ] 两个 doctidex-git 进程不能同时提交同一 `CacheStore` 或 `RuntimeStore`。
- [ ] 单个状态文件写入使用临时文件和原子替换，不产生半写 JSON。
- [ ] `RuntimeStore` 多文件事务具有 `prepared`、`publishing`、`committed` 阶段和可持久化 journal。
- [ ] 在每个提交阶段模拟进程中断后，下一次事务能够完成提交、恢复旧状态或明确报告不可自动恢复。
- [ ] 显式 `validate` 使用只锁定、不恢复且不创建 journal 的诊断读取事务；发现 `prepared` 或
      `publishing` journal 时，仅报告待恢复事务并跳过其余校验。
- [ ] 普通 RuntimeStore 事务只检测残留 journal；检测到后释放当前 RuntimeStore 锁并报告内部
      `repair-required` 信号。命令协调器运行不创建自身 journal 的 repair 锁定访问，再重试对应的
      RuntimeStore 操作；该信号最多处理 3 次，耗尽后返回含 `attempts: 3` 和残留 transaction ID 的
      `store.transaction.unavailable`；repair 不调用或消费 `validate`。
- [ ] CacheStore 的 `preparing` 记录及其 repository 在下一次事务进入时可直接清理，且追加式 Git object 残留不会导致 RuntimeStore 状态错误。
- [ ] GitCache 对外只提供 ReadOnly/Write 事务；Write 的 `load` 复用可用缓存、登记 `preparing` 并在加载完成后发布 `published`。
- [ ] 涉及两个 Store 的命令通过 GitCache 事务与 RuntimeStore 协调；需要同时持有时固定为
      `GitCache -> RuntimeStore`，但不为纯 RuntimeStore 命令预先打开 GitCache。repair 能复用当前
      GitCache Write 事务，使用 cache repository 的外部 Git 操作保持在 GitCache 事务内。
- [ ] install/worktree 的物理目录失败时，模型状态不会发布为已完成状态。
- [ ] 事务实现不改变当前 JSON 文件的权威性、tracked/untracked 投影规则和模型生命周期。

## 10. 状态

本子需求目前为 `draft`，用于审阅事务实现边界和恢复协议；本次补充已细化 CacheStore 的
`preparing`/`published` 状态、ReadOnly/Write 事务以及 GitCache 的对外事务封装。现有代码中的
CacheStore/GitCache 实现不因本次文档更新而视为已符合该协议；完成审阅并获得明确批准前，不授权
修改 CLI 实现、测试或 Architecture。后续实施计划需要单独安排该协议与现有实现的同步。
