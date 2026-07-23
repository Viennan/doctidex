# Git 场景下的 doctidex AI Agent 脚手架参考实现

状态：Non-normative Draft

本文档给出一种基于 Git 仓库的 `doctidex` AI agent 脚手架方案。它是
[doctidex 协议](../overview.md)的参考实现设计，不构成协议要求。

本文档只描述 Skill 的职责、实现层之间的关系以及代码工具应提供的功能，不规定
工具的编程语言、模块结构、命令行形式或内部算法。

## 1. 目标与边界

本方案适用于使用 Git 管理的任意工作仓库，不局限于代码开发。

目标包括：

- 将整个 Git 仓库作为一个 `doctidex` 知识库；
- 让 agent 能够读取、维护和校验与仓库共同演进的知识；
- 允许外部知识库就近挂载到与其内容相关的位置；
- 允许同一 Git source 的不同 revision 在一个解析工作区中同时存在；
- 支持包含间接引用和环状引用的知识库网络；
- 清晰区分外部源的存储、逻辑挂载位置和真实维护入口；
- 支持单根维护与多根协同维护；
- 在不制造 Git commit 循环锁定的前提下提供可重复的解析快照。

本方案不负责：

- 规定分支、提交、评审、合并或发布流程；
- 自动提交或推送用户的工作；
- 替代通用 Git 工具或托管平台；
- 将实现私有目录提升为 doctidex 协议结构；
- 规定 Skill 与代码工具的具体实现方式。

## 2. 三层模型

本方案将外部仓库相关能力拆分为 source store、mount projection 和 canonical
maintenance root。三者不得因使用同一个物理路径而混为同一概念。

### 2.1 Source store

Source store 保存 clone、worktree、对象缓存、解析锁和其他运行时状态，是实现
私有空间，不属于 doctidex 知识树。

本参考实现默认使用仓库内的 `.doctidex/ref/` 作为 source store。根
`index.md` 将 `.doctidex/` 排除在当前 doctidex 之外，Git 则忽略
`.doctidex/ref/`。因此该目录位于仓库文件系统中，但不属于知识树或版本化
内容。

仓库内的固定位置使不同层级的 mount projection 可以使用稳定的相对符号链接，
同时不把 source store 路径定义为协议结构。其他实现仍可以使用 Git 元数据空间、
用户缓存目录或独立工作区。

Source store 应将 Git 对象存储与可读取的工作树分开。同一仓库身份只保留一个
共享对象库；每个不同的已解析 commit 基于该对象库创建一个 detached Git
worktree，而不是分别 clone。同一仓库身份和 resolved commit 共同确定唯一的
checkout 身份；多个挂载点命中相同 checkout 身份时必须复用同一个 worktree，并
可分别投影其中的不同 `src_path`。

一种可行的私有布局是：

```text
.doctidex/ref/
└── <source-key>/
    ├── repository.git/              # bare repository 或等价共享对象库
    └── worktrees/
        ├── <commit-key-a>/          # detached worktree
        ├── <commit-key-b>/          # 同一 source 的另一 revision
        └── maintenance/
            └── <task-key>/          # 多根任务专用的可写 worktree
```

其中 `<source-key>` 由仓库身份稳定计算，`<commit-key>` 使用不会产生歧义的完整
resolved commit。创建 worktree 的逻辑等价于：

```shell
git --git-dir=.doctidex/ref/<source-key>/repository.git \
  worktree add --detach \
  .doctidex/ref/<source-key>/worktrees/<commit-key> \
  <resolved-commit>
```

`worktrees/<commit-key>/` 是按 checkout 身份复用的 revision worktree。它必须保持
detached 且内容与 `<commit-key>` 一致，允许多个 projection 同时读取，但不得直接
用于维护。`worktrees/maintenance/<task-key>/` 是多根协同任务创建的独立可写
worktree；它从目标 revision 建立，不作为任何现有 projection 的目标，也不按
commit key 复用。

首次使用仓库身份时可以 clone 或建立等价对象库。之后解析新的 revision 时，应在
该对象库中查找已有对象；只有缺少解析所需 ref 或对象且操作允许联网时，才对共享
对象库执行 fetch。不得仅因请求了同一 URL 的另一个 revision 而重新 clone。
旧 checkout 在仍被任何快照、projection 或进行中的操作引用时不得删除；垃圾回收也
不得重置、覆盖或移除包含本地修改的 worktree。

### 2.2 Mount projection

Mount projection 是源目录树在当前知识库 `mount_path` 上的逻辑呈现。
`mount_path` 可以位于知识库内任意合理位置，不需要位于隐藏目录中。

