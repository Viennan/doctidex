# 需求 0018：限定 hook 只安装在 owner root 的宿主仓库

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0018` |
| 状态 | `approved` |
| 日期 | 2026-08-04 |
| 来源 | 用户要求提醒 agent：不得在一个 owner root 所管理的 install Git repository 中执行 `hook --install`；Git hook 只针对当前选定 owner root 所在的 host Git repository 设置，原则与 external install 只在 owner root 下进行一致。 |
| 影响范围 | `doctidex-git-overview` Published Skill、其发布前检查，以及本记录与 Requirements 导航。 |
| 协议关系 | 产品 Skill 的使用边界；不改变 [doctidex 协议](../../spec/overview.md)。 |

## 1. 已核对的现状与意图

当前 [产品与 user surface](../doctidex-git/architecture/product-and-user-surfaces.md) 区分 owner root、content root
和 host Git repository；[hook CLI contract](../doctidex-git/architecture/interfaces/cli.md#10-hook) 规定
`hook --install` 在 selected root 所在的 Host Git Repository 建立 `post-checkout` entrypoint。Published
Overview 已说明 hook run 针对 exact affected owner root，但没有在安装 hook 前明确排除 owner root 管理的
install repository。

本 Requirement 只收紧已安装产品中 agent 的操作指引。它不新增 CLI 参数、hook 状态转换或运行时拒绝逻辑；
不得把这项 Skill 约束表述为 CLI 已自动阻止的事实。

## 2. 已确认的使用边界

agent 决定执行 `DOCTIDEX_GIT hook --install` 时，必须先确定当前任务的 owner root。只可将 hook 注册在该
owner root 所在的 host Git repository，并显式使用该 root：

```text
DOCTIDEX_GIT hook --install --root OWNER_ROOT --json
```

owner root 下由 doctidex-git 安装的 Git repository 是受管 install payload，不是当前任务可注册 hook 的
owner repository。即使其中存在独立的 doctidex root 或 Git working tree，agent 也不得在该 install 内容中
执行 `hook --install`，或把该 content root 传给 `--root` 来为它的 Git repository 设置 hook。

这一限制不改变一个明确 selected owner root 的现有 hook：它仍只服务该 root 的 managed state，并由该
owner root 所在 host Git repository 的 checkout 触发。它不递归给 install repository 设置 hook，也不把
install repository 的 checkout 视为 owner root hook 的触发条件。

## 3. 实施影响

授权实施后，依据 [Published Skill 系统](../doctidex-git/architecture/skill-system.md) 和现有
[hook CLI contract](../doctidex-git/architecture/interfaces/cli.md#10-hook)，在
[`doctidex-git-overview` Skill](../../impls/agent-plugins/doctidex-git/skills/doctidex-git-overview/SKILL.md)
的 checkout hook 指引附近加入上述 owner/install 区分与精确命令。

变更不得改写 Architecture、Python Impls、CLI、hook script 或 tests，也不得泄露 runtime、cache、lock 或
其他内部实现。实现后检查 Published Skill 的 frontmatter、阅读链、命令充分性、failure guidance 和用户/内部
信息边界，并验证 containing plugin 与 Requirements navigation。

## 4. 验收标准

1. Overview 明确要求 agent 仅对当前 selected owner root 的 host Git repository 执行
   `DOCTIDEX_GIT hook --install --root OWNER_ROOT --json`。
2. Overview 明确禁止在该 owner root 管理的 install Git repository 中运行 `hook --install`，包括以其
   content root 作为 `--root` 的情形。
3. 文本说明 hook 不递归安装到 install repository，且不会把 install repository 的 checkout 作为 owner
   root hook 的触发条件。
4. 提示只表达 agent 使用边界，不创造 CLI 拒绝、状态转换或其他产品行为，不暴露内部实现细节，并与当前
   Architecture 和 CLI contract 一致。
5. 受影响的 Published Skill、containing plugin 与 Requirements navigation 经当前验证工具检查通过后，
   记录证据并将本 Requirement 置为 `implemented`；只有用户明确批准后才可置为 `approved`。

## 5. 进展与依赖

本记录以后续使用引导方式依赖已批准的 [DX-REQ-0014](0014-doctidex-git-checkout-hook.md)（hook lifecycle）
和 [DX-REQ-0016](0016-doctidex-git-hook-run-skill-guidance.md)（Overview 的 hook guidance）。二者均为
`approved` 历史，尚未获得修改其内容以添加 reciprocal link 的授权；本记录暂保留单向关系。

已核对协议、当前 Architecture、CLI/root selection 实现、Published Overview 与上述历史 Requirements。用户已授权
实施；Overview 现要求 agent 在获得写入授权后，以 exact `OWNER_ROOT` 在其 host Git repository 执行
`DOCTIDEX_GIT hook --install --root OWNER_ROOT --json`，并明确禁止在该 root 管理的 install repository 或其
content root 中安装 hook。文本同时说明 owner root 的设置不会递归安装 hook，也不会把 install repository
checkout 当作 owner root hook 的触发条件。

验证已完成：`GIT_OPTIONAL_LOCKS=0 git diff --check` 通过；`.venv/bin/doctidex-git validate . --scope
/docs/requirements --json` 与 `.venv/bin/doctidex-git validate . --scope /impls/agent-plugins/doctidex-git
--json` 均返回 `protocol_structure: pass`、`scan_complete: true` 与零 findings；containing plugin 的
`.codex-plugin/plugin.json` 已由 JSON parser 读取。已人工确认 Overview 的 frontmatter、目录名与
`agents/openai.yaml` metadata 一致，全文 128 行，且阅读链、直接 links、命令提示和用户/内部信息边界均未被
破坏。当前 active Skill catalog 没有该本地插件的额外 Published-Skill validator；本次没有改变 CLI workflow，
故不需要独立 workflow forward test。所有授权工作已完成；用户随后明确批准当前实现可进入 PR/MR，状态为
`approved`。
