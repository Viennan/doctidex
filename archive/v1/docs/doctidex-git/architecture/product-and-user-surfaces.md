# 产品与用户表面（user surface）

doctidex-git 是 Git 管理的 doctidex tree 的辅助产品。它让 human、agent 和 program 在普通
file/Git 工具不能可靠取得的 doctidex/Git 交叉事实处获得确定性结果；它不替代阅读、搜索、
编辑、diff、commit、push、merge 或用户的权限决定。

本页拥有产品问题、共同 user surface、逻辑责任和非目标。各持久状态和 workflow 的细节由
[树与 validation](tree-and-validation.md)、[external snapshot 与 presentation](external-snapshots-and-presentations.md)、
[worktree 与 cache](worktrees-and-cache.md) 和 [operation safety](operation-safety-and-recovery.md) 定义。

## 1. 使用者与稳定边界

| 使用者 | 入口 | 稳定承诺 | 不应依赖 |
|---|---|---|---|
| Human | CLI human output、原生 file/Git | 可观察路径、状态、failure 和下一步。 | Python module、cache/runtime file 的私自修改。 |
| Agent | Overview + Mentions/Read/Maintenance Skill、CLI `--json`、原生工具 | 足够的任务路由、确定性事实、保留原生工具选择。 | repository Architecture、Impls、source 或 tests。 |
| Program | CLI `--json` subprocess | versioned envelope、operation schema、stable code、bounded collection。 | human output、private import、current storage layout。 |
| Variant maintainer | Architecture + 对应 Impls | 共同 contract、接手/compatibility boundary、realization evidence。 | 以另一 variant 的 source 推断未定义的产品语义。 |

Python import、registry、filesystem API、Git object store、lock、cache naming 和 shell launcher 不是
program API。它们只有在工作现场交接需要识别时才以本 Architecture 定义的语义出现，具体
realization 仍属于 Impls。

## 2. 三类根与状态归属

一个场景至少可能涉及下列边界，三者不能互相推导：

| 概念 | identity / owner | 用户可观察作用 |
|---|---|---|
| doctidex root | 协议解释的 root `index.md` | `/` 的路径意义、responsible index、validation scope。 |
| owner root | 一个 selected doctidex root | 受管 external install、manifest/runtime、worktree 的产品 ownership。 |
| content root | install 或 presentation 内被读取的 doctidex root | portable mapping、link-parse 与 dependency relation。 |
| host Git repository | 包含或关联 owner root 的 Git working tree | `.gitignore`、trackability、host hook 与 Git delivery。 |
| user cache | 不属于任一 owner root、可由用户为进程选定的本机 namespace | shared source objects、diagnostic 与可选 cleanup。 |

owner root 只在调用 external/worktree/hook surface 后存在相应受管状态。普通 doctidex 阅读、
native Git、手工 worktree、submodule 或第三方 symlink 不因其存在而成为 doctidex-git state。

## 3. 能力与用户问题