```text
repository/
├── index.md
├── architecture/
│   ├── index.md
│   └── payment-api/       # 外部知识库的 mount projection
└── operations/
    └── vendor-runbook/    # 另一个 mount projection
```

实现可以使用符号链接、文件系统 mount、overlay、虚拟映射或其他方式建立
projection。实现方式不改变 `mount_path` 的协议语义。

物理 projection 只是实现选择，不是 doctidex 使用者可观察的可用性条件。只要
source 与 revision 已解析，使用者就必须能够通过 `mount_path` 正常读取目标文件，
并保持一致的目录、link root 和路径边界语义。符号链接无法安全建立时，实现必须
透明改用虚拟 resolver、overlay 或其他可读映射，不得向使用者暴露“projection
不可物化”错误。

本参考实现优先使用相对符号链接作为 projection。每个 `mount_path` 直接指向：

```text
.doctidex/ref/<source-key>/worktrees/<commit-key>/<src_path>
```

多个 `mount_path` 可以指向同一个 worktree，或指向该 worktree 内不同的
`src_path`。Projection 不拥有 worktree；删除或更新某一 mount 声明不得影响仍被
其他 mount 使用的 checkout。

显式 revision 同步先将 selector 解析为新的 commit，再按 checkout 身份查找已有
worktree；若不存在则从同一共享对象库创建。最后将该 mount 的 projection 定向到
新 worktree。旧 worktree 保持不变，并在不再被任何 projection 或快照引用后才可
回收。普通恢复不得因远端 branch 或 tag 漂移而改变 projection。

Projection 是宿主知识库中的逻辑目录条目，但其内部内容仍归源目录树。宿主的
索引只负责 mount 条目本身，不递归接管源内容。

### 2.3 Git-clean projection

恢复或移除 projection 是运行时状态变化，不得因此污染宿主仓库的 Git 变化视图。
仅执行挂载恢复时，以下状态必须保持不变：

- 宿主仓库的 tracked 文件内容；
- Git index 与暂存区；
- 默认 `git status` 中与 projection 物化有关的条目；
- mount 声明和用户选择导出的解析快照。

物理 projection 应采用以下方式之一：

- 使用目标位于 `.doctidex/ref/` 的相对符号链接；显式 revision 同步需要改变链接
  目标时，应将其作为可见、可审阅的同步结果；
- 在不含 tracked 内容的 mount_path 上创建本地忽略的未跟踪 projection；
- 使用不改变宿主工作树内容的文件系统 mount、overlay 或虚拟映射。

实现可以使用仓库本地的非跟踪 ignore 状态隔离 projection。恢复动作不得为了隐藏
变化而自动修改受 Git 跟踪的 `.gitignore`。若 mount_path 已包含 tracked 内容且
物理 projection 会覆盖、隐藏或改变这些内容，实现必须透明改用非侵入式或虚拟
映射，同时保持 `mount_path` 可正常读取。

### 2.4 Canonical maintenance root

Canonical maintenance root 是某个 Git/doctidex 源针对当前维护任务实际进行
修改的根目录。单根维护可以使用用户明确选择的已有工作树；多根协同维护默认在
`worktrees/maintenance/<task-key>/` 中为每个受影响 source 建立独立 worktree。
这些 worktree 可以共享 Git 对象，但不得共享工作树状态、分支占用或维护范围。
供 projection 复用的 resolved revision checkout 是只读缓存，不得承担可写维护
入口。

Mount projection 不是 maintenance root。即使 projection 通过符号链接直接指向
revision worktree，维护工作也必须先定位或建立独立的可写 worktree，再从该
canonical root 建立维护范围。不得修改被多个 projection 复用的 detached
checkout，使其内容偏离快照中的 commit；维护 worktree 也不得在产生新 commit 前
替代任何既有 projection。

`doctidex.protected` 是相对于当前维护根的保护边界：它禁止从宿主范围穿透修改
挂载源，但不表示该源在自己的 canonical root 中全局只读。

## 3. 仓库模型

Git 仓库根目录同时是 `doctidex` 根目录：

```text
<git-repository>/
├── .git/
├── .gitignore
├── .doctidex/
│   └── ref/               # ignored shared repositories and revision worktrees
├── index.md
├── log.md
├── <本仓库内容>
└── <任意位置的 mount projection>
```

本参考实现采用以下约定：

- 根 `index.md` 包含 `doctidex.root: true`；
- 根 `log.md` 由脚手架初始化并维护，尽管协议只将其定义为可选文件；
- `.git/` 通过 `doctidex.excludes` 排除；
- `.doctidex/` 通过 `doctidex.excludes` 排除；
- `.doctidex/ref/` 被 `.gitignore` 忽略；
- mount projection 由最近负责的 `index.md` 声明和索引；
- 当挂载源是其他 `doctidex` 或其子树时，projection 由
  `doctidex.protected` 覆盖；
