# 约束与失败模型

本篇只定义跨工作流都成立的产品约束、失败信息和升级边界。各命令的参数、精确网络/写入
效果见 [CLI 用户接口](interfaces/cli.md)，字段和 failure code 见
[CLI JSON Schema](interfaces/cli-schema.md)，资源并发与发布次序见
[子系统及生命周期](subsystems-and-lifecycles.md)。协议强制条件只以
[`spec/overview.md`](../../../spec/overview.md) 为准。

## 1. 协议与产品边界

- validation 只依据最终可观察目录树；Git identity、管理记录、presentation 技术和 Skills
  不参与协议符合性判断。
- validation scope 只改变结论覆盖范围和返回事项；解释所选目录所需的祖先配置、导航和
  link targets 仍可读取。scoped pass 不能提升为全根 pass。
- `boundary-set` 只表达根内词法边界，`unsafe` 只表达协议严格规则例外；两者都不表示
  信任、安全、权限、所有权或维护授权。
- 手工 symlink、submodule、文件系统挂载和外部 repository 与受管 presentation 接受同样
  的可观察结构检查；未受管状态本身不是 finding。
- `.doctidex` 是协议保留目录，但协议 `v1.0.0` 不要求固定内部路径。产品扩展不得冲突，
  其中的可见内容仍受可达性、unsafe 和 link 规则约束。

## 2. 工作流选择与原生工具自由

external install/link/restore 和 worktree 约束只适用于调用方主动选择 doctidex-git 管理的
对象。CLI 和 Skills 不得把受管状态设为读取、安装、维护或符合性的前提，也不得阻止 agent
选择原生 Git、手工 worktree、submodule、symlink 或其他工具。

受管 presentation 和 worktree 必须给出普通文件系统路径。CLI 不提供专用 reader、search、
editor 或 Git diff wrapper；内部呈现失败不能被转化为“只能使用 CLI 读取”的产品限制。

## 3. 写入、覆盖与 Git 交付

- external install/link/restore 省略 apply 时只规划；只有显式 `--apply` 可以写入公开路径和
  持久受管状态。dry-run 只可使用调用期临时数据。
- 写命令不得覆盖未受管内容、不同 mapping、占用路径或并发变化。幂等重试只补齐同一
  identity 的缺失步骤，不替换其他 selector、target 或用户结果。
- CLI 只修改命令契约列出的结构化 frontmatter、精确 ignore 规则、恢复清单、受管路径、
  symlink 和运行期记录；不生成 index/log prose 或 Markdown link 正文。
- CLI 不执行 commit、push、merge、reset、clean、Git index 改写，也不删除 dirty 或归属
  不明的结果。需要这些动作时，返回公开事实并交给用户或 agent 使用原生 Git。
- `worktree close` 虽是显式移除动作，也只能删除可证明由 CLI 管理且当前 clean 的 exact
  worktree；无法证明时完整保留。
- `cache clean` 是唯一显式 shared bare object 回收入口，且默认 dry-run；close、restore、
  install、读取或失败恢复不得顺带触发。它只删除没有 valid linked worktree、且其余登记
  全部由 Git 判为 prunable 的单个 cache，不删除或修改任何 linked/root-owned path 或 record。

精确 command identity、direct/dependency、selector 隔离和 worktree 归属不变量由
[领域模型](domain-model.md)统一定义，不在本篇重复。

## 4. 宿主 Git 追踪边界

受管 install 和 CLI-created worktree 的 payload 必须由宿主 repository 中只覆盖受管路径的
root-relative ignore 规则排除，且不得已经 tracked。恢复清单与 external link symlink 必须
保持可追踪，不得被该规则或其他有效 ignore 规则排除。

CLI 可以报告 `.gitignore`、恢复清单和 symlink 的 tracked/modified/untracked 状态及冲突，
但不 stage、commit 或运行 `git rm --cached`，也不改写无关 ignore 规则。宿主 repository
无法唯一识别或追踪边界不能同时成立时，写操作 blocked，等待用户先处理 Git 状态。

