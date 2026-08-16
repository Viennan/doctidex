# `import`

`import` 将外部 Git 仓库的一个固定 revision 作为 Installation 管理，并可在当前目录树中通过受管理 Ref 公开其内容。它适用于把稳定的外部知识、代码或文档纳入当前 doctidex 树，而不让其 revision 随远程 branch 自动变化。

共同的 Git root、路径、缓存、JSON envelope 和通用错误规则见[共同接口与恢复](common.md)。

## 安装固定 revision

```bash
doctidex-git import install \
  (--tracked | --untracked) \
  --url <GIT-URL> \
  (--branch <BRANCH> | --tag <TAG> | --commit <HASH>) \
  [--key <QUERY-KEY>]...
```

| 参数 | 含义 |
|---|---|
| `--tracked` / `--untracked` | 必须选择一个。tracked 将 Installation 元信息写入 `imports.json`；untracked 写入本地 `runtime.json`。实际安装目录始终 Git ignored。 |
| `--url` | 必填的外部 Git URL。 |
| `--branch` / `--tag` / `--commit` | 必须且只能选择一个 revision selector。 |
| `--key` | 可重复的查询 key。 |

branch 或 tag 会先同步远程引用，再将当前指向的 commit 固定到 Installation。直接 commit 会获取并固定所给 hash。再次安装相同 branch/tag 时，远程 commit 未变则复用已有 Installation，已变则替换为新 Installation；同 URL、同 commit 的直接 commit 同样复用。

成功结果：

```json
{
  "status": "ok",
  "message": {},
  "install-id": "<INSTALL-ID>",
  "install-path": "/.doctidex-git/imports/<DOMAIN>/<REPOSITORY>/<SELECTOR>"
}
```

`install-path` 自动派生 `import` BoundaryPoint。已有同源、detached 且干净的 worktree 会被复用并切换到目标 commit；非 Git 残留或不可复用的同源目录会重建；不同 Git URL 控制的既有目录不会被覆盖。

## 恢复与跟踪

```bash
doctidex-git import restore --install-id <INSTALL-ID>
doctidex-git import track --install-id <INSTALL-ID>
```

`restore` 仅接受 tracked Installation，严格使用其已记录的 `commit-hash`，不重新解析 branch 或 tag。它解决 tracked 元信息已随 Git 恢复、而 `install-path` 尚不存在的正常状态。成功结果与 `install` 相同。

`track` 将 untracked Installation 提升为 tracked；已 tracked 时成功 no-op。它不重新安装或移动目录，成功结果也与 `install` 相同。

## 建立与移除 Ref

```bash
doctidex-git import ref \
  --install-id <INSTALL-ID> \
  [--src-sub-dir <INSTALL-REPOSITORY-PATH>] \
  --target-dir <REPOSITORY-PATH>

doctidex-git import unref --target-dir <REPOSITORY-PATH>
```

| 参数 | 含义 |
|---|---|
| `--install-id` | 要公开的 Installation。 |
| `--src-sub-dir` | 可选的 Installation 内部绝对路径；省略时公开 Installation 根。 |
| `--target-dir` | 当前 Git root 内创建符号链接的位置。 |

`ref` 创建从 `target-dir` 父目录到源目录的相对符号链接，并将 untracked Installation 提升为 tracked。它还派生 `import-ref` BoundaryPoint。Installation 尚未 restore、源目录不存在或目标被其他内容占用时，命令失败，不创建 Ref。

`unref` 在没有 Ref 记录时成功 no-op。若当前 doctidex 树内的 Markdown link 跨越该 Ref boundary，命令返回 `ref.remove.blocked`，必须先调整 link。两条命令成功时都返回通用成功结果。

## 查询

```bash
doctidex-git import query \
  (--install-id <INSTALL-ID> | --install-path <REPOSITORY-PATH> | \
   --ref-path <REPOSITORY-PATH> | --key <QUERY-KEY>...)
```

四种选择器必须选择一种。`--key` 可重复，是用户模糊搜索：任一保存 key 包含任一输入 key 即匹配；结果按匹配 key 数、精确匹配数和模型稳定顺序排序。没有候选项是成功结果。

```json
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
      "branch": "<BRANCH-OR-EMPTY>",
      "tag": "<TAG-OR-EMPTY>",
      "refs": [
        {"src-sub-dir": "/<INSTALL-SUB-DIR-OR-EMPTY>", "target-dir": "/<REPOSITORY-PATH>"}
      ]
    }
  ]
}
```

`refs[].src-sub-dir` 为空字符串时表示 Installation 根。`branch` 与 `tag` 也以空字符串表示该 Installation 未由对应 selector 创建。

## 移除 Installation

```bash
doctidex-git import remove \
  (--install-id <INSTALL-ID> | --untracked | --auto)
```

| 选择器 | 行为 |
|---|---|
| `--install-id` | 选择一个 Installation；记录不存在时成功 no-op。 |
| `--untracked` | 选择全部 untracked Installation。 |
| `--auto` | 选择 untracked Installation，以及没有受管理 Ref 的 Installation。 |

移除 tracked Installation 前，工具检查当前 doctidex 树中直接跨越 Installation boundary 的 link、经其 Ref 跨越的 link，以及关联 Ref。任一关系存在即返回 `installation.remove.blocked`，不删除本次选择的任何 Installation。通过检查后，命令移除模型记录和仍存在的实际目录；缺失的 tracked `install-path` 不阻止移除。

## 可处理错误

| 代码 | 原因与处理 |
|---|---|
| `revision.unresolvable` | branch、tag 或 commit 无法解析为需要的 revision；检查 `selector-kind`、`selector-value` 与远程可达性。 |
| `cache.repository.unavailable` | 无法获得该 URL 的 bare repository；检查 `git-url`、`operation` 和本地 cache。 |
| `installation.target.unavailable` | install-path 被不同来源占用或无法用于目标 revision；不要覆盖该路径，改正占用后重试。 |
| `installation.not-found` | 需要已有 Installation 的命令未找到 `install-id`；用 `import query` 查找。 |
| `installation.tracking-state.invalid` | `restore` 的 Installation 不是 tracked；先使用 `track`，或选择 tracked 记录。 |
| `installation.restore.unavailable` | 无法按记录的 commit 恢复 tracked Installation；检查 `install-id`、`install-path` 与 `commit-hash`。 |
| `installation.remove.blocked` | tracked Installation 仍有 Ref 或跨界 link；`blocked-installations` 给出 Ref 目标和 link 文件、行号。 |
| `ref.source.unavailable` | Installation 或 `src-sub-dir` 尚不能作为链接源；先 restore 或修正源路径。 |
| `ref.target.unavailable` | `target-dir` 已被不相容内容占用，或无法创建链接。 |
| `ref.target.inconsistent` | 实际符号链接与 Ref 记录不一致；先用 `validate` 检查，再按需要 `repair`。 |
| `ref.remove.blocked` | Markdown link 仍跨越该 Ref boundary；`blocking-links` 给出文件和行号。 |

关于跨界 link 的注释与删前阻塞关系，参阅[`validate`](validate.md)；关于 JSON/物理状态不一致，参阅[`repair`](repair.md)。
