# 需求 0003：维护范围的规划与执行语义

| 属性 | 值 |
|---|---|
| ID | `DXG-REQ-0003` |
| 状态 | `approved` |
| 日期 | 2026-07-28 |
| 来源 | 用户对协议维护边界与 Workspace 工作流的复核和补充决策 |
| 影响范围 | doctidex 协议维护语义、doctidex-git Architecture、Workspace Skill 与 Details |
| 协议关系 | 推动 doctidex 标准升级到 `v0.1.0`，明确第 9 节的维护范围语义 |

本记录澄清 `maintenance scope` 在多根工作中的定位：CLI 返回的 item 是本次
调用观察到的维护对象，agent 可以用它制定、复核或调整工作计划。item 本身
不表示“尚未分配”或“已经分配”，也不要求一个 item 必然对应一个新的
可写现场。

本文是需求历史，不是当前接口权威。当前行为见
[Architecture](../doctidex-git/architecture/index.md)、[CLI schema](../doctidex-git/architecture/interfaces/cli-schema.md)
和已发布 Skills。

## 1. 现状与假设核对

当前 `maintenance scope` 是只读、可重复运行的现场观察命令：

- 它根据本次传入的路径返回 host/mounted items、base commit、关系和复用建议；
- 它不创建 maintenance root，不持久化 agent 的工作计划，也不记录 item 是否
  已经分配到某个写入现场；
- agent 可以在工作开始前、发现新目标时、可复用现场变化后或交付前反复运行
  scope，并以最新事实调整计划。

因此，把 scope item 称为“待分配的维护目标项”会虚构 CLI 不存在的分配状态。
需要区分的是“本次调用观察到的对象”和“agent 选定的最终写入范围”。

## 2. 问题与设计意图

原协议的“独立维护范围”可被解读为每个 host/mount item 都必须建立单独的
物理现场。这与当前设计的意图不符：

- mount path 是严格只读入口，执行期不能通过它跨越写入边界；
- 但多个路径或 mount 引用可能指向同一 source 的同一维护基准，此时重复
  建立写入现场会拆散本应形成的一个 Git 结果；
- 维护范围应按实际被修改的源目录树及基准划分，而不是按达到它的引用
  数量划分。

设计必须同时保留规划灵活性和执行边界，不能为避免重复现场而把一个 scope
变成可沿 mount 任意扩张的写入权限。

## 3. 已接受要求

### 3.1 协议语义

1. doctidex 标准版本升级为 `v0.1.0`。
2. mount path 只是读取入口；修改源内容必须从选定的源目录树根目录进入。
3. 维护范围按实际源目录树划分，不按 mount path、声明或路径引用数量划分。
4. 多个目标被可靠确认为同一源目录树，并在适用时具有相同维护基准时，
   可以共用一个维护范围。当前根被确认为该源时，它可以作为共用写入入口。
5. 不同源目录树、不同维护基准或关系不能可靠确认时，必须使用独立范围。
6. 在一个范围的执行过程中，遇到指向其他源目录树的 mount 时不得直接写入；
   必须把目标重新交给维护范围决策。
7. 基础协议不规定 source identity、维护基准或兼容性的具体判定算法。

### 3.2 `maintenance scope` 与 agent 计划

1. scope item 表示本次命令观察到的 host root 或 mounted source 对象。
2. item 不携带分配状态；不得从 item 存在推断它尚未分配、已分配或必须
   建立独立 maintenance root。
3. agent 根据最新的 source、base commit、root relation、已有写入现场、授权和
   交付目标，自己决定每个 item 应在哪个最终写入范围中完成。
4. agent 可以在同一工作过程中反复运行 scope。每次返回当前观察事实，不创建或
   覆盖 agent 的工作计划。
5. agent 应在新目标出现、关系或已有现场变化、执行边界不再清楚时重新 scope。

### 3.3 执行范围

1. 最终写入范围有一个选定根，以该根自身的 index、log、过滤边界、Git diff、
   校验和交付流程完成工作。
2. 多个兼容 item 可以共用该范围，但范围不能因此跨越到其他目录树。
3. 自引用且同 commit 时，mount 路径继续用于读取快照，当前 host root 可作为选定
   写入根；不得把两条路径互相替换。
4. 一个最终范围产生一组可独立审阅的 diff、校验和交付决策。

## 4. 非目标

- 不要求 CLI 持久化或返回 item 的分配状态。
- 不要求每次 scope 运行都重新创建维护计划。
- 不把同 commit 当作同 source 的充分证据。
- 不因 scope 复用而放开 mount path 的写入边界。
- 不改变 `maintenance open/status/handoff/close` 的已有生命周期。
- 不要求为本次语义澄清重构 Python 实现。

## 5. 落实结果

| 层面 | 结果 |
|---|---|
| Protocol | 标准升级为 `v0.1.0`；明确按实际源目录树/维护基准划分范围和执行期 mount 边界。 |
| Architecture | 区分 scope 命令观察 item、agent 的可重评估范围决策和最终写入范围。 |
| Published Skill | Workspace 说明 scope 可重复运行、item 无分配状态以及执行期不能跨 mount 写入。 |
| CLI/Python | 不改变命令或实现行为；当前 scope 本就是无计划持久化的只读观察。 |
| Details | 记录 scope 的可重入、无分配状态和执行边界。 |

## 6. 历史关系

本需求澄清 [DXG-REQ-0002](0002-root-self-reference-and-maintenance.md) 中“将兼容变更合并到
同一 scope”的语义：合并是 agent 对最终写入范围的决策，不是 CLI 对 item
分配状态的记录，也不允许执行时透过 mount 扩张写入边界。

它同时对 [DXG-REQ-0001](0001-agent-git-plugin.md) 中“每个 mounted source 必然打开新的
独立维护根”的初始基线形成后续决策：不同源或基准仍独立，对同一 source/base
的多个引用不再强制重复建立写入现场。两份旧记录的历史正文保持不变。

[DX-REQ-0004](0004-project-docs-and-requirement-lifecycle.md) 后续迁移并治理本文的共享目录位置、
`implemented` 状态和双向关系链接；它不改变本文的产品语义。

## 7. 验收标准

1. 协议当前版本为 `v0.1.0`，且挂载维护条款明确区分引用数量与实际维护范围。
2. Architecture 和 Workspace Skill 不把 scope item 描述为“待分配”或“已分配”。
3. agent 能够了解 scope 可在一次工作中重复运行，每次返回当前观察而不覆盖计划。
4. 同 source/base 的兼容 item 可以共用最终写入范围，不同或未确认关系仍独立。
5. Skill 明确执行期只在选定根内写入；通过 mount 遇到其他源时必须重新 scope
   或复核范围决策。
6. 本次澄清不改变 CLI 参数、JSON 字段或 Python 运行行为。
