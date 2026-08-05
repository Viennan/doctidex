# 子需求 0021.3：`.github` workflow 的协议可达性

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0021.3` |
| 状态 | `implemented` |
| 日期 | 2026-08-05 |
| 所属大型 Requirement | [DX-REQ-0021](overview.md) |
| 对应 Issue | [DX-ISSUE-0003](../../issues/0003-root-index-omits-github.md) |
| 影响范围 | 仓库根 `index.md`、`.github` CI workflow 的阅读入口、全根 doctidex validation。 |
| 当前 authority | [协议第 5.2 节](../../../spec/overview.md#52-doctidexatomic-indexing)、[第 6 节](../../../spec/overview.md#6-indexmd)与[第 11 节](../../../spec/overview.md#11-符合性)。 |

## 1. 需求意图

将 `.github` 明确为仓库工具/配置的原子目录，同时保留它作为根索引范围内可发现的入口。该选择避免为单个 CI workflow
创建与其实际用途不符的导航层级，也不以 `unsafe` 掩盖一个本可安全索引的目录。

## 2. 解决方案

在根 `index.md` 的 `doctidex.atomic-indexing` 列表加入 `path: .github`，并在“Atomic Repository Content”或同等的
根阅读入口中加入到 `.github/` 的 Markdown file-path link，说明它保存 GitHub CI/automation configuration。

该目录当前只有 `.github/workflows/python.yml`，不含 `index.md` 或 `log.md`，满足 atomic directory 的内部元文件
限制。根索引的 link 使目录入口可达；atomic declaration 则免除其内部 workflow 文件的递归可达要求。

## 3. 实现与文档影响

- 只修改根索引 frontmatter 和正文导航，不修改 workflow 内容、GitHub Actions 行为、`.gitignore` 或 validator rule。
- 根 `index.md` 是本项 current documentation authority；无需创建 `.github/index.md`，也不应为原子目录创建它。
- 该修复与 0021.6 可能落在同一文件，但验收和 Issue 处置保持独立。

## 4. 验收标准

- `.venv/bin/doctidex-git validate . --json` 不再返回 `.github`、`.github/workflows` 或
  `.github/workflows/python.yml` 的 `path_unreachable`。
- validator 不因新增 atomic declaration 报告 `atomic_indexing_invalid`，并且根索引存在可解析的 `.github/`
  Markdown link。
- `.github` 内部不新增 doctidex `index.md` 或 `log.md`；CI workflow 内容与执行语义保持不变。

## 5. 实施状态

2026-08-05 已完成实施。根 `index.md` 将 `.github` 声明为 atomic directory，并以 GitHub CI/automation 的说明链接其
目录入口；未修改 workflow 内容或创建 `.github/index.md`。全根 validation 的 `protocol_structure` 为 pass，且无
`.github` 的 `path_unreachable` finding。DX-ISSUE-0003 仍需用户明确授权才可进入 `resolved`。
