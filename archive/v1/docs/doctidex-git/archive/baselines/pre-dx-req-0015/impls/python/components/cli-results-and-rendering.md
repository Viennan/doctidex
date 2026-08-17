# CLI、results 与 rendering

> 归档状态：`format-illegal`。本页是 DX-REQ-0015 前的历史文档基线，不定义当前产品。

Package、runtime 与 dependency direction 由
[Platform、package 与 dependencies](../platform-package-and-dependencies.md)统一定义。本篇只
负责 Architecture Surface Adapter、Result Budgeter 和 failure presentation 的 Python mapping。

## 1. [`errors.py`](../../../../../../../../impls/libs/python/whero/doctidex/errors.py) 与
[`results.py`](../../../../../../../../impls/libs/python/whero/doctidex/results.py)

调用者：protocol、Git domain 与 CLI。它们不决定业务事实，只统一可序列化结构。

`DoctidexError` 的全部属性为：`message`、`operation`、`affected`、`result`、`actions`、
`requires_user`、`code`、`domain`、`path`、`network`、内部 `details` 和可公开合并的
`fields`。`as_result(root)` 把错误变为 blocked envelope 和一个 error Finding，不暴露
traceback。

`results.py` 提供：

- `finding(domain, severity, code, message, path, actions)` 建立六字段 Finding；
- `envelope(...)` 固定 12 个公共字段，再合并 operation 字段；
- `query_identity` 对规范输入建立稳定摘要；
- `encode_cursor`/`decode_cursor` 编解码不透明 URL-safe token，并核对 identity/state；
- `paginate_lists` 对每个顶层列表分别应用同一 limit，产生 total/returned/truncated 与单一
  continuation cursor。

cursor 没有签名，属于调用期一致性 token 而非授权凭据；root fingerprint 或查询 identity
变化即拒绝。分页发生在完整领域结果排序之后。

## 2. [`cli/main.py`](../../../../../../../../impls/libs/python/whero/doctidex/cli/main.py) 与
[`cli/render.py`](../../../../../../../../impls/libs/python/whero/doctidex/cli/render.py)

`main(argv)` 是 console 入口。`Parser.error` 把 argparse 失败转成 `argument_invalid` JSON；
`_parser` 只注册 v1 command；`_dispatch` 选择 root、构造 selector、调用领域 service。`hook --install | --run`
构造 `HookService`：前者写当前 host 的 `post-checkout` entrypoint，后者离线协调 selected root；两者没有
dry-run/apply、selector 或 pagination。`external remove INSTALL_ID [--root ROOT] [--dry-run | --apply]` 调用
`ExternalService.remove`；hidden dependency 直接返回 `preserved_hidden` completed no-op，不进入 reference
scan。`cache clean` 的 mutually exclusive
`--url`/`--auto` selector 分别进入 `CacheService.clean`/`CacheService.clean_auto`；auto 的 item-level
preserved/blocked 仍是 completed warning，只有 parser 或 URL mode domain failure 才走 top-level blocked。
`_managed_owner_roots` 与 `_select_path_owner` 防止 install content root 冒充外层 owner；
`_owner_root_for_worktree` 只接受 exact managed path。

异常边界：领域错误退出 2；validation protocol fail 退出 1；中断退出 130；未知异常经
`git/diagnostics.py::write_diagnostic` 写入用户 cache 的内部 traceback，只把随机 diagnostic ID
放进结果。`render_json` 稳定输出 UTF-8 JSON；`render_human` 是非稳定摘要，不参与程序契约。

Python 不建立独立 `CommandContext` 或 `Plan` class。Architecture Command Context 由 argparse
`Namespace`、`main` 的 cwd/output mode 与 `_dispatch` 的 selected `RootContext`/selector/path/
apply/limit/cursor locals 共同实现；每个 service 的 planned paths、frontmatter plan、expected
record/mapping 与 first classification dict 构成 operation-specific Plan。Plan 不序列化、不跨调用
复用；apply 重新调用 service 并在 lock 内复查，而不是提交 dry-run token。

读写与并发：parser/renderer 无持久副作用；dispatch 的副作用由领域 service 决定。`--json`
在解析前识别且最多一次，因此语法错误仍能返回 envelope。

## 3. 典型调用

```python
completed = subprocess.run(
    ["doctidex-git", "validate", root, "--scope", "/docs", "--json"],
    text=True,
    capture_output=True,
)
payload = json.loads(completed.stdout)
```

## 4. Effects、concurrency 与 evidence

Parser、renderer 与 result helpers 不持有 persistent state；dispatch 的 effect 和 lock 由被调用
service 决定。典型失败在 `main` 边界转为 envelope，unexpected exception 只额外写 diagnostic。

证据：[tests/test_git_plugin.py](../../../../../../../../impls/libs/python/tests/test_git_plugin.py) 的
`test_parser_rejects_old_surface_with_json`、`test_validate_cli_and_nested_host_gitignore` 与
`test_root_lock_conflict_is_bounded_and_preserves_owner`；
[tests/test_protocol.py](../../../../../../../../impls/libs/python/tests/test_protocol.py) 的
`test_scoped_validation_filters_output_and_cursor_is_state_bound`。