- source store 与运行时锁不属于知识库内容；
- projection 的恢复与移除不改变宿主仓库的正常 Git 变化视图。

`.doctidex/` 是本参考实现的运行时锚点，不是协议保留目录。它必须被排除，而不是
标识为 atomic；其中的外部仓库不得参与宿主知识库的索引、日志或符合性判断。

根 `index.md` 可以采用：

```yaml
---
type: index
doctidex:
  type: index
  root: true
  excludes:
    - path: .git
    - path: .doctidex
  protected:
    - path: architecture/payment-api
    - path: migrations/payment-api-v1
  mounts:
    - type: git
      url: https://example.com/acme/payment-knowledge.git
      revision:
        tag: v1.2.0
      src_path: ""
      mount_path: architecture/payment-api
    - type: git
      url: https://example.com/acme/payment-knowledge.git
      revision:
        commit: 8f3c2d1a5b7e9c4f6a8d0b2e4c6f8a1d3b5e7c9f
      src_path: migrations
      mount_path: migrations/payment-api-v1
---
```

以上两个 mount 使用同一个 Git source，但允许解析到不同 commit，并在两个
`mount_path` 上同时可见。它们应共享 source store 中的仓库对象库，而不是各自从
远端 clone。

## 4. Git mount 扩展

本参考实现处理 `type: git` 的 `doctidex.mounts`。每个 Git mount 必须指定 Git
URL，并通过 commit、tag 或 branch 中的一种选择 revision。

### 4.1 字段约定

- `type` 必须为 `git`；
- `url` 是 Git source 的定位信息，不得包含需要持久化的明文凭据；
- `revision` 必须是 YAML 映射，并且只包含 `commit`、`tag` 或 `branch` 之一；
- `src_path` 沿用协议定义，空值等同于 `.`；
- `mount_path` 沿用协议定义，可以位于负责索引范围内任意位置。

commit 是可重复性最强的声明方式。tag 和 branch 在解析后应固定到工作区解析
快照中的实际 commit；常规读取和校验不得在未明确同步时静默漂移。

### 4.2 仓库、checkout 与源身份

实现必须区分以下三种身份：

- **仓库身份**：由规范化后的 Git URL 确定，用于复用 clone、fetch 结果和 Git
  对象；
- **checkout 身份**：由仓库身份和已解析的 commit hash 共同确定，用于复用
  detached worktree 或等价 checkout；
- **源身份**：由 checkout 身份和规范化后的 `src_path` 共同确定，用于图遍历、
  projection 和冲突判断。

同一仓库身份可以同时具有多个 checkout 身份，因此同一 Git URL 的 branch、tag
或 commit selector 可以在一个解析工作区中解析到不同 commit 并同时挂载。不同
selector 若解析到同一 commit，应复用同一 checkout。相同源身份可以投影到多个
`mount_path`；同一个 `mount_path` 在同一知识库范围内只能对应一个源身份，发生
冲突时不得静默覆盖。

共享以仓库身份为边界，图遍历去重以源身份为边界。实现不得因为两个 mount 的 URL
相同就把不同 commit 合并成同一个图节点，也不得为不同 commit 创建相互独立的
远端 clone。

### 4.3 根工作区解析快照

Revision 解析快照属于当前解析根工作区，而不是知识网络中每个仓库必须共同提交
的全局状态。

快照至少应记录：

- 快照格式版本；
- 当前解析根身份；
- 每个 mount 声明的 URL、revision、src_path 和 mount_path；
- revision 对应的实际 commit；
- 仓库身份和 checkout 身份；
- 已解析源身份；
- 声明来源和传递路径。

快照不得依赖 source store 的物理路径。不同 selector 即使解析到同一 commit，也
应分别保留其原始声明；checkout 可以复用，但声明身份不能因此丢失。

快照默认保存在 source store 等实现私有空间。实现可以支持将快照导出为可跟踪
文件，但导出位置必须由用户明确选择，并作为普通知识库文件被索引。

挂载恢复只读取已有快照，不得隐式改写用户导出的快照。恢复时若本地缺少快照已
锁定的 commit，可以显式获取该对象，但不得借此重新解析 branch 或 tag。Revision
重新解析和快照更新属于显式同步操作；同一仓库身份的多个 selector 应在同一个
受锁定的 fetch 与解析批次中处理。

快照不得保存访问令牌、私钥或其他凭据。

## 5. 环状知识关系与版本解析

知识库 link 与 mount 形成的关系图可以有环。实现必须通过源身份 visited 集合
停止重复解析，而不能通过递归复制每个仓库的依赖目录处理环。

