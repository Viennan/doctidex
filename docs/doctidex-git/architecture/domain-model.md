# 领域模型

本文负责定义支撑 v1.0.0 user surface 的语言无关概念、全部属性、关系和不变量。精确
JSON spelling 见 [CLI Schema](interfaces/cli-schema.md)，operation 的执行顺序见
[子系统与生命周期](subsystems-and-lifecycles.md)；本篇不充当命令教程。

## 1. 可见性

| 标记 | 含义 |
|---|---|
| Public | Human、agent 或 program 完成任务必须理解。 |
| Conditional | 只在 external/worktree/validation 场景出现。 |
| Internal | 支撑公开不变量，不得成为 Skills 或调用 CLI 的前置知识。 |

## 2. 命令上下文

| 属性 | 可见性 | 语义与约束 |
|---|---|---|
| cwd | Public | 解析相对文件系统路径和部分省略 root 的调用期默认值；不持久化。 |
| explicit root | Conditional | 调用方给出的 exact doctidex root；不能是普通子目录。 |
| selected root | Conditional | 本次 operation 实际解释协议路径和 root-owned presentation 的根；回显于结果。 |
| content root | Conditional | link-parse 输入实际位于的 doctidex root；在受管 install 中可以与拥有依赖安装的 selected root 不同。 |
| operation | Public | 决定参数、schema、副作用和退出码。 |
| target | Public | 本次读取、创建、解析或关闭的 path/source/worktree。 |
| output mode | Public | human 或 JSON；不改变 domain operation。 |
| page request | Conditional | limit 与 opaque cursor；只影响输出，不改变扫描或状态。 |
| validation scopes | Conditional | validate 的规范化根绝对目录集合；省略表示 `/`，仅限制结论 coverage 与返回信息，不改变 selected root。 |

不变量：root 必须唯一；cwd 不构成权限；同一 process 的前一次选择不影响下一次调用。

## 3. 修订选择器与提交

| 属性 | 可见性 | 语义与约束 |
|---|---|---|
| kind | Public | commit、tag 或 branch。 |
| value | Public | 调用方输入；省略 install revision 时归一化为 full commit。 |
| default branch | Conditional | 初次省略 revision 时 remote HEAD 的 branch name，只是 provenance。 |
| resolved commit | Public | install 固定的 immutable full commit ID。 |
| base commit | Conditional | maintenance worktree 创建基准；同样 immutable。 |

selector 不等于 commit：显式 branch/tag 可以是移动 ref，但任何已创建 install、link 或
worktree 只跟踪 resolved/base commit。既有 install 重试不得重新解析 ref；worktree open
每次按本次显式输入解析。
install 的 normalized selector 对 commit 使用 full object ID，对 tag/branch 保留不同 kind
及规范化 ref name；省略 revision 首次解析后变为 commit selector。identity 比较 selector，
不以 resolved commit 反向合并不同 selector。

## 4. 外部来源

| 属性 | 可见性 | 语义与约束 |
|---|---|---|
| input locator | Public at call | install 的 Git URL；可以临时含 credentials。 |
| public source URL | Public | 去除 credentials 后可报告的 identity。 |
| canonical source identity | Internal | 判断同 source、复用 objects 和串行化操作的稳定 identity；不证明镜像/fork 等价。 |
| revision selector | Public | 创建时的显式 selector，或省略时固定 commit selector。 |
| default branch | Conditional | 省略 revision 的初次来源；后续不用于选择内容。 |
| resolved commit | Public | external content 的唯一读取基准。 |
| object availability | Internal | 本地是否已有构成该 commit 所需 Git objects。 |

职责：说明内容来源与固定基准。非职责：证明协议符合、信任、写权限、remote 最新状态或
Git 交付目标。

### 4.1 共享 Bare 来源缓存与清理结果

shared bare source cache 是按 canonical source identity 跨 root 复用的内部 Git object
provider，不是 checkout、presentation 或恢复清单。清理接口只公开调用方作决定所需的
source facts：sanitized source URL、opaque cache source ID、linked/valid/prunable worktree
counts，以及 planned、removed 或 preserved state；物理 cache path、identity 编码和
worktree metadata layout 均为 Internal。

一个 linked registration 只能被分类为 Git-valid 或 Git-prunable。存在任何 valid worktree
时，cache 完整保留，不考虑其 clean/dirty、doctidex ownership 或 runtime record；存在无法
安全分类的 registration 时，清理不产生正常 state，而是 blocked 并保留。只有 valid 数量
为零且全部其余 registration 都由 Git 判为 prunable 时，cache 才具备删除资格。apply 删除
前必须在同一 source mutation boundary 内重查资格。

