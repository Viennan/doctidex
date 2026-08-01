---
type: index
doctidex:
  type: index
---

# Python `1.0.0` 实现地图

本目录映射 `whero-doctidex` `1.0.0` 的当前代码，不承诺 Python import API 稳定性。程序稳定
集成面是 [CLI JSON `schema_version: "1.0"`](../../architecture/interfaces/cli-schema.md)。

| 页面 | 代码所有权 | 对应设计 |
|---|---|---|
| [Package、结果与 CLI](package-results-and-cli.md) | packaging、错误/result、pagination、parser、dispatch、render、diagnostic | [CLI](../../architecture/interfaces/cli.md)、[程序集成](../../architecture/interfaces/programmatic-integration.md) |
| [协议解析与校验](protocol-validation.md) | UTF-8/YAML/Markdown、root、最近负责制、link、可达性、scope | [领域模型：校验](../../architecture/domain-model.md#10-校验结果) |
| [Git 来源与状态](git-source-and-storage.md) | Git subprocess、selector、bare objects、root storage、manifest、lock | [子系统与生命周期](../../architecture/subsystems-and-lifecycles.md) |
| [External 工作流](external.md) | install/link/restore/link-parse 与 portable mapping | [External 生命周期](../../architecture/subsystems-and-lifecycles.md#3-外部安装生命周期) |
| [Worktree、清理与测试](worktrees-cache-and-testing.md) | open/list/close、单来源清理、平台和测试证据 | [Worktree/清理生命周期](../../architecture/subsystems-and-lifecycles.md#7-受管-worktree-生命周期) |
| [Architecture 追踪矩阵](traceability.md) | 设计页到 producer、consumer、Details 与测试的落实关系 | [Architecture 入口](../../architecture/index.md) |

总体依赖是 `cli -> protocol/git -> errors/results`。`protocol` 不导入 Git；source provider 不
依赖 doctidex root；renderer 不产生领域事实。旧 mount、projection、filter 与 maintenance
scope 模块已经从 package 删除。

实现依据为 [DX-REQ-0008.2](../../../requirements/0008-doctidex-git-v1-0-0-alignment/02-python-details-and-implementation.md)。
