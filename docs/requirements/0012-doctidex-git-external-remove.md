# 需求 0012：增加 doctidex-git external remove 命令

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0012` |
| 状态 | `approved` |
| 日期 | 2026-08-02 |
| 来源 | 用户要求建立增加 `doctidex-git external remove` 命令的新需求骨架文档；随后确认 direct/dependency 的移除保护、cache 边界、`INSTALL_ID` target、引用扫描范围、Skill 引导和与 validate 统一的引用校验架构要求。 |
| 影响范围 | doctidex-git `external remove` CLI/JSON contract、external installation/mapping workflow、Python implementation 与测试、Published Skills，以及相应 Architecture/Impls。 |
| 协议关系 | 拟议的产品能力；当前不改变 [`doctidex` 协议](../../spec/overview.md)。 |

## 1. 已记录意图

为 doctidex-git 增加 `external remove` 命令，使 owner root 中由 doctidex-git 管理的 external
install 能有受管的移除入口。

本记录创建时，公开 `external` surface 只有 `install`、`link`、`restore` 与 `link-parse`；Python
`ExternalService` 也没有对应的 remove operation。因此本 Requirement 记录的是新增能力，而不是对
既有命令行为的文字澄清。实施后，`external remove` 已成为该 surface 的单目标命令。

本 Requirement 已获实施授权，并按 Architecture、Python Impls、implementation/test 与 Published
Skill 的顺序完成。实现与验证完成后，用户于 2026-08-02 明确接受当前实现，状态为 `approved`。

相关 current-artifact authority：

- [CLI 用户接口](../doctidex-git/architecture/interfaces/cli.md)；
- [External installation、link 与 mapping 模型](../doctidex-git/architecture/models/external-installation-and-mapping.md)；
- [External workflows](../doctidex-git/architecture/system/external-workflows.md)；
- [Python external realization](../doctidex-git/impls/python/components/external-installation-and-mapping.md)；
- [`ExternalService`](../../impls/libs/python/whero/doctidex/git/external.py) 与
  [`main.py`](../../impls/libs/python/whero/doctidex/cli/main.py)。

## 2. 已确认的移除边界

用户已确认 `remove` 同时适用于 direct install 和以 `--dependency-of` 创建的 dependency
install。它们都必须先检查 owner root 中是否仍存在指向该 install 的引用，至少包括文档中的
navigation link 和 filesystem symbolic link。存在任一这类引用时，命令必须拒绝移除、保留现场，
并说明阻断引用及其原因；命令不得擅自删除或改写引用以完成移除。

在没有阻断引用时，命令只移除当前 owner root 中该 install 的 readonly payload directory 和
与该 install 对应的 managed metadata。它不检测、更改或回收 shared Git cache 的 bare objects，
也不根据该移除推断或执行任何 cache 级联清理。Cache 的生命周期继续由现有 `cache clean`
workflow 单独处理。

dependency install 的相同引用检查是一层明确的防御：即使 runtime、manifest 或 role state 不一致，
命令也不得因为对象看似 dependency-only 而移除实际上仍被 direct presentation 使用的 payload。
当前模型中 direct install 才进入 portable manifest，dependency-only install 只存在于 runtime；
同一 stable install identity 还可能在 direct role 下保留 dependency parent edges。因此 remove
不能只以调用时的 `--dependency-of` 来源或单一 state document 推断可删除性。

现有 `external link` 只允许 direct install 建立 durable presentation，并在 runtime/manifest 中保存
其 mapping；`external restore` 只从 manifest 恢复 direct install。这些 managed facts 可作为引用
检查的依据，但不替代用户确认的文档 link 与 filesystem symlink 检查。

## 3. 已确认的公共契约边界

`remove` 每次只选择一个当前 owner root 的 `INSTALL_ID`。CLI 采用 required positional target：

```text
doctidex-git external remove INSTALL_ID [--root ROOT]
  [--dry-run | --apply] [--json]