### 5.1 图解析原则

1. 当前工作区选择一个解析根。
2. 解析器读取该根及传递 source 的 mount 声明。
3. 每个声明解析为源身份和 projection。
4. 已访问源身份不再递归展开。
5. 相同 checkout 身份复用 revision worktree；相同仓库身份的不同 checkout
   共享 Git 对象库。
6. projection 只建立逻辑可见性，不改变源身份或维护归属。

当前解析根的 `.doctidex/ref/` 是该工作区的共享 source pool。pool 对每个
仓库身份集中保存对象，对每个 checkout 身份保存独立工作树。挂载的仓库若也采用
本参考实现，其 `.doctidex/ref/` 运行时入口应连接到当前解析根的共享 pool，
使其已有相对 projection 可以复用同一组 repository 和 worktree，而不递归建立
嵌套 clone。

当前解析根也可能作为 source 被直接或传递 mount 引用。该场景必须按下一节处理，
不得仅因目标仓库就是当前根而绕过 checkout 身份、快照或 projection 规则。

### 5.2 当前解析根作为被引用源

实现必须先确认 mount 的仓库身份确实对应当前解析根。该对应关系应来自已定义的
Git URL 规范化结果、当前根明确选择的 source URL 或用户确认的映射；不得仅根据
仓库目录名、远端仓库 basename 或内容相似性猜测。

当前根被引用时采用以下规则：

1. 当前根的 Git common dir 作为该仓库身份在当前工作区中的对象库，不再从远端或
   当前目录重复 clone。若布局需要
   `.doctidex/ref/<source-key>/repository.git`，该位置可以是实现私有的关联入口，
   但不得复制出语义上独立的仓库身份。
2. 无论 mount 解析到当前 `HEAD` 还是其他 commit，projection 都应指向
   `.doctidex/ref/<source-key>/worktrees/<commit-key>/` 中按 checkout 身份复用的
   detached revision worktree，不直接指向当前根工作树。
3. 当前根工作树中的 staged、unstaged 或 untracked 内容不得泄漏到被引用视图，也
   不得导致快照锁定的 commit 在 projection 中漂移。
4. 若目标 commit 尚未存在于 Git common dir，只能在显式允许联网时通过已确认匹配
   的 remote 获取；不得为了补齐该 commit 再 clone 当前仓库。
5. 若多根任务需要修改当前根，也在其
   `worktrees/maintenance/<task-key>/` 下创建独立维护 worktree。当前解析根继续作为
   协调入口，不因维护任务被切换分支、重置或覆盖。
6. 图遍历继续以源身份去重。扫描器不得沿当前根的 projection 或 revision
   worktree 递归进入 `.doctidex/ref/`，也不得因主仓库回边无限展开。

图遍历去重不能替代文件系统路径安全检查。若当前根回边或环状 mount 的物理
projection 会指向其宿主祖先、包含自身 mount_path，或形成 projection 符号链接
环，实现不得物化该符号链接，而必须透明使用不产生文件系统递归的虚拟 resolver、
overlay 或等价映射。使用者仍通过原 `mount_path` 读取内容，不需要感知回边采用了
不同的 projection 机制。

当前根可能本身就是 linked worktree；对象库定位必须使用 Git common dir，而不能
假设 `<root>/.git` 一定是目录。

### 5.3 Link 语义

宿主文档 link projection 内的文档时，使用普通 doctidex 路径 link。

挂载源本身是 doctidex 时，其文档中的 link 继续以源 doctidex 根为链接根目录。
实现可以通过为每个 canonical root 建立独立视图，或通过 link resolver 映射其
mount 声明；不得把宿主 projection 路径误当作源文档的根目录。

目录扫描、索引和校验不得跨 mount boundary 递归接管源目录树，也不得因符号链接
环而无限遍历。

### 5.4 Commit 精确锁定环

知识关系允许有环，不代表每个仓库都能在 Git commit 中精确锁定其他仓库的最终
commit。若 A 与 B 的已提交状态都包含对方最终 commit hash，更新任意一方都会
改变自身 hash，从而无法形成稳定的相互固定点。

本参考实现采用以下调和方式：

- 知识关系图可以有环；
- commit 解析由当前根工作区快照统一持有；
- branch 或 tag 可以作为跨环的符号 selector；
- 不要求每个 ref 仓库提交反向锁定宿主最终 commit 的快照；
- 若用户要求所有边均使用精确 commit，则精确锁定关系必须不存在提交级环。

## 6. 多根协同维护

单个 Maintain Skill 始终只维护一个 doctidex 根。需要同时修改宿主和多个 ref
仓库时，由 Workspace Skill 协调多个独立根。

