# 需求 0002-01：CLI 命令行参数及返回结果结构设计

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-01` |
| 状态 | `approved` |
| 日期 | 2026-08-07 |
| 来源 | 用户要求以 `init`、`boundary-set`、`import`、`worktree`、`validate`、`repair` 六个命令簇逐步完成 `doctidex-git` CLI 命令行参数及返回结果结构设计 |
| 父需求 | [需求 0002：设计 doctidex-git 命令行工具 v2.x.x](overview.md) |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 影响范围 | 六个命令簇的调用参数、参数解析、返回结果、诊断信息和退出状态 |
| 文档性质 | 子 Requirement；仅记录设计需求，不授权实现 |

## 1. 需求意图

本文记录 `doctidex-git` v2.x.x 的 `init`、`boundary-set`、`import`、`worktree`、`validate`、`repair` 六个
命令簇的已确认命令行参数及返回结果结构。尚未确定的细节仅在相应命令或返回规则中保留。

本次重构不扩展上述命令簇之外的功能，不定义实现方案。

## 2. 总体约束

- 工具运行在 Git 环境中，以 doctidex 规范组织目录树并辅助开发工作。
- 设计应与 [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)
  一致，不通过 CLI 接口改变该 Architecture 的目录树语义。
- 六个命令簇均需分别明确：调用参数、参数错误、成功结果、失败结果和退出状态。
- 本需求完成前，未确认的方案保持为 `draft`，不授权修改 CLI 实现、测试或相关架构文档。

### 2.1 通用 Git root 参数

`--repos-path` 是 `doctidex-git` 的通用 Git root 指定参数。每个子命令均接受该可选参数；
在命令格式中，它位于可执行文件名后、命令簇前：

```text
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] <command> [command-options]
```

省略 `--repos-path` 时，从当前路径向上搜索第一个 Git root。

### 2.2 参数记法与术语

以下命令格式中，`<...>` 表示必填项；它可以包围必填的参数值，也可以包围必须从中选择
一项的参数组。`[...]` 表示可选部分，`|` 表示备选项，尾随 `...` 表示该选项可以重复。
`REPOSITORY-INTERNAL-ABSOLUTE-PATH` 是仓库内部绝对路径：路径根为当前仓库根目录，而不是
宿主文件系统根目录。

| 术语 | 含义 |
|---|---|
| `INSTALL-ID` | 一次 `import install` 产物的标识符。 |
| `INSTALL-PATH` | import 安装路径，类型为仓库内部绝对路径。 |
| `SRC-SUB-DIR` | `install-id` 对应安装仓库的内部子目录，类型为安装仓库内部绝对路径。 |
| `TARGET-DIR` | 当前仓库内部的受管理引用目标目录，类型为仓库内部绝对路径。 |
| `QUERY-KEY` | 用于查询 import 候选项的 key。 |

### 2.3 通用成功返回

除 `validate` 外，未定义额外返回字段的子命令在正常完成时使用以下返回结构：

```jsonc
{
  "status": "ok",
  "message": {}
}
```

`status: "ok"` 表示命令成功完成。除 `init` 检测到非空工作空间这一信息性场景外，正常完成时
`message` 固定为空对象。该场景的成功信息在第 3.1 节说明；命令无法完成时的 `message` 结构、
`status: "error"` 和退出状态由第 2.4 节定义。`validate` 的校验结果、诊断和
退出状态由第 7.4 节单独定义。

### 2.4 通用错误返回

当命令无法完成其工作流时，返回 `status: "error"`：

```jsonc
{
  "status": "error",
  "message": {
    "code": "installation.remove.blocked",
    "summary": "The tracked installation cannot be removed because it is still referenced.",
    "context": {
      "command": "import remove",
      "repos-path": "<REPOSITORY-ROOT-PATH>"
    },
    "subject": {
      "kind": "installation",
      "install-id": "<INSTALL-ID>",
      "install-path": "/<REPOSITORY-INTERNAL-ABSOLUTE-PATH>"
    },
    "details": {}
  }
}
```

| 字段 | 要求 |
|---|---|
| `status` | 命令无法完成时固定为 `error`。 |
| `message.code` | 稳定、面向程序的错误码，使用小写点分命名；取值见第 9 节。 |
| `message.summary` | 面向人类的简要错误说明；程序不得依赖其内容判断错误。 |
| `message.context` | 必填。`command` 为实际执行的命令；已解析 Git root 时提供 `repos-path`。 |
| `message.subject` | 可选。给出当前错误的核心模型对象或路径；至少包含 `kind`，其余字段由错误码规定。 |
| `message.details` | 必填。错误码对应的结构化上下文；禁止只返回未解释的底层文件系统或 Git 错误文本。 |

所有 `message` 中的仓库内部路径均使用以 `/` 开头的仓库内部绝对路径。除 `validate` 的
`valid: false` 结果外，`status: "error"` 的进程退出码固定为 `2`。

## 3. `init` 命令簇

用于完成当前 Git root 的 doctidex-git 工作模型初始化工作。

### 3.1 调用格式

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] init
```

