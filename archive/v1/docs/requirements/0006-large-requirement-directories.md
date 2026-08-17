# 需求 0006：大型 Requirement 目录与聚合状态

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0006` |
| 状态 | `approved` |
| 日期 | 2026-07-30 |
| 批准依据 | 用户于 2026-07-30 明确要求将需求 0006 转为 `approved` |
| 来源 | 用户明确要求增加大型需求目录、子需求独立状态和 overview 聚合状态规则 |
| 影响范围 | 仓库 Requirement 组织、文档维护 Skill、review Skill 与 Requirements 导航 |
| 协议关系 | 非规范性仓库治理需求；不改变 [`doctidex` 协议](../../spec/overview.md) |

本文细化 [DX-REQ-0004](0004-project-docs-and-requirement-lifecycle.md) 建立的单记录生命周期，
允许大型 Requirement 在不失去项目级编号、独立子需求状态或整体完成门槛的情况下拆分。
它只定义仓库中的 Requirement 维护形式，不把该目录形式提升为 doctidex 协议要求。

## 1. 需求意图

当一个 Requirement 大到需要分别讨论、实现或批准多个可独立追踪的子需求时，用户可以
选择在 `docs/requirements/` 中创建需求目录，而不是单个 Requirement 文件。目录包含：

```text
docs/requirements/
`-- <NNNN>-<kebab-case-title>/
    |-- overview.md
    |-- <NN>-<kebab-case-subrequirement>.md
    `-- ...
```

1. 目录整体占用一个全项目连续编号；`overview.md` 持有该大型 Requirement 的项目级
   稳定 ID，例如 `DX-REQ-0006`。
2. 每份子需求文档持有从整体 ID 派生的稳定 ID，例如 `DX-REQ-0006.1`，不额外占用
   项目级编号。子需求文件名应保持稳定、可辨认，并由 `overview.md` 导航。
3. `overview.md` 说明整体需求、共同背景与范围边界，并列出每份子需求的链接、ID、简要
   说明和当前状态。子需求的详细意图、决策、实现影响和验收条件保留在各自文档中。
4. 单文件形式仍是默认且有效的 Requirement 形式；不得仅为形式统一而拆分规模较小的
   Requirement，也不得未经用户选择把既有记录改成目录。

## 2. 子需求生命周期

每份子需求都必须显示且只能使用 `draft`、`implemented` 或 `approved`，并按
[DX-REQ-0004](0004-project-docs-and-requirement-lifecycle.md) 的权限和转换规则独立维护。
一个子需求的状态变化不自动改变其他子需求，也不自动表达用户对整体的批准。

`overview.md` 同样只显示一个允许状态，但它是聚合门槛：

| overview 目标状态 | 必要条件 |
|---|---|
| `draft` | 初始状态；至少一个子需求仍为 `draft` 时必须保持该状态，满足上移条件后也不自动转换。 |
| `implemented` | 每个子需求均为 `implemented` 或 `approved`；不得存在 `draft` 子需求。 |
| `approved` | 每个子需求均为 `approved`，并且用户明确批准整体 Requirement。 |

子需求可以逐项获得批准，因此 `implemented` overview 下可以同时存在 `implemented` 和
`approved` 子需求。全部子需求变为 `approved` 也不会自动批准 overview；只有用户明确
指令才能完成该转换。若子需求后续回到较早状态，overview 也必须回到仍满足门槛的状态；
涉及从 `approved` 回退时，仍需用户明确授权，不得以聚合计算代替批准权限。

overview 的状态变化不反向批量修改子需求。维护者必须先更新并验证子需求状态和
`overview.md` 中的导航状态，再判断 overview 是否具备转换条件。

## 3. 导航与关系

1. `docs/requirements/index.md` 对目录型 Requirement 链接到其 `overview.md`，并显示
   overview 的聚合状态。
2. overview 是进入大型 Requirement 的默认入口；子需求不能脱离 overview 导航而成为
   孤立文档。
3. 整体关系默认链接 overview。只影响特定子需求的依赖、细化、取代或后续关系应直接
   链接该子需求，并继续在关系两端提供方向明确的链接。
4. overview 中的状态表必须与子需求正文一致。overview 只汇总，不取代子需求自身的
   状态和历史。

## 4. 落实范围

| 层面 | 处理 |
|---|---|
| Repository rules | `AGENTS.md` 定义目录选择权、文件职责、派生 ID 和聚合状态门槛。 |
| Requirements navigation | 共享索引同时解释单文件与目录形式，并导航本记录。 |
| Design-document Skill | 创建、维护和校验 Requirement 时识别目录形式及聚合状态。 |
| Review Skill | review 范围包含相关 overview 与子需求，并检查状态聚合一致性。 |
| Architecture / Details | 本需求只改变仓库维护规则，不产生实现 Architecture 或语言 Details。 |

## 5. Requirement 关系

- 本记录是 [DX-REQ-0004](0004-project-docs-and-requirement-lifecycle.md) 的后续细化；0004
  建立共享目录和三态生命周期，本记录增加大型 Requirement 的目录形式与聚合状态。

## 6. 验收标准

1. 仓库规则明确允许用户为大型 Requirement 选择编号目录，且目录包含 `overview.md`
   和具有独立状态的子需求文档。
2. overview 导航每个子需求并显示与正文一致的状态。
3. 存在 `draft` 子需求时 overview 不得成为 `implemented`；未全部批准子需求时 overview
   不得成为 `approved`。
4. `approved` overview 仍只能由用户明确指令产生，聚合条件不构成自动批准。
5. 单文件 Requirement 保持有效，项目级编号序列不因子需求拆分产生歧义。
6. 相关维护 Skills 通过本地 Skill 校验。