| 场景 | 入口 | 输入与默认 | 可观察结果 / 下一决策 |
|---|---|---|---|
| 阅读树 | Read Skill + 原生工具 | 一个 doctidex root 或路径。 | 文件不变；按 root、boundary、unsafe 和 link 继续读取。 |
| 验证根或 scope | `validate ROOT [--scope PATH]...` | 省略 scope 为完整 root；重复 scope 合并。 | coverage、findings、semantic candidates；scoped pass 不等于全根 pass。 |
| 安装或更新 external snapshot | `external install SOURCE [REVISION]` | 默认 dry-run；省略 revision 记录 default provenance，实际读取固定 commit。调用本次 selector 建立或更新 snapshot，不是 manifest recovery。 | install ID/path、manifest/runtime/ignore 的计划或变更；审阅后才 `--apply`。 |
| 展开 dependency | `external install SOURCE REVISION --dependency-of ID` | parent 必须是当前 complete install。 | 扁平 dependency edge；需要 durable restore/link 时再提升为 direct。 |
| 解析 repository 提及 | Mentions Skill -> `external list [FILTER]` | 只读 selected owner root；可用 repository path、host、固定 revision 与 role 收窄。 | 可读 InstallReference 候选和分页事实；agent 结合上下文消歧后才把 exact ID 交给其他命令。 |
| 建立 presentation | `external link SOURCE_DIR TARGET` | TARGET 是 user 选择且须可 track。 | relative symlink、safe/index declaration、durable mapping；Git 审阅随后由原生工具完成。 |
| 替换或解除 presentation | `external rebind SOURCE_DIR TARGET` / `external unlink TARGET` | rebind 选择已审阅的新 direct snapshot；unlink 只接受 exact managed target。 | 同 path 切换到新 snapshot，或在 reference-free 时移除一个 presentation；不改变 install lifecycle。 |
| 恢复 direct install | `external restore [ID...]` | 默认 dry-run；只依当前 manifest exact commit/path。 | `planned`、`restored`、`unchanged` 或 `blocked`；不刷新 moving ref、改写 manifest 或改写 link。 |
| 解析 external-link 提及 | Mentions Skill -> `external link-parse PATH` | PATH 可以在 owner 或 installed content 中；不完整 spelling 先由任务上下文补全为唯一实际 path。 | current/portable mapping 与 target state；据此继续读取、restore、安装 dependency 或诊断。 |
| 协调 checkout snapshot | `hook --install` 后 Git `post-checkout` | 用户明确安装一次；run 是离线。 | existing payload 对齐、hidden/preserved/blocked item；不 materialize missing direct install。 |
| 移除 install | `external remove INSTALL_ID` | 默认 dry-run；只接受 exact ID。 | reference-free 才移除；reference 或 hidden state 时保留现场和 evidence。 |
| 隔离维护 | `worktree open/list/close` | 当前 working tree 优先原生维护；open 仅在需要隔离时。 | owner 内 writable worktree；changed/unavailable 一律保留并要求决定。 |
| 回收 shared cache | `cache clean --url URL` / `--auto` | 默认 dry-run；不是 Skill 路由。 | planned/removed/preserved/blocked；不改变 root state。 |

精确 argv、互斥参数、JSON fields 和 stable codes 分别由 [CLI](interfaces/cli.md) 与
[JSON schema](interfaces/cli-schema.md) 负责。上表不把 command syntax 变成第二 authority。

## 4. 共同模型与依赖方向

```text
doctidex tree/configuration      Git source/revision
            \                    /
             \                  /
           root / host ownership
                    |
       external snapshot + presentation ---- checkout hook
                    |
             worktree / cache
                    |
          operation result / recovery
                    |
          CLI, JSON, Published Skills
```

- tree/configuration 不依赖 Git；Git source/revision 不解释 doctidex protocol。
- root/host ownership 组合这两个边界，但不把 Git identity 变成 protocol fact。
- external、hook、worktree/cache 只消费共同模型；接口和 Skill 不创建第二套 state semantics。
- Impls 能增加 private component，却不得把共同 state/behavior 重新定义为 language-specific。

逻辑职责按下表协作，而不是按当前语言 module 划分：

| Logical responsibility | consumes | owns / produces | 禁止反向依赖 |
|---|---|---|---|
| Tree observer | root、`index.md`、Markdown links。 | protocol observation、validation finding、responsible-index fact。 | 不读取 Git source/runtime 以判定 protocol。 |
| Root/host resolver | filesystem/Git context、selected input。 | root、owner/content/host relation。 | 不从 managed record 伪造 root。 |
| Source resolver | public locator、revision request。 | sanitized source fact、selector、exact commit、source availability。 | 不定义 presentation 或 user permission。 |
| External coordinator | root/host/source/install records。 | install、manifest/runtime、link、managed-install discovery、restore/remove/link-parse outcome。 | 不把 cache/lock mechanics 变成 product state。 |
| Hook coordinator | registration、manifest/runtime、existing payload。 | offline alignment/hidden/preserved item result。 | 不重建 missing direct payload 或改写 manifest commit。 |
| Worktree/cache coordinator | source relation、runtime worktree record、Git registration。 | writable lifecycle 或 explicit cache-clean result。 | 不因 one root 回收 shared cache。 |
| Result boundary | domain outcome/finding。 | human/JSON observable result、pagination、next action。 | 不凭 renderer/Skill 创造领域事实。 |