该命令仅接受通用的 `--repos-path` 参数；初始化对象、幂等行为和返回结果由 [需求 0002-02：设计
doctidex-git 工作模型](02-working-model.md) 逐步定义。

当 `.doctidex-git/` 已存在且非空时，命令不执行工作模型校验或修改，返回成功信息：

```jsonc
{
  "status": "ok",
  "message": {
    "code": "workspace.already-initialized",
    "summary": "Initialization has already been run; use validate --model-structure to check the work model.",
    "details": {"next-command": "validate --model-structure"}
  }
}
```

`.doctidex-git/` 不存在或已存在但为空时，命令继续创建完整初始化工作空间，并创建或补齐根 `index.md`
的必需 frontmatter 后返回通用成功结构。`root-index.frontmatter.conflict` 与
`root-index.frontmatter.invalid` 的错误结构见第 9.2 节。

## 4. `boundary-set` 命令簇

用于管理仓库目录树中的 `boundary-set` 节点。

### 4.1 `boundary-set add`

添加 `boundary-set` 节点：

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] boundary-set add \
  <--path <REPOSITORY-INTERNAL-ABSOLUTE-PATH>>...
```

`--path` 为必填且可重复参数；每个值均为仓库内部绝对路径。

### 4.2 `boundary-set remove`

移除通过 `boundary-set add` 命令加入的 `boundary-set` 节点：

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] boundary-set remove \
  <--path <REPOSITORY-INTERNAL-ABSOLUTE-PATH>>...
```

`--path` 为必填且可重复参数；每个值均为仓库内部绝对路径。

`remove` 仅能移除通过 `add` 命令加入的路径，不能移除由内部机制添加的 `boundary-set` 路径。

### 4.3 `boundary-set parse`

解析给定仓库内部绝对路径是否包含 `boundary-set` 节点。沿每个输入路径解析时，命中遇到的
第一个节点后停止继续解析。

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] boundary-set parse \
  <--path <REPOSITORY-INTERNAL-ABSOLUTE-PATH>>...
```

`--path` 为必填且可重复参数；每个值均为仓库内部绝对路径。

成功返回：

```jsonc
{
  "status": "ok",
  "message": {},
  "results": [
    {
      "path": "<REPOSITORY-INTERNAL-ABSOLUTE-PATH>",
      "has-boundary": true,
      "boundary-point": "<BOUNDARY-POINT>",
      "boundary-type": "custom"
    }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `results` | 输入路径的解析结果集合。 |
| `path` | 当前结果对应的输入路径。 |
| `has-boundary` | 表示输入路径是否包含 `boundary-set` 节点。 |
| `boundary-point` | 输入路径中包含该 `boundary-set` 节点的路径前缀。 |
| `boundary-type` | `boundary-set` 节点类型，取值及来源如下：`custom` 表示用户通过 `boundary-set add` 添加的节点；`import` 表示由 `import install` 得到的 `install-path`；`import-ref` 表示创建的受管理引用；`worktree` 表示由 `worktree create` 创建的 `work-path`。 |

## 5. `import` 命令簇

### 5.1 已确认能力

`import` 基于 Git 实现外部 Git 仓库的 import，其机制不同于 Git 自身的 submodule：

- 支持环状依赖。
- 支持间接自引用，即依赖环包含自身。
- 支持同时引用同一个 Git 仓库的不同 revision，且无需 checkout。
- 支持创建受 Git tracked 或 untracked 的 import 仓库。
- 支持在仓库内任意符合 doctidex 规范的位置，创建 import 仓库整体或局部的受管理引用
  （文件系统符号链接），以便就近组织相关内容。
- `install-path` 自动加入当前仓库目录树的 `boundary-set`。
- 受管理引用的路径自动加入当前仓库目录树的 `boundary-set`。

### 5.2 子命令与参数

| 子命令 | 职责 |
|---|---|
| `install` | 安装外部 Git 仓库的 import。 |
| `restore` | 依据 tracked install 的元信息重新安装仓库文件。 |
| `track` | 确保指定 install 为 tracked；已 tracked 时成功完成 no-op。 |
| `remove` | 按指定范围移除 import 安装产物。 |
| `ref` | 为指定安装产物创建受管理引用。 |
| `unref` | 按目标位置移除受管理引用。 |
| `query` | 查询 import 安装产物及其受管理引用。 |

#### 5.2.1 `import install`

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] import install \
  <--tracked | --untracked> \
  --url <GIT-URL> \
  <--branch <BRANCH> | --tag <TAG> | --commit <HASH>> \
  [--key <QUERY-KEY>]...
```

| 参数 | 要求 |
|---|---|
| `--tracked` / `--untracked` | 必须且只能选择一个，用于指定 import 安装产物受 Git tracked 或 untracked。 |
| `--url <GIT-URL>` | 必填，指定外部 Git 仓库。 |
| `--branch <BRANCH>` | revision 选择器之一；必须与 `--tag`、`--commit` 互斥。 |
| `--tag <TAG>` | revision 选择器之一；必须与 `--branch`、`--commit` 互斥。 |
| `--commit <HASH>` | revision 选择器之一；必须与 `--branch`、`--tag` 互斥。 |
| `--key <QUERY-KEY>` | 可重复，提供额外的查询 key。 |

revision 选择器为必填项，且必须从 `--branch`、`--tag`、`--commit` 中恰好选择一种。branch 和
tag 安装时必须先从远程同步相应引用，记录其当前指向的最终 commit hash；commit 安装以传入 hash
作为指定 revision。

对同一 Git URL 和同一 selector，branch 或 tag 当前 commit 与已有 Installation 的记录相同时，
命令直接成功返回；当前 commit 已变化时，删除可能存在的旧 Installation，并按最新状态重新创建。
对 commit selector，同一 Git URL 和同一 commit hash 已有 Installation 时直接成功返回；否则获取
所需 Git object 后安装。具体安装与替换流程以[需求 0002-05](05-import.md)为准。

成功返回：

```jsonc
{
  "status": "ok",
  "install-id": "<INSTALL-ID>",
  "install-path": "/<INSTALL-PATH>",
  "message": {}
}
```

`install-id` 标识本次安装产物；`install-path` 是其仓库内部绝对路径。tracked install 仅由 Git
跟踪其元信息，不跟踪实际仓库文件；因此即使 tracked install 的元信息存在，`install-path`
也可能不存在。此时可通过 `import restore` 重新安装仓库文件。

#### 5.2.2 `import restore`

`restore` 用于依据 tracked install 的元信息重新安装其仓库文件，以恢复可能不存在的
`install-path`。该命令仅适用于 tracked install。

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] import restore \
  --install-id <INSTALL-ID>
```

| 参数 | 要求 |
|---|---|
| `--install-id <INSTALL-ID>` | 必填，指定要重新安装的 tracked install。 |

成功返回结构与 `import install` 一致：

```jsonc
{
  "status": "ok",
  "install-id": "<INSTALL-ID>",
  "install-path": "/<INSTALL-PATH>",
  "message": {}
}
```

`install-id` 标识被恢复的安装产物；`install-path` 表示恢复后的仓库内部绝对路径。

#### 5.2.3 `import track`

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] import track \
  --install-id <INSTALL-ID>
