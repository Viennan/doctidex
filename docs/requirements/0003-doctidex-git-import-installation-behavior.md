# 需求 0003：规范 doctidex-git 在作为 import installation 仓库内的行为

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0003` |
| 状态 | `planned` |
| 日期 | 2026-08-17 |
| 来源 | 用户补充 import installation 行为的草稿信息，并要求细化目标、需求、方案、细节处理和验收标准 |
| 影响范围 | `--repos-path` 语义、owner 识别、Installation 只读边界、间接 import 的恢复与查询、`import-by-installations` 关系、Installation 目录组织、`import remove` 语义、CLI 错误码，以及 Installation 上下文命令运行环境 |
| 文档性质 | 当前需求记录 |

本文细化 `doctidex-git` 在作为 import installation 的仓库内应遵循的行为。核心目标是：当命令
作用于某个已安装仓库时，不得把该安装仓库当作一个普通的、可随意写入的 doctidex-git 工作空间；
而应识别其所属的 owner 仓库，把可变状态写到 owner，同时保持 Installation 作为只读参考目录树。

## 1. 需求意图

`doctidex-git` 的 import 能力会把外部 Git 仓库固定到某个 commit，并在当前仓库的
`/.doctidex-git/imports/` 下建立 Installation。一个 Installation 自身也可能是 doctidex-git
仓库，其根目录下拥有自己的 `.doctidex-git/imports.json` 等元数据。当前命令在 Installation
目录内运行时，会把该 Installation 当作命令自己的 Git root，进而在安装树内部再次恢复或创建
import 产物，形成递归目录结构；这与“Installation 是只读参考目录树”的产品定位不一致。

本需求要求：当 `--repos-path`（或自动发现的当前目录）落在某个 Installation 内时，工具必须
先确定该 Installation 的 owner，然后把可写入操作重定向到 owner 的 RuntimeStore，把查询路径
解析到 owner 中的实际安装位置，并禁止任何会改变 Installation 自身 Git 可见状态的命令。

## 2. 目标与范围

### 2.1 目标

1. 定义 Installation 的 owner：一个 Installation 所属的、通过 import 安装该仓库的 doctidex-git
   仓库，称为该 Installation 的 `owner`。
2. 当命令位于 Installation 内时，可靠地识别其 owner；存在零个、一个或多个候选 owner 时给出
   明确、稳定的处理。
3. 定义 Installation 上下文中的命令白名单和拒绝规则：禁止 `init`、`worktree`、`import install`
   等会改变 Installation 自身或制造递归安装结构的命令。
4. 保证允许运行的命令不会对 Installation 自身产生可被 Git 感知的变更。
5. 变更 `import restore` 在 Installation 内的行为：不递归创建 install-path，而是在 owner 的
   `/.doctidex-git` 工作区中以扁平方式创建间接 import。
6. 变更 `import query`、`boundary-set parse` 等查询命令在 Installation 内的行为：将
   Installation 元数据中的 `install-path`、`Ref.target-dir` 等解析到 owner 中的实际物理路径，
   而不是继续使用 Installation 自身记录的路径。
7. 引入 `import-by-installations` 关系，记录“某个 Installation 由哪个或哪些 Installation 间接
   引入”，并让 `import remove` 在删除时考虑该关系。
8. 优化 Installation 目录组织：以 commit-hash 为真正的物理 worktree，branch/tag 作为指向
   具体 commit-hash 目录的符号链接，避免同一 revision selector 下的重复物理安装并支持间接
   import 的扁平管理。

### 2.2 非目标

- 不改变 [doctidex v2 目录树外观规范](../architecture/doctidex-v2-directory-tree.md) 对
  `index.md`、Markdown link 或抽象 `boundary-set` 的定义。
- 不改变 `init`、`import`、`boundary-set`、`worktree`、`validate`、`repair` 六个命令簇的
  外部命令名和既有参数名。
- 不重新定义普通 owner 仓库中的 `import install`、`import restore` 命令契约，只定义它们在
  Installation 上下文中的变化。
- 不定义 Python 类名、函数名、模块路径等实现细节；本文只固定行为和边界。
- 本需求不授权实现代码、测试、user 文档、Architecture 文档或 Skills 的修改。实施仍需单独的
  实现授权。
- 不定义跨版本兼容或向后兼容承诺。

## 3. 现状与问题

当前 `doctidex-git` 的主要入口通过 `resolve_git_root` 将 `--repos-path` 解析为命令的 Git root，
随后用该 Git root 初始化 `RuntimeStore`。当一个路径位于 Installation 内部时，`resolve_git_root`
返回的通常是该 Installation 自己的 Git worktree 根；于是命令会读取或创建 Installation 内部的
`.doctidex-git`，而不是其 owner 的工作空间。

当前 `import restore` 直接使用目标 Installation 已记录的 `install-path`，在该路径下创建或复用
Git worktree。若命令在 Installation 内部运行，目标路径仍以该 Installation 为根，导致安装目录
递归出现在被安装仓库内部。

当前 `import query` 返回 Installation 中持久化的 `install-path` 和 `Ref.target-dir`。在优化后的
Installation 目录组织中，这些路径可能是 branch/tag 符号链接路径或 Installation 自身坐标系下
的路径，不能直接作为 owner 中的实际物理路径使用。

## 4. 需求

### 4.1 owner 定义与识别

对于某个 Installation `A`，其 `owner` 是包含 `A` 的 import 管理状态的 doctidex-git 仓库；从
文件系统角度看，`A` 位于 owner 的 `/.doctidex-git/imports/` 之下。

命令开始后，先解析 `--repos-path`（省略时使用当前目录向上发现的 Git root）对应的 Git root，
并规范化该路径。随后检查该规范化根路径从自身向上到文件系统根目录的祖先路径中，出现了多少个
名为 `.doctidex-git` 的目录：

| 祖先路径中 `.doctidex-git` 数量 | 处理 |
|---|---|
| `0` | 当前路径不是某个 owner 的 Installation，按既有普通 Git root 行为处理。 |
| `1` | 该 `.doctidex-git` 所在目录是 owner；命令进入 Installation 上下文。 |
| 多于 `1` | 出现嵌套 Installation，owner 不唯一；命令失败并返回 `installation.owner.ambiguous`。 |

识别结果中的 owner 路径必须是该 `.doctidex-git` 目录的父目录，即包含该工作空间的 Git root。
如果该目录不是一个有效 doctidex-git 工作空间，仍不得静默回退为普通行为，而应按 owner 上下文
的后续模型读取错误处理。

### 4.2 Installation 上下文命令规则

在 Installation 上下文内，命令不得把 Installation 自身当作可写工作空间。允许和禁止的命令分
为以下三类：

| 命令 | 上下文行为 |
|---|---|
| `init`、`worktree create`、`worktree remove`、`import install` | 禁止；在进入业务逻辑前直接返回 `installation.context.forbidden`。 |
| `import track`、`import ref`、`import unref`、`boundary-set add`、`boundary-set remove`、`repair` | 禁止；这些命令会修改 owner 的 tracked 状态或物理模型，不由 Installation 上下文代理。 |
| `import restore`、`import query`、`boundary-set parse` | 允许；`restore` 按第 4.5 节写入 owner，查询命令按第 4.6 节解析路径。 |
| `validate` | 允许；针对 Installation 自身进行校验，可作为只读命令仅基于 Installation 自身执行。 |

对允许运行的命令，命令实现不应增加 owner/Installation 分支。它们继续使用与普通仓库相同的
`RuntimeStore`/`RuntimeTransaction` 风格接口，由 Installation 上下文命令运行环境在事务内部完成
逻辑映射，使命令实现仍认为自己在普通 repos 中运行。

允许的命令不得创建、修改或删除 Installation 自身工作区中的任何 Git tracked 文件，不得创建或
修改 Installation 自身的 `.doctidex-git` 状态文件、`.transactions/`、`.lock` 或 Git worktree
元数据。它们可以在 owner 的 `/.doctidex-git` 中写入必要状态。

### 4.3 `import-by-installations` 关系

`import-by-installations` 描述一个 Installation 与间接引入它的 Installation 之间的关系：

```jsonc
{
  "install-id": "<OWNER-LEVEL-INSTALL-ID>",
  // 运行时动态字段，不写入 imports.json 或 runtime.json
  "import-by-installations": [
    "<PARENT-INSTALLATION-INSTALL-ID>"
  ]
}
```

字段含义：

| 字段 | 含义 |
|---|---|
| `install-id` | owner 的 RuntimeStore 中目标 Installation 的 `install-id`。 |
| `import-by-installations` | 引入该 Installation 的父 Installation 的 `install-id` 列表。 |

`import-by-installations` 不是需要持久化或被 tracked 的字段，而是 Installation 在运行时动态
存在的字段。它不写入 `imports.json`，也不作为独立关系写入 `runtime.json`；只由当前 owner
RuntimeState 与当前 Installation 上下文中父 Installation 的 import 声明即时派生。`import query`
等只读命令可以在结果中输出该字段，但状态加载和保存不得序列化它。

### 4.4 Installation 命令运行环境

核心要求不是强制引入单一的 `InstallationTransaction` 囊括所有抽象，而是为 Installation 上下文
构建一套命令运行环境，使允许运行的命令获得与普通 `RuntimeStore`/`RuntimeTransaction` 相同的
支撑能力。

实现形式保持开放：

- 可以是一个或多个事务适配对象、模型视图、路径映射器或 Store 包装层的组合。
- 可以直接复用现有 `RuntimeStore`、`RuntimeTransaction` 以及已经积累的相关工具，在不重写命令
  业务逻辑的前提下加入 Installation 上下文映射。
- 是否引入名为 `InstallationTransaction` 的类、以及它承担多少职责，由实施决定，不作为本需求
  的固定约束。

该运行环境必须满足以下行为要求：

- 对允许命令暴露与普通 `RuntimeStore`/`RuntimeTransaction` 相同的入口，例如
  `read_only_transaction()`、`write_transaction()` 以及允许命令实际使用的其他事务入口。
- 命令模块优先仍按普通 repos 的方式调用这些入口，避免随意增加 `if installation:` 之类的上下文
  分支。
- 在运行环境内部，将 Installation 自身坐标映射到 owner 坐标，将 Installation 本地
  `install-id`/Ref 映射到 owner-level Installation/Ref，并将 owner-level 状态映射为
  Installation 可见视图。
- 阶段 3 的事务 `__enter__` 应在取得 owner 文件锁后，根据 `InstallationContext.install_path`
  匹配 owner RuntimeStore 中的 Installation，并校验其仍然存在；阶段 2 只负责记录
  `install_path`，不提前读取或校验。
- 写事务中的状态更新和物理副作用必须落在 owner 的工作区；读事务返回的模型视图应让命令认为
  自己在读取当前 Installation 的普通模型，但路径和数据已经过映射。
- 命令参数和命令主流程优先不做大规模变化；当某些代码路径难以通过现有接口透明映射时，允许
  新建共同的环境抽象，并对已有实现做出必要调整，而不是在每个命令中散落临时的上下文特判。
- 本需求当前只要求为第 4.2 节允许运行的命令提供该运行环境；被禁止的命令在进入运行环境之前
  失败。

### 4.5 Installation 内 `import restore`

当命令位于 Installation `A` 内且执行 `import restore --install-id <B-local-id>` 时，命令分发层
仍然复用现有的 `import restore` 工作流，但其 `RuntimeStore` 参数替换为 Installation 上下文命令
运行环境提供的适配对象。

该运行环境优先复用现有 restore 主流程；仅在难以通过环境抽象透明处理的路径上，才调整已有实现。
需要完成以下映射：

- 把 `--install-id` 从 Installation 本地身份映射到 owner-level Installation 身份；映射规则为
  按 `(git-url, commit-hash)` 在 owner 的 **commit-hash Installation** 中匹配。Installation 自身
  `imports.json` 中的 branch/tag 形式 revision，必须使用其记录的 commit-hash 参与匹配，而不是
  去匹配 owner 中的 branch/tag Installation。
- 把目标 Installation 的 `install-path`、Ref 等 Installation 自身坐标映射为 owner 中的实际物理
  路径。
- 把 restore 写事务中的 Installation 状态更新提交到 owner 的 RuntimeStore，而不是 Installation
  自身的 `.doctidex-git`。
- 对不存在或 owner 中已有匹配记录的情况，沿用现有 restore 的成功、no-op 或错误语义。在当前
  架构下，`git-url + commit-hash` 唯一标识一个 commit-hash Installation（排除 branch/tag），因此
  不需要处理多个候选。
- restore 最终返回的 `install-id` 和 `install-path` 经过适配层转换，表现为 owner 实际安装结果，
  或按命令输出契约所需的可见形式。

restore 仍然通过 owner 的 `GitCache` 获取 Git object，并遵守既有
[需求 0002-05](0002-doctidex-git-cli-v2/05-import.md) 中只使用已记录 commit、不重新解析
branch/tag 的规则。


### 4.6 Installation 内查询命令

在 Installation 上下文内，查询命令优先调用现有查询工作流，并使用 Installation 上下文命令运行
环境提供的只读视图。查询实现原则上不增加 owner/Installation 分支，由运行环境完成数据映射；
仅在难以透明处理的路径上允许调整已有查询实现：

- `import query` 从运行环境的只读视图中读取候选 Installation 和 Ref；
  返回结果中的 `install-path`、`refs` 等字段应解析为 owner 中的实际物理路径，而不是
  Installation 元数据中的原始记录路径。
- `import query` 可以继续输出动态字段 `import-by-installations`，该字段仍只存在于运行时视图，
  不来自持久化文件。
- `boundary-set parse` 继续调用现有解析逻辑；运行环境先把输入路径映射到 owner 坐标系，再使用
  owner 的完整 `boundary-set` 视图解析，最后将结果映射回命令可见形式。
- 查询命令不得修改 CacheStore、RuntimeStore、Installation 文件或边界集合。

路径转换必须拒绝越过仓库边界的路径，避免把 Installation 内路径解释为 owner 的任意文件系统
路径。

### 4.7 Installation 目录组织

新的 Installation 目录组织以 commit-hash 为唯一物理目录，branch/tag 作为符号链接：

Installation 上下文进行间接 import 身份匹配时，只匹配 commit-hash Installation；branch/tag
Installation 只作为同一 commit-hash 的语义化别名，不参与该匹配。

```text
<owner>/.doctidex-git/imports/
└── github.com/
    └── Viennan/
        └── doctidex/
            ├── <COMMIT-HASH>/
            ├── <BRANCH> -> <COMMIT-HASH>
            └── <TAG> -> <COMMIT-HASH>
