---
type: index
doctidex:
  type: index
---

# doctidex-git v1.0.0 Architecture

本 Architecture 是 doctidex-git 当前、语言无关的共同设计。它从使用者问题进入，以关键
模型、机制、策略、state ownership、依赖与 workflow 为主体；独立实现者不需要读取 Python
Impls 就能理解必须保持的能力和 observable semantics，也不被要求复制 Python 的内部对象、
算法或物理表示。

设计依据为 [DX-REQ-0008.1](../../requirements/0008-doctidex-git-v1-0-0-alignment/01-doctidex-git-alignment.md)，
模型化重构依据为
[DX-REQ-0009](../../requirements/0009-architecture-and-details-maintenance-rules.md)。协议语义只由
[`spec/overview.md`](../../../spec/overview.md) 定义；本层解释产品，不增加 protocol rule。

## 阅读路径

1. 从 [产品与使用者](product-and-users.md)理解问题、使用画面、共同心智模型与产品边界。
2. 按任务读取下方关键模型，再进入消费这些模型的 system workflows。
3. 从 [组件与依赖](system/components-and-dependencies.md)理解责任、state owner 和禁止反向依赖。
4. 进入对应 workflow，最后以 interfaces 和 Skill system 核对公共 surface。
5. 具体 Python realization、物理 state 与 tests 见 [Python Impls](../impls/python/index.md)。

## 模型层

| Authority | 定义内容 |
|---|---|
| [Tree 与 configuration](models/doctidex-tree-and-configuration.md) | document/directory/index/log、local configuration、link annotation、shared tree observations、reachability、scope/support closure。 |
| [Root、ownership 与 paths](models/root-ownership-and-paths.md) | doctidex root、owner/content root、host Git、path types、selection 与 ownership proof。 |
| [Git source、revision 与 repository](models/git-source-revision-and-repository.md) | locator/canonical identity、selector/exact commit、repository/worktree、objects、network 与 source boundary。 |
| [External installation 与 mapping](models/external-installation-and-mapping.md) | install identity/role/parents、recovery manifest、durable link、current/portable mapping。 |
| [Worktree 与 cache](models/worktree-and-cache.md) | writable worktree ownership/lifecycle、shared cache registrations、cleanup eligibility。 |
| [Operation、result 与 failure](models/operation-result-and-failure.md) | command context、plan/apply、result/finding、partial success、pagination/cursor 与 diagnostics。 |

模型依赖方向是：tree/configuration 与 Git source 各自独立；root/ownership 为 root-scoped
composition 提供边界；external 组合 root + Git；worktree/cache 组合 Git 与可选 owner；operation
包装所有 workflow。任何 interface、Skill 或 Impls 都不能创建第二套模型语义。

## 系统与 workflow

| Authority | 设计问题 |
|---|---|
| [组件、责任与依赖](system/components-and-dependencies.md) | 组件 DAG、inputs/outputs/non-responsibilities、state ownership。 |
| [Validation](system/validation-workflow.md) | root/scope、configuration、reachability、finding/candidate 与 coverage。 |
| [External](system/external-workflows.md) | install/link/restore/remove/link-parse，以及 checkout hook reconciliation 的完整 state flow 与下一决策。 |
| [Worktree 与 cache](system/worktree-and-cache-workflows.md) | open/list/close、cache clean 与 native Git boundary。 |
| [并发、publication 与 recovery](system/concurrency-publication-and-recovery.md) | mutation domains、资源顺序、partial publication、conflict、interruption 与 destructive boundary。 |

## 公共 surface

| Surface | Authority |
|---|---|
| CLI grammar/effects | [CLI 用户接口](interfaces/cli.md) |
| JSON fields/codes | [CLI JSON Schema](interfaces/cli-schema.md) |
| Program subprocess | [程序集成](interfaces/programmatic-integration.md) |
| Installed agent workflows | [Published Skill system](skill-system.md) |

Surface 页面只定义调用方式与可观察 contract；领域模型和 workflow 链接回上述 authority，不以
command 表格作为系统信息架构。Variant-specific parser、serialization、storage layout、lock、
hash 与辅助模型属于 Impls，除非某个 exact representation 明确成为公共互操作 contract。

## 能力与非目标

必需能力包括：原生渐进读取、full/scoped validation、fixed external snapshot、扁平 dependency、
durable presentation、exact restore、checkout 后的受管 snapshot reconciliation、reference-protected remove、
offline mapping、native/managed maintenance choice、isolated worktree、explicit source-cache cleanup、bounded
results 和 installed agent routing。当前 Python coverage 见
[coverage and tests](../impls/python/architecture-coverage-and-tests.md)。

doctidex-git 不生成语义正文、不替代 native read/search/edit/Git delivery、不把 managed state
提升为 protocol/trust/permission，也不提供跨 repository transaction、moving-ref auto refresh、
dirty cleanup 或隐式 cache reclamation。
