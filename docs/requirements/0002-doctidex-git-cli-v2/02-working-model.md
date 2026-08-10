# 需求 0002-02：设计 doctidex-git 工作模型

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-02` |
| 状态 | `draft` |
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
  "is-auto-resolved-hash": true,
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
| `commit-hash` | 安装产物对应的 commit hash。 |
| `is-auto-resolved-hash` | `commit-hash` 是否由工具自动解析。未指定 `--commit` 时，工具从远程同步 branch 或 tag 后确定并设置该 hash，将此字段设为 `true`；显式指定 `--commit` 时设为 `false`。该标记影响同一仓库在未指定 hash 且 revision 过滤条件相同情况下的覆盖行为。 |
| `install-id` | 安装产物标识符。 |
| `install-path` | 安装产物的路径。 |
| `keys` | 用于查询安装产物的 query key；其中包含内置默认值。 |
| `branch` | 可选的 branch。 |
| `tag` | 可选的 tag。 |

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
  "work-path": "<REPOSITORY-INTERNAL-ABSOLUTE-PATH>"
}
```

| 字段 | 当前含义 |
|---|---|
| `url` | 外部 Git 仓库 URL。 |
| `install-id` | 可选的关联安装产物标识符。 |
| `work-path` | worktree 的仓库内部绝对路径。 |

### 3.4 全局缓存

#### `CacheItem`

`CacheItem` 表示用户级 Git object cache pool 中一个外部 Git 仓库的缓存记录。

```jsonc
{
  "git-url": "",
  "path": ""
}
```

| 字段 | 当前含义 |
|---|---|
| `git-url` | 外部 Git 仓库 URL。 |
| `path` | 相对于缓存状态文件的路径。 |

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

`records` 中的每一项都是一个 `CacheItem`，用于关联 Git URL 与缓存仓库路径。
`CacheItem` 只记录 Git URL 和本地 bare Git repository 的位置；缓存仓库自身负责提供更详细的
Git 状态。

`CacheStore` 通过事务上下文访问数据：

- 创建事务时获取锁并读取缓存目录下的 `status.json`；
- 事务上下文提供缓存条目的读写操作；
- 退出事务时写回变更并释放锁。

缓存状态恢复时按以下规则处理 `status.json` 与本地 bare Git repository 的不一致：

| 不一致情况 | 处理方式 |
|---|---|
| `status.json` 存在记录，但对应 bare Git repository 不存在 | 直接恢复对应的 bare Git repository。 |
| 记录路径上的 bare Git repository 与记录的 `git-url` 不匹配 | 删除不匹配的本地 bare Git repository，并恢复正确的 repository。 |
| `status.json` 没有记录，但本地存在 bare Git repository | 默认不处理，留待后续 cache 维护命令处理。 |

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

`RuntimeStore` 通过事务上下文访问数据：

- 创建事务时获取锁，读取 `runtime.json` 及各 tracked 文件，并重建完整的内存运行时数据；
- 事务上下文提供 `boundary-set`、`imports`、`import-refs` 和 `worktrees` 的读写操作，必要时可通过索引或访问方法封装查询；
- 退出事务时分别写回 `runtime.json` 和各 tracked 文件，然后释放锁；
- 写入时可以进行必要的优化，避免每次退出事务都覆盖未发生变化的文件。

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

本子需求目前为 `draft`。工作模型内容已与命令簇、事务、修复和校验子需求完成一次同步；
获得明确批准前，不授权修改 CLI 实现、测试或相关 Architecture 文档。