清理职责仅是回收一个已具备资格的 bare source cache。它不删除 linked worktree path、
install/worktree payload、manifest、runtime record 或其他 source cache，不修改 root，也不
替代 Git worktree 生命周期管理；其他 operation 不能隐式触发该清理。

## 5. 受管安装

| 属性 | 可见性 | 语义与约束 |
|---|---|---|
| root | Public | install 所属 doctidex 根。 |
| install key | Public by components | selected root、canonical source identity 与 normalized revision selector 的组合。 |
| install ID | Public | 在 root 内稳定标识该 install key 的不透明值。 |
| install path | Public | 工具分配的 `/.doctidex` 内稳定路径；调用方不能选择。 |
| working path | Public | 原生工具读取 repository 根的文件系统路径。 |
| source | Public | 外部来源事实。 |
| host repository | Public | 包含 selected root 并承担 payload ignore 与 manifest tracking 的 Git 根。 |
| payload tracking | Public | 必须是 ignored 且 untracked；已有 tracked entry 时不能自动修复。 |
| Git exclusion file/state | Public | 宿主根 `.gitignore` 及 absent、tracked、modified 或 untracked 状态。 |
| recovery manifest/state | Public | portable 恢复清单路径及 absent、tracked、modified 或 untracked 状态。 |
| role | Public | `direct` 或 `dependency`；direct 进入恢复清单，dependency-only 不进入。 |
| dependency of | Public | 请求该 key 的 parent install ID 有界摘要；direct 也可以同时具有 parents。 |
| responsible index | Public | 负责内部受管命名空间 boundary/unsafe 声明的 index。 |
| managed state | Public | complete、missing 或 damaged。 |
| publication mechanism | Internal | 让 install path 指向逻辑只读 Git state 的实现选择。 |

不变量：一个 install key 只有一个 install；同 source 的不同 selector 即使解析到相同 commit
也拥有不同 ID/path；内容始终对应记录的 resolved commit；payload 被宿主 Git 忽略，manifest
不被该精确规则忽略。dependency 可以提升为 direct 但 direct 不降级；恢复只处理 direct。
逻辑只读不承诺安全沙箱，内部子路径命名属于 Details。

依赖关系是 root-owned 的有向图，不是目录嵌套。parent/child 都直接位于 owner root 的
`/.doctidex` 下；命中既有 install key 即复用并停止展开，因此 self edge 与 cycle 都是有限
记录。CLI 不解析依赖文档或自动递归。宿主 repository 作为依赖时仍使用独立 install；是否
复用其本地 Git objects 是 Internal，不改变公开路径和 fixed commit。

## 6. 外部链接

| 属性 | 可见性 | 语义与约束 |
|---|---|---|
| owner root | Public | link 所属 selected root。 |
| install ID/path | Public | link 最终引用的稳定 direct 安装。 |
| source path | Public | 调用时选择的受管 install/link 内目录。 |
| target path | Public | 用户选择的 root-relative POSIX symlink 路径。 |
| presentation path | Public | symlink 的文件系统入口。 |
| relative symlink target | Public as observable path | 从 target 指向 install path 或其子目录，不依赖宿主绝对路径。 |
| repository-relative base | Public | link 根对应外部 repository 内的位置。 |
| safe state | Public | safe 或 unsafe 的产品接入分类。 |
| responsible index | Public | 声明该 link boundary/unsafe 的最近负责 index。 |
| tracking state | Public | link 必须可被宿主 Git 追踪；是否已 stage/commit 由用户决定。 |
| managed state | Public | managed、unmanaged 或 damaged；不改变协议事实。 |

不变量：link 必须是相对 symlink，禁止目录复制 fallback；suffix 必须词法映射到同一
repository 且不得越出；target 不重叠；restore 不修改 link。内部 install 恢复到稳定路径后，
既有 link 自动恢复可读。dependency-only install 必须先提升为 direct 才能成为 link source。

## 7. 恢复清单与恢复项

