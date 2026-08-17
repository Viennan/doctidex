# `validate`

`validate` 只读地检查 doctidex 根、工作模型、当前目录树范围内的 Markdown link，以及受管理 Worktree。它适合用于初始化后检查、提交前检查和 repair 前后的问题确认。

共同的 Git root、路径、JSON envelope、退出码和通用错误规则见[共同接口与恢复](common.md)。

## 调用与范围

```bash
doctidex-git validate \
  [--subdir <REPOSITORY-PATH> | --model-structure]
```

| 选项 | 行为 |
|---|---|
| 不提供选项 | 检查完整工作模型、当前 doctidex 树、有效范围内 link 和全部受管理 Worktree。 |
| `--subdir` | 将内容检查限制到一个可读取的现有目录。工作模型仍完整检查；只检查该子目录可能包含的 Worktree。 |
| `--model-structure` | 只检查工作模型和根 `index.md` 的基础 frontmatter，不扫描 Markdown 内容、跨界注释或 Worktree 未提交修改。 |

`--subdir` 与 `--model-structure` 互斥。`--subdir` 不得指定 `/.doctidex-git` 或其后代，也不得越过当前目录树的 BoundaryPoint。

## 结果与退出码

校验发现问题不是命令执行错误，因此结果仍为 `status: "ok"`，但 `valid` 为 `false`：

```json
{
  "status": "ok",
  "message": {},
  "valid": false,
  "scope": {"repos-path": "/work/repository", "subdir": "/"},
  "diagnostics": [
    {
      "rule": "link.annotation.required",
      "path": "/docs/guide.md",
      "line": 12,
      "message": "A cross-boundary link requires a matching doctidex annotation.",
      "details": {
        "link-path": "/external/doctidex/index.md",
        "expected-cross-boundary-point": "/external/doctidex"
      }
    }
  ]
}
```

| 字段 | 含义 |
|---|---|
| `valid` | 所有校验通过时为 `true`，任一诊断存在时为 `false`。 |
| `scope.repos-path` | 实际使用的 Git root。 |
| `scope.subdir` | 实际内容范围；默认和 `--model-structure` 均为 `/`。 |
| `diagnostics` | 空数组表示通过；每项使用稳定 `rule`、仓库内部 `path`、人类可读 `message` 和结构化 `details`。Markdown link 相关项还包含 1 起始的 `line`。 |

退出码为 0（`valid: true`）、1（`valid: false`）或 2（命令无法完成）。

## 检查内容

| 规则 | 含义与下一步 |
|---|---|
| `work-model.valid` | 工作空间、状态投影、记录关系、受管理路径或 Git ignore 不符合模型。`details.violations` 给出具体对象；先检查结构，再按需执行 `repair`。 |
| `index.conforms` | 根 `index.md` 缺失、不可读或不满足 doctidex 根 frontmatter；修正文档或重新初始化空工作空间。 |
| `link.path.conforms` | 本地 Markdown link 不能规范化为当前仓库内路径；修正 link path。 |
| `link.target.exists` | 本地 link 目标不存在；修正 link 或创建目标。 |
| `link.annotation.required` | link 跨越第一个 BoundaryPoint，但没有匹配的 `cross-boundary-point` 注释；按下文补充注释。 |
| `import.link.tracked` | link 跨越的 Installation 为 untracked；使用 `import track` 或建立 Ref。 |
| `worktree.clean` | 受管理 Worktree 有未提交修改；提交、暂存、还原，或确认其工作状态。 |

当 tracked Installation 的物理目录在本地缺失时，validate 只确认其 `install-id` 与工作模型记录有效，不执行 restore，也不将该 Installation 下的缺失 link target 作为问题。这是 Git clone 后的合法状态。

## 跨界 link 注释

本地 Markdown link 首次跨越 BoundaryPoint 时，必须在 link 后紧邻的连续 HTML 注释序列中提供 `doctidex` YAML 映射：

```markdown
[外部文档](/external/doctidex/index.md)
<!-- another comment -->
<!-- doctidex: {cross-boundary-point: /external/doctidex} -->
```

注释块之间可以有空白，`doctidex` 注释不必是第一个。读取方按源码顺序采用第一个有效映射。`cross-boundary-point` 必须是 link path 的完整路径段前缀，并保持与 link 相同的绝对或相对路径形式；相对路径将按源 Markdown 文档解析。

## 命令错误

| 代码 | 原因与处理 |
|---|---|
| `validation.scope.unavailable` | `--subdir` 不是可读目录、位于工作空间内部或越过 boundary；检查 `details.reason` 后选择有效范围。 |
| `validation.scan.unavailable` | 无法遍历或读取校验范围；检查 `details.phase` 与 `unreadable-paths`，修复权限或目录状态后重试。 |
| 通用错误 | 见[共同接口与恢复](common.md)。 |

`validate` 不修复任何问题。需要让物理 Installation、Ref、Worktree、boundary 或 ignore 状态与记录相容时，转到[`repair`](repair.md)。
