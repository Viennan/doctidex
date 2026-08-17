# `init`

`init` 为当前 Git root 建立 doctidex-git 工作模型。它适合在一个现有 Git 仓库首次采用 doctidex v2 时执行。

共同的 Git root、路径、JSON 结果和通用错误规则见[共同接口与恢复](common.md)。

## 调用

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] init
```

除通用 `--repos-path` 外没有参数。

## 首次初始化

当 `.doctidex-git/` 不存在或为空时，命令创建以下工作模型工件：

```text
.doctidex-git/
├── config.toml
├── boundary-set.json
├── imports.json
├── import-refs.json
└── runtime.json
```

它还会创建或补齐根 `index.md` 的必需 frontmatter：

```yaml
---
type: index
doctidex:
  type: index
  root: true
---
```

已有正文和不相关 frontmatter 保持不变。运行时状态、事务、Installation 和默认 Worktree 目录会进入 Git ignore。成功时返回通用成功结果。

## 已有工作空间

若 `.doctidex-git/` 已存在且非空，`init` 不覆盖、不恢复、不补建也不校验已有状态，而是返回：

```json
{
  "status": "ok",
  "message": {
    "code": "workspace.already-initialized",
    "summary": "Initialization has already been run; use validate --model-structure to check the work model.",
    "details": {"next-command": "validate --model-structure"}
  }
}
```

下一步执行 [`validate --model-structure`](validate.md)，而不是重复初始化。

## 可处理错误

| 代码 | 原因与处理 |
|---|---|
| `root-index.frontmatter.conflict` | 根 `index.md` 的 `type`、`doctidex.type` 或 `doctidex.root` 已有冲突值或类型；修正该字段后重试。 |
| `root-index.frontmatter.invalid` | 现有 frontmatter 不是可安全补充的 YAML 映射；修正 frontmatter 后重试。 |
| `workspace.initialize.failed` | 无法建立完整工作空间或 ignore 保护；检查 Git root 的目录权限和可用磁盘空间。 |
| 通用错误 | 见[共同接口与恢复](common.md)。 |

`init` 不创建 Installation、Ref、Worktree 或 custom boundary。需要这些对象时分别进入[`import`](import.md)、[`worktree`](worktree.md) 或 [`boundary-set`](boundary-set.md)。