```

`track` 用于确保指定 install 为 tracked：untracked install 被提升为 tracked，已 tracked install
成功完成 no-op。

| 参数 | 要求 |
|---|---|
| `--install-id <INSTALL-ID>` | 必填，指定要确保为 tracked 的 install。 |

成功返回结构与 `import install` 一致：

```jsonc
{
  "status": "ok",
  "install-id": "<INSTALL-ID>",
  "install-path": "/<INSTALL-PATH>",
  "message": {}
}
```

`install-id` 标识已确保为 tracked 的安装产物；`install-path` 表示该安装产物的仓库内部绝对路径。

#### 5.2.4 `import remove`

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] import remove \
  <--install-id <INSTALL-ID> | --untracked | --auto>
```

| 参数 | 要求 |
|---|---|
| `--install-id <INSTALL-ID>` | 按安装产物标识符选择移除对象。 |
| `--untracked` | 选择所有 untracked 的 import 安装产物。 |
| `--auto` | 自动清理所有 untracked 的 import 安装产物，以及所有未被仓库内文件建立受管理引用的 import 安装产物。 |

移除选择器为必填项，且 `--install-id`、`--untracked` 与 `--auto` 互斥，必须且只能选择一个。

#### 5.2.5 `import ref`

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] import ref \
  --install-id <INSTALL-ID> \
  [--src-sub-dir <INSTALLED-REPOSITORY-INTERNAL-ABSOLUTE-PATH>] \
  --target-dir <REPOSITORY-INTERNAL-ABSOLUTE-PATH>
```

| 参数 | 要求 |
|---|---|
| `--install-id <INSTALL-ID>` | 必填，指定要创建受管理引用的安装产物。 |
| `--src-sub-dir <INSTALLED-REPOSITORY-INTERNAL-ABSOLUTE-PATH>` | 可选，指定 `install-id` 对应安装仓库的内部子目录，作为受管理引用源。 |
| `--target-dir <REPOSITORY-INTERNAL-ABSOLUTE-PATH>` | 必填，指定当前仓库内部、符合 doctidex 规范的受管理引用目标目录。 |

该命令根据 `install-id` 对应的安装产物和可选的 `--src-sub-dir`，在 `--target-dir` 所指定的、
符合 doctidex 规范的位置创建受管理引用。

如果 `install-id` 对应 untracked install，创建受管理引用时自动将该 install 提升为 tracked。

#### 5.2.6 `import unref`

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] import unref \
  --target-dir <REPOSITORY-INTERNAL-ABSOLUTE-PATH>
```

