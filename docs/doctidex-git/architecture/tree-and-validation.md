# 树、根与验证

本页定义 doctidex-git 如何观察 doctidex tree、选择 root 并报告 validation。协议格式、
safe/unsafe、index continuity 与 link rules 的规范 authority 是 [`spec/overview.md`](../../../spec/overview.md)；
本页定义产品如何把这些可观察规则交给 user surface，以及受管 external/worktree 如何与它们共存。

## 1. 根、所有者、内容与主机观察

`validate` 和 Read 工作流先确定一个 doctidex root。root 是含有 `doctidex.root: true` 的
`index.md` 所在目录，`/` 只在该 root 内解释。一个 Git working tree 可包含多个 root，亦可没有
任何 root；Git repository、owner root 与 content root 不是 root 的替代身份。

| 观察 | 作用 | 不推出 |
|---|---|---|
| selected root | validation scope、root-absolute path、受管 owner state 的候选边界。 | host Git repository 或 content root。 |
| owner root | external manifest/runtime/install/worktree 的 owner。 | 每个 nested doctidex root 都由它拥有。 |
| content root | installed source 或 presentation 中的 portable mapping scope。 | 当前 host 的 write permission。 |
| host Git repository | `.gitignore`、tracking、hook 的宿主。 | doctidex protocol compliance。 |

调用方应传精确 ROOT；省略时只使用当前 cwd 的本次观察，不形成跨 invocation default。nested root
歧义、不可读 root、scope 越界或 missing `index.md` 是 blocked input，而不是隐式回退到另一个 root。

## 2. 索引配置与根观察

每个 safe `index.md` 必须是可读 UTF-8 Markdown，并有 protocol 要求的 frontmatter。下表是
Architecture reader 在工作现场遇到 `index.md` 时必须理解的全部 doctidex configuration options：

| Option | value / lifecycle | 对 user surface 和 managed workflow 的影响 |
|---|---|---|
| top-level `type` | index 为 `index`。 | 是与其他文档约定互操作的类型标识；`doctidex.type` 才是 protocol semantic discriminator。安全 root index 必须保持二者一致，不能把未知顶层 field 当作它的替代。 |
| `doctidex.type` | `index`；root 和 sub-index 都存在。 | 使目录成为负责索引入口；不符合时 validation 的 protocol finding 说明结构错误。 |
| `doctidex.root` | root index 为 `true`；子 index 省略或 `false`。 | 确定 path `/`、root selection 和 owner/content boundary 的合法观察范围。 |
| `doctidex.boundary-set[].path` | root 内相对目录路径列表。 | 进入/离开该目录的 file-path link 是 cross-boundary；external link apply 可在 responsible index 维护对应 declaration。 |
| `doctidex.atomic-indexing[].path` | root 内相对目录路径列表。 | 该目录作为整体可达，内部不递归索引；不能含 protocol `index.md`/`log.md`。 |
| `doctidex.unsafe[].path` | root 内相对文件或目录路径列表。 | 声明 strict structure/link exception；safe link 进入它必须带 protocol annotation，且不表示信任/权限。 |
| 与 Markdown file-path link 关联的 `<!-- doctidex: {...} -->` comment | 一个 link 最多一个 annotation；当前字段是 boolean `unsafe` 与可选的 `cross-boundary-point` path。 | `unsafe: true` 明确 safe 文档进入 unsafe path；跨 boundary 时 point 标识首次 boundary。它是 link 的 protocol metadata，不是独立 product configuration；修改 Markdown 时必须保持其与对应 link 的关联和语义。 |

每个 list entry 只以 `path` 表示目标，路径是相对 responsible index 的词法路径；unknown extension
field、其它 top-level frontmatter、其它 HTML comment 与 Markdown content 都不替代上述语义。variant
在修改一个 responsible index 前必须保留它们，保证每个 path 与 link 的 protocol meaning 不变。具体
YAML round-trip 和 write algorithm 由 Impls 定义。

受管 install/restore/worktree 可能创建或维护 root-internal `.doctidex/git/` 的必要 boundary/ignore
关系；durable presentation link 可能维护 responsible index 的 `boundary-set`/`unsafe` entry。它们不能
借此把 runtime、payload 或 Git state 变为 protocol requirement。

## 3. 验证工作流

`validate ROOT [--scope PATH]... [--limit N] [--cursor TOKEN] [--json]` 是 read-only observation。
它按 selected root 解释 protocol structure、link/reachability 与产品提供的 semantic candidates，
不读取或修复 managed runtime 作为 compliance 前提。

| 输入 / default | 处理 | 可观察结果与下一步 |
|---|---|---|
| ROOT | 必须是可读 doctidex root；program 使用 exact path。 | `root`、coverage 和 normalized scope；无 root/非法 scope 时 blocked。 |
| no `--scope` | 覆盖整个 root。 | `coverage: full`；protocol conclusion 对整 root 有效。 |
| one or more `--scope` | 合并为 root 内现有可读目录集合。 | `coverage: scoped`；pass 只覆盖列出的区域，不能缓存为全根 pass。 |
| limit/cursor | limit 有界；cursor opaque，绑定 root、normalized scope、query/state。 | collection total/returned/truncated/next_cursor；失效 cursor 从第一页重读。 |

结果分为 `protocol_structure`、scan 完整性、semantic review 状态、findings 和 candidates。`warning`
或 candidate 不是等于 protocol failure；调用方读取 stable code、coverage、scope 和 action，而不是
只看 exit code 或 message。具体 envelope 和 fields 见 [JSON schema](interfaces/cli-schema.md#2-common-envelope)
及 [validate payload](interfaces/cli-schema.md#3-validate)。

## 4. 与工作现场及跨变体的关系

一个 incoming variant 遇到 root configuration 时：

1. 先按 protocol 解释 `index.md`，不因存在 manifest/runtime/payload 而修改 compliant tree 的含义；
2. 若要操作 owner state，确认 selected root/host repository/owner root 的关系，而不从 Git cwd 猜测；
3. durable presentation 的 target、safe state 和 responsible index 必须与
   [外部映射](external-snapshots-and-presentations.md#5-安装载荷隐藏状态与持久呈现)
   一致；
4. 不能安全解释的 configuration/version 保持不变并返回 diagnostic/blocked result，不能用本 variant
   的 default 覆盖。

这足以让另一个 variant 正确实现 validation、root selection、external presentation 的 protocol side
effects；它不需要复现 current parser AST、YAML emitter、filesystem traversal order 或 candidate heuristic。