```

规则：

| 类型 | `install-path` | 物理形态 |
|---|---|---|
| commit selector | `/.doctidex-git/imports/<domain>/<repo-path>/<commit-hash>` | 真实 Git worktree 目录。 |
| branch selector | `/.doctidex-git/imports/<domain>/<repo-path>/<branch>` | 指向对应 commit-hash 目录的符号链接。 |
| tag selector | `/.doctidex-git/imports/<domain>/<repo-path>/<tag>` | 指向对应 commit-hash 目录的符号链接。 |

`import install` 或 `import restore` 使用 branch/tag 时，同时创建：

- 一个 untracked 的 commit-hash Installation，其 `install-path` 为真实 commit-hash 目录；
- 一个 branch/tag Installation，其 `install-path` 为符号链接路径；
- 在当前运行时视图中，commit-hash Installation 的动态 `import-by-installations` 需要包含对应
  的 branch/tag Installation。

branch/tag 的 `install-path` 返回符号链接路径，不直接返回 commit-hash 路径。删除 branch/tag
Installation 时，需要一并处理其关联的 commit-hash Installation，且只有在
`import-by-installations` 等关系允许时才物理删除。

### 4.8 `import remove` 与间接 import

`import remove` 在 owner 上下文中处理被间接引入的 Installation 时，先基于当前状态即时派生
`import-by-installations`，再检查：

| Installation 状态 | `import-by-installations` | 行为 |
|---|---|---|
| tracked | 空 | 按既有删除规则检查 Markdown link 和 Ref 阻塞，通过后移除元信息并物理删除。 |
| tracked | 非空 | 不物理删除；将 Installation 从 `imports.json` 迁移到 `runtime.json`，并标记为 untracked。 |
| untracked | 空 | 移除运行时记录并物理删除。 |
| untracked | 非空 | 保留运行时记录，不物理删除。 |

“非空”表示还有至少一个父 Installation 依赖该目标。物理删除只能在
`import-by-installations` 为空时执行。对于 branch/tag 与 commit-hash 的关联，删除 branch/tag
后应先从其 commit-hash Installation 的 `import-by-installations` 中移除对应关系，再判断该
commit-hash Installation 是否仍被其他 selector、Ref 或 link 使用。

## 5. 实施方案

以下方案用于记录实施范围和阶段边界；`planned` 或本阶段拆分本身不授权修改代码。

| 阶段 | 状态 |
|---|---|
| 1. 扩展 RuntimeStore 模型 | `completed` |
| 2. owner 识别与命令路由 | `completed` |
| 3. Installation 命令运行环境 | `pending` |
| 4. restore、query 与 boundary parse 上下文适配 | `pending` |
| 5. Installation 目录组织与 remove 语义 | `pending` |
| 6. 验证与文档 | `pending` |

### 阶段 1：扩展 RuntimeStore 模型

1. 在运行时 `Installation` 视图中增加动态字段 `import-by-installations`。
2. 保持 `imports.json` 和 `runtime.json` 的现有序列化字段不变，不新增持久化关系表。
3. 更新 `RuntimeStore` 状态重建和 `RuntimeModelView`，从当前 owner 状态派生该动态字段。
4. 更新 `import query` 结果，使该字段可以在只读查询中输出。

检查点：`import-by-installations` 只存在于运行时视图和查询结果中，不会写入 `imports.json`
或 `runtime.json`。

### 阶段 2：owner 识别与命令路由

1. 在命令分发前加入 Installation/owner 识别逻辑。
2. 增加 `installation.owner.ambiguous`、`installation.context.forbidden` 等错误映射。
3. 对进入 Installation 上下文的命令执行白名单/黑名单检查。
4. 对不允许的命令，保证在创建任何状态文件或锁之前失败。

检查点：owner 唯一、无 owner、多 owner 三种情况均有稳定行为；禁止命令不会写入 Installation。

### 阶段 3：Installation 命令运行环境

1. 构建 Installation 上下文的命令运行环境，向允许命令提供与
   `RuntimeStore`/`RuntimeTransaction` 等价的支撑能力；实现形式开放，不强求使用单一
   `InstallationTransaction`。
2. 优先复用现有 `RuntimeStore`、`RuntimeTransaction` 及相关工具，仅在需要时增加适配对象、
   模型视图或路径映射。
3. 让允许运行命令优先通过既有入口调用该运行环境；仅在难以处理时新建共同的环境抽象，并对
   已有实现做必要调整。
4. 在运行环境内部封装 owner 的 RuntimeStore 事务，并实现 Installation 本地 `install-id`、
   `install-path`、Ref 与 owner-level 记录之间的映射。
5. 为允许命令需要的只读视图和写视图提供映射后的模型视图。

检查点：允许命令的参数和主流程保持基本稳定；现有命令工作流可以优先传入 Installation 命令运行
环境提供的 Store/Transaction 对象完成读、写和查询。对难以透明映射的路径，允许在共同环境抽象
内调整已有实现，且不要求在命令模块中保持零修改。

### 阶段 4：restore、query 与 boundary parse 上下文适配

1. 验证 `import restore` 在 Installation 上下文中优先复用现有工作流，通过 Installation 命令
   运行环境完成映射；对难以透明处理的路径，可在共同环境抽象内调整实现。
2. 验证 `import query`、`boundary-set parse` 优先复用现有查询逻辑，通过只读映射视图完成路径
   和身份转换；仅在必要时调整已有查询实现。
3. 确保所有返回路径均为 owner 实际路径，且查询不产生副作用。

检查点：允许命令的参数和主流程没有大规模改动；间接 restore 只在 owner 的
`/.doctidex-git/imports/` 下创建扁平目录；查询命令返回 owner-level 实际路径。对难以处理的
代码路径，允许通过共同环境抽象调整已有实现，但不以命令级临时特判为默认方式。

### 阶段 5：Installation 目录组织与 remove 语义

1. 调整 `import install`/`import restore` 对 commit-hash 物理目录和 branch/tag 符号链接的创建。
2. 调整 `import remove` 对 `import-by-installations`、branch/tag 与 commit-hash 关联的处理。
3. 补充 `validate`/`repair` 对新增关系和目录组织的一致性规则。

检查点：branch/tag 重解析到新 commit 时不破坏旧 commit 的仍被使用的 Installation；remove 不
删除仍被间接 import 的物理目录。

### 阶段 6：验证与文档

在获得实现授权后，补充单元测试、集成测试、回归测试，并同步更新
[doctidex-git v2 Architecture](../architecture/doctidex-git-v2.md) 与 user 文档。

## 6. 细节处理

### 6.1 路径解析与 owner 识别边界

| 场景 | 处理 |
|---|---|
| `--repos-path` 指向普通 owner Git root | 祖先路径不含 `.doctidex-git`，按普通行为处理。 |
| `--repos-path` 指向某个 Installation 根目录 | 祖先路径包含一个 `.doctidex-git`，进入 Installation 上下文。 |
| Installation 内嵌在另一个 Installation 内 | 祖先路径包含多个 `.doctidex-git`，返回 `installation.owner.ambiguous`。 |
| 指定路径不是有效 Git root | 保持现有 `git-root.unresolved` 语义。 |

### 6.2 禁止命令的失败边界

禁止命令必须在解析 owner 后、但在读取 owner RuntimeStore、创建任何锁或物理副作用前失败。错误
返回应使用统一结构化错误结构，`subject` 至少包含 `kind: "installation"` 和 `install-path`；
禁止命令的报错信息无需进一步解析 `install-id`。

### 6.3 只读保证

允许运行的命令只能读取 Installation 自身文件，并只能在 owner 的 RuntimeStore 中写入。若发现
需要写 Installation 自身的情况，命令必须失败，不得静默降级或忽略。

### 6.4 身份唯一性与符号链接

在当前架构下，`git-url + commit-hash` 唯一标识一个 commit-hash Installation；branch/tag
Installation 不作为间接 import 的匹配对象，因此 Installation 上下文查询或 restore 不存在多个
候选需要消歧。符号链接损坏、指向错误 commit 或目标缺失时，应转换为稳定的 Installation 目标
错误，而不是底层文件系统错误。

### 6.5 `import remove` 幂等性

目标 Installation 不存在时，`import remove` 保持既有成功 no-op；`import-by-installations`
非空但目标记录已缺失时，不创建新记录，也不执行物理删除。tracked 转 untracked 的迁移必须在
同一个 RuntimeStore 事务中原子完成。

### 6.6 命令实现保持普通 repos 视图

Installation 命令运行环境必须提供与普通 `RuntimeStore`/`RuntimeTransaction` 一致的调用面，使
允许命令的业务逻辑优先不因当前处于 Installation 上下文而增加分支。命令模块原则上不通过
`isinstance`、全局标志或额外参数判断 owner 与 Installation；上下文差异应集中在运行环境、模型
视图和分发层。对难以通过现有接口透明处理的代码路径，允许新建共同的环境抽象，并对已有实现做
必要调整。

如果某个允许命令使用了未由运行环境支持的底层入口，该命令应转换为稳定错误，而不是修改命令
实现来绕过映射。当前范围只覆盖允许运行的命令。运行环境实现允许直接复用
`RuntimeStore`/`RuntimeTransaction` 及既有工具，是否引入单一 `InstallationTransaction` 类不构成
验收条件。

## 7. 验收标准

以下验收标准尚未全部完成；阶段 1 相关项已由自动化测试覆盖，其余项待后续阶段实现后验证。

1. 当 `--repos-path` 位于某个 Installation 内时，工具能识别唯一 owner；不存在 owner 时按普通
   行为处理，存在多个候选 owner 时返回 `installation.owner.ambiguous`。
2. `init`、`worktree`、`import install` 以及会修改 owner tracked 状态的命令在 Installation
   上下文中返回 `installation.context.forbidden`，且不创建或修改任何状态文件、锁或物理目录。
3. 允许运行的查询、`import restore` 和 `validate` 不会对 Installation 自身产生 Git 可感知的
   变更；`validate` 在 Installation 上下文针对 Installation 自身执行。
4. 在 Installation 内执行 `import restore` 时，新产物创建在 owner 的
   `/.doctidex-git/imports/` 下，不递归出现在 Installation 的 install-path 下。
5. 间接恢复产生的 Installation 默认写入 owner 的 `runtime.json`，`tracked` 为 `false`；运行时
   视图中 `import-by-installations` 包含其父 Installation 的 owner-level `install-id`，且该字段
   不被持久化。
6. `import query` 和 `boundary-set parse` 在 Installation 上下文返回 owner 实际物理路径，不
   返回 Installation 元数据中的原始 `install-path` 或 `target-dir`。
7. `import-by-installations` 非空的 tracked Installation 在 `import remove` 中只迁移为
   untracked，不物理删除；非空 untracked Installation 保留运行时记录。
8. commit-hash 是唯一物理目录；branch/tag 使用符号链接指向对应 commit-hash 目录；删除
   branch/tag 时能正确处理关联 commit-hash Installation 的引用关系。
9. 所有新增关系都可通过 `validate` 检查，且不会破坏现有 `boundary-set`、Markdown link、
   Ref 或 Worktree 语义。
10. 本需求完成后，普通 owner 仓库中的既有 import 行为不因本需求发生非预期变化。
11. 允许运行命令的命令模块优先不做大量修改，其参数和主流程保持基本稳定；对难以处理的代码
    路径，允许新建共同的环境抽象并调整已有实现，但不应以命令级临时特判为默认方式。
12. Installation 命令运行环境对允许命令提供与 `RuntimeStore`/`RuntimeTransaction` 等价的入口，
    并在运行环境内部完成 `install-id`、`install-path`、Ref 和 owner 状态的映射；实现不要求
    必须使用单一 `InstallationTransaction`。
13. `import restore`、`import query` 和 `boundary-set parse` 在 Installation 上下文优先复用既有
    工作流，通过运行环境完成行为差异；仅在必要时通过共同环境抽象调整已有实现。
14. 间接 import 的 `(git-url, commit-hash)` 匹配只针对 owner 中的 commit-hash Installation；
    Installation 自身声明为 branch/tag 时，必须按其记录的 commit-hash 匹配，不匹配 branch/tag
    别名记录；在该集合内该组合唯一标识一个 Installation，不产生重复候选。

## 8. 依赖与相关记录

- 上游 Architecture：[doctidex v2 目录树外观规范](../architecture/doctidex-v2-directory-tree.md)。
- 产品 Architecture：[doctidex-git v2 Architecture](../architecture/doctidex-git-v2.md)。
- CLI 参数与返回结构：[需求 0002-01](0002-doctidex-git-cli-v2/01-cli-arguments-results.md)。
- 工作模型：[需求 0002-02](0002-doctidex-git-cli-v2/02-working-model.md)。
- `import` 命令簇：[需求 0002-05](0002-doctidex-git-cli-v2/05-import.md)。
- Store 事务与恢复：[需求 0002-08](0002-doctidex-git-cli-v2/08-store-transactions.md)。

当前没有已确认的 Issue、实现记录或其他 Requirement 依赖。

## 9. 实施与状态

本记录目前为 `planned`。用户给出的三个 answer 已吸收：`validate` 在 Installation 上下文针对
Installation 自身执行；`import-by-installations` 是动态字段，不持久化；Installation 身份按
`(git-url, commit-hash)` 匹配，且该匹配发生在 commit-hash Installation 上；Installation 自身的
branch/tag 声明按其记录的 commit-hash 匹配，不匹配 owner 的 branch/tag 别名。新增实现约束也已吸收：允许命令不大改现有实现，改用
Installation 命令运行环境提供与 `RuntimeStore`/`RuntimeTransaction` 相同的支撑能力，在运行环境
内部完成逻辑映射，使命令实现仍认为自己在普通 repos 中运行；实现形式开放，可以复用现有
`RuntimeStore`/`RuntimeTransaction` 及工具，不一定使用单一 `InstallationTransaction`。命令实现
原则上是尽量保持现有逻辑；对难以处理的代码路径，允许新建共同的环境抽象并调整已有实现。此外，
`git-url + commit-hash` 在 commit-hash Installation 集合中唯一，不需要设计多个候选消歧。

阶段 1 已完成：

- `Installation` 增加运行时字段 `import_by_installations`，但不进入 `to_json()`。
- `RuntimeState.from_documents()` 通过占位派生函数 `_derived_installation_importers()` 初始化该
  字段；当前返回空关系，后续阶段再接入真实 Installation 上下文。
- `RuntimeModelView.installation_importers()` 暴露该动态字段。
- `import query` 的候选结果新增 `import-by-installations` 字段。
- 序列化文件 `imports.json` 和 `runtime.json` 的结构保持不变。

阶段 2 已完成：

- 新增 `installation.py`，通过解析 Git root 祖先路径中的 `.doctidex-git` 目录识别 owner；零个
  owner 保持普通行为，一个 owner 进入 Installation 上下文，多个 owner 返回
  `installation.owner.ambiguous`。
- `InstallationContext` 当前只记录 `owner_root` 和 `install_path`；不读取 owner RuntimeStore，
  也不提前校验 Installation 是否存在。该匹配和校验延后到阶段 3 的 Installation 事务
  `__enter__` 阶段，取得文件锁后执行。
- CLI 分发增加 Installation 上下文预检：禁止命令返回 `installation.context.forbidden`；
  `validate` 允许并继续针对 Installation 自身执行；`import restore`、`import query` 和
  `boundary-set parse` 当前返回 `installation.context.unavailable` 占位，等待阶段 3 接入命令
  运行环境。
- 禁止命令在实际创建或修改 Installation 工作区前失败；测试已覆盖 `init`、`worktree create`。
- 阶段 3 需要把当前 `installation.context.unavailable` 占位替换为真实的命令运行环境适配。

后续阶段仍需单独取得实现授权；在授权前不得继续修改代码、测试、user 文档、Architecture 文档或
Skills。