| 参数 | 要求 |
|---|---|
| `--target-dir <REPOSITORY-INTERNAL-ABSOLUTE-PATH>` | 必填，指定要移除的受管理引用目标目录。 |

该命令按受管理引用的目标位置移除受管理引用。

#### 5.2.7 `import query`

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] import query \
  <--install-id <INSTALL-ID> \
   | --install-path <REPOSITORY-INTERNAL-ABSOLUTE-PATH> \
   | --ref-path <REPOSITORY-INTERNAL-ABSOLUTE-PATH> \
   | --key <QUERY-KEY>...>
```

| 参数 | 要求 |
|---|---|
| `--install-id <INSTALL-ID>` | 按安装产物标识符查询。 |
| `--install-path <REPOSITORY-INTERNAL-ABSOLUTE-PATH>` | 按安装路径查询。 |
| `--ref-path <REPOSITORY-INTERNAL-ABSOLUTE-PATH>` | 按受管理引用路径查询。 |
| `--key <QUERY-KEY>` | 按查询 key 查询；可以重复。 |

查询选择器为必填项，且 `--install-id`、`--install-path`、`--ref-path` 与 `--key` 互斥，
必须且只能选择一种。选择 `--key` 时，该选项可以重复提供多个 query key。

`--key` 是 `import query` 专用的用户模糊搜索：Installation 的任一已保存 key 包含任一输入 key
即为候选。候选按匹配的已保存 key 数量降序排列；数量相同时，按其中与任一输入 key 完全相等的 key
数量降序排列；仍相同时保持工作模型中的稳定顺序。

成功返回：

```jsonc
{
  "status": "ok",
  "message": {},
  "candidates": [
    {
      "git-url": "<GIT-URL>",
      "commit-hash": "<HASH>",
      "install-id": "<INSTALL-ID>",
      "install-path": "/<INSTALL-PATH>",
      "keys": ["<QUERY-KEY>"],
      "refs": [
        {
          "src-sub-dir": "",
          "target-dir": "/<REPOSITORY-INTERNAL-ABSOLUTE-PATH>"
        }
      ],
      "branch": "<BRANCH>",
      "tag": "<TAG>"
    }
  ]
}
```

| `candidates` 项字段 | 含义 |
|---|---|
| `git-url` | 外部 Git 仓库 URL。 |
| `commit-hash` | 安装产物对应的 commit hash。 |
| `install-id` | 安装产物标识符。 |
| `install-path` | 安装产物的仓库内部绝对路径。 |
| `keys` | 该安装产物的全部查询 key。默认内置 Git URL 中的仓库路径。例如 `git@github.com:Viennan/doctidex.git` 包含 `Viennan/doctidex`；安装时指定 branch 或 tag 时，分别还包含 `Viennan/doctidex@<BRANCH>` 或 `Viennan/doctidex@<TAG>`；另包含安装时通过 `--key` 指定的 key。 |
| `refs` | 所有受管理引用的数组。 |
| `refs[].src-sub-dir` | 对应 `--src-sub-dir` 的安装仓库内部子目录；未提供该参数时为空字符串，视为引用根目录。 |
| `refs[].target-dir` | 对应 `--target-dir` 的当前仓库内部目标目录绝对路径。 |
| `branch` | 可选的 branch。 |
| `tag` | 可选的 tag。 |

## 6. `worktree` 命令簇

### 6.1 已确认能力

`worktree` 支持创建多根工作区，可据此完成横跨多个 Git 仓库的开发维护任务，尤其适合
agent 使用。该能力基于 Git，并封装一套固定的、符合 doctidex 规范的工作区目录组织模式。

### 6.2 `worktree create`

在当前 Git 仓库内创建 untracked 的受管理 worktree：

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] worktree create \
  <--install-id <INSTALL-ID> | --url <GIT-URL> <--branch <BRANCH> | --tag <TAG> | --commit <HASH>>> \
  [--work-path <REPOSITORY-INTERNAL-ABSOLUTE-PATH>] \
  [--tree-name <TREE-NAME>]
```

