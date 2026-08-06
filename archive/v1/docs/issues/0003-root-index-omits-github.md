# DX-ISSUE-0003：根索引未使 `.github` 工作流目录可达

状态：`resolved`

创建日期：2026-08-05

严重程度：high

来源：2026-08-05 对当前 `HEAD`（`259085abd8c324a53840f55a6783fa31eb874fbb`）进行的全仓 review；用户授权将严重度最高、已验证的问题记录为 Issue。

确认：2026-08-05，用户明确要求将本轮 review 创建的全部 6 个 Issue 置为确认状态。

## 问题

根索引既未将 `.github` 声明为 `atomic-indexing` 或 `unsafe`，也没有到该目录的 Markdown file-path link。
`.github/workflows/python.yml` 因此不属于任何协议例外，且无法从负责它的根索引到达。该问题同时使 `.github`、
`.github/workflows` 与 workflow 文件本身不可达，但三项 finding 具有同一根因。

## 具体场景

从仓库 root 执行当前公开 validator：

```text
.venv/bin/doctidex-git validate . --json
```

根 `index.md` 的 `atomic-indexing` 只列出 `.agents`、`.codex` 与 `spec`；其 Markdown links 也没有 `.github`。
因此 validator 从根索引开始遍历时，既没有到 `.github` 的阅读边，也没有可适用的原子目录例外。

## 当前错误状态

命令返回的关键片段如下，三个 finding 是同一遗漏的目录及其祖先/文件展开结果：

```json
{
  "status": "warning",
  "protocol_structure": "fail",
  "findings": [
    {"code": "path_unreachable", "path": ".../.github"},
    {"code": "path_unreachable", "path": ".../.github/workflows"},
    {"code": "path_unreachable", "path": ".../.github/workflows/python.yml"}
  ]
}
```

这不是 GitHub Actions 本身运行失败，而是仓库的 doctidex 阅读图没有公开它的 CI 配置入口。

## 正确行为

根索引必须让 `.github` 作为其负责范围的一部分可达：若该目录需要递归披露，应建立能够到达 workflow 的 Markdown
路径；若只需整体入口，应声明符合协议约束的 atomic directory，并使目录本身可达。完成后这三个 path 不应再产生
`path_unreachable`。

## 受影响范围与条件

- 当前仓库作为 doctidex 目录树的协议符合性。
- root index 负责的 `.github` 目录与其中 CI workflow；无须特殊输入即可复现。

## Authority 与证据

- [协议第 6 节](../../spec/overview.md#6-indexmd)要求每个 index 使其负责范围内每个文件和目录可达，除非适用列举的例外。
- [协议第 7 节](../../spec/overview.md#7-可达性)规定以负责 `index.md` 出发的 Markdown file-path link 图计算可达性；
  [第 11 节](../../spec/overview.md#11-符合性)将此列为必须满足的符合性条件。
- [根索引](../../index.md#L1) 的 local configuration 仅声明 `.agents`、`.codex`、`spec` 为 atomic，且未链接 `.github`。
- 执行 `.venv/bin/doctidex-git validate . --json` 返回 `path_unreachable`，affected paths 为 `.github`、
  `.github/workflows` 与 `.github/workflows/python.yml`。

## 影响与后续决定

仓库当前无法通过自身协议 validator，也没有向人或 agent 暴露 CI 配置的受控阅读入口。后续应依据该目录是否需要
递归导航，选择从根索引建立链接，或以符合 atomic 语义的方式声明其整体入口；不能仅抑制 validator finding。
Issue 目前不授权此类文档或配置修改。

## 处置

解决：2026-08-05，用户明确要求将本轮六项 Issue 标记为 `resolved`。根据
[DX-REQ-0021.3](../requirements/0021-resolve-confirmed-review-issues/03-github-workflow-reachability.md)，根
`index.md` 现将 `.github` 声明为 `atomic-indexing`，并提供 GitHub CI/automation configuration 的目录入口；未修改
workflow 内容，也未在 atomic directory 内创建 doctidex 元文件。

验证：`.venv/bin/doctidex-git validate . --json` 返回 `protocol_structure: pass`、无 findings，且不再报告 `.github`、
`.github/workflows` 或 `.github/workflows/python.yml` 的 `path_unreachable`；Requirement scope validator 与
`git diff --check` 同样通过。

残余边界：`.github` 保持原子索引，协议只要求其目录入口可达；workflow 内部文件仍由 native Git、GitHub 和搜索工具读取，
不是逐文件 doctidex 导航的承诺。
