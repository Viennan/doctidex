# 需求 0003-02：owner 识别与命令路由

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0003-02` |
| 状态 | `approved` |
| 日期 | 2026-08-20 |
| 父需求 | [需求 0003](overview.md) |
| 影响范围 | `--repos-path`、`InstallationContext`、CLI 预检 |


## 详细内容

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

### 阶段 2：owner 识别与命令路由

1. 在命令分发前加入 Installation/owner 识别逻辑。
2. 增加 `installation.owner.ambiguous`、`installation.context.forbidden` 等错误映射。
3. 对进入 Installation 上下文的命令执行白名单/黑名单检查。
4. 对不允许的命令，保证在创建任何状态文件或锁之前失败。

检查点：owner 唯一、无 owner、多 owner 三种情况均有稳定行为；禁止命令不会写入 Installation。

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