| 参数 | 要求 |
|---|---|
| `--install-id <INSTALL-ID>` | 与 `--url` 必须且只能选择一个。指定已有 import 安装产物；Worktree 使用其已记录的 commit-hash 作为 base-commit-hash。不能与 revision selector 一起使用。 |
| `--url <GIT-URL>` | 与 `--install-id` 必须且只能选择一个。指定外部 Git 仓库；必须同时提供一种 revision selector。 |
| `--branch <BRANCH>` | 仅适用于 `--url`，必须与 `--tag`、`--commit` 互斥。创建时同步远程 branch 并解析其当前 commit。 |
| `--tag <TAG>` | 仅适用于 `--url`，必须与 `--branch`、`--commit` 互斥。创建时同步远程 tag 并解析其当前 commit。 |
| `--commit <HASH>` | 仅适用于 `--url`，必须与 `--branch`、`--tag` 互斥。创建时获取并确认指定 Git object。 |
| `--work-path <REPOSITORY-INTERNAL-ABSOLUTE-PATH>` | 可选的仓库内部绝对路径。提供时直接指定工作路径。 |
| `--tree-name <TREE-NAME>` | 可选，仅在省略 `--work-path` 时参与默认 work-path 派生。可包含 `\`，按目录路径解释并创建相应目录。未提供时使用短随机标识作为末级目录名。 |

`--branch`、`--tag`、`--commit` 必须从中恰好选择一个，且仅 URL 来源使用。branch 或 tag 解析出的
commit 与直接指定的 commit 都是创建 Worktree 的基准 revision，并写入其 `base-commit-hash`。该字段
不跟踪 worktree 后续的提交变化。`--work-path`
省略时，默认路径为
`/.doctidex-git/worktrees/<domain>/<repository-path-without-.git>/<tree-name>`；`--tree-name` 只在该
默认路径中生效。创建成功后，该 `work-path` 自动加入当前仓库目录树的 `boundary-set`。

成功返回：

```jsonc
{
  "status": "ok",
  "message": {},
  "work-path": "<REPOSITORY-INTERNAL-ABSOLUTE-PATH>"
}
```

### 6.3 `worktree remove`

删除受管理 worktree：

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] worktree remove \
  --work-path <REPOSITORY-INTERNAL-ABSOLUTE-PATH> \
  [--force]
```

| 参数 | 要求 |
|---|---|
| `--work-path <REPOSITORY-INTERNAL-ABSOLUTE-PATH>` | 必填，指定要移除的 worktree。 |
| `--force` | 可选；允许在 worktree 存在未提交修改或 Git worktree 状态异常时强制移除。 |

当 worktree 工作目录已经缺失时，`remove` 不报错，仍清理对应的 doctidex-git 状态。未提供
`--force` 时，存在未提交修改或 Git worktree 状态异常将导致命令报错。

### 6.4 `worktree query`

查询指定 worktree 的 doctidex-git 相关 meta 信息：

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] worktree query \
  --work-path <REPOSITORY-INTERNAL-ABSOLUTE-PATH>
```

`--work-path` 为必填的仓库内部绝对路径。

成功返回：

```jsonc
{
  "status": "ok",
  "message": {},
  "install-id": "<INSTALL-ID>"
}
```

`install-id` 为可选返回字段，仅在该 worktree 由 import 安装产物创建时返回。

## 7. `validate` 命令簇

### 7.1 已确认能力

`validate` 为当前目录组织中的 doctidex 规范问题和 import 相关问题提供诊断。

`validate` 不区分 doctidex 与 import 校验入口，对指定范围执行统一校验。

### 7.2 `validate`

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] validate \
  [--subdir <REPOSITORY-INTERNAL-ABSOLUTE-PATH> | --model-structure]
```

| 参数 | 要求 |
|---|---|
| `--subdir <REPOSITORY-INTERNAL-ABSOLUTE-PATH>` | 可选，限定仓库内容的校验范围；不得指定 `/.doctidex-git` 或其子目录。 |
| `--model-structure` | 可选，仅校验当前 Git root 的工作模型结构；与 `--subdir` 互斥。启用时校验根 `index.md` 及其必需 frontmatter，但不扫描其正文或其他 Markdown/link、跨界结构化注释或 worktree 未提交修改。 |

### 7.3 统一校验项

未提供 `--model-structure` 时，`validate` 在指定范围内执行以下校验：

- 校验 `index.md` 是否符合 doctidex 标准。
- 校验位于 `boundary-set` 内的 Markdown 文档：其 Markdown link 路径是否符合 doctidex 标准、其
  Markdown link 目标是否存在，以及是否缺少必要的结构化注释；待恢复的 tracked import 所对应的
  跨界 link 例外由需求 0002-07 定义。
- 校验位于 `boundary-set` 内的 Markdown 文档对 import 安装仓库的 Markdown link：其对应的
  install 必须为 tracked。
- 仅校验指定范围可能包含的 worktree `work-path` 下是否存在未提交修改；未提供 `--subdir` 时，
  指定范围为 `/`，因此校验全部 worktree。
- 校验当前 Git root 的 doctidex-git 工作模型是否有效。

提供 `--model-structure` 时，`validate` 执行根 `index.md` 的根身份和基础 frontmatter 校验，以及最后一项
仓库级工作模型校验。它仍使用本节的 `valid`、`diagnostics` 和退出状态结构；`scope.subdir` 固定为 `/`。

具体校验工作流和 `work-model.valid` 的违规项由 [需求 0002-07：`validate` 命令簇工作流与校验设计](07-validate.md) 定义。

### 7.4 返回结果与诊断结构

`validate` 将命令执行结果与校验结果分离：`status` 表示命令是否完成，`valid` 表示指定范围
是否通过所有校验。因此，发现规范问题仍是一次成功执行，返回 `status: "ok"` 与
`valid: false`。

正常完成时，返回以下结构：