### 6.1 基本流程

1. 根据任务、mount 图和 revision 影响识别所有可能受影响的仓库身份、知识库根与
   基准 commit；当前解析根若也是被引用 source，按同一节点处理。
2. 为每个仓库身份定位共享对象库。普通 source 使用
   `.doctidex/ref/<source-key>/repository.git`，当前解析根使用其 Git common dir。
3. 检查基准 revision worktree、用户已有工作树、目标分支占用、source store 锁和
   保护边界；任何被 projection 使用的 revision worktree 都只读。
4. 由 Mount Skill 在对应 source 的
   `.doctidex/ref/<source-key>/worktrees/maintenance/<task-key>/` 下，从基准 commit
   创建独立 worktree。若任务需要产生 commit，应使用用户选择或实现为该任务创建的
   独立分支，不得抢占已在其他 worktree 中 checkout 的分支。Source store 应记录
   task key、base commit、分支、创建时间和当前状态，供并发检查与安全回收使用。
5. 将每个 maintenance worktree 作为独立 canonical maintenance root，恢复该根
   所需的 mount 视图，并为每个根分别形成维护计划。
6. 按依赖顺序在各 maintenance worktree 中完成知识、index、log 及其他授权内容的
   修改和校验。不得通过 projection 穿透修改其他 root。
7. 汇总各根的 diff、校验结果和预期 revision 影响。提交、推送及远端分支操作仍需
   遵守用户授权，不得由 Workspace Skill 隐式执行。
8. 某个维护根产生新 commit 后，按新的 checkout 身份查找
   `worktrees/<new-commit-key>/`；不存在时从同一对象库创建新的 detached revision
   worktree。不得把可写 maintenance worktree 直接改作共享 projection checkout。
9. 按依赖顺序更新相关 mount 声明、解析快照和 projection，使其定向到新 revision
   worktree；仍引用旧 commit 的 mount 保持不变。
10. maintenance worktree 只有在工作树干净、结果已被安全保留且用户工作流允许时
    才能移除。存在未提交修改、未合并分支或未报告结果时必须保留并提供其路径。

创建维护 worktree 的 Git 操作等价于：

```shell
git --git-dir=<repository-git-dir> \
  worktree add -b <task-branch> \
  .doctidex/ref/<source-key>/worktrees/maintenance/<task-key> \
  <base-commit>
```

`<repository-git-dir>` 对普通 source 是其 `repository.git`，对当前解析根是其 Git
common dir。若用户工作流暂不创建分支，可以先使用 detached maintenance
worktree，但在提交、保留或交接结果时必须明确其 commit 或分支归属。

任何一步都不得把宿主 `mount_path` 当作源仓库的写入入口。
Revision worktree 只服务于读取、校验和 projection；maintenance worktree 只服务于
当前维护任务。两者共享对象库，但生命周期、可写性和引用关系必须分别管理。

### 6.2 更新顺序

通常应先完成 ref 仓库的内容修改并取得其新 revision，再更新依赖这些 revision 的
宿主声明或解析快照。

维护 worktree 中尚未形成 commit 的内容没有可供 mount 锁定的 revision，不得提前
切换 projection。产生 commit 后也应先建立或复用对应的 detached revision
worktree，再更新引用关系。这样 maintenance worktree 的后续修改、分支切换或清理
不会影响已经更新的 projection。

若 ref 仓库也引用宿主，应优先保留符号 selector 或根工作区快照，不应尝试通过
反复改写双方 commit hash 达成循环精确锁定。

跨仓库修改不具备天然原子性。Workspace Skill 应先形成完整计划并分别校验，
但提交、推送和远端协调仍由用户授权的 Git 工作流负责。

## 7. Skill 分工

每个 Skill 应保持单一主要职责，并复用统一的代码工具。

### 7.1 设计原则

Skill 是用户和 agent 使用本参考实现的稳定操作界面。本文档描述 source store、
worktree、锁、projection 物化等内部设计，不表示 Skill 应在正常交互中原样暴露
这些约定。实现本文档时必须区分以下信息层：

| 信息层 | 主要使用者 | 应提供的信息 |
|---|---|---|
| 用户层 | 人类用户 | 操作目标、可观察结果、风险、需要确认的选择和后续 Git 协调事项 |
| Agent 作业层 | 执行任务的 agent | doctidex 根、逻辑 `mount_path`、声明与 resolved revision、读写边界、canonical maintenance root、跨根顺序、校验结果和下一步动作 |
| 内部程序层 | Skill 背后的代码工具 | source key、对象库与 worktree 布局、Git common dir 关联、锁、缓存、fetch 批次、projection 物化方式和生命周期元数据 |

