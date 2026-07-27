# Python 参考实现导航

本目录面向维护 `whero-doctidex` Python 包的人和 agent。它提供稳定的代码阅读地图，
但不把包内类和函数声明为公共兼容 API。

| 主题 | 文档 | 主要代码范围 |
|---|---|---|
| 包结构、依赖和模块关系 | [包与模块地图](package-and-module-map.md) | `whero.doctidex` 全包 |
| Markdown、路径、目录树与校验 | [协议实现](protocol.md) | `protocol/` |
| Git context、内部 state 和命令边界 | [Git context 与 state](git-context-and-state.md) | `git/context.py`、`git/state.py`、`git/runner.py` |
| source、revision、mount 和可读呈现 | [Source 与 mount](sources-mounts-and-projection.md) | `git/repository.py`、`git/mounts.py`、`git/projection.py`、`git/setup.py` |
| 独立维护根与多根结果 | [Maintenance](maintenance.md) | `git/maintenance.py` |
| 参数分发、预算、结果和渲染 | [CLI 与 rendering](cli-and-rendering.md) | `cli/main.py`、`cli/render.py`、`errors.py` |
| 完整生命周期与内部布局 | [Git runtime](git-runtime.md) | Git 运行时整体 |
| 本地开发与测试 | [开发和测试](development-and-testing.md) | `pyproject.toml`、`tests/` |
| 已知代码限制 | [当前限制](known-limitations.md) | 跨模块现状 |

精确 CLI 语法和结果字段属于公共接口，分别见
[CLI 用户接口](../../architecture/interfaces/cli.md) 和
[CLI 结果契约](../../architecture/interfaces/cli-schema.md)。

## 模块文档约定

每个模块说明：职责与非职责、上游调用者、依赖、主要类型或函数、全部数据属性、
副作用和错误边界、典型使用方式、测试证据。示例用于说明模块协作方式，不代表新增
稳定公共 API。
