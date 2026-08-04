# 需求 0019：就近 external link 映射与受管重绑定

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0019` |
| 状态 | `approved` |
| 日期 | 2026-08-04 |
| 来源 | 用户确认暂不引入更复杂的 external install 更新机制，并提出以就近、按需的 `external link` 组织外部内容：文档只引用 presentation path；当新 snapshot 的相关目录结构兼容时，重建同名 link 即可让既有文档引用继续成立，避免大范围 Markdown link 重写。 |
| 影响范围 | doctidex-git Architecture、CLI/JSON contract、portable manifest/runtime link record、Python external realization 与测试、Published Maintenance/Read Skills，以及 Requirements navigation。 |
| 协议关系 | doctidex-git 产品工作流；不改变 [doctidex 协议](../../spec/overview.md)。 |

## 1. 已核对的现状与意图

当前 `external link` 已允许从 complete direct install 或既有 presentation 内任一可读目录，向 owner root
中用户选择的非占用 `TARGET_PATH` 创建相对 symlink。它为 target 维护 mapping 和必要的 boundary/unsafe
frontmatter，但不编写 Markdown navigation prose 或其中的 doctidex annotation。因此 agent 已可将外部内容
按需映射到使用它的文档范围附近，再让文章只引用这个 root 内 presentation path，而不暴露
`/.doctidex/git/installs/<id>/`。

这种组织方式把文档对外部 repository 的依赖收敛到少量 local presentation path。若以后为相同 source 的
新 selector 创建新的 immutable install，而相关目录结构和所需文件路径仍兼容，文章的 Markdown link 可以
保持不变；只需把该 presentation path 改为指向新 install 的对应目录。

不过当前产品不提供这个重绑定步骤。`external link` 对已存在的不同 mapping 返回 `target_occupied`，不 replace、
删除或移动旧 symlink；`external remove` 只删除没有任何 durable mapping/reference 的 install，并明确不改写
presentation。因此“先删除同名 external link，再创建新 external link”目前只能靠直接编辑 symlink、manifest、
runtime 和 index configuration，不能作为 agent 自动推导的受管工作流。

本需求的目标不是为 install 建立 mutable identity，也不是自动追踪 moving ref。它是在仍保持每个 install
为 fixed snapshot 的前提下，为受管 local presentation 定义安全、可审阅的 unlink/rebind lifecycle，使
agent 能用现有的“新 install + 就近 presentation”实践完成内容迁移。

## 2. 待设计的工作流与边界

agent 在计划引用外部内容时，应只在实际需要该内容的文档范围附近创建 `external link`，并在文章中使用该
presentation 的 root 内路径。它仍须以 native editing 维护导航 prose、Markdown link 和适用的
`cross-boundary-point` / `unsafe` annotation；`external link` 继续只负责受管 symlink、mapping 和 index
configuration。

受管 link lifecycle 确认同时提供两个独立操作：

1. `rebind` 明确替换一个既有 presentation target 的 mapping。用户选择新 source/selector/commit 且确认内容
   结构兼容后，agent 先创建并审阅新 fixed install，再以同一 target 重绑定到其对应的
   repository-relative path。该操作必须作为一个受审阅的整体切换，不出现临时 broken presentation；成功结果
   保留原 target path，使文档链接无需改写。
2. `unlink` 明确删除一个 external link。它移除该 presentation，而不是替换为另一个 source；后续如需再次
   呈现内容，调用者以既有或新的 install 重新执行 `external link`。它不是 install remove，也不隐式删除
   payload、source cache 或其它 presentation。

新 target 不兼容、source/revision 不可用、mapping/symlink/index 状态损坏、权限不足、并发变化或用户未确认时，
`rebind` 必须保持旧 presentation 可读且可诊断。`unlink` 是独立的删除请求，须有自己的 dry-run/apply、
reference、恢复和用户授权契约。它发现仍指向 target 的 safe Markdown navigation link 或其它受管 reference
时，必须返回可定位 evidence 并 blocked；agent 先改写或移除这些引用后才能重试，不能在 `--apply` 下留下
broken link。

受管解绑或重绑定必须同时处理 symlink、portable manifest link record、runtime link record 和该 target 的
boundary/unsafe configuration。它不得自动改写文章内容、Markdown navigation、无关 frontmatter、Git index 或
旧 install payload。旧 install 只有在其余 mapping/reference 已解除且用户另行授权删除时，才可交由既有
`external remove` 生命周期处理。

## 3. 实施影响

获得实施授权且问题解决后，先使用 Architecture authoring workflow 定义 local presentation、`unlink`、
atomic `rebind`、target identity、source-to-target mapping、frontmatter ownership、reference/preflight policy、
partial failure、recoverability 与 JSON result contract。随后使用 Impls workflow 定义 Python 的 record mutation、
symlink publication、configuration cleanup/reuse、locking 和 diagnostic evidence。

CLI/JSON 需要提供以 owner-root-relative presentation target 为中心的 `unlink` 与 `rebind`，而不是要求
human/agent 用 opaque `install_id` 处理 link 生命周期。Published Maintenance Skill 应先引导 agent 按需就近
映射，再说明新 snapshot 迁移的 dry-run、用户决定、content-structure review、文章不变条件和旧 install 的
独立清理边界；Read Skill 的 `link-parse` 结果应足以支持该决策。

实现与测试须覆盖：从 install/link 内子目录映射、同 target/same mapping 幂等、target rebind 到不同 selector
或 source、新旧 symlink target/path、manifest/runtime/index frontmatter 同步、source-relative suffix 兼容与不兼容、
safe/unsafe presentation、safe Markdown 与其它受管 reference 阻止 unlink 的 evidence、损坏/占用/并发/中断、旧
install reference protection，以及 rebind 后文章链接不变但读取新内容的完整 fixture。

## 4. 验收标准

1. Published Skills 说明 agent 可将 complete direct install 的所需目录按需映射到相近的 root 内 presentation，并在文章中引用 presentation path，而非 private install path。
2. 产品提供并定义以 presentation target 为输入的受管 `unlink` 与 atomic `rebind`；二者的 dry-run/apply、结果、failure、恢复和用户授权边界明确，agent 不需要手工修改 manifest/runtime 来删除或更换 mapping。
3. `rebind` 对新 fixed install 成功替换同一 target 后，presentation 的 root 内路径保持不变；结构兼容的既有 Markdown links 无需改写，读取内容来自新 install，过程中没有可观察的临时 broken presentation。
4. `unlink` 只删除精确 target 的 external presentation 及其受管 mapping/configuration，不删除 install payload、source cache 或其它 presentation；safe Markdown navigation link 或其它受管 reference 仍指向 target 时返回可定位 evidence 并 blocked，必须先改写引用；删除后的后续呈现仍使用 `external link`。
5. 操作一致更新或移除 symlink、portable/runtime mapping 和必要的 index configuration；不代写文章、navigation prose、Markdown annotation、Git index 或无关状态。
6. 任何 blocked、failed 或 interrupted 结果保留旧的可读 presentation，或明确报告可观察的实际 partial state；不会留下无法解释的 symlink/record/frontmatter 不一致。
7. 旧 install 继续受现有 reference protection；只有所有 mapping/reference 已解除且用户明确授权时，才能由 `external remove` 删除。
8. Architecture、Impls、CLI/JSON、Python implementation、tests 和 Published Skills 对这条工作流保持一致，并以真实 fixture 验证兼容结构下的文章 link 无需重写。

## 5. 进展与依赖

本记录依赖已批准 [DX-REQ-0008](0008-doctidex-git-v1-0-0-alignment/overview.md) 的 fixed install、durable link
与 restore 模型，并细化已批准 [DX-REQ-0012](0012-doctidex-git-external-remove.md) 的 reference-protected
install removal。二者均为 `approved` 历史，尚未获得修改其内容以添加 reciprocal link 的授权；本 Requirement
暂保留单向关系。

已核对 current CLI、Published Maintenance Skill、Python `ExternalService` 和 tests：就近 link mapping 已是
现有能力，`external link` 对不同 mapping 不 replace，且不存在受管 link removal/rebinding command。用户已确认
同时提供 `unlink`（删除）与 `rebind`（替换），并确认 `unlink` 对 remaining safe Markdown/managed reference
返回 evidence 后 blocked。用户现已明确授权实施：先更新 Architecture，再更新 Python Impls，随后对齐 CLI/JSON、
Python implementation、tests 和 Published Skills。

已完成实施：Architecture 定义了 target identity、atomic rebind、unlink reference preflight、legacy mapping
preservation 与 frontmatter ownership；Python variant 增加 `external rebind`、`external unlink`、runtime/manifest
同步、sibling symlink publication、safe Markdown/filesystem/overlap managed-record evidence，以及新 record 的
`frontmatter_ownership`。旧 record 缺少该 optional field 时，unlink 保留无法证明归属的 index declaration。Published
Overview/Maintenance/external reference 已给出“就近 link、新 fixed install、dry-run rebind、内容兼容判断、引用阻断
unlink、旧 install 独立 remove”的工作流；Read 的既有 `link-parse` fixed source/commit/path facts 可支持这一路由。

验证证据：`2026-08-04` 运行 `.venv/bin/python -m pytest impls/libs/python/tests`（`47 passed`）、
`.venv/bin/python -m ruff check impls/libs/python`、`git diff --check`，以及
`.venv/bin/doctidex-git validate . --scope /docs/doctidex-git --json` 和
`.venv/bin/doctidex-git validate . --scope /docs/requirements --json`，均通过。独立 fresh agent 只读取已发布
Skill，并在隔离 Git fixture `/tmp/doctidex-git-forward-lifecycle-file-url-Vrxybm` 完成 v1 install/link、v2 same-target
rebind、link-parse fixed-commit 确认、Markdown `presentation_referenced` blocked 和 reference-free unlink；最终 target
及两种 link record 消失，v1/v2 install payload 均保留。该受限演练显式设置隔离 `DOCTIDEX_GIT_CACHE`，因为 sandbox
默认 user cache 不可写；这不是本 Requirement 的 product workflow 或 Published Skill 信息边界变更。

用户已明确认可当前实现；本记录现为 `approved`，可进入 PR/MR。
