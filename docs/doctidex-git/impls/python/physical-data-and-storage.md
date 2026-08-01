# Physical data 与 storage

本篇把 Architecture logical state 映射到 Python/file/Git representation。Public fields 仍由
[JSON Schema](../../architecture/interfaces/cli-schema.md)定义；这里的路径和 schema 是 internal
realization，不能成为 installed user prerequisite。

## 1. Physical state map

Owner-root layout 固定为：

```text
<root>/.doctidex/git/
|-- installs/<install-id>/
|-- worktrees/<worktree-id>/
|-- manifest.json
|-- runtime.json
`-- .mutation.lock/
```

`manifest.json` 可被 host Git track；其余四类 exact paths 进入 host repository `.gitignore`。
User cache layout 为 `<cache-root>/sources/<source-id>.git`、`locks/<source-id>.lock/` 与
`diagnostics/<diagnostic-id>.log`。`cache_root()` 的 platform 选择见
[Platform/package](platform-package-and-dependencies.md)。

| Physical data | Owner/module | Layout/content | Validation/publication | Visibility |
|---|---|---|---|---|
| Markdown/frontmatter | `protocol.document` + responsible index | UTF-8 Markdown、round-trip YAML、links | duplicate key reject；temp/fsync/replace | 文件公开。 |
| Host ignore rules | `RootStorage.ensure_host_layout` | 仅 managed installs/worktrees/runtime/lock 的 exact root-relative entries | Git tracking/ignore preflight；保留其他行 | path/state 公开，mechanics internal。 |
| Portable manifest | `RootStorage` | schema 1.0、direct installs、durable links | duplicate/schema/path/reference check；atomic JSON | versioned path/state 与 portable facts 公开。 |
| Runtime records | `RootStorage` | schema 1.0、installs/links/worktrees | full identity/path/reference validation；atomic JSON | internal，结果投影 decision facts。 |
| Source cache | `git.source/storage` | per canonical source bare Git repository + registrations | source boundary、Git commands | physical path internal。 |
| Install payload | `git.external/source` | detached exact-commit worktree under owner namespace | runtime/manifest/HEAD consistency、permission hardening | working/install path 公开。 |
| Maintenance worktree | `git.worktrees` | detached writable worktree + runtime record | Git status/identity recheck | path/state 公开。 |
| Diagnostic | `git.diagnostics` | opaque-ID traceback file in user cache | best effort bounded write | 仅 ID 公开。 |
| Locks/temp files | `git.storage` | cache/root lock directories、same-dir temp | bounded acquire、finally cleanup | internal。 |

## 2. Runtime schema

读写与校验由
[`git/storage.py::RootStorage`](../../../../impls/libs/python/whero/doctidex/git/storage.py)拥有；本节
只展开影响跨调用恢复和 component 协作的主要 physical records。

Top-level 是 `schema_version: "1.0"` 与 object-valued `installs`, `links`, `worktrees`。Record key
必须等于自身 ID/target。Install fields：

| Field | Python/physical constraint |
|---|---|
| `install_id` / `install_path` | non-empty string；path 必须为 `/.doctidex/git/installs/<id>`。 |
| `source_url` / `canonical_source` | non-empty string；前者 sanitized/public，后者 runtime equality。 |
| `source_relation` | `host_repository|other|unknown`。 |
| `revision_selector` | dict `{kind, value}`；kind 为 commit/tag/branch，value non-empty。 |
| `default_branch` | `str | None`。 |
| `requested_default` | bool；省略 revision 创建时为 true，供 idempotent lookup。 |
| `resolved_commit` | 40/64 lowercase hex string。 |
| `role` / `parents` | `direct|dependency`；parents 为去重 non-empty ID list。 |
| `managed_state` | 当前只接受 literal `complete`；incomplete 现场不伪造 valid record。 |

Link record fields 与 Architecture PortableLink 同型，target key/root-relative path 和 install
reference 必须自洽。Worktree fields：

| Field | Python/physical constraint |
|---|---|
| `worktree_id` | non-empty object key。 |
| `source_kind` | `managed_path|url|working_tree|bare_gitdir|gitfile`。 |
| `source_identity` | canonical source 或 common-gitdir absolute string，按 source kind 产生。 |
| `source_url` | sanitized string/null。 |
| `gitdir` | source object repository/common gitdir absolute string。 |
| `revision_selector` / `base_commit` | selector dict；40/64 lowercase full commit。 |
| `root_internal_path` / `worktree_path` | `/.doctidex/git/worktrees/<id>` 与对应 owner absolute path。 |
| `repository_relative_path` | `.` 或 normalized relative POSIX suffix。 |

Runtime 是当前 host ownership authority，不版本化，不包含 credentials 或 agent plan。未知 schema、
duplicate key、invalid object ID、non-normalized path、missing reference 都令整个 document blocked；
实现不进行 silent repair/migration。

## 3. Portable manifest schema

Top-level 与 known-field contract 实现 Architecture 的
[Recovery Manifest](../../architecture/models/external-installation-and-mapping.md#2-recovery-manifest)。
`_valid_manifest`、`_valid_install(portable=True)` 与 `_valid_link` 是 read/write 共用 validator；
portable record 不含 canonical local identity、requested-default、role/parents 或 runtime state。
`_restore_item` 从 portable `default_branch` 是否 non-null 恢复 runtime-only
`requested_default` boolean，再补入 canonical identity、direct role、empty parents 与 complete
state。该投影使重建 record 满足 `_valid_install(portable=False)`，同时不把 Python lookup flag
加入 portable schema，也不改变 selector 或 exact commit。

`RootStorage.manifest_identity` 以 `json.dumps(sort_keys=True, separators=(",", ":"))` 的 ASCII
escaped UTF-8 bytes 求 SHA-256 前 24 hex，用于本 variant 的 restore pagination/state consistency。
Write 前使用与 read 相同 validator，保证 CLI 不发布自身无法读取的 state。

## 4. Cache 与 IDs

Canonical source 的 SHA-256 前 24 hex 形成 opaque `source_id`，只用于内部 cache/lock naming。
Install ID 对 owner root/source/selector identity 求稳定摘要；worktree ID 随每次 open 随机生成。
Opaque ID 不用于 permission 或 trust，collision/record mismatch 按 damaged state 处理。

## 5. Publication

Text/JSON 以同目录 temporary、UTF-8 LF、flush/fsync、`os.replace` 发布。Directory lock 以 atomic
`mkdir` 获取，10 秒 bounded timeout 后 conflict。Git objects/worktree、frontmatter、ignore、
manifest/runtime 与 symlink 之间无 transaction；跨组件恢复见
[并发、失败与恢复](concurrency-failures-and-recovery.md)。
