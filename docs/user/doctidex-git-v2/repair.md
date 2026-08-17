# `repair`

`repair` 以当前 Git root 的 JSON 工作模型为基准，让可修复的物理状态与记录相容。它适合在 `validate` 已报告模型或物理对象问题后使用，也会被普通命令在发现可恢复的残留 RuntimeStore 事务时内部调用。

共同的 Git root、路径、JSON envelope、退出码和通用错误规则见[共同接口与恢复](common.md)。先用[`validate`](validate.md)观察问题；修复完成后再次运行 `validate` 确认结果。

## 调用与结果

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] repair
```

除通用 `--repos-path` 外没有参数。成功时返回：

```json
{"status": "ok", "message": {}}
```

重复运行在已经相容的环境中不应引入额外变化。

## 修复范围

| 对象 | repair 的行为 |
|---|---|
| 残留 RuntimeStore 事务 | 分类 journal，必要时用 backup 收敛 JSON；除已确认 committed 的残留外，先完成物理修复再清理 journal。 |
| Installation | 对有实际目录的记录对齐物理状态；对缺失但可恢复的 Installation 重建其 worktree。JSON 未记录但实际存在的 install-path 不会被提升为新 Installation。 |
| Ref | 缺少符号链接时重建；目标存在但不符合记录时删除后重建；Ref 的 Installation 不再存在时直接删除 Ref 记录。 |
| 未登记 Installation 链接 | 删除仓库内指向 Installation 或其子目录、但没有 Ref 记录的符号链接。 |
| Worktree | 已记录的 `work-path` 缺失时重新创建。 |
| Boundary 与 Git ignore | 让派生 boundary 所依赖的对象和受管理 ignore 规则回到模型要求。 |

## 不做的事

repair 不扫描、诊断或改写 Markdown 文件中的 link，也不为 JSON 中缺失的物理对象创建新的领域记录。它不尝试将仓库恢复到一次中断前的历史文件系统快照，不回滚 Git fetch、bare object 的追加或用户在 Worktree 中作出的提交。

因此，`validate` 报告 `link.annotation.required`、`link.target.exists` 或文档路径问题时，应由用户修改 Markdown 内容；repair 只能修复工作模型已声明对象的物理一致性。

## 命令错误

repair 复用对应对象操作的结构化错误，而不是暴露原始文件系统或 Git 错误。例如恢复 Installation 时可返回 `installation.restore.unavailable`，恢复 Worktree 时可返回 `worktree.source.unavailable`，缓存不可用时可返回 `cache.repository.unavailable`。具体对象错误见[`import`](import.md)和[`worktree`](worktree.md)，Store 与 Git root 错误见[共同接口与恢复](common.md)。

repair 自身失败时不会提前删除仍待处理的 residual journal，下一次普通命令或显式 repair 仍能感知并继续处理。
