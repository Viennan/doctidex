# 需求 0002-07：`validate` 命令簇工作流与校验设计

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-07` |
| 状态 | `draft` |
| 日期 | 2026-08-09 |
| 来源 | 用户要求在非 `validate` 命令簇的核心模型完成后，盘点工作流错误并设计结构化诊断与 `validate` 命令簇 |
| 父需求 | [需求 0002：设计 doctidex-git 命令行工具 v2.x.x](overview.md) |
| 关联子需求 | [需求 0002-01：CLI 命令行参数及返回结果结构设计](01-cli-arguments-results.md)、[需求 0002-02：设计 doctidex-git 工作模型](02-working-model.md)、[需求 0002-03：`boundary-set` 命令簇工作流与生命周期设计](03-boundary-set.md)、[需求 0002-04：`init` 命令簇工作流与生命周期设计](04-init.md)、[需求 0002-05：`import` 命令簇工作流与生命周期设计](05-import.md)、[需求 0002-06：`worktree` 命令簇工作流与生命周期设计](06-worktree.md) |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 影响范围 | `validate`、`work-model.valid`、目录树和 Markdown link 诊断、Installation、Ref、Worktree 及工作模型有效性 |
| 文档性质 | 子 Requirement；仅记录校验与诊断设计，不授权实现 |

## 1. 需求意图

定义 `validate` 如何在不修改状态的前提下，检查当前 Git root 的 doctidex 目录树、受管 import、
worktree 与工作模型。诊断必须描述可理解的模型状态、对象和位置，使人和程序能决定后续修复
动作；不得将未加解释的文件系统、JSON 解析或 Git 命令错误作为主要输出。

本子需求落实需求 0002-01 的 `validate` 返回结构、通用错误返回和 `work-model.valid` 诊断。
它不设计自动修复、缓存维护、网络可达性探测或新的命令。

`validate` 只检查和报告问题，绝不调用或隐式执行 `repair`。普通 RuntimeStore 事务发现残留 journal 后
释放当前锁并报告内部 `repair-required` 信号；命令级协调器运行 repair 后重试发生该信号的 RuntimeStore
操作。具体循环和停止条件以需求 0002-08 第 5.4 节为准。

## 2. 设计依据

- `validate` 的参数、返回结构、退出状态和命令错误以 [需求 0002-01](01-cli-arguments-results.md)
  第 7、9 节为准。
- 工作空间、RuntimeStore 投影、Installation、Ref 和 Worktree 的权威状态以
  [需求 0002-02](02-working-model.md) 为准。
- 有效 `boundary-set` 的来源、路径解析和边界语义以 [需求 0002-03](03-boundary-set.md) 为准。
- 已存在工作空间的 `init` 行为以 [需求 0002-04](04-init.md) 为准。
- import 安装、受管引用及其 tracked 约束以 [需求 0002-05](05-import.md) 为准。
- worktree 的登记、Git ignore 保护和移除语义以 [需求 0002-06](06-worktree.md) 为准。
- `repair` 的物理状态对齐和修复边界以 [需求 0002-09](09-repair.md) 为准；`validate` 不调用
  `repair`，只报告待修复状态。
- doctidex 根、`index.md`、Markdown link、结构化注释及边界语义以配套 Architecture 为准。

## 3. 校验范围和结果原则

`validate` 的 Git root 由通用 `--repos-path` 解析。默认模式或指定 `--subdir` 时，目录树内容扫描范围为
`/`；`--subdir` 提供时必须是 Git root 内可读取的目录，且不得为 `/.doctidex-git` 或其子目录。若该路径
本身位于某个 `BoundaryPoint` 或其后代，则它已不属于当前 doctidex 目录树的规则范围，命令返回
`validation.scope.unavailable`，并在 `message.details.reason` 中标记 `outside-current-tree`。

`--model-structure` 是与 `--subdir` 互斥的显式模式。它读取并校验 Git root 的 RuntimeStore 工作模型结构、
仓库级投影约束，以及根 `index.md` 是否存在且具有 Architecture 规定的基础 frontmatter；`scope.subdir`
固定为 `/`。该模式不扫描根 `index.md` 正文或其他 Markdown 文件/link、跨界结构化注释，也不检查
`worktree.clean`。根入口问题继续使用 `index.conforms` 诊断。该模式仍返回普通 `validate` 的 `valid`、
`diagnostics` 与退出状态，不构成另一个命令或单独的校验 API。

`--subdir` 只限制目录树内容和其中 Markdown link 的扫描起点，不限制以下仓库级校验：

| 校验对象 | 是否受 `--subdir` 限制 | 原因 |
|---|---|---|
| Git root 的 `/index.md` 根身份 | 否 | 根入口定义当前目录树身份。 |
| 工作模型有效性 | 否 | RuntimeStore、tracked 投影和 Git ignore 约束均以 Git root 为作用域。 |
| 已登记 Worktree 的清洁状态 | 是 | 仅检查 `work-path` 等于或位于 `scope.subdir` 之下的 Worktree；`scope.subdir` 为 `/` 时覆盖全部。 |
| Markdown 文件、其本地 link 和 import link | 是 | 这些是当前目录树内容检查；扫描不会越过任一有效 BoundaryPoint。 |

对于扫描范围内的 Markdown 源文件，link 的目标即使位于该范围外，仍须检查其是否存在。若目标
越过 BoundaryPoint，继续按当前目录树的跨界 link 语义检查结构化注释，但不递归把目标区域作为
当前目录树内容扫描。

Worktree 的 RuntimeStore 投影、路径保护和物理登记是否有效仍属于仓库级
`work-model.valid` 校验；`--subdir` 只限制 `worktree.clean` 对实际未提交修改的检查范围。

`validate` 分离命令运行结果和校验结果：

| 情况 | 返回 | 退出码 |
|---|---|---|
| 校验范围可建立，且没有诊断 | `status: "ok"`、`valid: true`、空 `diagnostics` | `0` |
| 校验范围可建立，发现任意目录树、模型或 worktree 诊断 | `status: "ok"`、`valid: false`、非空 `diagnostics` | `1` |
| 无法解析 Git root、建立可读范围或完整遍历范围 | `status: "error"`、结构化 `message` | `2` |

状态文件缺失、格式错误或模型数据互相矛盾是待报告的工作模型诊断，而不是命令错误。只有读取
权限、I/O 或目录遍历问题使工具无法获得足以完成本次范围扫描的输入时，才使用
`validation.scope.unavailable` 或 `validation.scan.unavailable`。

显式 `doctidex-git validate` 使用专用诊断读取事务：只获取 RuntimeStore 锁和读取快照，不恢复、创建、
重写或清理 journal，也不修改 CacheStore。默认模式执行本需求的完整范围校验，`--model-structure` 执行
仓库级工作模型和根入口 frontmatter 校验；两者均向用户返回 `valid` 与 `diagnostics`。已有工作空间上的 `init` 不调用本命令，也
不构成另一种 `validate` 执行形态或触发 repair；用户可显式执行 `validate --model-structure` 检查工作模型。

命令簇还可以在自己的工作流中执行解决当前操作所需的局部校验，例如 remove 前的 link 或引用
阻塞检查；这些校验不等同于对外执行完整的 `validate`，也不得因此修改工作模型。

## 4. 校验工作流

### 4.1 建立范围和诊断快照

1. 按通用规则解析 Git root；失败时返回 `git-root.unresolved`。
2. 未提供 `--model-structure` 时，规范化 `--subdir`。路径不在 Git root 内、为 `/.doctidex-git` 或其子目录、不是目录或不可读取时，返回
   `validation.scope.unavailable`；`details.reason` 依次使用 `outside-repository`、
   `workspace-internal`、`not-directory` 或 `unreadable`。
3. 以专用诊断读取事务检查 `.doctidex-git/.transactions/`，目录不存在时视为空。该事务只获取锁和
   读取快照，不得恢复、创建、修复、重写或删除任何文件，也不得修改 CacheStore；不得改用会自动
   恢复 journal 的普通 `read_only_transaction()`。若发现一个或多个状态为 `prepared` 或 `publishing`
   且可读取的 RuntimeStore journal，则只返回 `transaction.recovery.required` 违规，设置
   `work-model.valid.details.content-scan: "skipped"`、`valid: false`，并立即结束本次校验；不得继续
   执行后续模型、根入口、Markdown 或 link 检查。仅状态为 `committed` 且所有目标均为 `new-sha256`
   的 journal 已代表完成的业务提交，可由后续 repair 清理，不单独构成该违规。journal 无法读取或无法判定状态时，返回
   `store.transaction.unavailable`。
4. 未发现未完成事务时，读取 tracked 投影和 `runtime.json`，对可读取的状态数据逐项完成结构和
   一致性检查，并从有效记录重建可用的 Installation、Ref、Worktree 和 BoundaryPoint 视图。状态
   文件缺失或格式不合法时记录模型违规，而不是暴露原始解析器信息。
5. 未提供 `--model-structure` 且完整 BoundaryPoint 视图可用时，检查 `--subdir` 是否位于某个 BoundaryPoint 或其后代；若是，
   返回 `validation.scope.unavailable`，并设置 `details.reason: "outside-current-tree"`。
6. 提供 `--model-structure` 时，在本步骤完成后校验根 `index.md` 的根身份和基础 frontmatter，汇总并返回
   诊断；不扫描其正文或执行其他内容、link 或 worktree 检查。否则，如果模型违规使完整的有效 `boundary-set` 无法确定，则仍返回所有可确定的
   `work-model.valid` 违规及根入口诊断，但跳过依赖边界集合的 Markdown 文件和 link 扫描。
   此时 `work-model.valid.details.content-scan` 为 `skipped`。模型已经无效，因此结果固定为
   `valid: false`，不会把不完整扫描表示为通过。

### 4.2 检查目录树内容

本节只适用于未提供 `--model-structure` 的完整校验。`--model-structure` 已在第 4.1 节完成根入口
frontmatter 校验；完整校验同样检查 Git root 的 `/index.md` 是否满足 doctidex 根入口要求，并继续扫描正文和其他内容。
在完整 BoundaryPoint 视图可用时，显式校验继续执行以下步骤：

1. 使用父需求定义的共享领域工具从 `scope.subdir` 枚举 Markdown 文件；遇到 BoundaryPoint 时不进入
   该节点的后代目录。
2. 使用同一工具对每个 Markdown 文档解析本地文件系统 link，得到仓库内部目标、源文件行号、源码范围和第一个
   跨越的 BoundaryPoint。带 URI scheme 的外部 link 不具有当前 Git root
   的路径语义，不纳入本命令的本地路径存在性检查；只有 fragment 的 link 以源文件为目标文件。
3. 按 Architecture 的根路径和相对路径规则解析本地 link。不能在当前 Git root 内得到规范化
   目标的 link 产生 `link.path.conforms`。
4. 对不越过 BoundaryPoint 的 link，检查目标文件或目录是否实际存在；对越过 BoundaryPoint 的
   link，先确定第一个跨越点及其关联 Installation 是否处于本节定义的待恢复状态，仅在不属于
   该例外时检查物理目标是否实际存在。
5. 对越过 BoundaryPoint 的每个 link，通过共享领域工具从该 link 的结束位置解析
   `InlineAnnotation`；解析器仅考察紧邻的连续 HTML 注释块序列，link 与首个注释块、相邻注释块之间允许
   空白，注释块内部允许空白和换行。它按源码顺序采用首个合规的 `doctidex` YAML 映射，再由本命令检查
   `InlineAnnotation.cross_boundary_point` 是否为 link 目标 path 的完整路径段前缀，并按源文档规范化后是否
   等于第一个跨越 BoundaryPoint。每个 link 独立从自己的结束位置提取序列，因此同一行的多个 link 不共享注释。
6. 当 link 的第一个跨越点是某个 `import` 类型 BoundaryPoint 时，检查对应 Installation 是
   tracked。通过 `import-ref` 类型点的 link 不额外产生该诊断，因为 `import ref` 已将其
   Installation 提升为 tracked；其关联正确性由工作模型校验负责。

若 link 的第一个跨越点是 `import` 类型的 `Installation.install-path`，或 `import-ref` 类型的
`Ref.target-dir`，且所关联的 tracked Installation 缺少实际 `install-path`，该 Installation 处于
合法的“文件待恢复”状态。此时 `validate` 只校验边界点关联的 `install-id` 在工作模型中存在、
没有冲突，且满足本节的 tracked 约束；不得调用 `import restore`，也不得对该 link 产生
`link.target.exists` 诊断。跨界结构化注释仍须按本节检查。对于 `import-ref`，受管符号链接的
目标文本仍须与 Ref 记录的预期源一致；其因安装目录缺失而成为悬空链接不构成不一致。

Architecture 没有要求验证 Markdown anchor 是否存在，也没有要求对外部网络地址发起请求；本
命令不增加这两类校验。

### 4.3 检查 Worktree

本节只适用于未提供 `--model-structure` 的完整校验。仅对 `work-path` 等于或位于 `scope.subdir` 之下、且结构和物理登记均可用的 Worktree 检查其
未提交修改。`scope.subdir` 为 `/` 时，该条件覆盖全部 Worktree。存在暂存、未暂存或未跟踪修改
时，产生 `worktree.clean` 诊断。缺失、未登记或与 RuntimeStore 记录不一致的物理 worktree
属于工作模型违规，不将无法读取的工作区误报为“干净”。

### 4.4 汇总结果

诊断按 `path`、`line`（缺失时排在文件级诊断之前）和 `rule` 升序排列，确保同一状态得到稳定
的机器可读结果。每个独立问题最多产生一个同类诊断；单个 `work-model.valid` 诊断可以在
`details.violations` 中聚合多个模型违规。

`validate` 不提交 RuntimeStore 或 CacheStore 事务，不改变 Git worktree、受管理引用、
`.gitignore`、状态文件或目录树内容。repair 是独立的写入步骤，不属于 validate 的行为。

## 5. `work-model.valid` 违规结构

工作模型问题以一个 `work-model.valid` 诊断返回。其 `path` 固定为 `/.doctidex-git`；若工作
空间本身缺失仍使用该逻辑路径。`details` 使用以下结构：

```jsonc
{
  "violations": [
    {
      "code": "ref.installation.missing",
      "path": "/.doctidex-git/import-refs.json",
      "message": "A managed reference has no tracked installation record.",
      "details": {
        "install-id": "<INSTALL-ID>",
        "target-dir": "/<REPOSITORY-INTERNAL-ABSOLUTE-PATH>"
      }
    }
  ],
  "content-scan": "complete"
}
```

| 字段 | 要求 |
|---|---|
| `violations` | 非空数组。每项表示一个可独立定位和修复的工作模型问题。 |
| `violations[].code` | 稳定、小写点分的违规 ID；取值见下表。 |
| `violations[].path` | 引发问题的状态文件、受管路径或工作区的仓库内部绝对路径。 |
| `violations[].message` | 面向人的简要说明；程序不得依赖其内容。 |
| `violations[].details` | 违规 ID 对应的结构化上下文。不得用未处理的 JSON、文件系统或 Git 命令错误替代。 |
| `content-scan` | `complete` 表示可依据完整边界集合完成内容扫描；`skipped` 表示模型已使边界范围不可判定，或存在待恢复事务而未执行进一步校验。 |

### 5.1 工作空间和状态投影

| `violations[].code` | 触发条件 | `details` 必填字段 |
|---|---|---|
| `workspace.uninitialized` | `.doctidex-git/` 不存在，因而没有仓库级工作模型。 | `required-command: "init"` |
| `workspace.artifact.missing` | 工作空间存在，但 `config.toml`、任一 tracked 状态文件或 `runtime.json` 缺失。 | `required-artifact` |
| `workspace.runtime-protection.invalid` | `.command.lock`、`runtime.json`、`.transactions/`、`imports/` 或 `worktrees/` 未受 Git ignore 保护。 | `artifact-path`、`required-protection: "git-ignore"` |
| `transaction.recovery.required` | `.transactions/` 中存在状态为 `prepared` 或 `publishing` 且可读取的 RuntimeStore journal。显式 `validate` 仅报告该事务并立即结束，不执行恢复或其他校验。 | `transaction-id`、`journal-path`、`state` |
| `state-file.malformed` | 某个状态文件不是其定义的 JSON 结构，或无法转换为该文件负责的集合。 | `state-file`、`expected-shape` |
| `state-record.invalid` | 状态文件中的记录缺少必需字段、字段类型错误，或路径/ID 不符合对应领域模型。 | `state-file`、`record-kind`、`record-index`、`invalid-fields` |
| `installation.projection.misplaced` | tracked Installation 出现在 `runtime.json`，或 untracked Installation 出现在 `imports.json`。 | `install-id`、`actual-state-file`、`expected-state-file` |
| `installation.identity.conflict` | 同一 `install-id` 或 `install-path` 被多条 Installation 记录占用。 | `identity-field`、`identity-value`、`conflicting-state-files` |
| `boundary-point.custom.invalid` | `boundary-set.json` 包含非 custom 点、无效路径、重复点，或位于另一 BoundaryPoint 后的冗余 custom 点。 | `boundary-path`、`reason` |
| `managed-path.conflict` | Installation、Ref 或 Worktree 为同一物理路径登记了不相容的职责。 | `managed-path`、`owners` |

`workspace.uninitialized` 是模型诊断，使 `validate` 能够报告未初始化仓库；其他命令在同一情形
下使用需求 0002-01 定义的 `work-model.uninitialized` 命令错误。`state-file.malformed` 与
`state-record.invalid` 的 `details` 只说明预期结构和失效字段，不返回原始解析器错误文本。

### 5.2 受管关系和物理对象

| `violations[].code` | 触发条件 | `details` 必填字段 |
|---|---|---|
| `boundary-point.git.missing` | `/.git` 未出现在有效 `boundary-set` 中。 | `required-boundary-path: "/.git"` |
| `installation.worktree.missing` | untracked Installation 的 `install-path` 不存在，因而该运行时安装无法使用。 | `install-id`、`install-path`、`tracked: false` |
| `installation.worktree.inconsistent` | 存在的 Installation 工作目录不是记录的 Git URL 或 commit hash 所表示的安装产物。 | `install-id`、`install-path`、`expected-git-url`、`expected-commit-hash` |
| `ref.installation.missing` | Ref 的 `install-id` 没有对应 Installation。 | `install-id`、`target-dir` |
| `ref.installation.untracked` | Ref 指向的 Installation 不是 tracked。 | `install-id`、`target-dir` |
| `ref.source.unavailable` | Ref 的 Installation 工作目录存在，但 `src-sub-dir` 不存在或不能作为其记录的引用源。 | `install-id`、`install-path`、`src-sub-dir`、`target-dir` |
| `ref.target.inconsistent` | `target-dir` 缺失、不是受管理符号链接，或其目标不等于 Ref 记录的源。 | `install-id`、`target-dir`、`expected-source`、`actual-target` |
| `worktree.physical-state.invalid` | 已登记 Worktree 缺失，或 Git worktree 登记与其 `work-path`、来源记录不一致。 | `work-path`、`reason` |
| `worktree.path-protection.invalid` | 不在 `/.doctidex-git/worktrees/` 下的 Worktree 路径未受 Git ignore 保护。 | `work-path`、`gitignore-path` |

tracked Installation 的实际 `install-path` 缺失是允许的“文件待恢复”状态，不产生
`installation.worktree.missing`；`import restore` 可根据其 tracked 元信息恢复实际文件。若
Ref 指向该安装产物，缺失的安装目录也不产生 `ref.source.unavailable`；只要其 `install-id`
有效，Ref 可以保持指向预期源的悬空符号链接。安装目录实际存在而 `src-sub-dir` 无效时，才由
`ref.source.unavailable` 报告。

`boundary-point.git.missing` 直接落实工作模型的既有不变量，不改变 `.git` 的来源或持久化设计。

## 6. 目录树与 link 诊断

除 `work-model.valid` 外，每项检查均使用需求 0002-01 第 7.4 节的公共 `diagnostics` 项结构。
所有 `path` 和 `details` 中的仓库路径都使用仓库内部绝对路径。

| `rule` | 触发条件 | `path` / `line` | `details` 必填字段 |
|---|---|---|---|
| `index.conforms` | Git root 的 `/index.md` 缺失，或其根入口 frontmatter 缺少、类型错误或值不匹配。 | `path: "/index.md"`；无 `line`。 | `expected`、`actual`；字段问题另含 `field`。 |
| `link.path.conforms` | 扫描范围内 Markdown 文档的本地 link 不能按根路径或相对路径规则在 Git root 内规范化。 | `path` 为源文档，必须有 `line`。 | `link-path`、`reason`、`resolved-from`。 |
| `link.target.exists` | 已规范化的本地 link 的目标文件或目录不存在，且不属于本节定义的待恢复 import 例外。 | `path` 为源文档，必须有 `line`。 | `link-path`、`target-path`。 |
| `link.annotation.required` | link 越过 BoundaryPoint，但其紧邻连续注释序列中不存在合规的 `doctidex` 映射，或该映射的 `cross-boundary-point` 与第一个跨越点不匹配。 | `path` 为源文档，必须有 `line`。 | `link-path`、`expected-cross-boundary-point`、`reason`；存在但不正确时另含 `actual-cross-boundary-point`。 |
| `import.link.tracked` | link 的第一个跨越点是 untracked Installation 的 `import` 类型 BoundaryPoint。 | `path` 为源文档，必须有 `line`。 | `link-path`、`install-id`、`install-path`、`tracked: false`。 |
| `worktree.clean` | `work-path` 等于或位于 `scope.subdir` 之下、且结构和物理状态有效的 Worktree 存在未提交修改。 | `path` 为 `work-path`；无 `line`。 | `work-path`、`changes`；每个 `changes[].path` 为仓库内部绝对路径，`changes[].state` 表示 Git 修改状态。 |
| `work-model.valid` | 第 5 节任一工作模型违规成立。 | `path: "/.doctidex-git"`；无 `line`。 | `violations`、`content-scan`。 |

`index.conforms` 为每个独立的根入口条件产生诊断。`expected` 表示 Architecture 要求的字段或值；
缺失项的 `actual` 为 `null`。非根位置的 `index.md` 没有 Architecture 强制的 frontmatter，因此
不适用该 rule。

对于 `link.annotation.required`，`reason` 使用简洁的自然语言说明连续注释序列中缺少合规映射或
跨界点不匹配等具体原因。程序以 `rule`、`expected-cross-boundary-point` 和
`actual-cross-boundary-point` 等结构化字段判断问题，不依赖 `reason` 的措辞。

## 7. 与命令工作流的关系

| 调用方或模型 | 与本命令的关系 |
|---|---|
| `init` | 非空 `.doctidex-git/` 工作空间上，`init` 不执行本需求的校验，直接返回已运行过初始化并建议执行 `validate --model-structure` 的成功信息；空工作空间由 `init` 继续完成初始化。 |
| 非 `validate` 命令 | 可以执行各自所需的局部校验。在不能安全重建模型时，使用 `work-model.invalid` 返回相同违规数组；工作模型无效时不继续变更 Installation、Ref、BoundaryPoint 或 Worktree。若普通 RuntimeStore 事务检测到残留 journal，按需求 0002-08 第 5.4 节释放锁并报告 `repair-required`，由命令协调器运行 repair 后重试对应的 RuntimeStore 操作；只有重试能建立无残留事务的状态快照时才进入该操作的业务工作流。 |
| `import remove` | 仍按需求 0002-05 在修改前检查实际阻塞它的 Markdown link 和 Ref，并以 `installation.remove.blocked` 返回；该动作前置检查不依赖用户先执行 `validate`。 |
| `import unref` | 与 `import remove` 使用同一 BoundaryPoint/link 关联语义；Markdown link 跨越待移除 Ref 的 `import-ref` BoundaryPoint 时，以 `ref.remove.blocked` 返回。 |
| tracked Installation | `validate` 允许安装文件不存在，也不会执行 `import restore`。link 首次跨越 import 或 import-ref BoundaryPoint 时，若其 Installation 正处于待恢复状态，仅校验关联 `install-id` 的模型有效性和既有 tracked 约束，不检查物理 link 目标。 |
| CacheStore | CacheStore 的状态与 bare repository 不一致由其既有恢复规则处理，不作为当前 Git root 的 `work-model.valid` 违规。缓存不可用时由执行该操作的命令报告 `cache.repository.unavailable`。 |
| `repair` | 负责按照 JSON 描述修复物理安装、受管理引用、Worktree、派生 BoundaryPoint 和 Git ignore，并处理残留 RuntimeStore journal；它不处理 Markdown link。`validate` 在发现待恢复事务时仅报告事务并退出；普通事务仅检测残留事务并报告 `repair-required`，由命令协调器运行 repair，不先执行或消费 `validate` 的诊断。 |

`validate` 只报告问题，不修复状态。因此诊断不会自行改变 Installation 生命周期、Ref 生命周期、
BoundaryPoint 派生结果或 Worktree 生命周期。

## 8. 受影响的产品表面

| 表面 | 需要定义的内容 | 当前状态 |
|---|---|---|
| `validate` 范围 | Git root、`--subdir` 与仓库级检查的关系 | 已定义 |
| 目录树校验 | 根入口、边界过滤、本地 link 与结构化注释诊断 | 已定义 |
| import 校验 | untracked import link 与 Ref 依赖关系 | 已定义 |
| Worktree 校验 | 范围内 Worktree 的清洁状态，以及仓库级物理登记问题 | 已定义 |
| 工作模型校验 | 违规聚合结构、投影、受管关系与 ignore 约束 | 已定义 |
| 错误返回 | 校验诊断与无法完成校验的命令错误边界 | 已定义，并以需求 0002-01 为准 |

## 9. 依赖与验收标准

- 父需求：[需求 0002](overview.md)。
- CLI 契约与错误目录：[需求 0002-01](01-cli-arguments-results.md)。
- 工作模型：[需求 0002-02](02-working-model.md)。
- 命令工作流：[需求 0002-03](03-boundary-set.md)、[需求 0002-04](04-init.md)、
  [需求 0002-05](05-import.md)、[需求 0002-06](06-worktree.md)。
- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。

- [x] `validate` 的目录树内容范围、工作空间排除、边界过滤和仓库级检查范围已明确。
- [x] 成功校验、发现诊断与无法完成校验的返回及退出状态边界已明确。
- [x] `work-model.valid` 的违规结构、稳定违规 ID 和必填上下文字段已定义。
- [x] 根入口、link、跨界注释、untracked import link 和 worktree 清洁的诊断规则已定义。
- [x] 与 `init` 及其他命令的模型失效处理关系已定义。
- [x] 设计与 CLI 契约、工作模型、各命令簇及 Architecture 的一致性已完成审阅。

## 10. 实施与状态

本子需求目前为 `draft`。设计内容已与 CLI 契约、工作模型及各命令簇完成一次同步；获得明确
批准前，不授权修改 CLI 实现、测试或相关 Architecture 文档。
