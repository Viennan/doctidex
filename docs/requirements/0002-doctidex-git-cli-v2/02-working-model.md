# 需求 0002-02：设计 doctidex-git 工作模型

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-02` |
| 状态 | `implemented` |
| 日期 | 2026-08-08 |
| 来源 | 用户要求为 doctidex-git 工作模型建立专门的子需求并逐步完成设计 |
| 父需求 | [需求 0002：设计 doctidex-git 命令行工具 v2.x.x](overview.md) |
| 关联子需求 | [需求 0002-01：CLI 命令行参数及返回结果结构设计](01-cli-arguments-results.md) |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 影响范围 | Linux/macOS 运行环境、用户级缓存、Git root 工作空间、import 安装产物、受管理引用、worktree、`boundary-set` 和有效性校验 |
| 文档性质 | 子 Requirement；仅记录工作模型设计，不授权实现 |

## 1. 需求意图

需要定义 doctidex-git 在一个 Git root 中使用的工作模型，使 `boundary-set`、`import`、
`worktree` 和 `validate` 能够基于同一套状态、生命周期和有效性规则协作。该模型必须与
doctidex v2 目录树 Architecture 配套，但不得替代或改变其目录树身份、link 和边界语义。

## 2. 已确认范围

- 工作模型以 `doctidex-git` 解析出的 Git root 为操作范围；CLI 使用通用 `--repos-path` 指定该
  根目录。
- 模型必须说明 `boundary-set`、import 安装产物、受管理引用和 worktree 之间的关系。
- tracked install 仅跟踪元信息，不跟踪实际仓库文件；其 `install-path` 可以不存在，并由
  `import restore` 重新安装。
- 创建 import 安装路径、受管理引用和 worktree 路径时，它们自动加入 `boundary-set`。
- `validate` 必须校验当前 Git root 的工作模型是否有效，并以 `work-model.valid` 规则报告
  无效状态；其诊断结构和违规项由 [需求 0002-07：`validate` 命令簇工作流与校验设计](07-validate.md)
  定义。
- 本需求不修改 CLI 实现、测试、Architecture 或已有命令参数及返回字段。

## 3. 核心领域模型

本节记录当前已确定的工作模型实体及其字段。字段的权威状态、持久化位置和生命周期由后续
命令簇子需求展开；校验规则与诊断结构由
[需求 0002-07：`validate` 命令簇工作流与校验设计](07-validate.md) 定义。

### 3.1 `import` 命令簇

#### `Installation`

`Installation` 表示一次 import 安装产物。它关联外部 Git 仓库、已解析的 commit、安装位置和
查询 key，并以 `install-id` 标识。

```jsonc
{
  "tracked": true,
  "git-url": "",
  "commit-hash": "",
  "install-id": "",
  "install-path": "",
  "keys": [],
  "branch": "",
  "tag": ""
}
```

| 字段 | 当前含义 |
|---|---|
| `tracked` | 安装产物是否作为 tracked install 管理。 |
| `git-url` | 外部 Git 仓库 URL。 |
| `commit-hash` | 安装产物最终对应的 commit hash；branch 或 tag selector 在安装时解析并记录其当前指向的 hash。 |
| `install-id` | 安装产物标识符。 |
| `install-path` | 按 Git URL 和 revision selector 派生的安装产物路径。 |
| `keys` | `import query` 用于用户模糊搜索安装产物的 query key；其中包含内置默认值。key 的匹配与结果排序属于 `import query` 私有逻辑，不属于工作模型通用查询。 |
| `branch` | branch selector 的值；使用 tag 或 commit selector 时为空。 |
| `tag` | tag selector 的值；使用 branch 或 commit selector 时为空。 |

Installation 的 revision selector 由 `branch` 与 `tag` 字段确定：`branch` 非空时为 branch selector，
`tag` 非空时为 tag selector，两者均为空时为 commit selector；三种 selector 互斥。`commit-hash`
始终保存 Installation 最终对应的 commit。

`install-path` 不是命令输入，而是位于 `/.doctidex-git/imports/` 下的语义化派生路径：依次使用
Git URL 中仓库的 Domain、Name 和 revision selector 值。Git URL
`git@github.com:Viennan/doctidex.git` 的 branch、tag 或 commit Installation 分别位于
`/.doctidex-git/imports/github.com/Viennan/doctidex/<branch>`、
`/.doctidex-git/imports/github.com/Viennan/doctidex/<tag>` 或
`/.doctidex-git/imports/github.com/Viennan/doctidex/<commit-hash>`。selector 值包含 `/` 时，保留
其路径层级。

#### `Ref`

`Ref` 表示从一个 `Installation` 创建的受管理引用。

```jsonc
{
  "install-id": "",
  "src-sub-dir": "",
  "target-dir": ""
}
```

| 字段 | 当前含义 |
|---|---|
| `install-id` | 受管理引用所使用安装产物的标识符。 |
| `src-sub-dir` | 受管理引用源在安装仓库内的子目录。 |
| `target-dir` | 受管理引用在当前仓库中的目标目录。 |

### 3.2 `boundary-set` 命令簇

#### `BoundaryPoint`

`BoundaryPoint` 表示 `boundary-set` 中的一个节点。

```jsonc
{
  "type": "<custom | import | import-ref | worktree>",
  "path": "<REPOSITORY-INTERNAL-ABSOLUTE-PATH>"
}
```

| 字段 | 当前含义 |
|---|---|
| `type` | 节点类型：`custom`、`import`、`import-ref` 或 `worktree`。 |
| `path` | 仓库内部绝对路径。 |

### 3.3 `worktree` 命令簇

#### `Worktree`

`Worktree` 表示一个 worktree 及其来源关联。

```jsonc
{
  "url": "[${GIT-URL}]",
  "install-id": "[${INSTALL-ID}]",
  "base-commit-hash": "",
  "work-path": "<REPOSITORY-INTERNAL-ABSOLUTE-PATH>"
}
```

| 字段 | 当前含义 |
|---|---|
| `url` | 外部 Git 仓库 URL。 |
| `install-id` | 可选的关联安装产物标识符。 |
| `base-commit-hash` | Worktree 创建时实际使用的基准 commit hash。使用 Installation 创建时，它等于该 Installation 已记录的 hash；使用 URL 创建时，branch 或 tag 在创建时解析为此 hash。 |
| `work-path` | worktree 的仓库内部绝对路径。 |

`Worktree` 不持久化 URL 来源所使用的 branch 或 tag selector。它们只用于创建时确定 revision；后续
repair 依据 `base-commit-hash` 重建 URL 来源 Worktree，避免远程引用变化改变已记录工作区的 revision。
该字段不跟踪 worktree 工作区后续的提交变化，也不会因其当前 `HEAD` 改变而更新。

### 3.4 Markdown link

#### `InlineAnnotation`

`InlineAnnotation` 表示附着于单个 Markdown link 的有效结构化注释。它是从 Markdown 源码读取的瞬态
领域模型，不持久化到 RuntimeStore，也不作为 CLI 输出模型。

```python
InlineAnnotation(cross_boundary_point: str)
```

| 字段 | 当前含义 |
|---|---|
| `cross_boundary_point` | 结构化注释 `cross-boundary-point` 字段的原始路径字符串。共享领域工具先确认该值是 link 目标 path 部分的完整路径段前缀，再按 link 所在文档将其规范化为仓库内部路径；`validate` 将该结果与实际第一个跨越 BoundaryPoint 比较。 |

### 3.5 全局缓存

#### `CacheItem`

`CacheItem` 是 `CacheStore` 内部用于管理特定 Git 仓库缓存的记录，不属于 doctidex-git
面向用户的领域模型。同一 `CacheStore` 中，一个 `git-url` 只能对应一条记录。

```jsonc
{
  "status": "published",
  "git-url": "",
  "path": ""
}
```

| 字段 | 当前含义 |
|---|---|
| `status` | `CacheStore` 内部状态，仅允许 `preparing` 或 `published`，不作为外部命令结果或工作模型字段暴露。 |
| `git-url` | 外部 Git 仓库 URL，在当前 `CacheStore` 中唯一。 |
| `path` | 相对于 `cache-path` 的 bare Git repository 路径。 |

## 4. 已确认运行环境与物理目录结构

doctidex-git 当前仅设计为在 Linux 和 macOS 上运行。工作模型依赖用户级目录和具体 Git root
中的仓库级工作空间。

### 4.1 用户级目录

`DOCTIDEX-GIT-HOME` 默认为 `${HOME}/.doctidex-git`：

```text
<DOCTIDEX-GIT-HOME>/
├── cache/
│   ├── status.json
│   └── <bare-git-repositories>/
└── config.toml
```

| 路径 | 责任 |
|---|---|
| `cache/` | 用户级 Git object cache pool。以 bare Git repository 缓存同一 Git URL 的 Git object，避免频繁从远程拉取。 |
| `cache/status.json` | 记录 cache pool 状态，主要包括缓存 Git 仓库的元信息。 |
| `config.toml` | 用户级配置文件；具体选项待定。 |

### 4.2 仓库级工作空间

doctidex-git 在目标 Git root 中使用 `.doctidex-git/` 作为工作空间：

```text
<git-root>/
├── .doctidex-git/
│   ├── config.toml
│   ├── imports.json
│   ├── boundary-set.json
│   ├── import-refs.json
│   ├── runtime.json
│   ├── .transactions/
│   ├── imports/
│   └── worktrees/
└── index.md
```

| 路径 | 责任与约束 |
|---|---|
| `config.toml` | 仓库级配置文件；具体选项待定。 |
| `imports.json` | 记录 tracked import。 |
| `import-refs.json` | 记录 import refs。 |
| `boundary-set.json` | 记录 `runtime.json` 中类型为 `custom` 的 `BoundaryPoint`。 |
| `runtime.json` | 记录未投影到 tracked 文件的运行时状态，例如 untracked import install 和 worktree；必须被 Git ignore。 |
| `.command.lock` | 命令级协调锁，覆盖一个 CLI 命令的残留事务检测、释放当前 RuntimeStore 锁后的 repair、RuntimeStore 操作重试及业务工作流；必须被 Git ignore。 |
| `.transactions/` | 暂存 RuntimeStore 事务的 journal、stage 和 backup；必须被 Git ignore，按需创建。 |
| `imports/` | 用于创建 `install-path`；必须被 Git ignore，并加入 `boundary-set`。 |
| `worktrees/` | 默认用于创建 worktree `work-path` 的空间；必须被 Git ignore，并加入 `boundary-set`。 |
| `index.md` | Git root 的 doctidex 根入口。 |

## 5. 状态管理模型

### 5.1 用户级缓存配置

用户级 `<DOCTIDEX-GIT-HOME>/config.toml` 配置 bare Git repository cache 目录：

```toml
# bare git repos cache dir
# 相对路径相对于本配置文件所在目录，绝对路径直接解释为文件系统路径。
# 默认值为 `cache`。
cache-path = 'cache'
```

`cache-path` 用于初始化 `CacheStore` 的缓存目录。

### 5.2 `CacheStore`

`CacheStore` 管理 `cache-path` 指定的用户级缓存目录及其状态。默认缓存状态文件为
`<DOCTIDEX-GIT-HOME>/cache/status.json`；使用其他 `cache-path` 时，状态文件位于该目录下的
`status.json`，结构如下：

```jsonc
{
  "records": [] // CacheItem 数组
}
```

`CacheStore` 只负责 `status.json` 与记录路径上的 bare Git repository 之间的缓存状态协调，
不负责 revision 解析、fetch、clone 或 Git 对象验证。其事务协议和 `GitCache` 对外封装以
[需求 0002-08](08-store-transactions.md) 为准。

### 5.3 `RuntimeStore`

`RuntimeStore` 管理具体 Git root 的 doctidex-git 运行时状态。内存中的运行时数据包含
`boundary-set`、`imports`、`import-refs` 和 `worktrees` 四类集合；其持久化状态由 tracked 文件
和 `<git-root>/.doctidex-git/runtime.json` 共同提供。`runtime.json` 只保存未投影到 tracked
文件的部分，结构如下：

```jsonc
{
  "imports": [], // 未被投影到 imports.json 的 Installation 数组
  "worktrees": [] // Worktree 数组
}
```

状态重建时，各 tracked 文件是其负责部分的权威来源，`runtime.json` 是其余运行时数据的
权威来源；两者合并形成内存中的完整运行时数据。各文件的负责范围如下：

| 文件 | 对应运行时数据 |
|---|---|
| `boundary-set.json` | 类型为 `custom` 的 `BoundaryPoint` |
| `imports.json` | `tracked` 为 `true` 的 `Installation` |
| `import-refs.json` | 全部 `Ref` |
| `runtime.json` | 未被上述文件投影的 `Installation` 和全部 `Worktree` |

`worktree`、`Installation` 和 `Ref` 对应的 `BoundaryPoint` 不单独写入文件，而是在状态重建
过程中恢复：`Installation.install-path` 对应 `import` 类型，`Ref.target-dir` 对应
`import-ref` 类型，`Worktree.work-path` 对应 `worktree` 类型。

`worktrees` 不写入 Git tracked 文件，所有 Worktree 均不需要被 Git tracked。

`RuntimeStore` 通过区分只读和写入的事务上下文访问数据：

- 普通只读和写 Transaction 在 `__enter__()` 的准备阶段获取锁，并只检查是否存在残留 journal。没有
  残留时才读取 `runtime.json` 及各 tracked 文件、重建完整内存状态；存在残留时释放 RuntimeStore 锁，
  并报告内部 `repair-required` 信号。命令级协调器运行 repair 后重试触发信号的 RuntimeStore 操作，最多
  三次；诊断读取 Transaction 不参与此协调流程；
- Transaction 持有完整状态、维护 Installation、Ref、Worktree 和 BoundaryPoint 的索引，并负责锁、
  残留 journal 检测、业务 journal 与持久化。残留 journal 的分类、JSON 恢复、物理修复和清理由 repair
  工作流负责。索引是 Transaction 的内部数据结构，不直接构成命令簇查询 API；每次状态变更后必须
  立即与当前状态一致；
- `RuntimeModelView` 是依赖 Transaction 的更高层模型抽象，而不是 Transaction 的成员。命令簇在
  Transaction 上下文内显式创建 View；View 在 Transaction 索引之上提供公共领域查询与关联逻辑，命令
  簇不得为常规查询自行遍历状态集合或读取 Transaction 的内部索引；
- 只读 Transaction 不创建事务目录；其上下文中只能使用只读 `RuntimeModelView`。`validate` 只读取
  该视图；repair 使用同一种只加锁访问，但仅可通过专用的 repair ModelView 批量移除其
  `install-id` 已不存在的 Ref。该维护性状态修复只原子发布 `import-refs.json`，不创建业务
  journal，也不改变 Installation、Worktree 或 custom BoundaryPoint；
- 写 Transaction 仅在完成残留 journal 检测、必要 repair 委派和快照后立即创建事务目录及初始 journal。
  它的
  `RuntimeWriteModelView` 在公共查询基础上提供标准领域记录的新增、更新、替换和删除，并将集合状态
  变更委托给 Transaction。调用方只表达领域记录与字段变化，不手动重建完整 `RuntimeState` 或复制未
  变化的记录字段；当一个命令的多个同类记录构成一个逻辑变更时，写 View 必须提供批量接口并一次提交
  该集合变更；
- 命令簇可以在公共 View 查询和 Transaction 事务边界的基础上实现自己的私有查询、更新与物理副作用，
  但不得绕过 View 访问模型关系或绕过 Transaction 修改状态；
- 写事务退出时分别写回 `runtime.json` 和各 tracked 文件，然后释放锁；写入时可以进行必要的优化，
  避免每次退出事务都覆盖未发生变化的文件。

多文件事务的锁、journal、提交和恢复要求以
[需求 0002-08：`CacheStore` 与 `RuntimeStore` 事务机制实现设计要求](08-store-transactions.md) 为准。

### 5.4 命令启动时的状态恢复

每次命令行启动时，doctidex-git 根据 `${DOCTIDEX-GIT-HOME}` 和
`<git-root>/.doctidex-git/` 下的配置文件、数据文件恢复 `CacheStore` 与 `RuntimeStore` 的
运行状态。

## 6. 已确认规则

`Installation`、`Ref`、`Worktree` 与 `BoundaryPoint` 的状态关系和生命周期由
[需求 0002-01](01-cli-arguments-results.md) 的命令设计自然推导，本子需求不重复建立独立的
命令生命周期定义。

当前已确认的 `work-model.valid` 核心不变量如下：

- `.git` 必须位于 `boundary-set` 中；
- `.doctidex-git/` 下要求显式处理的目录和文件必须被 Git ignore，或加入 `boundary-set`；
- `runtime.json` 与各 tracked 文件负责的数据之间不得发生冲突；
- `import-refs.json` 中每个 `install-id` 必须能在 `imports.json` 中找到对应的 Installation；
- 不在默认位置的 worktree `work-path` 必须被正确 Git ignore。

上述不变量的完整校验规则、违规 ID 和诊断 `details` 字段由
[需求 0002-07：`validate` 命令簇工作流与校验设计](07-validate.md) 第 5 节定义；该子需求已将
状态文件、tracked 投影、受管关系、物理对象和 Git ignore 约束统一转换为可诊断的模型违规。

## 7. 受影响的产品表面

| 表面 | 需要定义的内容 | 当前状态 |
|---|---|---|
| 核心领域模型 | `Installation`、`Ref`、`BoundaryPoint`、`Worktree` 和 `CacheItem` 的字段及关联 | 已定义；命令交互见需求 0002-03、05、06 |
| 运行环境 | Linux/macOS 支持范围及用户级目录 | 已定义 |
| Git root | 工作模型的范围、初始化、发现和仓库级工作空间 | 由需求 0002-01、04 定义 |
| 持久状态 | 用户级缓存、仓库级文件的权威性、tracked/untracked 边界和派生状态 | CacheStore、RuntimeStore 的权威来源、投影规则和恢复处理已定义 |
| import | 安装产物、元信息、实际文件和恢复关系 | 由需求 0002-05 定义 |
| 受管理引用 | 与安装产物、目录位置和 `boundary-set` 的关系 | 由需求 0002-03、05 定义 |
| worktree | 工作区状态、`work-path` 和多仓库关系 | 由需求 0002-06 定义 |
| 有效性校验 | `work-model.valid` 的不变量和诊断详情 | 完整规则和诊断详情由需求 0002-07 定义 |

## 8. 依赖与验收标准

- 父需求：[需求 0002](overview.md)。
- CLI 接口：[需求 0002-01](01-cli-arguments-results.md)。
- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。

- [x] 核心领域模型 `Installation`、`Ref`、`BoundaryPoint`、`Worktree` 和 `CacheItem` 及其字段已定义。
- [x] `CacheStore`、`RuntimeStore` 的职责、状态文件和事务访问模式已定义。
- [x] tracked JSON 的投影筛选规则、缓存状态与缓存仓库的边界及恢复处理规则已定义。
- [x] 工作模型的所有者、权威状态和派生状态已定义。
- [x] Linux/macOS 运行范围、用户级目录和仓库级工作空间的责任与约束已定义。
- [x] import、受管理引用、worktree 和 `boundary-set` 的状态关系及生命周期由需求 0002-03、05、06 展开。
- [x] tracked/untracked、恢复和移除的状态转换及约束已定义。
- [x] `work-model.valid` 的校验不变量和 `details` 返回字段已定义。
- [x] 模型与 Architecture 及 [需求 0002-01](01-cli-arguments-results.md) 的命令契约一致。

## 9. 实施与状态

本子需求为 `implemented`。工作模型已由命令簇、事务、修复和校验实现，并由 phase 7 集成验收；
当前模型、状态归属和约束以 Architecture 文档为权威说明。