## 5. 可观察结果、授权与非目标

所有 mutation 以独立 dry-run/apply 表达：dry-run 不保留写入授权或状态 reservation；apply 会
重新验证 root、target、manifest、Git tracking、reference 与 concurrency condition。`requires_user`
非空时调用方停止自动重试。部分成功、interruption 和 preserved state 的读取方式见
[operation safety](operation-safety-and-recovery.md)。

doctidex-git 不：

- 生成语义正文、label 或内容摘要；
- 把 managed state 变成 trust、permission、protocol compliance 或 Git delivery 授权；
- 自动跟随 moving branch、自动创建 delivery branch、丢弃 dirty changes 或进行跨 repository transaction；
- 用 checkout hook 重建缺失 direct payload、覆盖 foreign hook 或为 metadata 对齐改写 manifest fixed commit；
- 由 install/restore/close/普通读取隐式回收 source cache；
- 强制 agent 使用受管 external/worktree 而排除 native 或第三方工作流。

<a id="6-release-and-cache-configuration"></a>
## 6. 发布身份、安装与用户 cache 配置

doctidex 协议、`doctidex-git` 产品和其 distribution 各自拥有完整的语义版本。它们的 major 必须一致；minor
与 patch 独立演进，不能因三者当前恰好相同而建立完整版本绑定。协议版本由 `spec/overview.md` 的 `vX.Y.Z`
标识，产品版本由已安装 plugin metadata 标识，distribution 版本由其 variant package metadata 标识。

每个产品 release 以用户创建和确认的 Git tag `v<doctidex-git-version>` 固定 source revision；agent 可以建议
版本，但不能自行创建 tag 或发布。README 是参数化安装入口：用户提供 target `doctidex-git` version 后，调用方以
该值选择 `vX.Y.Z` tag，不能改用默认 branch、猜测 tag 或从 distribution version 推导 target。该 tag 同时定位 Python
distribution 和 Published agent bundle；具体 Git URL、package identity、subdirectory、checkout 路径与安装命令由相应
Impls 负责。

Published agent bundle 是已安装产品的离线工作流入口。四个 `skills/*/SKILL.md` 是其可移植核心：host 可以使用自己的
plugin/skill 注册机制导入整个 `skills/` 目录，或在没有该机制时直接读取与任务相关的 Skill。`.codex-plugin` 和
`agents/openai.yaml` 是 Codex 的可选包装 metadata，不能成为其他 agent 使用 bundle 的前提，也不定义通用 host command
或安装位置。Skill 正文只说明产品使用场景和相应操作；唯一例外是 Overview 中受限的 GitHub distribution bootstrap，
它必须明确当前 Skill/product metadata 与协议版本、匹配的 tag、GitHub URL 和 package 子目录，并说明命令在已选兼容
`.venv` 中执行。该段是已安装产品的版本化分发入口，不是 repository
development setup，也不得扩展为 editable install、发布、tag 确认、测试或维护验证教程。README 提供同一 tag 的 Python
package 与 bundle 获取入口；Architecture、Impls、Requirement 和后置验证负责版本关系、release identity 与安装可用性。

`DOCTIDEX_GIT_CACHE` 是可选的 user configuration。非空值选择当前进程的 shared user-cache root；未设置时
variant 使用其平台默认值。一个需共享 cache 的 CLI、automation 或 host hook 进程必须继承同一用户设置，产品不保存、
同步或猜测该值。用户决定是否配置及其可写路径；agent 可以解释这项配置，却不得写 shell profile、project
configuration 或其他持久环境设置。该配置不公开 cache 内部 layout，也不改变 `cache clean` 仅由 human/program
operator 显式调用的边界。
