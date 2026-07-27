# 程序集成模式

本文说明程序如何组合 `doctidex-git`。当前受支持的稳定模式是启动 CLI 并消费
`--json`；Python 包内模块属于参考实现，不承诺跨版本兼容。

## 1. 调用模式

```text
caller
  -> 构造精确命令和显式写模式
  -> 启动 doctidex-git ... --json
  -> 解析单个 JSON object
  -> 先按 status/operation 分支
  -> 再读取 operation-specific fields
  -> 处理 collection 或 finding actions
```

调用方应设置明确 cwd，因为 mount、部分 maintenance 命令和省略 PATH 的命令使用 cwd
作为上下文。多根系统应为每次调用记录 cwd、argv、operation 和返回 root，不能只保存
命令名。

## 2. 成功判断

| 检查顺序 | 原因 |
|---|---|
| `status` | 判断请求完成、带警告完成或被阻止。 |
| `operation` | 同名字段在不同操作可能有不同类型，例如 `changed`。 |
| 独立结果域 | `check`/`handoff` 的 protocol、semantic、readiness 不能由顶层状态替代。 |
| `findings`/`semantic_candidates` | 前者是客观问题，后者需要调用方把内容交给人或 agent 判断。 |
| `collection` | 当前页为空不能证明全量为空。 |

退出码是 shell 集成辅助，不是完整业务结果。`warning` 可以退出 0；只有 JSON 字段能
表达三结果域和保留结果。

## 3. 写操作模式

对支持 preview/apply 的命令，程序集成应把两个阶段建模为不同调用：

```text
preview -> 展示 planned result -> 获得调用方授权 -> apply -> 验证实际结果
```

不要把省略 `--dry-run` 当成写入授权。mount prepare 和 maintenance open/close 是显式
生命周期动作，没有 dry-run；调用前应由上层工作流确认其必要性。

## 4. Collection 模式

程序应优先缩小 PATH、MOUNT_PATH 或 MAINTENANCE_ROOT。必须翻页时，只回传返回的
opaque `next_cursor`，并累计每个 collection key 的 `total` 和 `returned`。不要自行
解析或生成 cursor，也不要假设一个 cursor 只影响某个顶层数组。

## 5. Blocked 模式

```text
status == blocked
  -> 保留 result 描述的已有结果
  -> 按 finding.code 选择已知恢复分支
  -> 依次呈现 actions
  -> requires_user != null 时暂停并请求对应输入
```

调用方不得通过无限重试解决凭据、网络、revision、tracked content 或 Git 交付授权。
`unexpected_failure` 可以记录 diagnostic ID 并有限重试一次，但不应向终端用户显示内部
日志。

## 6. 兼容性

- 把新增可选字段视为向后兼容；忽略未知字段。
- 不依赖 JSON key 顺序或人读 label。
- 按稳定 `code` 分支，不匹配英文 message。
- 对必需字段缺失、未知 operation 或字段类型变化执行显式兼容失败。
- 版本升级时以 [CLI 结果契约](cli-schema.md) 和 release information 为准。

## 7. 不提供的程序集成

当前没有声明稳定的 Python service、dataclass 或 state-file API。程序不得读取内部
状态文件来替代 CLI，也不得根据可读路径反推出缓存或 worktree 管理操作。