恢复清单位于同一 `/.doctidex` 受管命名空间中、与被忽略的安装载荷互为 sibling，因而
可以由精确 ignore 规则保留为可追踪状态；具体子路径命名属于 Details。它保存 portable
状态，只记录 direct installs 及其 durable links。属性包括 schema version、install ID、
sanitized source identity、revision selector、default branch provenance、resolved commit、
stable root-internal install path，以及每个 link 的 target 与 repository-relative base。它不
包含 dependency-only install、dependency edges、credentials、宿主绝对路径、cache path、
lock 或临时下载状态。

该清单随宿主 repository 提交后，也会作为普通版本化内容出现在其 install 快照中。此时
其中的 link record 是 installed-repository portable mapping：它不授权在只读 install 内
restore，也不要求原 stable path 在快照内存在，而是为当前外层 owner root 提供 dependency
source/selector/commit 和 repository-relative base。原 symlink target 缺失是依赖尚未在
owner root 展开的合法产品状态，不等同于 portable mapping 损坏。

恢复项公开 install ID/path、source provenance、exact commit、
`planned|restored|unchanged|blocked` 状态和 item findings；`planned` 只表示 dry-run 已确认
可重建。恢复集合还公开规范化 filter、manifest identity、分页与模式。restore
重建载荷和必要的内部 install/link mapping，不改变清单 identity、既有 link、frontmatter 或
Git index；单项失败不撤销其他项。

## 8. 外部路径映射

| 属性 | 可见性 | 语义与约束 |
|---|---|---|
| input path/kind | Public | link-parse 接收的可读目录或 symlink 自身；broken symlink 仍是合法输入。 |
| managed | Public | 是否识别到 current-owner 或 installed-repository 受管 mapping 身份；完整性和可用性由 target state 表达。 |
| owner root | Public | 拥有当前 install/dependency namespace 的 selected root；所有新依赖都在这里扁平展开。 |
| content root | Conditional | input 所在 doctidex root；主仓库通常等于 owner root，install 内容中可以不同。 |
| mapping origin | Public | owner_root、installed_repository 或 null。 |
| matched presentation | Public | current-owner presentation，或 install 内匹配的 portable symlink。 |
| target state | Public | available、owner_install_missing、dependency_not_installed、unavailable 或 not_applicable。 |
| target install ID/path | Conditional | 当前 owner root 中实际提供 source/selector 的 install；尚未安装时为空。 |
| dependency parent install ID | Conditional | portable mapping 所在的当前外层 install；供 `--dependency-of` 使用。 |
| relative suffix | Internal | input 相对 matched presentation 的词法 suffix。 |
| repository-relative path | Public | portable/current base 加 suffix，规范化后仍位于 target repository。 |
| source/selector/default/commit | Public | 从 current record 或 portable manifest 恢复的 target source facts。 |
| working path | Conditional | target install 已在 owner root 时映射出的原生工具路径；不返回 install 内 broken target。 |
| integrity state | Public through status | complete、合法未展开、可恢复缺失或真实 mapping damage。 |

mapping 只提供客观路径和 dependency facts。它不运行 validation、不联网、不自动安装依赖，
也不授权维护。PATH 位于受管 install 时，外层 presentation ownership 优先确定 owner root；
install 中的 `doctidex.root: true` 只确定 content root，不能使命令在只读树内递归展开。

current-owner link 指向缺失 install 时是 `owner_install_missing`，由 restore 恢复原稳定路径；
installed-repository portable link 没有匹配外层 install 时是正常 `dependency_not_installed`。
后者找到匹配 install 后，即使物理 symlink 仍 broken，也以外层 install 和
repository-relative path 返回 available working path。source/selector/commit 或 link record
不能互相验证时才是 damage。调用方决定安装 portable dependency 时使用 exact resolved
commit 构造 commit selector；portable branch/tag 只保留 provenance，不重新解析。

## 9. 维护工作区（Worktree）

| 属性 | 可见性 | 语义与约束 |
|---|---|---|
| source kind | Public | managed_path、url、working_tree、bare_gitdir 或 gitfile。 |
| owner root | Public | 拥有 CLI-created worktree 的 selected doctidex root。 |
| source identity | Public/Internal | 输出 sanitized URL；内部 canonical identity 支持候选比较。 |
| revision selector | Public | open 的显式 commit/tag/branch。 |
| base commit | Public | detached worktree 的 immutable 创建基准。 |
| root-internal path | Public | owner root 的 `/.doctidex` 下扁平、唯一的受管路径。 |
| worktree path | Public | repository root 的 exact writable filesystem path。 |
| repository-relative path | Public | 最初 source target 在 repository 内的位置。 |
| working path | Public | 对应调用目标的 writable path。 |
| state | Public | clean、changed 或 unavailable。 |
| managed identity | Internal | 证明 list/close ownership 的不可猜测 identity。 |