```

不存在 batch filter、pagination 或以 source URL、payload path、selector 反向猜测 target 的入口。
未知、损坏或不属于 selected owner root 的 ID 必须 blocked 并保留现场。该命令沿用 external write
workflow 的 explicit `--apply` 边界；dry-run 必须执行相同的 target 和引用 preflight，但不得持久
写入。

引用扫描在 owner root 的词法路径范围中同时检查下列对象：

1. safe Markdown documents 中可解析到 target install 或其 presentation 的 Markdown navigation
   links；
2. filesystem symlink 指向 target install 或其内部路径的事实；
3. runtime/portable manifest 中的 managed link mapping；
4. runtime `parents` 中指向 target 的 dependency parent edge。

扫描不进入任何 installed repository、`boundary-set` 目录的内部或 `unsafe` 范围的内部。因而这些
排除范围内部仅由外层可见的 managed mapping/parent edge 参与保护；不会承诺发现其中任意手工
Markdown link 或 symlink。`boundary-set` 在 doctidex 协议中只表达跨界路径事实，本身不表示
unsafe 或不可读；本节的排除是 `external remove` 的产品扫描边界，不是协议规则。

对于 ID 不明确的 managed path，后续 Published Skill 必须引导调用者先运行
`doctidex-git external link-parse PATH [--root ROOT] --json`。结果中的 `install_id` 是 remove 的
target；`dependency_parent_install_id` 仅标识 parent edge，不能替代 target。没有 `install_id` 的
unmanaged 或 `dependency_not_installed` 结果不构成可移除的当前 install。

第 2、3 节的用户回答已被吸收到正文，原 question/answer 已删除。其余结果字段、lock/publication
顺序、interruption/retry 保证，以及 shared root layout（如 `.gitignore` 与 internal index）在移除
最后一个 install 后是否清理，留待 Architecture 在实施获得授权时按本 Requirement 的边界定义。

## 4. 预期实施影响

第 2、3 节已确认；在用户授权实施后，工作预计需要：

1. 先以 Architecture 记录 `INSTALL_ID` command、引用分类/排除范围、direct/dependency 状态转换、
   保护条件、dry-run/apply 和结果/失败语义；再以 Python Impls 记录具体 storage、lock、
   publication/recovery 与测试证据。
2. 将 Markdown link 提取、词法路径解释、safe/unsafe/boundary 范围判定和不跟随 directory
   symlink 的扫描事实，与 `validate` 使用的底层能力统一设计。可以复用现有
   `protocol/document.py::markdown_links`，并在需要时从 `validation.py` 提取 operation-neutral
   scanner/link-fact API；不得在 external remove 中复制另一套 Markdown parser、目录 walker 或
   link/path classifier。
3. 保持调用层策略分离：`validate` 继续根据完整 protocol policy 产生 findings、reachability 和
   scoped coverage；`external remove` 只消费共享的客观 link/scan facts，再施加本 Requirement 的
   target 与排除范围并产生 external blocked/result。remove 不调用 CLI-level validate，不把
   remove 的引用阻断误报为 protocol finding，也不借此改变 validate 的可观察契约。
4. 扩展 Python CLI parser/dispatch 和 `ExternalService`，使实现严格遵循已确认的 target 与
   state-transition 规则、引用阻断与 per-install metadata 清理，而不是以直接 filesystem 删除
   替代受管一致性检查。
5. 增加覆盖 direct/dependency 的成功移除、dry-run、safe Markdown/symlink/managed mapping/
   parent-edge 引用阻断、排除范围不递归扫描、damaged 或冲突 state、partial failure/retry（如适用），
   以及不触发 cache cleanup 和不影响其他 external/worktree/cache workflow 的回归测试。共享层应有
   面向同一 fixture 的直接测试，并由 validate 与 remove 的调用级测试共同约束，防止 link extraction
   或 scan facts 随后分叉。
6. 在命令行为稳定后，更新 Published Skills 的 command reference 与阅读引导，明确 ID 不明时使用
   `external link-parse`；不将尚未实现的命令写入当前用户 surface。

用户已明确授权本 Requirement 第 4 节的 Architecture、Impls、implementation、test 与 Published
Skill 变更；不授权 doctidex protocol 变更或与 external remove 无关的改动。

## 5. 验收标准

在 `remove` 设计获确认并获实施授权后：

1. `external remove INSTALL_ID [--root ROOT] [--dry-run | --apply] [--json]` 的 target identity、
   root selection、JSON result 和 failure categories 有一份可观察且无歧义的当前 Architecture
   contract；不支持 batch、pagination 或非 ID target。
2. 对 direct 与 dependency install，只要在 safe Markdown、filesystem symlink、managed mapping 或
   dependency parent edge 中发现阻断引用，命令就拒绝移除、保留所有 state，并在结果中给出原因和
   可定位的 path/record 证据；installed repository、boundary-set 和 unsafe 内部不递归扫描。
3. 未发现阻断引用时，apply 只移除 selected owner root 的 install payload 和 per-install managed
   metadata；不自动改写引用、不清理 shared host layout，且绝不检测、删除或级联处理 shared Git
   cache bare objects。
4. 实际写入遵循已确认的 lock、publication、interruption/retry 与 recovery 规则，不产生无法由
   后续 doctidex-git operation 读取的 state。
5. 代表性 Python tests 覆盖正常移除、dry-run、关键 blocked/conflict cases、扫描排除范围与相关
   现有 workflow 不回归；已授权的 Architecture、Impls 和 Published Skills 与实现一致。Published
   Skills 在 ID 不明时引导使用 `external link-parse`，只将返回的 `install_id` 用作 remove target。
6. 对同一 safe-scope fixture，validate 与 remove preflight 使用同一 Markdown link 提取、词法路径
   解释和 filesystem scan facts；差异只能来自各自明示的 policy（protocol finding/reachability 与
   remove target/排除范围）。实现中不存在第二套独立 Markdown parser、directory walker 或 link/path
   classifier。remove 不调用 CLI-level validate，也不改变 validate 的当前结果契约。
7. 除非另有明确授权，`doctidex` 协议不变。

## 6. 进展与依赖

用户已确认 direct/dependency 的引用保护、仅移除本 root payload/per-install metadata、不处理
shared Git cache、单一 `INSTALL_ID` target、safe 文档与 owner-root reference 扫描范围，以及 ID
不明时使用 `external link-parse` 的 Skill 引导；相应内容已吸收到第 2、3 节，所有 question/answer
均已移除。用户进一步要求 remove 引用校验与 validate 在 link extraction、scan facts 与代码架构上
统一，避免演化出两套独立校验框架；该约束已写入第 4、5 节。

用户于 2026-08-02 明确要求实施本 Requirement，授权范围为第 4 节列出的 Architecture、Python
Impls、Python implementation/test 和 Published Skill 变更。实施没有修改 doctidex protocol，也没有
扩大到未列出的 external lifecycle 语义或无关 artifact。验收标准和下列验证证据已完成；用户于
2026-08-02 明确接受当前实现，状态更新为 `approved`。

## 7. 实施与验证证据

- Architecture 已定义 `external remove` CLI/JSON、reference policy、shared tree observations、锁定
  顺序和 interruption retry；Python Impls 记录了 concrete source/root lock、Git worktree removal、
  runtime/manifest publication 与恢复边界。
- Python 新增 `TreeObservations`/`ObservedMarkdownLink` 与 `tree_observations`。validation 的 link
  validation 直接消费该 observation；remove 仅叠加 target/reference policy，不调用 validate CLI，
  不产生 protocol finding。
- Python 新增 `ExternalService.remove`、`remove_detached_worktree` 和 CLI parser/dispatch。实现覆盖
  direct/dependency、dry-run/apply、safe Markdown、filesystem symlink、runtime/portable mapping、parent
  edge、unsafe/boundary/install exclusion、cache preservation、unknown ID 指引，以及 payload 删除后的
  same-ID retry。
- Published Maintenance Skill 已新增 remove command contract，并要求 ID 不明时以 `external
  link-parse` 的 `install_id` 为 target，禁止以 `dependency_parent_install_id` 替代。
- 已运行 `.venv/bin/python -m pytest impls/libs/python/tests -q`（40 passed）、
  `.venv/bin/python -m ruff check impls/libs/python`、`git diff --check`、Published Skill quick validation
  与 doctidex-git plugin validation，均通过。
- 已运行 `.venv/bin/doctidex-git validate . --scope /docs --scope /impls --json`。该 scoped validation
  保持 5 条已有 root `index.md` `link_annotation_invalid` finding，`scan_complete: true`；这些 root
  navigation annotation 与本 Requirement 无关，未在本授权范围内修改。

没有已确认的 Requirement 依赖、细化、取代或后续关系；若后续确认与既有 Requirement 形成关系，
将按双向链接规则处理，且不会未经用户授权修改已 `approved` 的历史记录。