Skill 应遵守以下原则：

- **最小暴露**：默认只向用户和 agent 提供完成当前任务所需的信息，不要求其理解
  `.doctidex/ref/` 布局、worktree 管理、锁名称、缓存键或 projection 的物理实现；
- **语义稳定**：对外使用 doctidex 根、`mount_path`、revision、维护范围和任务结果
  等稳定概念，不把可变的内部目录结构或工具调用方式提升为使用契约；
- **信息充分**：最小暴露不得造成信息缺失。Skill 必须明确任务入口、前置条件、
  允许的读写范围、实际结果、未完成事项、需要的用户授权以及可继续执行的下一步；
- **Agent 自足**：Skill 的说明和输出必须足以让 agent 在不阅读程序源码、不检查
  私有缓存或锁文件、不推断隐藏状态的情况下完成正常读取、维护、校验和跨根协调；
- **诊断翻译**：代码工具可以产生包含内部路径和状态的结构化诊断，但 Skill 应将其
  翻译为用户或 agent 可执行的原因、影响和下一步，只在调试或用户明确请求时展示
  必要的内部细节；
- **透明实现**：符号链接、虚拟 resolver、overlay 或其他 projection 机制之间的
  切换应保持相同的用户层读取语义，不把内部降级、缓存命中或 worktree 复用情况
  暴露为用户需要处理的问题；
- **知识隔离**：内部 source store 路径、锁、缓存身份和临时维护元数据不得写入
  doctidex 知识文档、普通 link 或需要长期维护的用户配置。

每个 Skill 的公开说明至少应包含适用意图、输入与前置条件、读写边界、成功输出、
可恢复问题的继续方式和需要用户决策时的升级条件。内部程序可以采用不同模块、
命令和存储结构，只要上述公开契约保持完整且一致。

| Skill | 主要职责 | 允许的写入 | 明确不负责 |
|---|---|---|---|
| `doctidex-git-bootstrap` | 初始化或接管 Git 仓库中的 doctidex 骨架 | 根 index、根 log、`.gitignore`、`.doctidex/` 运行时骨架 | clone 外部源、维护业务知识、提交 Git 变更 |
| `doctidex-git-read` | 定位知识库、沿 index/link 读取、按需请求 projection 可用 | 默认无 | 修改知识、同步 revision |
| `doctidex-git-maintain` | 在单一 canonical root 中维护知识、index 与 log | 当前根内未受保护的范围 | 穿透 projection 修改源、管理 source store |
| `doctidex-git-mount` | 解析 mount 图、管理 source store、快照与 projection | 实现私有状态和 projection 状态 | 修改宿主或源知识内容 |
| `doctidex-git-workspace` | 协调一个任务涉及的多个 canonical root | 各根中经独立 Maintain 流程授权的内容 | 将多根伪装成单根、自动提交或推送 |
| `doctidex-git-validate` | 校验协议、脚手架、projection、解析快照和根边界 | 默认无 | 自动修复或隐式在线同步 |
| `doctidex-git-review` | 只读审阅单根及跨根变化 | 无 | 修改文件、恢复 source、提交或推送 |

插件可以提供轻量入口将用户意图路由到上述 Skill，但入口不应复制各 Skill 的完整
工作流。

### 7.2 Bootstrap Skill

Bootstrap Skill 应：

- 确认 Git 根目录并将其作为 doctidex 根目录；
- 在保留已有内容的前提下创建或补全根 `index.md` 与 `log.md`；
- 通过 `doctidex.excludes` 排除 `.git` 与 `.doctidex`；
- 创建 `.doctidex/ref/` 并补充对应 Git ignore；
- 明确 `.doctidex` 只是参考实现运行时目录；
- 保留用户已有的 mount_path 组织方式；
- 在交付前调用 Validate Skill。

### 7.3 Read Skill

Read Skill 应保持只读：

- 定位当前文档所属的 doctidex 根；
- 读取最近负责的 index；
- 只加载任务所需条目和 anchor；
- link 指向未恢复 projection 时查询 Mount Skill；
- 明确区分宿主知识、projection、canonical source 与普通外部资料；
- 不隐式更新 branch、tag 或解析快照。

### 7.4 Maintain Skill

Maintain Skill 应：

- 只接受一个明确的 canonical root；
- 使用 Git 状态与 diff 确定候选影响范围；
- 遵守 atomic、excludes、protected 和 mount boundary；
- 按最近负责制维护 index 与 log；
- 保留未知 frontmatter 字段和无关用户修改；
- 修改后执行与范围相称的校验。

### 7.5 Mount Skill

Mount Skill 应支持：