职责：在 owner root 下提供独立可写 Git 现场和安全 close 边界。非职责：强制调用方创建
现场、创建交付 branch、决定权限、自动复用、commit/push/merge/reset 或删除 dirty work。
相同 source/base commit 只是候选事实。

不变量：CLI-created worktree 不位于 install、另一个 worktree 或 root 外部；即使 SOURCE
来自这些位置，也在 owner root 的 `/.doctidex` 下作为 sibling 创建并被宿主 Git ignore。
当前宿主 working tree/current commit 可由 agent 直接维护，不属于受管 worktree record。

## 10. 校验结果

| 属性 | 可见性 | 语义与约束 |
|---|---|---|
| coverage | Public | full 或 scoped；界定结果能否作为全根结论。 |
| scopes | Public | 规范化、排序、去重且无祖先/后代冗余的根绝对目录集合；full 固定为 `/`。 |
| support closure | Internal | 为正确解释 scopes 必须读取的 root/祖先 index、配置、可达导航与必要 link targets。 |
| protocol structure | Public | pass/fail；只由当前 coverage 及支持闭包中的协议强制规则决定。 |
| scan complete | Public | 当前 coverage 及支持闭包的应检查 safe 内容是否全部判断。 |
| findings | Public | scopes 内或直接阻止其验证的可机械确认 protocol errors。 |
| semantic review | Public | clear/required；不改变协议结果。 |
| semantic candidates | Public | scopes 内需要阅读判断的建议性事项。 |
| collection | Public | 每个列表的 total/page/truncation/cursor。 |

validation 不含 plugin readiness、Git status、remote、registry integrity、source trust 或
维护授权。scoped pass 不能提升为 full pass；scope 也不能阻止 interpreter 读取形成正确
结论所需的支持内容。一个结果不能用 status 或 exit code 代替上述独立属性。

## 11. 结果、问题项与集合

Result envelope 的每个字段都属于 Public。`status` 只描述 operation；`result` 描述完成与
保留；`changed` 是实际公开路径变化；`network` 是实际效果；`affected` 和
`requires_user` 界定 blocked 决策；`next_actions` 面向已完成结果。

Finding 的 domain、severity、code、message、path、actions 全部 Public。code 用于稳定
分支，message 不稳定且只解释用户层原因。Collection 的 limit、list counts、truncated
与 cursor 全部 Public；cursor 内容 Internal，不可解析或构造。

## 12. 内部支持概念

| 概念 | 必需属性 | 责任 | 非责任 |
|---|---|---|---|
| source object provider | canonical source、available objects、proven host relation、linked worktree registrations、cleanup eligibility | 从受管 bare store 或已匹配宿主 Git 复用 immutable objects，并在 source mutation boundary 内为显式 cleanup 提供 Git-derived 分类。 | 向 Skill 暴露 `.git`/cache 路径、保存 credentials、承载 checkout view、推断 root ownership 或清理仍有 valid/unknown worktree 的 source。 |
| install record | owner root、install key/ID/path、source、selector、commit、role、parents、host Git、manifest relation | 让 install/restore 幂等、截止 dependency cycle 并维持固定路径与 commit。 | 递归解析依赖、充当协议配置、保存 credentials 或代替版本化清单。 |
| link record | owner root、target、install、repository-relative base、safe state | 让 link-parse 与幂等 link 恢复路径事实，并作为安装快照中的 portable mapping。 | 充当读取授权、要求内层 restore 或替用户 stage symlink。 |
| recovery manifest | schema、portable installs、portable links、identity | 支持 clone/clean 后恢复 exact installs，并让外层 owner 解释 install 内 dependency link。 | 保存主机路径、移动 ref 当前值、运行期锁或要求递归恢复。 |
| worktree record | managed identity、source、base、exact path | 证明 list/close ownership。 | 替代 Git status 或保存 agent 计划。 |
| mutation plan | inspected state、planned paths、expected commit/index version | 支持 dry-run、冲突检测和部分成功报告。 | 跨 Git/filesystem/frontmatter 的总事务。 |
| diagnostic record | opaque ID、bounded internal failure context | 支持实现排障。 | 出现在正常 workflow 或泄漏 traceback。 |

具体 storage path、serialization、lock primitive 和 cleanup 算法由 Python Details 决定。