恢复清单只保存 portable facts，不包含 credentials、宿主绝对路径、cache path、lock 或
临时下载状态。完整属性见[领域模型中的恢复清单](domain-model.md#7-恢复清单与恢复项)。

## 5. 逻辑只读、凭据与信任

external presentation 是受管工作流中的逻辑只读入口。实现应阻止自身写命令把它当作编辑
目标，并可以移除普通 write bits；这不是 sandbox、访问控制或恶意内容隔离。用户、其他
进程或高权限工具仍可能改变物理文件，后续 operation 必须重新观察当前事实。

URL credentials 只存在于调用期。结果、records、diagnostics 和普通日志不得保存 userinfo、
token 或 credential-bearing remote；失败消息只使用 sanitized source 和公开 path。

safe/unsafe、managed/unmanaged、read-only/writable 都不能推导来源可信、内容无害或用户已
授权维护。

install 快照中由 portable manifest 描述的 external symlink 可以因 dependency 尚未在当前
owner root 展开而成为 broken symlink。对 link-parse 而言，这是正常
`dependency_not_installed`，不是 damage；命令只返回外层依赖 facts，不在只读 install 内
restore 或改写 link。该产品状态不改变 validation 对最终可观察目录树的协议判断。

## 6. 网络与确定性

命令在调用前必须能由公开契约判断是否可能联网；结果必须报告实际 network effect。只读
本地事实的命令不因“检查更新”而隐式 fetch。install 一旦建立便固定 commit，restore 只取
清单中的 exact commit，任何重复读取都不得因 moving ref 改变既有内容。

网络失败不能破坏已存在的 presentation、objects 或 worktree。需要 network、credentials
或 repository permission 时，失败结果明确 `requires_user`，不能把 authentication failure
伪装成 revision missing。cache clean 始终离线，不能为判断存活性访问 remote。逐命令网络
矩阵由 [CLI 用户接口](interfaces/cli.md#14-读写与网络矩阵)
负责。

CLI 保持确定性且不配置或调用 AI。相同参数、目录树、受管记录和允许观察的 Git state
产生相同排序与领域事实；远端本身可变化的操作必须在结果中固定实际 resolved commit。
内容相关性、语义正文、unsafe 范围是否合适、diff 质量和交付决定属于 human 或 agent。

## 7. 有界输出

任何可能返回集合的命令都必须默认有界。完整 limit、最大值、列表预算和 cursor identity
由 [CLI](interfaces/cli.md) 与 [JSON Schema](interfaces/cli-schema.md#3-集合与分页)定义；
本篇只规定以下跨命令不变量：

- 先对完整领域结果应用 scope/filter，再计算 total 和分页，不能先截断再过滤；
- human 与 JSON 使用同一预算，截断必须公开 total、returned、truncated 和 continuation；
- continuation 保持确定性顺序，无法延续同一状态时返回 cursor invalid；
- summary 只使用 counts、state、severity、code 和 path grouping，不生成内容语义摘要；
- 单结果命令不接受无效果的 pagination option。

## 8. 失败结果必须回答的问题

每个 blocked 或 partial result 必须让调用方回答：

1. 哪个 operation 没有完成？
2. 哪个 root、source、path、revision、install parent 或 worktree 受影响？
3. 哪些结果已经完成并仍可使用？
4. 最小安全恢复或重试动作是什么？
5. 是否需要用户提供输入、权限、凭据或 Git 决定？

缺少任何一项时，失败契约不完整。公共 envelope、Finding、`requires_user` 和稳定 code 的
精确结构由 [CLI JSON Schema](interfaces/cli-schema.md) 定义。

## 9. 失败分类与下一步

| 类别 | 典型问题 | 保留与下一步 | 是否通常需要用户 |
|---|---|---|---|
| 语法与输入 | selector 互斥、非法 root/path/scope/install ID | 不写入；修正参数后重试。 | 否。 |
| Root 上下文 | not found、ambiguous、mismatch | 不猜测；传 exact root。 | 候选无法判断时是。 |
| 协议结构 | frontmatter、连续性、可达性、link 注释 | 保留 validation 结果；修复后重跑。 | 语义取舍可能是。 |
| Source 与 revision | network、credentials、default branch、ref/object | 保留既有结果；恢复访问或显式选择 revision。 | 通常是。 |
| Dependency | parent 无效、dependency-only 不能 durable link | 修正 parent，或先提升为 direct。 | 通常否。 |
| Target 与 mapping | occupied、overlap、owner install missing、mapping damaged | 主仓库缺失 install 时 restore；portable dependency 未展开不是失败；真实损坏才修复 mapping。 | 破坏性处理时是。 |
| 宿主 Git | repository 不明确、payload tracked、ignore 冲突 | 不改 Git index；用户处理后重试。 | 通常是。 |
| 恢复 | manifest 无效、exact commit 不可得、原路径冲突 | 保留其他项；恢复清单、source 或处理占用。 | 可能是。 |
| Worktree | changed、unavailable、unmanaged close | 完整保留现场；用原生 Git 审阅。 | Git 交付决定是。 |
| Shared cache 清理 | source cache 不存在、有效 worktree、metadata 损坏/无法分类、复查冲突 | 有效 worktree 返回 preserved；其余失败完整保留，修正 URL、修复 Git metadata 或并发结束后重新 dry-run。 | 通常否；metadata 修复可能需要 operator。 |
| 并发或中断 | plan 过期、operation cancelled | 返回已完成效果；重新观察后有限重试。 | 通常否。 |
| 未预期失败 | 未分类实现异常 | 保存 diagnostic ID；安全重试一次。 | 重复时是。 |

## 10. 部分成功、并发与取消

external apply、restore batch 和跨根维护都不是总事务。顶层 blocked 或 warning 不撤销独立
成功项；result 必须说明 changed、affected、preserved state 和 next actions。重试复用已
完成的 fixed commit、mapping、manifest 或 worktree，只补齐缺失步骤。

同一 source、install identity 和 root 的冲突 mutation 必须协调，独立 source/root 可以
并发；具体串行边界和资源获取顺序以[生命周期中的并发设计](subsystems-and-lifecycles.md#10-并发)
为准。调用者中断后不再启动新步骤，已发布效果保留并进入结果；归属无法证明的 artifact
不得自动 cleanup。

## 11. 人工升级边界

以下事项不能仅靠技术推断继续：credentials 或 network authorization、多个 root/revision/
target 都合理、未受管内容需要覆盖、dirty worktree 的 commit/reset/delete、跨 repository
交付目标，以及 unexpected failure 重复。

升级只呈现用户做决定需要的公开事实和可选动作，不暴露内部 state、object-store 布局、
lock、traceback 或实现调试步骤。