- 校验 Git mount 扩展字段；
- 在不写入的情况下生成解析与 projection 计划；
- 将 tag 或 branch 解析为 commit；
- 管理根工作区解析快照；
- 按仓库身份建立和复用共享对象库，避免同源重复 clone；
- 按 checkout 身份建立和复用 revision worktree，允许同源多 revision 共存；
- 对共享对象库执行显式、去重且有锁保护的 fetch；
- 管理当前解析根共享 `ref` pool 及挂载仓库的运行时连接；
- 创建、检查和安全移除任务隔离的 maintenance worktree；
- 创建、验证和移除 projection；
- 在符号链接无法安全物化时透明建立可读的虚拟 projection；
- 保证恢复和移除 projection 不改变宿主 tracked diff、Git index 或默认状态视图；
- 构建传递 mount 图并检测环；
- 识别返回当前根的边；
- 检测路径、源身份和 projection 冲突；
- 提供离线检查和显式在线同步；
- 保护所有工作树中的本地修改。

### 7.6 Workspace Skill

Workspace Skill 应：

- 将任务分解为多个明确的 canonical root；
- 生成跨根修改顺序和 revision 影响计划；
- 协调 Mount Skill 为每个受影响 source 建立任务隔离的 maintenance worktree；
- 将当前解析根作为被引用 source 时也纳入相同的 worktree 流程；
- 分别调用或指导各根的 Maintain 与 Validate 流程；
- 阻止任何通过 projection 的写入；
- 汇总跨根结果、未解决冲突和后续 Git 协调需求；
- 不自动执行提交、推送或远端合并。

### 7.7 Validate Skill

Validate Skill 应提供：

- 协议结构与 frontmatter 检查；
- index、log、过滤条件和 link 检查；
- Git 根与 doctidex 根一致性检查；
- mount 声明与 protected 覆盖检查；
- projection 与 canonical source 对应关系检查；
- projection 恢复前后的宿主 Git-clean 检查；
- 解析快照与实际 revision 一致性检查；
- revision worktree 不可变性、maintenance worktree 隔离与生命周期检查；
- 当前解析根被引用时的 common dir 复用和未提交内容隔离检查；
- 单根维护边界和跨根穿透写入检查；
- 显式请求时的在线 revision 检查。

### 7.8 Review Skill

Review Skill 重点关注：

- Git 变化是否正确反映在负责 index 与 log 中；
- 是否修改了 excluded、protected 或 projection 后的源内容；
- mount 声明、projection、source 与快照是否一致；
- 多根修改是否分别从 canonical root 完成；
- maintenance worktree 是否与 projection checkout 隔离，且结果已被安全保留；
- 主仓库回边是否隔离工作树内容，并透明提供不会形成文件系统环的可读 projection；
- 是否产生 commit 精确锁定环；
- 是否把实现约定误写为协议要求。

## 8. 必要代码工具能力

| 工具能力 | 功能要求 |
|---|---|
| 根目录发现 | 同时识别 Git 根、Git common dir、doctidex 根、canonical root 和当前维护边界 |
| Frontmatter 处理 | 解析、校验并保留未知 YAML 字段 |
| 负责范围计算 | 应用最近负责制、过滤条件及 index、atomic、exclude、mount 边界 |
| 目录清单 | 生成协议视角的文件树，不跨 projection 或符号链接环递归 |
| Link 分析 | 提取 Markdown 与扩展 link/anchor，按正确链接根解析目标 |
| Git 变化分析 | 提供 status、diff、rename 和 revision，将变化映射到知识范围 |
| Source 身份计算 | 分别计算仓库、checkout 与源身份，识别可共享对象、可复用 checkout 和冲突 source |
| Source store 管理 | 每个仓库身份复用对象库，每个 checkout 身份复用只读 revision worktree，并为任务建立独立 maintenance worktree |
| Mount 图规划 | 构建传递关系，检测环、回根边和精确锁定环 |
| Projection 管理 | 将 mount_path 映射到指定 checkout/src_path，复用相同 checkout 并安全定向到新 revision |
| 解析快照管理 | 记录、比较、导入和导出根工作区 revision 快照 |
| 多根计划 | 计算受影响根、修改顺序和跨根 revision 影响 |
| 统一校验 | 输出文件、字段、路径、根和 source identity 可定位的结构化诊断 |

工具应共同遵守：

- 支持只读检查和 dry-run；
- 写入前明确 canonical root 和影响范围；
- 不静默覆盖来源不明的文件、目录或链接；
- 不自动提交、推送、重置或清理用户 Git 状态；
- 不因恢复 projection 修改 tracked `.gitignore`、Git index 或用户导出的快照；
- 不将 source store 的物理路径写入知识 link；
- 网络不可用时区分远端未验证与本地不符合；
- 以结构化结果向 Skill 返回计划、诊断和实际变更。

