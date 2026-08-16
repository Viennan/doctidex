# doctidex-git v2 共同接口与恢复

本页定义所有命令簇共享的 Git root、路径、缓存配置、JSON 返回和恢复边界。命令的具体参数、结果字段和对象错误见对应的[overview](../doctidex-git-v2.md)。

## Git Root 与路径

所有命令使用同一调用形式：

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] <command> [options]
```

省略 `--repos-path` 时，工具从当前目录向上发现第一个 Git root。提供该参数时，它必须正好是 Git root，不能是其子目录。无法发现或确认根时返回 `git-root.unresolved`。

`--path`、`--install-path`、`--ref-path`、`--target-dir`、`--work-path` 和 `--subdir` 都是仓库内部绝对路径：以 `/` 开头，且 `/` 表示 Git root，不是宿主文件系统根。

```text
/docs/guide.md                 # Git root 下的 docs/guide.md
/.doctidex-git/imports/...     # Git root 下的受管理安装路径
```

路径可包含内部的 `.` 或 `..`，但规范化后不得越过 Git root。违反该约束时返回 `repository-path.invalid`。

## Git Cache 配置

Git cache 默认位于 `~/.doctidex-git/cache`。可通过环境变量 `DOCTIDEX-GIT-HOME` 选择另一个 doctidex-git home；该目录中的 `config.toml` 可用 `cache-path` 指定 cache 的绝对路径，或相对于该 home 的路径。

缓存保存 bare Git repository，用于安装、恢复和创建 Worktree。它不是 Installation、Ref 或 Worktree 的权威记录；这些对象仍由当前 Git root 下的工作模型定义。

## 成功结果与退出码

除 `validate` 外，无命令特有字段的成功结果均为：

```json
{"status": "ok", "message": {}}
```

命令特有字段由相应命令簇文档定义。`validate` 将工作流成功与校验通过分离：出现诊断时仍返回 `status: "ok"`，但 `valid: false`。

| 结果 | `status` | 退出码 |
|---|---|---:|
| 命令完成，或 `validate` 校验通过 | `ok` | 0 |
| `validate` 发现诊断 | `ok`, `valid: false` | 1 |
| 参数、工作模型或命令工作流无法完成 | `error` | 2 |

## 结构化错误

命令失败时返回：

```json
{
  "status": "error",
  "message": {
    "code": "<STABLE-CODE>",
    "summary": "<HUMAN-READABLE-SUMMARY>",
    "context": {"command": "<COMMAND>", "repos-path": "<GIT-ROOT>"},
    "subject": {"kind": "<MODEL-OR-PATH>"},
    "details": {}
  }
}
```

自动化必须依据稳定的 `message.code` 与 `message.details` 作判断，不能依赖 `summary`。`context.command` 总会给出实际命令；成功解析 Git root 时 `context.repos-path` 也存在。`subject` 只在错误有明确核心对象时出现。

| 代码 | 原因与处理 |
|---|---|
| `argument.invalid` | 参数缺失、互斥、重复或格式不满足命令契约；检查 `details.parameter`、`received` 和 `constraint`。 |
| `git-root.unresolved` | 指定或发现路径不是可用 Git root；检查 `requested-repos-path` 与 `discovery-start-path`。 |
| `repository-path.invalid` | 仓库内部路径不以 `/` 开头或越过 Git root；检查 `details.parameter` 与 `constraint`。 |
| `work-model.uninitialized` | 当前 Git root 尚未执行 `init`；先运行 `init`。 |
| `work-model.invalid` | 模型文件无法作为当前操作的可靠输入；用 `validate --model-structure` 检查。 |
| `store.transaction.unavailable` | 状态 Store 或残留事务恢复无法完成；检查 `details.store`、`phase`、`state-path`，然后按需执行 `repair` 或重试。 |

命令簇专有错误及其 `details` 见相应文档。

## 恢复边界

`validate` 只读，不创建或清理事务记录，因此适合先观察工作模型和目录树问题。`repair` 以 JSON 工作模型为基准，尽力让 Installation、Ref、Worktree、boundary 和 Git ignore 回到相容状态；它不会修改 Markdown link，也不恢复故障前的历史快照。

普通命令发现残留 RuntimeStore 事务时，会先运行内部修复再重试原操作，最多三次。三次后仍不稳定时返回 `store.transaction.unavailable`。需要直接排查时，依次运行：

```bash
doctidex-git validate --model-structure
doctidex-git repair
doctidex-git validate
```

详细的只读诊断见[`validate`](validate.md)，可修复物理状态的范围见[`repair`](repair.md)。
