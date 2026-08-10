# 需求 0002：设计 doctidex-git 命令行工具 v2.x.x

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002` |
| 状态 | `planned` |
| 日期 | 2026-08-07 |
| 来源 | 用户要求设计在 Git 环境中与 doctidex v2 目录树外观规范配套使用的 `doctidex-git` 命令行工具 v2.x.x |
| 影响范围 | `doctidex-git` CLI 的产品目标、Git 工作区与版本库边界、命令与输出契约、目录树识别与导航、校验/诊断、错误与退出状态、兼容性和交付验证 |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 文档性质 | 大型 Requirement；仅记录总体设计，不授权实现代码、测试或发布配置 |

本文记录 `doctidex-git` v2.x.x 当前已经确认的总体设计及其子需求。命令契约、工作模型、
事务、校验和修复规则分别由下列子需求展开。

## 1. 需求意图

需要设计一个可在 Git 环境中工作的 `doctidex-git` 命令行工具，使其能够以明确、可脚本化
且与 [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) 一致的方式
处理 doctidex 目录树。

## 2. 已确认的范围事实

- 工具名称为 `doctidex-git`。
- 目标版本属于 `v2.x.x` 开发线；具体主、次、补丁版本策略尚未确定。
- 工具当前设计的运行范围为 Linux 和 macOS，并以 Git root 作为仓库级工作模型边界。
- 工具应与 doctidex v2 目录树外观 Architecture 配套使用，而不是定义另一套目录树身份规则。
- CLI 使用通用 `--repos-path` 指定 Git root，省略时从当前路径向上搜索。
- 当前确认的命令簇为 `init`、`boundary-set`、`import`、`worktree`、`validate` 和 `repair`。
- 命令返回机器可读的 JSON 结构；普通命令使用统一成功/错误结构，`validate` 使用
  `valid`、`diagnostics` 和结构化命令错误的分离结果。
- 工作模型由 `CacheStore`、`RuntimeStore`、Installation、Ref、Worktree 和 BoundaryPoint
  组成；tracked 投影、事务恢复及派生边界规则分别由子需求定义。
- `repair` 以 JSON 描述为基准，使物理安装、引用、worktree、派生边界和 Git ignore 与模型相容；
  它不从历史或事务备份恢复旧版本。
- 本次需求包含代码库开发；代码开发完成后还必须完成配套 Architecture 文档的撰写。
- 本次需求暂不撰写 user 文档；人类维护者、agent 和自动化程序的差异仅在后续 user 文档中用于
  调整内容组织。

### Python 代码库组织

- Python 源代码位于 `src/python/whero/doctidex/`。
- Python 项目配置文件位于 `src/python/pyproject.toml`。
- Python 包的 import 路径前缀为 `whero.doctidex`。
- `whero` 是共享的顶级 package name，其他仓库也维护以 `whero` 为顶级 package name 的
  Python 库；本项目不得改用其他顶级 import 前缀或将 `whero` 视为本项目独占的顶级 package。

### Architecture 文档交付要求

- Architecture 文档在本次需求的代码库开发完成后撰写，作为实现完成后的独立交付物。
- 撰写时必须重新组织语言逻辑和文档结构，按照 Architecture 文档自身的组织要求表达内容，
  不直接复用或照搬本需求的子需求结构。
- 需要理清并解耦当前混合在各子需求中的定义、规则和概念描述，将分散在各子需求中的有效信息
  整合到 Architecture 文档中。
- 本次需求不包含 user 文档撰写。

## 3. 与 Architecture 的已知依赖

`doctidex-git` 设计尊重以下已在 Architecture 中定义的约束；具体校验和跨界行为由需求
0002-03、0002-05 和 0002-07 展开：

- 候选 doctidex 根目录必须直接包含 `index.md`。
- 根 `index.md` 的基础 frontmatter 必须包含 `type: index`、`doctidex.type: index` 和
  `doctidex.root: true`，且字段类型和值必须匹配。
- 当前目录树范围内的 `index.md` 可以按需出现在任意位置，不要求祖先路径连续包含
  `index.md`。
- `index.md` 正文承担渐进式披露、导航和查询入口职责，但没有固定组织格式。
- `boundary-set` 是当前目录树的 escape 节点抽象集合；越过节点后，当前树的
  `index.md`、link 和其他结构规则不再适用，且 v2 不在 frontmatter 中规定其字段或声明格式。
- 当前规则有效范围内的 Markdown 文档可使用 Markdown link；以 `/` 开头的路径从当前
  doctidex 根解释，并鼓励使用相对路径。
- 结构化 link 注释使用 link 后连续 HTML 注释中的 `doctidex` YAML 映射，并支持
  `cross-boundary-point` 字段。

任何需要改变这些模型、字段、边界或语义的方案，都必须先说明对 Architecture 的影响，
并在获得授权后更新对应 Architecture 文档。

## 4. 受影响的产品表面

| 表面 | 预期影响 | 当前状态 |
|---|---|---|
| CLI 命令树 | 定义六个命令簇、子命令、参数、返回结构和退出状态 | 由需求 0002-01 定义 |
| Git 集成 | 定义 Git root、revision、cache、安装仓库和 worktree 的交互 | 由需求 0002-02、05、06、08 定义 |
| doctidex 目录树识别 | 使用 Architecture 规定的根入口、frontmatter 和边界语义 | 约束已知，由需求 0002-03、07 落实 |
| 导航与追踪 | 通过 boundary-set、import-ref、worktree 和 Markdown link 提供稳定定位 | 由需求 0002-03、05、06、07 定义 |
| 校验与诊断 | 报告目录树、link、工作模型和 worktree 状态问题 | 由需求 0002-07 定义 |
| 输出接口 | 提供统一 JSON 成功、错误和 validate 诊断结构 | 由需求 0002-01 定义 |
| Python 代码库组织 | 定义源码目录、项目配置文件位置和 Python import 包前缀 | 约束已确认 |
| 文档与发布 | 代码开发完成后的 Architecture 文档；user 文档暂不撰写 | Architecture 文档为本次需求后续交付物 |

## 5. 设计决策记录

当前已确认的总体设计决策如下；各项细节以对应子需求为准：

- CLI 采用六个命令簇，并为每个命令使用通用 `--repos-path`。
- 工作模型以 tracked 状态投影和 `runtime.json` 共同提供权威数据，边界点按来源模型派生。
- CacheStore 使用单文件原子提交，RuntimeStore 使用带 journal 的多文件可恢复事务。
- 除 `validate`、`init` 外，事务回滚后命令在继续业务流程前执行一次内部 `repair`。
- Python 代码库按本页第 2 节的 `src/python/whero/doctidex` 布局组织。
- 代码开发完成后，按本页第 2 节的 Architecture 文档交付要求完成独立 Architecture 文档。
- 当前不额外定义 v2.x.x 的版本兼容或向后兼容承诺。

后续决策应在主题子需求中记录内容、理由、影响面和确认日期，并从本页保持可导航关系。

## 6. 依赖与相关记录

- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。
- 子需求：[CLI 命令行参数及返回结果结构设计](01-cli-arguments-results.md)。
- 子需求：[设计 doctidex-git 工作模型](02-working-model.md)。
- 子需求：[`boundary-set` 命令簇工作流与生命周期设计](03-boundary-set.md)。
- 子需求：[`init` 命令簇工作流与生命周期设计](04-init.md)。
- 子需求：[`import` 命令簇工作流与生命周期设计](05-import.md)。
- 子需求：[`worktree` 命令簇工作流与生命周期设计](06-worktree.md)。
- 子需求：[`validate` 命令簇工作流与校验设计](07-validate.md)。
- 子需求：[`CacheStore` 与 `RuntimeStore` 事务机制实现设计要求](08-store-transactions.md)。
- 子需求：[`repair` 命令簇工作流与生命周期设计](09-repair.md)。
- 当前没有已确认的 Issue、实现记录或其他 Requirement 依赖。

父需求已进入 `planned` 阶段；各子需求当前状态如下。子需求仍作为设计依据维护，未单独授权实现：

| 子需求 | 状态 |
|---|---|
| 0002-01 CLI 参数及返回结果 | `draft` |
| 0002-02 工作模型 | `draft` |
| 0002-03 `boundary-set` | `draft` |
| 0002-04 `init` | `draft` |
| 0002-05 `import` | `draft` |
| 0002-06 `worktree` | `draft` |
| 0002-07 `validate` | `draft` |
| 0002-08 Store 事务 | `draft` |
| 0002-09 `repair` | `draft` |

后续新增的协议、解析器、仓库结构、发布流程或 Issue 记录，应在相关文档中补充双向链接；
当前没有可补充的已确认记录。

## 7. 验收标准

以下标准用于完成本 Requirement 的定义，不代表当前已满足：

- [ ] 产品目标、适用范围、首要 Git 工作流和非目标已明确；角色优先级不作为本需求前置条件。
- [ ] 支持的 Git 环境、仓库范围、工作区状态、提交/分支/远程语义已明确。
- [ ] 命令树、参数、配置来源、输出格式、退出码和机器接口已明确。
- [ ] doctidex v2 根识别、frontmatter 校验、任意位置 `index.md`、`boundary-set` 和 link
      语义与 Architecture 一致，并有冲突处理方案。
- [ ] 读操作、写操作、暂存区/工作树影响和幂等性已明确。
- [ ] 错误分类、诊断信息、权限与安全边界和性能目标已明确；本次需求不额外定义版本兼容承诺。
- [ ] 每项关键行为都有可执行的验收场景和测试证据要求。
- [x] Architecture 文档作为代码库开发完成后的独立交付物，其重组、解耦和信息整合要求已明确；
      本次需求暂不撰写 user 文档。
- [x] 分阶段实施计划、每阶段具体输出、验证/审阅检查点和 Architecture 后置交付已记录。
- [ ] 需求、Architecture、Issue、实现和测试之间的链接已校验。

## 8. 实施计划

本计划记录父需求从代码库开发到 Architecture 文档交付的分阶段范围。每个阶段均应独立完成并
通过检查点后再进入下一阶段；`planned` 只表示计划已记录，不授权直接修改实现代码、测试、
Architecture 或 Skills。实施前仍需取得明确的实现授权。

| 阶段 | 状态 | 范围与具体输出 | 验证与审阅检查点 |
|---|---|---|---|
| 1. Python 工程与 CLI 基础 | `completed` | 在 `src/python/whero/doctidex/` 建立 Python 包，在 `src/python/pyproject.toml` 建立项目配置；实现 CLI 入口、通用 `--repos-path`、六个命令簇的分发和基础参数错误/返回结构。依据 [需求 0002-01](01-cli-arguments-results.md) 固化公共 CLI 契约。 | 已验证项目可编辑安装、`whero.doctidex` 可导入和 `doctidex-git` 入口；已为命令分发、通用参数、JSON 成功/错误结构建立自动化检查，并完成与 01 的一致性审阅。 |
| 2. 工作模型、Store 与初始化 | `pending` | 实现 [需求 0002-02](02-working-model.md) 定义的领域模型和状态投影，实现 [需求 0002-08](08-store-transactions.md) 的 CacheStore/RuntimeStore 事务、锁、journal、恢复及并发保护，实现 [需求 0002-04](04-init.md) 的工作空间初始化。 | 验证状态文件重建、tracked/untracked 投影、事务提交/回滚/遗留恢复和 `init` 幂等行为；模拟中断和外部 hash 变化后审阅模型不变量。 |
| 3. boundary-set 与 import | `pending` | 实现 [需求 0002-03](03-boundary-set.md) 的 custom/派生边界点和路径解析，实现 [需求 0002-05](05-import.md) 的 install、restore、track、remove、ref、unref、query，以及 CacheStore、安装目录和受管 link 的交互。 | 使用包含 tracked/untracked、revision 组合、缺失 install-path、受管 link 和边界合并的场景验证；检查失败时物理对象与 Store 状态不产生未提交变更。 |
| 4. worktree | `pending` | 实现 [需求 0002-06](06-worktree.md) 的 worktree create/remove/query、Installation/URL 两种来源、默认及自定义 work-path、Git ignore 和派生 BoundaryPoint。 | 验证创建、查询、缺失目录清理、`--force` 移除、路径冲突及自定义 ignore 规则；审阅与 Worktree 生命周期和事务边界的一致性。 |
| 5. repair 与 validate | `pending` | 实现 [需求 0002-09](09-repair.md) 的 JSON 基准物理对齐和事务回滚后的内部 repair；实现 [需求 0002-07](07-validate.md) 的范围限制、工作模型校验、Markdown/link 诊断、待恢复事务短路和退出状态，并复用 [需求 0002-01](01-cli-arguments-results.md) 的结构化错误。 | 建立有效、失效、待恢复和可 repair 场景矩阵；验证 `validate` 只读、`repair` 幂等、错误信息具备模型诊断意义，以及非 `validate`/`init` 命令的内部 repair 行为。 |
| 6. 集成验收与 Architecture 交付 | `pending` | 完成各命令簇端到端集成、回归验证和需求验收证据；在代码库开发完成后，依据 Architecture 文档自身的组织要求重新撰写并整合 Architecture 文档。此阶段不撰写 user 文档。 | 运行完整自动化测试和跨阶段场景检查，校验需求、Architecture 与实现的链接及术语一致性；完成 Architecture 文档审阅后，才可将父需求转为 `implemented`。 |

## 9. 实施与状态

本记录目前为 `planned`。阶段 1 已完成并待审阅，阶段 2 至 6 尚未开始；每个阶段完成后应暂停
并进行人类审阅，未取得下一阶段的明确实现授权前不得继续修改代码、测试或 Architecture 文档。
