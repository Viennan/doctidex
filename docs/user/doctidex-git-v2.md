# doctidex-git v2 使用指南

`doctidex-git` 为一个 Git 仓库建立和维护 doctidex v2 工作模型。它将固定 revision 的外部仓库作为 Installation 管理，以 Ref 公开其内容，并用 Worktree 提供可继续开发的工作区。

目录树的根身份、`index.md`、boundary 与 Markdown link 规则由[doctidex v2 目录树外观规范](../architecture/doctidex-v2-directory-tree.md)定义。关于工作模型、缓存、事务和实现约束，请参阅[doctidex-git v2 Architecture](../architecture/doctidex-git-v2.md)。

## 开始使用

工具适用于 Linux 和 macOS 上的 Git worktree。先进入目标 Git root，并完成初始化：

```bash
cd /path/to/repository
doctidex-git init
doctidex-git validate --model-structure
```

首次 `init` 创建或补齐根 `index.md`、`.doctidex-git/` 工作空间和必要的 Git ignore 规则。随后可安装外部固定 revision、在当前树中建立引用，或创建用于开发的 worktree。

```bash
doctidex-git import install \
  --tracked \
  --url git@github.com:Viennan/doctidex.git \
  --branch main \
  --key doctidex

doctidex-git import ref \
  --install-id <INSTALL-ID> \
  --target-dir /external/doctidex

doctidex-git worktree create \
  --install-id <INSTALL-ID> \
  --tree-name maintenance

doctidex-git validate
```

`import install` 的结果提供 `<INSTALL-ID>`，供 Ref 与 Worktree 创建使用。Ref 目标和 Worktree 路径都会成为当前目录树的 boundary。

## 心智模型

| 概念 | 用户可观察的含义 |
|---|---|
| Git root | 单次命令的仓库边界，也是仓库内部路径 `/...` 的根。 |
| 工作空间 | Git root 下的 `.doctidex-git/`，保存仓库级状态和受管理目录。 |
| Installation | 某个外部 Git URL 的固定 commit 及其安装路径；它可为 tracked 或 untracked。 |
| Ref | 从当前仓库目录到 Installation 内源目录的受管理符号链接；它总是 tracked。 |
| Worktree | 从 Installation 或 URL 创建的可修改 Git worktree；只记录其创建基准 commit。 |
| BoundaryPoint | 当前 doctidex 目录树规则停止适用的目录；custom、Installation、Ref 和 Worktree 都可形成它。 |

tracked Installation 只将元信息交给 Git 跟踪，实际安装目录仍是 Git ignored。因此克隆已有仓库后，缺少 tracked Installation 的 `install-path` 是合法状态；使用 `import restore` 重新创建物理目录。

## 按需文档

先阅读[共同接口与恢复](doctidex-git-v2/common.md)，了解 Git root、路径、JSON 结果、退出码、缓存配置和跨命令恢复边界。随后只加载正在使用的命令簇：

| 任务 | 文档 |
|---|---|
| 建立或检查工作模型入口 | [`init`](doctidex-git-v2/init.md) |
| 划定当前目录树的 escape boundary | [`boundary-set`](doctidex-git-v2/boundary-set.md) |
| 固定外部 revision、建立 Ref、查询或移除 Installation | [`import`](doctidex-git-v2/import.md) |
| 创建、查询或移除可修改工作区 | [`worktree`](doctidex-git-v2/worktree.md) |
| 只读检查模型、目录树和 Markdown link | [`validate`](doctidex-git-v2/validate.md) |
| 让物理状态与工作模型相容 | [`repair`](doctidex-git-v2/repair.md) |

## 使用边界

不要手工编辑 `.doctidex-git/` 中的状态 JSON，也不要把其中的实际 Installation 或 Worktree 目录加入 Git。使用 `validate` 观察问题，使用 `repair` 对齐可修复的物理状态。

doctidex-git 只协调遵守其锁和事务协议的 doctidex-git 进程。它不保证用户、编辑器或其他程序同时直接修改状态文件、缓存或受管理目录时的 race 安全性，也不能回滚 Git fetch、bare repository object 的追加或用户在 Worktree 中作出的提交。
