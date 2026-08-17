# `worktree`

`worktree` 在当前 Git root 内创建和管理可修改的 Git worktree。它与 Installation 的固定 revision 用途不同：Worktree 只记录创建时的 base commit，之后的提交、分支切换和开发仍由用户与 Git 管理。

共同的 Git root、路径、缓存、JSON envelope 和通用错误规则见[共同接口与恢复](common.md)。

## 创建

```bash
doctidex-git worktree create \
  (--install-id <INSTALL-ID> | --url <GIT-URL> \
    (--branch <BRANCH> | --tag <TAG> | --commit <HASH>)) \
  [--work-path <REPOSITORY-PATH>] \
  [--tree-name <TREE-NAME>]
```

| 输入 | 行为 |
|---|---|
| `--install-id` | 与 `--url` 互斥。使用 Installation 已记录的 `commit-hash` 作为 `base-commit-hash`；不能同时提供 revision selector。 |
| `--url` | 与 `--install-id` 互斥。必须同时提供 `--branch`、`--tag` 或 `--commit` 之一。 |
| `--branch` / `--tag` / `--commit` | 仅 URL 来源可用，且必须且只能选择一个。branch/tag 解析当前远程 commit，commit 固定给定 hash。 |
| `--work-path` | 可选的仓库内部绝对路径，直接指定创建位置。 |
| `--tree-name` | 只在省略 `--work-path` 时生效。可用 `/` 或 `\` 表示嵌套名称。 |

省略 `--work-path` 时，默认路径是 `/.doctidex-git/worktrees/<domain>/<repository-path>/<tree-name>`。省略 `--tree-name` 时，工具生成短随机末级目录名，并在遇到模型或物理冲突时重试。显式 `tree-name` 或 `work-path` 冲突直接失败，不自动改名。

成功时，`work-path` 自动派生 `worktree` BoundaryPoint：

```json
{
  "status": "ok",
  "message": {},
  "work-path": "/.doctidex-git/worktrees/<DOMAIN>/<REPOSITORY>/<TREE-NAME>"
}
```

自定义 `work-path` 会获得工具管理的 Git ignore 规则。Worktree 创建为 detached Git worktree；`base-commit-hash` 只描述创建基准，不随其后的开发变化。

## 查询与移除

```bash
doctidex-git worktree query --work-path <REPOSITORY-PATH>
doctidex-git worktree remove --work-path <REPOSITORY-PATH> [--force]
```

`query` 返回与该路径相关的 Installation；URL 来源 Worktree 没有 `install-id` 字段：

```json
{
  "status": "ok",
  "message": {},
  "install-id": "<INSTALL-ID>"
}
```

`remove` 删除受管理目录、Worktree 记录和自定义路径的 ignore 保护。记录不存在或工作目录已经缺失时成功 no-op。目录有未提交修改或 Git worktree 状态异常时，必须提供 `--force`；成功结果为通用成功结果。

## 可处理错误

| 代码 | 原因与处理 |
|---|---|
| `revision.unresolvable` | URL 来源的 revision 无法解析；检查 `selector-kind`、`selector-value` 与远程。 |
| `worktree.source.unavailable` | Installation 或 URL source 不能提供目标 commit；检查 `install-id` 或 `git-url`，必要时先 restore Installation。 |
| `worktree.target.unavailable` | work-path 已存在、被其他记录管理或无法创建；选择其他显式路径，或先处理占用。 |
| `worktree.ignore.protection.failed` | 自定义路径的 Git ignore 规则无法维护；检查 `.gitignore` 可写性和冲突。 |
| `worktree.not-found` | `query` 指定的路径没有 Worktree 记录。 |
| `worktree.remove.blocked` | 未指定 `--force`，且 Worktree 有未提交修改或状态异常；确认后使用 `--force`。 |
| `worktree.remove.unavailable` | 记录存在但目录无法删除；检查 `work-path` 的权限和占用。 |

使用[`validate`](validate.md)查看 dirty Worktree 或模型诊断；使用[`repair`](repair.md)重建已记录但缺失的 Worktree。
