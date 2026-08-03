# 需求 0014：增加 doctidex-git checkout Git hook 命令

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0014` |
| 状态 | `approved` |
| 日期 | 2026-08-03 |
| 来源 | 用户要求提供 Git hook 命令，解决执行 `git checkout` 后 install repositories 可能出现的状态不一致问题；用户随后确认 hook 安装、direct/dependency 对齐与 hidden dependency 的处理策略，并补充每次 hook 都必须重新确定所有 hidden state，以及 revision 对齐须尽力同步 metadata 中的 branch 等状态。 |
| 影响范围 | doctidex-git hook CLI/JSON contract、Git `post-checkout` hook、external install/restore/remove workflow、runtime schema、Architecture、Python Impls、Python implementation、tests 与 Published Skills。 |
| 协议关系 | 拟议的 doctidex-git 产品能力；当前不改变 [doctidex 协议](../../spec/overview.md)。 |

## 1. 已记录意图

当前 direct external install 的 portable manifest 随 host Git 版本化，而 install payload 与 runtime state
位于被 Git ignore 的受管 namespace。执行 `git checkout` 后，版本化 manifest 可能切换到另一份
install 声明，而本地 install repositories 仍保留 checkout 前的 payload 或 runtime state。因此需要
一个由 Git hook 调用的 doctidex-git 命令，在 checkout 后将仍受当前版本化声明管理的 install
repositories 与 manifest 要求的完整 revision state 对齐。

当前 `external install` 对不同或受损 stable install path 拒绝操作；`external restore` 对同路径、
不同 revision 的 payload 同样保留现场并报告 blocked。runtime schema 也只接受
`managed_state: complete` 与由 install ID 导出的固定 install path。因此本 Requirement 是新增的
checkout reconciliation 与 dependency hidden-state capability，不是既有 install/restore 行为的文字澄清。

已核对的 current-artifact authority：

- [external CLI interface](../doctidex-git/architecture/interfaces/cli.md)；
- [external installation and mapping model](../doctidex-git/architecture/external-snapshots-and-presentations.md)；
- [external workflows](../doctidex-git/architecture/external-snapshots-and-presentations.md)；
- [Python external realization](../doctidex-git/impls/python/components/external-presentation-and-mapping.md)；
- [`ExternalService`](../../impls/libs/python/whero/doctidex/git/external.py)；
- [Published Skill system](../doctidex-git/architecture/skill-system.md)。

## 2. 已确认的 hook 命令与触发

新增 `doctidex-git hook` command family。其 `--install` mode 在当前 Git repository 安装用于
checkout 后协调的 Git `post-checkout` hook；重复执行必须幂等，不得产生额外副作用。该 hook 由
Git 在 checkout 后自动调用，不要求 agent 或用户在每次 checkout 后另行运行 install、restore 或
其他等价的对齐操作。

`--install` 仅管理当前 repository 的 hook 配置；它不 stage、commit、push、merge、reset 或改写
无关的 host Git 内容。已有非 doctidex-git `post-checkout` hook 的保留、组合或冲突结果，及 hook
执行 entrypoint 的精确 invocation，由 Architecture 定义；在未定义前不得静默覆盖用户 hook。

hook 处理遇到真实错误时必须报告并保留可诊断现场；下列明确列为合法非错误状态：

1. 当前 manifest 未声明的已安装 direct install；
2. 当前 manifest 声明但尚未安装的 direct install；
3. 未处于 `hidden` 状态、且无法沿 dependency parent edge 找到 direct ancestor 的 dependency
   install；
4. 未处于 `hidden` 状态、且找到的 direct ancestor 未能按当前 checkout 的 manifest 完成对齐的
   dependency install。

上述 dependency 状态不报错不表示可以跳过 hidden record。所有 hidden dependency install 无论是否
能找到已对齐的 direct ancestor，都必须在每次 hook 中参与状态重新判定。

## 3. Checkout 后 direct install 对齐

hook 只以 checkout 后 owner root 的 versioned portable manifest 为 direct install 的权威声明。对同时
满足“当前 manifest 有 portable entry”与“对应 payload 已安装”的 direct install，revision 对齐分为两层：

1. `resolved_commit` 是硬约束：payload 的 detached Git `HEAD` 必须与 manifest entry 的 exact commit
   相同，否则该 install 未对齐。
2. revision metadata 是尽力约束：runtime 必须尽力与 manifest entry 的
   `revision_selector`、`default_branch` 及当前 schema 所定义的其他 revision provenance/state 对齐。
   commit 已相同但这类 metadata 仍不一致时，不得宣称该 install 已完全对齐；hook 必须完成安全可行的
   同步，或在 result 中明确报告未能对齐的字段和保留原因。

branch/tag/default branch metadata 的对齐不允许重新解析 moving ref 以替代 manifest 的
`resolved_commit`。payload 是否始终 detached、是否还需表达 Git symbolic branch 等工作树状态，及每项
metadata 的 best-effort 成功、warning 或 blocked contract，由 Architecture 定义；任何实现都不得为了
对齐 metadata 改变已确定的 commit。

hook 不创建、恢复或删除未安装的 direct install，也不处理当前 manifest 没有记录的已安装 direct
install。这两类情况是 checkout 导致的合法本地残留或缺失，不是错误。所有 payload 切换都使用当前
manifest 记录的 exact `resolved_commit`。不能安全完成 commit 或 metadata 对齐的 dirty、损坏、冲突或
Git failure 必须报告并保留现场，不能丢弃本地更改来伪造对齐成功。

## 4. Dependency 森林与 hidden 状态

dependency install 使用 runtime `parents` edge 表示外层 owner root 中的引入关系。hook 对每个 dependency
runtime record，包括已迁移到 hidden location 的 node，沿 parent edge 向 ancestor 扫描，寻找已按第 3 节
完成对齐的 direct install。没有这种 direct ancestor，或 ancestor 未对齐时，未隐藏 dependency
component 可忽略而非报错。能找到 direct ancestor 的节点，以这些 direct install 为根形成本次 checkout
处理的 dependency forest；遍历必须对现有的 shared parent、self-reference 与 cycle 保持有界，不能无限
递归或从 install path 猜测关系。

每次 hook 必须重新确定所有 hidden node 的状态，不能因其上一轮的 hidden 标记、hidden location 或
ancestor 不可用而跳过它。无法重新连接到已对齐 direct ancestor 的 hidden node 明确保持 hidden；重新
进入可处理 forest 后，按本节的 manifest metadata 规则判断该 node 是解除 hidden 还是再次保持/进入
hidden。这样，每次 hook 的结果都对每个 hidden node 给出本轮重新确定的状态，而非沿用未检查的旧值。

每个 forest node 在自身已对齐的 worktree 中观察它是否为 doctidex root、是否有合法 manifest，以及
该 manifest 是否包含相应 child repository 的 metadata：

1. 条件都满足时，hook 按 child metadata 执行与第 3 节相同的 revision 对齐：以其 exact commit
   切换 dependency child worktree，并尽力同步 branch 等 revision metadata；随后递归处理 child 的
   descendants。
2. 任一条件不满足时，child dependency install 及其所有 descendants 在本轮判定为 `hidden`。hidden
   解决该工作树没有可用 manifest metadata、因而无法安全确定其应有 revision 的情形；它不是 error，
   也不从未声明的内容推导 revision。

hidden 只适用于 dependency install，并具有以下效果：

1. hidden node 及其 descendants 不作为当前 checkout 的可用 dependency payload；其 install directory
   必须迁移到不再能被 normal install path 或 symlink 意外命中的受管 hidden location，具体命名和
   atomic publication 由 Impls 定义。
2. `external remove` 选择 hidden dependency install 时必须 no-op：不物理删除 payload、不删除 runtime
   state 或 parent edge，也不改写 manifest、link、cache 或 host Git 内容。公开 result 必须明确说明
   保留原因。
3. 当 hook 在当前 checkout 中依据有效 metadata 重新 install 一个 hidden node 时，解除该 node 的 hidden
   状态并恢复其 normal managed location；不递归解除 descendants 的 hidden 状态。未被解除的 descendants
   仍须在同一次及后续每次 hook 中重新判定，不能因其 hidden 状态被忽略。

## 5. 安全边界与待定义契约

1. 只处理拥有可证明 owner root、runtime record、manifest entry 或 dependency parent edge 的 managed
   identity；不得从任意 ignored directory、path name 或 shared source cache 推断 ownership。
2. direct/dependency commit switch、revision metadata 同步、hidden-path 迁移和 runtime 更新必须在已定义
   的 mutation boundary 内重查。并发变化、中断与部分成功不得伪装成完成，必须保留可诊断的实际状态。
3. hook 不修改 manifest、durable symlink、Markdown、frontmatter、`.gitignore` 或 Git index，除非后续
   Architecture 对某项必要 effect 另作明确授权；它尤其不得为 hidden node 把旧 symlink 改指向其他
   revision。
4. hook 的 network policy、JSON/human result schema、commit/metadata 对齐的逐字段 outcome、exit status、
   跨 platform hook installation、existing-hook composition、item-level error continuation 与 `hidden`
   record serialization，均须先由 Architecture 规定，再由 Python Impls 实现。
5. 不修改 doctidex protocol；该能力只扩展产品的 Git workflow 与受管 runtime state。

## 6. 实施影响

授权实施前，须按以下顺序更新并保持一致：

1. doctidex-git Architecture：hook CLI、`post-checkout` lifecycle、direct/dependency 的 commit 与 revision
   metadata reconciliation、dependency forest、hidden state、remove no-op、concurrency/recovery 与公共结果。
2. Python Impls：hook script placement/composition、runtime schema migration、hidden payload location、
   Git linked-worktree mutation、locking、failure recovery、platform limits 与测试证据。
3. Python CLI、storage 与 `ExternalService` implementation，以及覆盖 checkout state transitions、commit
   alignment、branch/default provenance 等 metadata alignment、dependency forest、每次执行的 hidden
   re-evaluation、hidden/unhide、remove no-op、cycle/shared-parent、hook idempotence 和 errors 的 tests。
4. Published `doctidex-git-overview` Skill：简要说明已安装 hook 自动处理 checkout 后的 dependency
   state alignment，agent 无需采取同类手动动作；不得把内部 runtime、hidden path 或 lock 细节带入
   Published Skill。其余 Published Skill 是否需要调整，由对应 Architecture contract 决定。

## 7. 验收标准

1. `doctidex-git hook --install` 能在当前 repository 幂等安装 `post-checkout` hook；hook 的配置、
   invocation、existing-hook 处理、结果与失败契约由 Architecture 明确，且不会执行 Git delivery。
2. checkout 后，当前 manifest 中已安装的 direct install 的 `HEAD` 与 `resolved_commit` 一致，且其
   `revision_selector`、`default_branch` 和其他适用 revision metadata 已尽力与 runtime 对齐；不能安全
   对齐的 metadata 被逐字段报告，不能以 commit 一致冒充完全成功。当前 manifest 未声明或尚未安装的
   direct install 保持忽略且不报错。
3. hook 从完成 revision 对齐的 direct install 处理可达 dependency forest。manifest metadata 足够时按
   metadata 对 child 执行 commit 与 metadata 对齐并递归；metadata 缺失、当前 worktree 不是 doctidex
   root 或没有合法 manifest 时，按本记录进入 hidden 而不是猜测 revision 或报错。
4. 每次 hook 都重新判定每个 hidden dependency install 及其 descendants，不得把 hidden record 当作
   忽略对象；结果明确表明该 node 本轮保持 hidden 或被解除。hidden remove 是可审计 no-op；有效
   metadata 重新 install 时只解除目标 node 的 hidden，不递归改变 descendants。
5. Architecture、Python Impls、CLI、storage、implementation、tests 与 Overview Skill 一致覆盖正常、
   no-op、未安装/未声明、commit 与 revision metadata divergence、ancestor 缺失、manifest 缺失、每次
   hidden re-evaluation、hidden/unhide、shared parent/cycle、并发、中断和真实 Git/hook failure。
6. 不修改 doctidex protocol，且 Published Skill 不泄露内部 runtime schema、hidden path、cache 或
   lock details。

## 8. 进展与依赖

用户对原有 question/answer 的回复已被吸收至第 2--4 节，临时问答块已移除。用户随后授权实施；已更新
Architecture、Python Impls、CLI/result contract、runtime validator、`HookService`、Git worktree move、
hidden remove no-op 与 Published Overview Skill。`hook --install` 写入可识别的 executable
`post-checkout` entrypoint，拒绝覆盖其他 hook；`hook --run` 只使用现有 local Git objects，按 manifest
exact commit 对齐 direct/dependency runtime provenance，缺少 parent metadata 时迁移 dependency subtree 到
hidden namespace，并在每次 run 重新判断已有 hidden record。

实现证据为 [`test_git_plugin.py`](../../impls/libs/python/tests/test_git_plugin.py) 的
`test_hook_install_is_idempotent_and_preserves_foreign_hook`、
`test_post_checkout_aligns_direct_commit_and_revision_provenance` 与
`test_hook_rechecks_hidden_dependencies_and_unhides_from_parent_manifest`；其中第二项通过真实 Git
`post-checkout` 执行 installed script，第三项覆盖 hidden 保留、无 direct ancestor 的再次判定、
parent manifest 恢复后的单 node unhide，以及 hidden `external remove --apply` no-op。完整 Python test、
Ruff 与 doctidex validation 已完成：`.venv/bin/python -m ruff check impls/libs/python` 通过，
`.venv/bin/python -m pytest impls/libs/python/tests -q` 为 `45 passed`，并且 scoped
`doctidex-git validate` 覆盖 requirements、doctidex-git docs、Python implementation 与 changed Published
Skill/plugin，得到 `protocol_structure: pass`、`scan_complete: true` 与零 findings；`git diff --check` 也通过。
状态为 `implemented`，尚未获得用户对 PR/MR 的 `approved` 授权。

当前没有已确认的 Requirement 依赖、细化、取代或后续关系。该 Requirement 改变 external install、
restore 与 remove 的后续 current behavior，但不改写已批准的历史 Requirement；实施前需要先完成
Architecture，再完成 Python Impls。