```jsonc
{
  "status": "ok",
  "message": {},
  "valid": false,
  "scope": {
    "repos-path": "<REPOSITORY-ROOT-PATH>",
    "subdir": "/<REPOSITORY-INTERNAL-ABSOLUTE-PATH>"
  },
  "diagnostics": [
    {
      "rule": "link.target.exists",
      "path": "/<REPOSITORY-INTERNAL-ABSOLUTE-PATH>",
      "line": 42,
      "message": "<HUMAN-READABLE-MESSAGE>",
      "details": {
        "link-path": "<LINK-PATH>",
        "target-path": "/<REPOSITORY-INTERNAL-ABSOLUTE-PATH>"
      }
    }
  ]
}
```

| 字段 | 类型 | 要求 |
|---|---|---|
| `status` | 字符串 | 正常完成时固定为 `ok`。命令无法完成时为 `error`。 |
| `message` | 对象 | 命令无法完成时使用第 2.4 节的结构化错误信息；正常完成时为空对象。 |
| `valid` | 布尔值 | 正常完成时必填。所有校验通过时为 `true`，发现任一诊断时为 `false`。命令无法完成时省略。 |
| `scope.repos-path` | 路径字符串 | 本次实际使用的 Git root。 |
| `scope.subdir` | 仓库内部绝对路径 | 本次实际校验范围；未提供 `--subdir` 时为 `/`。 |
| `diagnostics` | 数组 | 正常完成时必填。`valid` 为 `true` 时为空数组，`valid` 为 `false` 时包含一个或多个诊断项。命令无法完成时省略。 |

每个 `diagnostics` 项使用以下公共结构：

| 字段 | 类型 | 要求 |
|---|---|---|
| `rule` | 字符串 | 触发诊断的稳定规则 ID，取值见下表。 |
| `path` | 仓库内部绝对路径 | 发生问题的文件或目录路径。 |
| `line` | 正整数 | 问题在 `path` 文件中的起始行号，从 `1` 开始计数。所有 Markdown link 相关规则必须提供；其他规则可省略。 |
| `message` | 字符串 | 面向人类的诊断说明；程序必须以 `rule` 和 `details` 判断问题。 |
| `details` | 对象 | 与 `rule` 对应的结构化上下文，字段见下表。 |

| `rule` | 触发条件 | `details` 必填字段 |
|---|---|---|
| `index.conforms` | `index.md` 不符合 doctidex 标准。 | `expected`、`actual` |
| `link.path.conforms` | Markdown link 路径不符合 doctidex 标准。 | `link-path` |
| `link.target.exists` | Markdown link 目标不存在，且不属于需求 0002-07 定义的待恢复 import 例外。 | `link-path`、`target-path` |
| `link.annotation.required` | Markdown link 缺少必要的结构化注释。 | `link-path` |
| `import.link.tracked` | Markdown link 指向的 import 安装产物不是 tracked。 | `link-path`、`install-id`、`install-path` |
| `worktree.clean` | worktree 的 `work-path` 存在未提交修改。 | `work-path` |
| `work-model.valid` | 当前 Git root 的 doctidex-git 工作模型无效。 | `violations`、`content-scan`；具体结构由 [需求 0002-07](07-validate.md) 定义。 |

`details` 中的所有路径字段均使用仓库内部绝对路径。`index.conforms` 的 `expected` 和
`actual` 用于表示不符合的 `index.md` 条件；缺少项的 `actual` 为 `null`。
`link.path.conforms`、`link.target.exists`、`link.annotation.required` 和
`import.link.tracked` 均为 Markdown link 相关规则，必须返回该 Markdown link 在源 Markdown
文件中的 `line`。

命令无法完成时，返回 `status: "error"` 与 `message`，且不返回 `valid`、`scope` 或
`diagnostics`。进程退出状态如下：

| 执行结果 | `status` | `valid` | 退出码 |
|---|---|---|---|
| 校验通过 | `ok` | `true` | `0` |
| 校验发现问题 | `ok` | `false` | `1` |
| 命令无法完成 | `error` | 省略 | `2` |

## 8. `repair` 命令簇

使当前 Git root 的物理状态与 `.doctidex-git/` 配置文件描述的工作模型相容。

