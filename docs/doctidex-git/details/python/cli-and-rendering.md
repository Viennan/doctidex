# CLI 编排、预算与 Rendering

本篇说明 `cli/main.py`、`cli/render.py` 和 `errors.py` 如何把协议与 Git services 组合成
公共 CLI。精确语法与字段以 [CLI 用户接口](../../architecture/interfaces/cli.md) 和
[CLI 结果契约](../../architecture/interfaces/cli-schema.md) 为准；本文不复制完整字段表。

## 1. 控制流

```text
argv
  -> _global_options 提取任意位置的全局选项
  -> _parser 解析 command/subcommand
  -> _dispatch 选择 RootContext 和 service
  -> command helper 返回 dict，或抛 DoctidexError
  -> _apply_budget 裁剪所有 collection
  -> render_json / render_human
  -> 根据 blocked / protocol fail 决定退出码
```

`main(argv=None)` 是 console script 入口。传入 `argv` 便于测试；省略时读取
`sys.argv[1:]`。它捕获执行期 `DoctidexError`、`KeyboardInterrupt` 和未预期异常；命令行
parser 自身的 `SystemExit` 不在统一结果边界内。

## 2. 参数层

`_parser()` 声明所有公开命令，`_write_mode()` 为 init/add/remove/sync 添加互斥但非必选
的 dry-run/apply。`_argument_selector()` 把三种互斥参数转换为 `RevisionSelector`。

`_global_options(arguments)` 在正式解析前提取 `--json/--limit/--depth/--cursor`，因此
全局选项可置于任意位置。limit 被 clamp 到 1..1000，depth 到 0..32；depth 当前不被
下游消费。缺值或非整数会在结构化异常边界前退出。

## 3. 上下文与 dispatch

`_dispatch` 是命令总路由。主要辅助函数：

| 函数 | 责任 |
|---|---|
| `_context_for_target(cwd, target, operation)` | inspect 优先保留包含 target 的明确 cwd 宿主，否则按 target 选根。 |
| `_context_for_link_document(cwd, document)` | resolve `--from` 确定宿主与 mounted source link root，保留普通嵌套根歧义。 |
| `_maintenance_context(cwd, args)` | 有精确 maintenance root 时先反查宿主，否则从 cwd 选根。 |
| `_inspect(context, target)` | 组合 host PathContext、mount item、source PathContext、links 和候选。 |
| `_resolve(context, value, link_document)` | 计算规范内部路径、link root、working path 和 mount 状态；涉及 mount 时通过 MaintenanceService 补 relation/reuse facts。 |
| `_mount/_maintenance` | 把子命令转交相应 service，并包装 list/status/scope。 |
| `_check(context, online)` | 合并协议、Git extension、readiness、remote 与 Git-change candidates。 |

`_uses_host_mount_namespace` 识别规范化输入是否回到宿主 namespace；`_is_within` 使用
`absolute().relative_to()`，不解析 symlink。`_raise_ambiguous_link_roots` 统一产生
`root_ambiguous`。

## 4. 批量 mount

`_mount_batch(operation, root, targets, callback)` 在目标数恰好为 1 时直接返回单项
payload，否则顺序调用并把每个 `DoctidexError` 转成 blocked item。它不回滚成功项；
顶层汇总 `findings/completed_count/total_count`。callback 产生的非预期异常会中止整个
批量操作并进入顶层 unexpected failure。

## 5. 输出预算

`_apply_budget(payload, options)` 原地遍历所有 dict/list：

- 顶层列表从 cursor offset 开始，嵌套列表从 0 开始；
- 每个列表最多保留 limit 项；
- 截断或 offset 非零时，按字段路径在 `collection` 记录 total、returned、目录分组、
  truncated 和顶层 next_cursor；
- 分组优先使用 item 的 `path`，其次 `internal_path`，按 parent 排序并再次受 limit 限制；
- 同一 offset 作用于所有顶层列表。

`_encode_cursor/_decode_cursor` 当前实现 offset token。它们是实现细节，程序集成只能把
CLI 返回的 token 原样回传。预算发生在成功或 blocked payload 形成之后，因此 findings
和 actions 也可能截断。

## 6. `DoctidexError`

dataclass 的全部属性：

| 属性 | 默认值 | 含义 |
|---|---|---|
| `message` | 必填 | 用户层失败原因。 |
| `operation` | `operation` | 被阻止的公开操作。 |
| `affected` | `[]` | 受影响路径或对象。 |
| `result` | `No changes were made.` | 已保留结果。 |
| `actions` | `[]` | 有序可执行动作。 |
| `requires_user` | `None` | 需要的用户输入类别。 |
| `code` | `doctidex_error` | 稳定分支标识。 |
| `details` | `{}` | 有限机器诊断；不进入人读输出。 |

`as_result(root=None)` 构造统一 blocked schema，finding 固定为单个 error，`changed=[]`。
业务层在部分成功时必须通过 `result` 或 batch item 显式覆盖默认值。

## 7. Rendering

`render_json(payload)` 使用 UTF-8 字符、两空格缩进和排序 key。`render_human(payload)`：

- blocked 只展示第一个 finding、保留结果、changed、actions 和 requires_user；
- 非 blocked 先按 preferred key 顺序输出，再按字典序输出剩余非空 key；
- `details` 永不人读显示；object/array 压成单行 JSON；boolean 为 yes/no；
- `_label` 只替换下划线并首字符大写。

renderer 不重算状态或字段。新增字段应先在 producer 和公共 schema 中定义，再决定其
人读优先级。

`root_relation` 和 `maintenance_reuse` 位于 human preferred keys 的 maintenance 字段
之后、changed 之前；object 被压成单行 JSON。稳定分支处理仍应使用 `--json`。

```python
from whero.doctidex.cli.main import main

exit_code = main(["--json", "context", "/workspace/docs"])
```

在库内测试可调用 `main(argv)`；其他程序集成仍应启动 CLI 并消费 JSON，因为包内函数
没有稳定兼容承诺。

## 8. 变更检查清单

修改命令或字段时同步检查：parser/help、dispatch 和 service、成功与 blocked 测试、
公共 CLI 文档、结果 schema、相关 Skill、bounded output，以及人读 renderer。不得只改
renderer，也不得让 Skill 依赖 Python 实现术语。
