# 需求 0013：增加 doctidex-git cache clean --auto

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0013` |
| 状态 | `approved` |
| 日期 | 2026-08-02 |
| 来源 | 用户要求为 doctidex-git 增加可自动清理所有未使用 bare Git cache 的命令；用户随后明确 selector 应为 `--auto`，而不是 `--all`，并要求该变更不进入 Published Skill 文档。 |
| 影响范围 | doctidex-git `cache clean` CLI/JSON contract、worktree/cache Architecture、Python Impls、implementation 与测试；不包括 Published Skills。 |
| 协议关系 | 拟议的产品能力；当前不改变 [`doctidex` 协议](../../spec/overview.md)。 |

## 1. 已记录意图

在保持现有单 source cleanup 的安全判定不变的前提下，为 `doctidex-git cache clean` 增加批量
自动回收入口：

```text
doctidex-git cache clean --auto [--dry-run | --apply] [--json]
```

`--auto` 表示命令自行枚举本机 doctidex-git shared bare source cache，并对每个候选独立判断
是否可回收。它不是调用方提供的全选 source URL 集合，因此不使用 `--all` 命名。

本记录创建时，当前 surface 只有单 source 形式
`doctidex-git cache clean --url URL [--dry-run | --apply] [--json]`。它一次只定位一个 canonical
source，且工作流明确禁止 batch、watch 和 implicit cleanup。因此本 Requirement 记录的是新增的
batch capability，不是对既有接口的文字澄清。

相关 current-artifact authority：

- [CLI 用户接口](../doctidex-git/architecture/interfaces/cli.md)；
- [Worktree 与 cache 模型](../doctidex-git/architecture/worktrees-and-cache.md)；
- [Worktree 与 cache workflows](../doctidex-git/architecture/worktrees-and-cache.md)；
- [Python worktree/cache realization](../doctidex-git/impls/python/components/worktrees-and-cache-cleanup.md)；
- [`CacheService`](../../impls/libs/python/whero/doctidex/git/worktrees.py) 与
  [`source_cache` storage](../../impls/libs/python/whero/doctidex/git/storage.py)。

## 2. 已确认的范围与安全边界

`--auto` 与 `--url URL` 是互斥的 cache selector。`--url` 继续保留为单 source operator action；
`--auto` 不选择 doctidex root，也不接受 scope、filter、pagination 或 cursor 作为隐式批量范围。

自动枚举的每个 bare cache 必须沿用当前 cleanup eligibility：Git-valid linked worktree 存在时保留；
只有没有 valid registration、其余 registration 都被 Git 判为 prunable，且 metadata 可完整分类时才
能成为可回收对象。metadata 损坏、无法分类、并发复查变化或其他不确定状态不得导致删除。

该命令默认 dry-run；只有显式 `--apply` 才能删除已重新验证仍可回收的 bare cache。它离线运行，
不得创建、fetch 或联网，不得删除 linked worktree filesystem path、owner-root payload、manifest、
runtime record 或 Git index，也不得把自动 cleanup 接入 worktree close、external remove、restore 或
其他命令的隐式后续动作。

`--auto` 仅处理 doctidex-git 自己的 shared source-cache namespace 中可识别的 bare cache。它不能因
扫描便利而把 cache root 外的 repository、lock 或未知 filesystem object 作为删除目标。当前 source
cache 的 canonical URL 不作为持久 metadata 保存；批量公共结果因此不得泄露 internal cache path，
并须由后续 Architecture 定义可审计的候选 identity、逐项状态与汇总结果。

本 Requirement 明确排除 Published Skill 文档的创建或修改。该命令仍是 human/program CLI surface；
实现、Architecture 与 Impls 不得把 `--auto` 写入任何已发布 Skill 的 command reference 或 agent
workflow。

## 3. 实施范围与影响

用户于 2026-08-02 明确授权实施本 Requirement，范围包括 Architecture、Python Impls、CLI、Python
implementation 与测试。实施已完成：

1. Architecture 已定义 `--auto` 与 `--url` selector 关系、候选枚举边界、每项
   planned/removed/preserved/blocked 语义、batch result/failure contract，以及 dry-run/apply 的
   并发复查规则；Python Impls 已记录 source-cache directory traversal、锁定顺序、异常隔离、
   public JSON shape 与测试证据。
2. Python CLI parser/dispatch 与 `CacheService` 已实现自动枚举，限定在受管 source-cache namespace；
   每项复用 Git registration 分类与 source mutation locking，不以直接递归删除替代 eligibility
   recheck。
3. Python tests 已覆盖空 cache namespace、多个可回收 cache、仍有 valid linked worktree 的
   preserved cache、prunable registration、损坏/未知 candidate、dry-run、apply、并发变化与其他
   source cache/worktree workflow 不回归。验证确认不会联网、不会改写 root-owned state、不会触碰
   非 source-cache object，且没有 Published Skill 文档改动。

Published Skills 即使在本次实施后仍明确不在范围内；doctidex protocol 也未获修改授权。

## 4. 验收标准

1. `doctidex-git cache clean --auto [--dry-run | --apply] [--json]` 有一份无歧义的当前
   Architecture contract；`--auto` 与 `--url` 互斥，且不会出现 `--all` selector。
2. 自动发现的每个候选均按现有 Git linked-worktree registration rules 重新验证；任何 valid 或
   unknown/damaged 状态都保留对应 cache，只有可证明 eligible 的 bare cache 可在 `--apply` 下删除。
3. dry-run 不持久写入；apply 不联网且只删除完成复查的 selected source cache。两种模式都不修改
   linked paths、root-owned payload、manifest、runtime、Git index、其他 cache 或 cache root 外对象，
   也不被其他 lifecycle command 隐式触发。
4. 结果能在不公开内部 cache filesystem path 或不可得 source URL 的条件下，审计每个候选和批量
   汇总的 planned/removed/preserved/blocked outcome；精确 schema、exit status 与局部失败处理由
   Architecture 明确规定，并在 Python Impls 中实现和测试。
5. 代表性 Python tests 覆盖多 candidate、空 cache、active/prunable/damaged states、dry-run/apply、
   retry/concurrency 和回归边界；Architecture、Impls、implementation 和 tests 一致。
6. 不修改 doctidex protocol 或任何 Published Skill 文档。

## 5. 进展与依赖

用户已确认新增 selector 的名称与语义为 `--auto`，不采用先前讨论的 `--all`。用户还明确排除
Published Skill 文档，并于 2026-08-02 授权实施 Architecture、Python Impls、CLI、Python implementation
与测试。实现将 `--auto` 定义为 source-cache namespace 的当次 stable ID enumeration；每项在同一
source lock 内独立重查，结果以 opaque ID、item outcome 和 aggregate counts 公开，不公开 source URL
或 internal cache path。

实施与验证证据：

- Architecture 已更新 CLI/JSON、worktree/cache model/workflow、component 与 concurrency contract；
  Python Impls 已更新 user surface、CLI/result adapter、cache/storage、physical state、concurrency 和
  coverage evidence。
- Python 新增 `CacheService.clean_auto`、受限 candidate discovery 和 `source_mutation_id`，让 auto 与
  canonical source 的 open/remove/URL clean 共用同一 lock；CLI parser 使 `--url` 与 `--auto` 互斥。
- `test_cache_cleanup_auto_isolated_candidates` 覆盖 empty namespace、active/prunable/eligible/damaged
  cache、未知 directory/symlink preservation、dry-run/apply、result counts 与 mutually exclusive selector；
  `test_cache_cleanup_auto_rechecks_each_candidate` 模拟一项 recheck conflict，确认其保留且不回滚
  其他 candidate。原 single-source cleanup tests 保持通过。
- 已运行 `.venv/bin/python -m pytest impls/libs/python/tests -q`（42 passed）、
  `.venv/bin/python -m ruff check impls/libs/python`、`git diff --check`，均通过。已运行
  `.venv/bin/doctidex-git validate . --scope /docs/requirements --scope /docs/doctidex-git --scope
  /impls/libs/python --json`；它只报告根 `index.md` 的 5 条既有 `link_annotation_invalid` finding，
  `scan_complete: true`，本 Requirement 未扩大到修复该根导航问题。

所有授权工作与验收标准均已完成。用户于 2026-08-02 明确要求将本 Requirement 标记为 `approved`，
接受当前实现为 PR/MR-ready。

没有已确认的 Requirement 依赖、细化、取代或后续关系。现有已批准
[DX-REQ-0012](0012-doctidex-git-external-remove.md) 仅记录 external remove 不触发 cache cleanup；
本 Requirement 不改写该历史，也不改变该边界。