### 8.1 调用格式

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] repair
```

该命令仅接受通用的 `--repos-path` 参数，不接受 `--subdir` 或对象选择器。修复范围、模型基准、
物理对象修复和事务遗留处理以 [需求 0002-09：`repair` 命令簇工作流与生命周期设计](09-repair.md)
为准。

成功返回通用成功结构：

```jsonc
{
  "status": "ok",
  "message": {}
}
```

`repair` 不因仓库中存在 JSON 未登记的 install-path 而自动创建模型记录；修复失败时
沿用对应操作已有的错误码和通用错误结构。

## 9. 命令错误目录

本节的错误都表示命令无法完成，因此使用第 2.4 节的 `status: "error"` 结构。错误码描述的是
工作模型、Git 对象或用户意图的可诊断状态，不直接暴露未经解释的文件系统或 Git 底层错误。

### 9.1 通用错误

| `message.code` | 触发条件 | `subject` / `details` 必填信息 |
|---|---|---|
| `git-root.unresolved` | `--repos-path` 无法指向 Git root，或当前路径向上无法发现 Git root。 | `details.requested-repos-path`、`details.discovery-start-path`。 |
| `argument.invalid` | 参数缺失、重复、互斥或不满足命令约束。 | `details.parameter`、`details.received`、`details.constraint`。 |
| `repository-path.invalid` | 仓库内部路径不以 `/` 开头，或规范化后越过仓库根目录。 | `details.parameter`、`details.path`、`details.normalized-path`、`details.constraint`。 |
| `work-model.uninitialized` | 命令需要仓库级工作模型，但 Git root 未初始化。 | `subject.kind: "workspace"`、`subject.path: "/.doctidex-git"`、`details.required-command: "init"`。 |
| `work-model.invalid` | 非 `validate` 命令读取或重建工作模型时发现违规，因而无法安全继续其工作流。 | `details.violations`，其元素使用 `work-model.valid` 的 violation 结构。 |
| `store.transaction.unavailable` | 无法建立 CacheStore 或 RuntimeStore 事务，因而无法读取或提交模型状态。 | `details.store`、`details.phase`、`details.state-path`。 |

### 9.2 `init` 与 `boundary-set`

| `message.code` | 触发条件 | `subject` / `details` 必填信息 |
|---|---|---|
| `workspace.initialize.failed` | 新建工作模型时，无法建立所需的状态文件或 Git ignore 保护。 | `subject.kind: "workspace"`、`subject.path: "/.doctidex-git"`、`details.required-artifacts`、`details.unavailable-artifacts`。 |
| `root-index.frontmatter.conflict` | 初始化时，根 `index.md` 的必需 frontmatter 字段已存在但类型或值不符合固定根身份。 | `subject.kind: "root-index"`、`subject.path: "/index.md"`、`details.field`、`details.expected`、`details.actual`。 |
| `root-index.frontmatter.invalid` | 初始化时，已有根 `index.md` 的 frontmatter 不是可安全补充字段的 YAML 映射。 | `subject.kind: "root-index"`、`subject.path: "/index.md"`、`details.reason`。 |
| `boundary-point.not-found` | `boundary-set remove` 指定的路径没有 custom BoundaryPoint。 | `subject.kind: "boundary-point"`、`subject.path`、`details.required-type: "custom"`。 |
| `boundary-point.remove.prohibited` | 试图通过 `boundary-set remove` 移除 import、import-ref 或 worktree 派生点。 | `subject.kind: "boundary-point"`、`subject.path`、`details.boundary-type`、`details.managed-by`。 |

`boundary-set parse` 未命中边界点是正常的成功结果，不使用错误结构。

### 9.3 `import`

| `message.code` | 触发条件 | `subject` / `details` 必填信息 |
|---|---|---|
| `revision.unresolvable` | 给定 Git URL 的 branch、tag 或 commit selector 无法解析为所需 revision。 | `subject.kind: "git-source"`、`subject.git-url`、`details.selector-kind`、`details.selector-value`、`details.operation`。 |
| `cache.repository.unavailable` | 需要的 bare Git repository 无法从 CacheStore 获得或恢复。 | `subject.kind: "cache-item"`、`subject.git-url`、`details.operation`、`details.revision`。 |
| `installation.target.unavailable` | install-path 已被非目标 Installation 占用，或无法作为指定 revision 的安装 worktree 使用。 | `subject.kind: "installation"`、`subject.install-path`、`details.operation`、`details.occupant`。 |
| `installation.not-found` | 需要现有 Installation 的非查询命令指定的 install-id 或 install-path 无对应 Installation。 | `subject.kind: "installation"`、`subject.install-id` 或 `subject.install-path`、`details.operation`。 |
| `installation.tracking-state.invalid` | `import restore` 要求 tracked Installation，但当前 Installation 为 untracked。 | `subject.kind: "installation"`、`subject.install-id`、`details.required-tracked: true`、`details.actual-tracked: false`。 |
| `installation.restore.unavailable` | 依据已保存 revision 无法恢复 tracked Installation 的实际文件。 | `subject.kind: "installation"`、`subject.install-id`、`subject.install-path`、`details.commit-hash`。 |
| `installation.remove.blocked` | tracked Installation 仍有当前目录树有效范围内的 Markdown link，或仍有关联 Ref。Markdown link 可以直接跨越该 Installation 的 `import` BoundaryPoint，也可以跨越关联 Ref 的 `import-ref` BoundaryPoint。 | 单个 `--install-id` 时为 `subject.kind: "installation"` 和 `subject.install-id`；多对象选择时为 `subject.kind: "installation-selection"`。`details.blocked-installations` 的每项包含 `install-id`、`install-path`、`blocking-links`（元素包含 `path`、`line`、`link-path`）和 `blocking-ref-target-dirs`。 |
| `ref.source.unavailable` | Installation 的 install-path 或指定 src-sub-dir 不能作为受管理引用源。 | `subject.kind: "installation"`、`subject.install-id`、`details.install-path`、`details.src-sub-dir`。 |
| `ref.target.unavailable` | target-dir 已被不相容内容占用，或无法建立受管理引用。 | `subject.kind: "ref"`、`subject.target-dir`、`details.install-id`、`details.operation`。 |
| `ref.remove.blocked` | 当前目录树有效范围内仍有 Markdown link 跨越待移除 Ref 的 `import-ref` BoundaryPoint。 | `subject.kind: "ref"`、`subject.target-dir`、`details.blocking-links`；每项包含 `path`、`line`、`link-path`。 |
| `ref.target.inconsistent` | 目标位置的受管理引用与 Ref 记录不一致，无法安全更新或移除。 | `subject.kind: "ref"`、`subject.target-dir`、`details.expected-source`、`details.actual-target`。 |

`import query` 没有候选项是正常成功结果，返回空 `candidates`，不使用错误结构。

### 9.4 `worktree`

| `message.code` | 触发条件 | `subject` / `details` 必填信息 |
|---|---|---|
| `revision.unresolvable` | URL 来源的 branch、tag 或 commit selector 无法解析为创建 Worktree 所需 revision。 | `subject.kind: "git-source"`、`subject.git-url`、`details.selector-kind`、`details.selector-value`、`details.operation: "worktree create"`。 |
| `worktree.source.unavailable` | `--install-id` 没有可用 Installation，或 `--url` 对应 Git source 无法用于创建工作区。 | `subject.kind: "worktree"`、`subject.work-path`、`details.install-id` 或 `details.git-url`、`details.operation: "create"`。 |
| `worktree.target.unavailable` | work-path 已存在、发生路径冲突或无法创建工作区。 | `subject.kind: "worktree"`、`subject.work-path`、`details.operation: "create"`、`details.occupant`。 |
| `worktree.ignore.protection.failed` | 自定义 work-path 无法加入或移出 Git ignore，导致工作区无法满足模型约束。 | `subject.kind: "worktree"`、`subject.work-path`、`details.operation`、`details.gitignore-path`。 |
| `worktree.not-found` | `query` 指定的 work-path 没有 Worktree 记录。 | `subject.kind: "worktree"`、`subject.work-path`、`details.operation: "query"`。 |
| `worktree.remove.blocked` | worktree 存在未提交修改或无法读取 Git worktree 状态，且未指定 `--force`。 | `subject.kind: "worktree"`、`subject.work-path`、`details.reason`、`details.required-option: "--force"`。 |
| `worktree.remove.unavailable` | `worktree remove` 无法直接删除已记录的 work-path。 | `subject.kind: "worktree"`、`subject.work-path`、`details.operation: "remove"`、`details.reason: "worktree-path-unavailable"`。 |

工作目录缺失但 Worktree 记录仍存在时，`worktree remove` 清理模型状态并成功完成，不产生错误。

### 9.5 `validate`

`validate` 发现目录树、链接、import、worktree 或工作模型问题时，使用 `status: "ok"`、
`valid: false` 和 `diagnostics`，而不是本节错误码。仅在无法读取或建立指定校验范围时使用以下
命令错误：

| `message.code` | 触发条件 | `subject` / `details` 必填信息 |
|---|---|---|
| `validation.scope.unavailable` | `--subdir` 无法作为当前 Git root 内可读取的校验范围使用，或已位于当前 doctidex 目录树的边界外。 | `subject.kind: "validation-scope"`、`subject.path`、`details.repos-path`、`details.operation: "validate"`、`details.reason`。 |
| `validation.scan.unavailable` | 无法遍历或读取校验范围，从而不能保证诊断完整性。 | `subject.kind: "validation-scope"`、`subject.path`、`details.phase`、`details.unreadable-paths`。 |

### 9.6 `repair`

`repair` 的物理修复失败沿用对应操作已有的错误码和 `message.details` 结构；复用规则由
[需求 0002-09：`repair` 命令簇工作流与生命周期设计](09-repair.md) 第 6 节确定。工作模型未初始化、
事务不可用和状态无效仍使用本节通用错误。

## 10. 验收标准

- [x] `init`、`boundary-set`、`import`、`worktree`、`validate`、`repair` 六个命令簇的已确认能力分别记录完整。
- [x] 每个命令簇的参数层级、参数错误行为和返回结果结构均已明确。
- [x] 每个命令簇的成功、失败和退出状态关系均已明确。
- [x] 设计保持与父需求和 doctidex v2 Architecture 一致。
- [x] 本文未引入上述命令簇之外的功能或实现方案。
- [x] 已确定的 CLI 契约已实现，并由完整回归和 phase 7 端到端场景验证。

## 11. 依赖与状态

- 父需求：[需求 0002](overview.md)。
- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。

本子需求为 `approved`，其实施已完成。CLI 参数、返回结构、结构化错误和退出状态已实现，并由 phase 7 的
完整回归和端到端场景验证；当前用户接口以 user 文档为权威说明。
