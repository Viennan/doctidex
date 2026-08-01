---
type: index
doctidex:
  type: index
---

# doctidex-git v1.0.0 Implementation Details

状态：当前 Python `1.0.0` 实现代码地图。

当前参考实现位于 [`impls/libs/python`](../../../impls/libs/python/)，package 版本为 `1.0.0`，
实现 [v1.0.0 Architecture](../architecture/index.md) 的 CLI、validation、external 与 worktree
surface。具体入口见 [Python Details](python/index.md)。本层只说明实际代码机制；公开命令和
JSON 语义仍以 Architecture 为权威。

历史 `0.1.0` Details 位于
[`archive/v0.1.0/details`](../archive/v0.1.0/details/index.md)。
