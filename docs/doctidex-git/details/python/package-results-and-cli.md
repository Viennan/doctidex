# Package、结果与 CLI

## Package 与调用关系

`pyproject.toml` 发布 `whero-doctidex==1.0.0`、Python `>=3.11` 和 `doctidex-git` console
script。运行时依赖 `markdown-it-py` 与 `ruamel.yaml`；Git 是外部可执行依赖。顶层
`whero.doctidex.__version__` 报告 package 版本；`protocol.__init__` 和 `git.__init__` 只导出
当前解析/服务入口，不保留 v0 类。

## `errors.py` 与 `results.py`

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

## `cli/main.py` 与 `cli/render.py`

`main(argv)` 是 console 入口。`Parser.error` 把 argparse 失败转成 `argument_invalid` JSON；
`_parser` 只注册 v1 command；`_dispatch` 选择 root、构造 selector、调用领域 service。
`_managed_owner_roots` 与 `_select_path_owner` 防止 install content root 冒充外层 owner；
`_owner_root_for_worktree` 只接受 exact managed path。

异常边界：领域错误退出 2；validation protocol fail 退出 1；中断退出 130；未知异常经
`git/diagnostics.py::write_diagnostic` 写入用户 cache 的内部 traceback，只把随机 diagnostic ID
放进结果。`render_json` 稳定输出 UTF-8 JSON；`render_human` 是非稳定摘要，不参与程序契约。

读写与并发：parser/renderer 无持久副作用；dispatch 的副作用由领域 service 决定。`--json`
在解析前识别且最多一次，因此语法错误仍能返回 envelope。

典型程序集成：

```python
completed = subprocess.run(
    ["doctidex-git", "validate", root, "--scope", "/docs", "--json"],
    text=True,
    capture_output=True,
)
payload = json.loads(completed.stdout)
```

证据：`tests/test_git_plugin.py` 覆盖旧 surface/重复 JSON 拒绝、operation dispatch、退出码和
blocked schema；`tests/test_protocol.py` 覆盖双列表分页和 cursor 失效。