## 9. 关键工作流

### 9.1 初始化

1. 发现 Git 根并检查是否已有 doctidex 根。
2. 规划需要创建或修改的根 index、log 和忽略规则。
3. 建立被排除的 `.doctidex/` 与被忽略的 `ref/`。
4. 保留已有内容并建立最小知识骨架。
5. 运行离线校验。

### 9.2 恢复挂载视图

1. 读取当前根及传递 source 的 mount 声明。
2. 生成源身份、projection 和图解析计划。
3. 识别返回当前根的边和已访问 source。
4. 按仓库身份合并远端访问计划，检查共享对象库、revision worktree 与本地 Git
   状态。
5. 对每个仓库身份合并缺失对象请求，执行一次必要的 clone 或批量 fetch，并为不同
   checkout 身份建立或复用独立 worktree。
6. 记录宿主仓库恢复前的 tracked diff、Git index 与默认状态视图。
7. 以 Git-clean 方式建立或恢复 projection；物理映射不安全时透明使用虚拟映射，
   保证 `mount_path` 仍可读取。
8. 校验恢复前后的宿主 Git 状态保持等价。
9. 校验 projection、link root 与 protected 边界。

恢复流程不更新 revision 或解析快照；需要更新时必须进入显式同步流程。

### 9.3 单根维护

1. 从 canonical root 建立维护上下文。
2. 读取 Git 状态、diff 与相关 index。
3. 排除不属于当前根或当前维护范围的内容。
4. 更新必要的知识文档、index 和 log。
5. 校验 link、索引覆盖和保护边界。
6. 保留修改供用户审阅，不自动提交。

### 9.4 多根维护

1. Workspace Skill 识别所有受影响 source、基准 commit 和依赖顺序。
2. 为每个 source 检查对象库和现有工作树，并由 Mount Skill 创建任务隔离的
   maintenance worktree；当前解析根被引用时使用其 Git common dir。
3. 从各自 maintenance worktree 执行 Maintain 与 Validate，不修改 revision
   worktree 或 projection 后的内容。
4. 汇总各根变化，并在用户授权的 Git 工作流取得新 commit。
5. 为每个新 commit 创建或复用 detached revision worktree。
6. 按依赖顺序更新解析根声明、快照和 projection，保留仍被引用的旧 revision。
7. 报告跨仓库提交、远端协调以及仍需保留的 maintenance worktree。

## 10. 失败处理原则

以下情况必须停止有写入影响的操作并提供可操作诊断：

- mount 声明缺少或同时设置多个 revision selector；
- 同一 mount_path 对应不同源身份；
- 同一仓库身份被错误映射到多个独立 clone，或不同 checkout 身份被错误复用为同一
  工作树；
- 当前解析根与 mount 的仓库身份无法可靠确认；
- maintenance worktree 将复用或修改现有 revision worktree，或目标分支已被其他
  worktree 占用；
- projection 目标与声明或 canonical source 不一致；
- projection 的相对符号链接不再指向当前根的 `ref` pool；
- 快照与声明、实际 checkout 或解析根不一致；
- mount_path、src_path 或过滤路径越界；
- revision worktree 存在使其偏离 checkout 身份的本地修改；
- 快照锁定的 commit 在本地缺失，且当前操作不允许联网或远端无法提供该对象；
- source store 的 fetch、worktree、projection 或垃圾回收锁无法安全取得；
- 需要写入 source，但当前入口是宿主 projection；
- 精确 commit 锁定关系形成无法稳定更新的环；
- 网络、凭据或远端状态不足以完成显式同步。

只读查询可以在 source 或 revision 信息不完整时继续，但必须标明哪些 revision 或
link 未经验证。仅物理 projection 无法建立不属于此类不完整状态，也不得降低
`mount_path` 的正常读取能力。

## 11. 后续待定事项

- Git URL 的规范化规则；
- 根工作区解析快照的 schema 与可选导出格式；
- branch 与 tag 的同步策略及用户提示方式；
- source store 的生命周期、共享范围与垃圾回收；
- maintenance worktree 与任务、分支和用户工作区之间的命名及保留策略；
- snapshot、projection、worktree 与 Git 对象之间的引用计数或租约模型；
- 共享仓库 fetch 的并发锁、refspec 与凭据复用策略；
- `.doctidex/ref` 中 Git worktree 在不同平台下的路径处理；
- projection 的平台兼容性与冲突处理；
- 多根修改的分支与远端协作策略；
- 常见 Markdown 扩展 anchor 的解析范围；
- 大型仓库中目录清单与 link 校验的增量策略。
