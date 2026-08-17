# `boundary-set`

`boundary-set` 管理当前 doctidex 目录树的 custom escape boundary，并解析给定路径首先遇到的 BoundaryPoint。它适用于排除生成目录、外部内容或其他不应继续应用当前树规则的范围。

共同的 Git root、路径、JSON 结果和通用错误规则见[共同接口与恢复](common.md)。

## 添加与移除 custom boundary

```bash
doctidex-git boundary-set add --path <REPOSITORY-PATH> [--path <REPOSITORY-PATH>]...
doctidex-git boundary-set remove --path <REPOSITORY-PATH> [--path <REPOSITORY-PATH>]...
```

`--path` 必填且可重复。每个路径都是仓库内部绝对路径，目标目录不必已经存在。

`add` 将路径作为 `custom` BoundaryPoint 持久化到 Git-tracked `boundary-set.json`。`remove` 只删除 custom 记录；没有对应 custom 记录时成功 no-op，且不会影响由 Installation、Ref 或 Worktree 派生的 boundary。两条命令成功时返回通用成功结果。

## 解析边界

```bash
doctidex-git boundary-set parse --path <REPOSITORY-PATH> [--path <REPOSITORY-PATH>]...
```

对每个输入路径，`parse` 从 Git root 向下寻找第一个 BoundaryPoint。它只读，不修改工作模型：

```json
{
  "status": "ok",
  "message": {},
  "results": [
    {
      "path": "/external/doctidex/readme.md",
      "has-boundary": true,
      "boundary-point": "/external/doctidex",
      "boundary-type": "import-ref"
    }
  ]
}
```

`boundary-type` 为 `custom`、`import`、`import-ref` 或 `worktree`。路径未命中 boundary 是正常结果：该项的 `has-boundary` 为 `false`，不返回 `boundary-point` 和 `boundary-type`。

## 派生 boundary

| 类型 | 来源 | 正确的管理方式 |
|---|---|---|
| `custom` | 本命令创建 | 使用 `add` 和 `remove`。 |
| `import` | Installation 的 `install-path` | 使用[`import`](import.md)管理 Installation。 |
| `import-ref` | Ref 的 `target-dir` | 使用 `import ref` 或 `import unref`。 |
| `worktree` | Worktree 的 `work-path` | 使用[`worktree`](worktree.md)管理 Worktree。 |

命令不会单独保存派生 boundary；它们随各自模型记录自动出现或消失。路径重叠时，只使用从 Git root 出发首先命中的 boundary。

## 可处理错误

| 代码 | 原因与处理 |
|---|---|
| `boundary-point.remove.prohibited` | `remove` 收到了由 Installation、Ref 或 Worktree 派生的 boundary，而不是 custom 记录；使用对应的 [`import`](import.md) 或 [`worktree`](worktree.md) 命令管理其来源。 |
| 通用错误 | 见[共同接口与恢复](common.md)。 |
