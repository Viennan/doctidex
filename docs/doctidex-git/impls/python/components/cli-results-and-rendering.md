# CLI、结果与渲染的实现

Python 的 console dispatch、稳定 result 构造和 human/JSON rendering 由
[`cli/main.py`](../../../../../impls/libs/python/whero/doctidex/cli/main.py),
[`cli/render.py`](../../../../../impls/libs/python/whero/doctidex/cli/render.py),
[`errors.py`](../../../../../impls/libs/python/whero/doctidex/errors.py) 和
[`results.py`](../../../../../impls/libs/python/whero/doctidex/results.py) 实现。它们落实
[CLI](../../../architecture/interfaces/cli.md)、[JSON schema](../../../architecture/interfaces/cli-schema.md) 和
[operation safety](../../../architecture/operation-safety-and-recovery.md) contract；不负责 external、worktree
或 protocol semantics。

## 职责

| 责任主体 | 职责 | 边界 |
|---|---|---|
| CLI parser/dispatcher | 规范化 argv、选择 service，并请求 JSON/human presentation。 | 带 `--json` 的 syntax error 仍输出 blocked envelope；parser 不虚构 domain fact。 |
| `envelope`、`finding` 与 pagination helpers | 构造共同 result shape、stable code/finding 和 opaque cursor identity。 | JSON field 的 meaning/requiredness 由 Architecture 负责；implementation encoding/cursor bytes 属于 private。 |
| `DoctidexError` translation | 携带 operation、domain、affected path/action、`requires_user` 和 safe detail。 | unexpected failure 映射为 opaque diagnostic；traceback/cache path 不属于正常 user surface。 |
| renderer | 格式化 human result 或单个 UTF-8 JSON object。 | human labels/message 不能作为 program contract 解析。 |

dispatcher 通过 domain services 完成 protocol、external、hook、worktree 和 cache work，不会访问 private
runtime/cache state 来绕过这些 owner。console/package assembly 见
[variant delivery](../variant-delivery-and-surface.md)；实际创建的 artifacts 见
[worksite inventory](../worksite-inventory-and-construction.md)。

## 证据与限制

[`test_protocol.py`](../../../../../impls/libs/python/tests/test_protocol.py) 和
[`test_git_plugin.py`](../../../../../impls/libs/python/tests/test_git_plugin.py) 覆盖 JSON parser failure、
envelope/finding/pagination behavior 和 operation results。当前 hook-specific `metadata_warning` limitation
不会由 generic rendering 修复；其记录仍在
[coverage](../architecture-coverage-evidence-and-worksite-validation.md#5-known-gaps-and-limits)。
