# 需求 0016：在 doctidex-git Skill 中引导主动执行 hook run

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0016` |
| 状态 | `approved` |
| 日期 | 2026-08-04 |
| 来源 | 用户要求在 Skill 文档中增加 `hook --run` 的主动触发提示：`post-checkout` hook 失败后，agent 解决可恢复问题时，应能直接重新执行协调，而不是通过一次无业务目的的 `git checkout` 间接触发。 |
| 影响范围 | `doctidex-git-overview` Published Skill、其发布前 Skill validation，以及本记录与 Requirements 导航。 |
| 协议关系 | 产品 Skill 的使用引导；不改变 [`doctidex` 协议](../../spec/overview.md)。 |

## 1. 已记录意图

当前 `doctidex-git-overview` 已说明：安装 `hook --install` 后，Git `post-checkout` 会自动协调受管
external dependency state，正常 checkout 后不应重复手动协调。但它只要求在 Git 报告 warning 时检查
hook result，未告诉 agent 在定位并解决该次 `post-checkout` hook 的可恢复问题后，能够直接重新运行已有的
协调 entrypoint。

`hook --run` 已是公开的 root-scoped 离线 reconciliation command，可由 human 或 program 显式诊断性调用；
它不是待新增的 CLI 或 hook 行为。本 Requirement 只补足已安装产品的 agent 使用引导：避免为了重试 hook
而执行一次不需要的 `git checkout`，同时不把正常 checkout 变成每次都需要人工重复的工作流。

## 2. 已确认的使用边界

Published Overview Skill 应在现有 checkout hook 提示附近明确以下决定：

1. Git 未报告该 hook 的 failure 或 warning 时，agent 不主动重复 reconciliation。
2. Git 报告 `post-checkout` hook 的 failure 或 warning 时，agent 先读取相关 result/finding，识别受影响对象、
   已保留 state 与可恢复动作；需要用户决定的情况仍按现有安全边界停下。
3. 在 agent 已在授权范围内解决该次可恢复问题后，使用准确 owner root 主动执行：

   ```text
   doctidex-git hook --run --root ROOT --json
   ```

   该命令用于重试已有 hook reconciliation；不得为了触发它而另行执行 `git checkout`。
4. 这项提示不授权绕过 dirty、damaged、object missing、manifest/runtime damage、concurrent change 或
   `requires_user` 等保留/阻塞结果，也不替代对 result/finding 的复查。

提示必须保持 Published Skill 的用户信息边界：只说明公开 command、root、结果和下一决定，不泄露 runtime
schema、hidden path、cache、lock 或 Python implementation mechanics。

## 3. 实施影响

授权实施后，先依据 [Published Skill 系统](../doctidex-git/architecture/skill-system.md) 和
[hook CLI contract](../doctidex-git/architecture/interfaces/cli.md#10-hook) 更新
[`doctidex-git-overview` Skill](../../impls/agent-plugins/doctidex-git/skills/doctidex-git-overview/SKILL.md)。
变更只表达现有公开 `hook --run` contract，不改变 Architecture、Python Impls、CLI、hook script 或 tests；
若核对时发现这些 current authorities 与上述前提不一致，须先将本 Requirement 保持为 `draft` 并记录差异，
不得由 Skill 文本暗中定义新产品行为。

实施后须按 Skill-system 的发布前规则检查 frontmatter、触发条件、精确 command、failure guidance、直接
links、阅读链、用户/内部信息边界，并验证 containing plugin。该项 Published Skill 的变更也须与现有
Overview 的“正常 checkout 不重复手动协调”提示共同阅读，保证两者不产生相反指令。

## 4. 验收标准

1. Overview Skill 清楚区分正常 checkout 与 Git 报告 `post-checkout` hook failure/warning 的场景；正常
   checkout 不会得到重复运行 hook 的指令。
2. 对可恢复的 hook failure/warning，Skill 要求先检查 result/finding、解决问题并尊重 `requires_user`，随后
   使用 `doctidex-git hook --run --root ROOT --json` 主动重试。
3. Skill 明确禁止只为触发 reconciliation 而进行无业务目的的 `git checkout`。
4. 新提示不创造 CLI、状态转换或恢复语义，不暴露内部 implementation details，并与现有公开 hook contract
   一致。
5. 受影响的 Published Skill、containing plugin 和相关 navigation 经当前验证工具检查通过；完成后记录证据，
   将本 Requirement 置为 `implemented`，等待用户明确批准后才可置为 `approved`。

## 5. 进展与依赖

本记录是已批准 [DX-REQ-0014](0014-doctidex-git-checkout-hook.md) 的后续使用引导，但该历史记录未获修改
授权，故关系暂由本记录单向保留；若未来需要在 `DX-REQ-0014` 添加 reciprocal link，须先取得用户对
approved history 的明确授权。

已核对 `DX-REQ-0014` 的已实现 `hook --run`、当前 CLI contract、Python hook realization 与 Published
Overview Skill。用户随后授权实施；[`doctidex-git-overview` Skill](../../impls/agent-plugins/doctidex-git/skills/doctidex-git-overview/SKILL.md)
现已区分普通 checkout 与 Git 报告的 `post-checkout` hook failure/warning，要求 agent 先检查并在当前授权
范围内解决问题，再以 exact owner root 执行 `doctidex-git hook --run --root ROOT --json`，并明确禁止为了
触发该 hook 而进行无业务目的的 `git checkout`。

验证已完成：`GIT_OPTIONAL_LOCKS=0 git diff --check` 通过；`doctidex-git validate . --scope
/docs/requirements` 和 `doctidex-git validate . --scope /impls/agent-plugins/doctidex-git` 均返回
`protocol_structure: pass`、`scan_complete: true` 与零 findings；插件 `plugin.json` 已由 JSON parser
读取，Overview 的 frontmatter/metadata 保持匹配且全文 106 行。当前 Codex active plugin catalog 未提供
该本地插件的 published-Skill validator，故没有可运行的额外 catalog validation entrypoint；本次没有改变
hook workflow contract，因此不触发独立 workflow forward test。所有已授权工作已完成；用户随后明确批准
当前实现可进入 PR/MR，状态为 `approved`。
