# Architecture coverage 与 tests

本页按 Architecture 的关键模型和主要 workflow 定位 Python `1.0.0` realization。Architecture
是共同语义 authority；组件页、source 与 tests 是实现证据。辅助类型和局部算法不逐项建立
coverage row，material limitation 必须说明实际影响而不能只列字段差异。

下表中的 test name 均位于
[`test_protocol.py`](../../../../impls/libs/python/tests/test_protocol.py) 或
[`test_git_plugin.py`](../../../../impls/libs/python/tests/test_git_plugin.py)。

## 1. Model coverage

| Architecture model | Python types/state | Component authority | Evidence |
|---|---|---|---|
| [Tree/configuration](../../architecture/models/doctidex-tree-and-configuration.md) | `DoctidexDocument`, `MarkdownLink`, `IndexInfo`, `TreeObservations`, `_Validator`；annotation/edge 是局部 helper facts | [Protocol interpreter](components/protocol-interpreter.md) | `test_boundary_unsafe_annotation_and_reachability`, `test_tree_observations_share_link_resolution`, `test_tree_observations_preserve_boundary_unsafe_and_symlink_scan`。 |
| [Root/ownership/path](../../architecture/models/root-ownership-and-paths.md) | `RootContext`, root/path owner selectors、runtime records | [Protocol](components/protocol-interpreter.md)、[External](components/external-installation-and-mapping.md) | `test_valid_tree_and_scopes`, `test_portable_broken_link_dependency_can_be_flattened`, `test_unrecorded_worktree_namespace_path_is_preserved`。 |
| [Git source/revision](../../architecture/models/git-source-revision-and-repository.md) | `RevisionSelector`, `ResolvedSource`, `WorktreeSource`, source cache | [Git source/storage](components/git-source-and-storage.md) | `test_default_revision_is_fixed_and_self_dependency_is_bounded`, `test_explicit_branch_retry_stays_fixed_and_root_is_part_of_identity`, `test_different_selectors_keep_distinct_install_paths`, `test_worktree_source_kinds_managed_bare_and_submodule`。 |
| [External/mapping](../../architecture/models/external-installation-and-mapping.md) | complete/hidden runtime install records、manifest/link records、`ExternalService`、`HookService` | [External](components/external-installation-and-mapping.md)、[Physical data](physical-data-and-storage.md) | `test_link_restore_and_current_owner_parse`, `test_restore_rebuilds_requested_default_provenance`, `test_portable_broken_link_dependency_can_be_flattened`, `test_hook_rechecks_hidden_dependencies_and_unhides_from_parent_manifest`, `test_post_checkout_aligns_direct_commit_and_revision_provenance`。 |
| [Worktree/cache](../../architecture/models/worktree-and-cache.md) | `WorktreeService`, `CacheService`, Git registrations | [Worktree/cache](components/worktree-and-cache.md) | `test_worktree_dirty_preservation_and_close`, `test_cache_cleanup_preserves_active_then_removes_eligible`, `test_cache_cleanup_accepts_prunable_registration`, `test_cache_cleanup_auto_isolated_candidates`, `test_cache_cleanup_auto_rechecks_each_candidate`。 |
| [Operation/result/failure](../../architecture/models/operation-result-and-failure.md) | `DoctidexError`, envelope/finding/cursor helpers、CLI main/render | [CLI/results](components/cli-results-and-rendering.md) | `test_parser_rejects_old_surface_with_json`, `test_restore_preserves_blocked_item_and_restores_other_item`, `test_scoped_validation_filters_output_and_cursor_is_state_bound`。 |

## 2. Workflow coverage

| Architecture workflow | User entry | Realization | Tests |
|---|---|---|---|
| [Validation](../../architecture/system/validation-workflow.md) | `validate` / Maintenance Skill | `select_root -> validate_protocol -> paginate_lists` | `test_valid_tree_and_scopes`, `test_scoped_validation_filters_output_and_cursor_is_state_bound`。 |
| [Install](../../architecture/system/external-workflows.md#1-install) | `external install` | `ExternalService.install` + source/root storage | `test_default_revision_is_fixed_and_self_dependency_is_bounded`, `test_install_blocks_an_ignored_recovery_manifest`。 |
| [Link](../../architecture/system/external-workflows.md#2-link) | `external link` | mapping preflight、round-trip index、relative symlink、manifest/runtime | `test_link_retry_rejects_a_changed_symlink_target`, `test_link_classifies_only_a_complete_doctidex_root_as_safe`, `test_link_reports_symlink_unsupported_before_persistent_changes`。 |
| [Restore](../../architecture/system/external-workflows.md#3-restore) | `external restore` | manifest identity、item restore、exact cache、runtime provenance rebuild | `test_link_restore_and_current_owner_parse`, `test_restore_rebuilds_requested_default_provenance`, `test_restore_preserves_blocked_item_and_restores_other_item`。 |
| [Remove](../../architecture/system/external-workflows.md#4-remove) | `external remove` | `ExternalService.remove` + shared tree observations + source/root locks | `test_external_remove_direct_dry_run_apply_and_cache`, `test_external_remove_dependency_and_reference_blocks`, `test_external_remove_excludes_unsafe_boundary_and_installs`。 |
| [Checkout hook](../../architecture/system/external-workflows.md#6-checkout-hook-reconciliation) | `hook --install` / `hook --run` | `HookService` + existing Git objects + source/root locks | `test_hook_install_is_idempotent_and_preserves_foreign_hook`, `test_post_checkout_aligns_direct_commit_and_revision_provenance`, `test_hook_rechecks_hidden_dependencies_and_unhides_from_parent_manifest`。 |
| [Link parse](../../architecture/system/external-workflows.md#5-link-parse) | Read Skill / CLI | current + portable mapping resolver | `test_portable_broken_link_dependency_can_be_flattened`, `test_link_retry_rejects_a_changed_symlink_target`。 |
| [Worktree](../../architecture/system/worktree-and-cache-workflows.md) | Maintenance Skill / open/list/close | `WorktreeService` + Git detached worktrees + runtime | `test_worktree_dirty_preservation_and_close`, `test_unrecorded_worktree_namespace_path_is_preserved`, `test_interrupted_worktree_publication_leaves_orphan_evidence`。 |
| [Cache clean](../../architecture/system/worktree-and-cache-workflows.md#4-cache-clean) | human/program CLI | `CacheService.clean`/`clean_auto` + Git registration classification | `test_cache_cleanup_preserves_active_then_removes_eligible`, `test_cache_cleanup_accepts_prunable_registration`, `test_cache_cleanup_auto_isolated_candidates`, `test_cache_cleanup_auto_rechecks_each_candidate`。 |
| [Concurrency/recovery](../../architecture/system/concurrency-publication-and-recovery.md) | all write workflows | directory locks、revalidation、atomic JSON/text、error translation | `test_root_lock_conflict_is_bounded_and_preserves_owner`, `test_interrupted_worktree_publication_leaves_orphan_evidence`, `test_restore_rebuilds_requested_default_provenance`, `test_restore_preserves_blocked_item_and_restores_other_item`。 |

## 3. Surface coverage

CLI grammar/effects map to `cli.main._parser/_dispatch`; JSON schema maps to `results.py`, `errors.py`
and service result builders; program subprocess maps to `render_json`; installed agent routing maps to
the three Published Skills. Validators cover all Skills and containing plugin; behavior tests verify old v0
commands are rejected and no stable Python import surface is promised.

## 4. Realization 结论与限制

Native progressive read、full/scoped validation、fixed snapshot、flat dependency、exact restore、offline
mapping、checkout 后的 exact commit/provenance reconciliation、hidden dependency 重判、native-current
maintenance、isolated worktree、explicit source-cache cleanup、agent routing、
bounded JSON 与 subprocess integration 均有当前 realization 和 tests。

第二阶段列出的 17 项 differences 已按新边界重分类：metadata-based validation fingerprint、
scanner-driven support/suppression、Python parser profile、source normalization、JSON identity、
symlink-first link publication、selector-based install key、generic `content_root` fallback、保留
unavailable worktree record，以及现有 `requires_user` 集合，都是 Python realization choice 或
已由 Architecture 接纳的 current behavior，不再标作 coverage gap。CLI 不重复提示通用 Markdown
写作动作，低层排序/hash/serialization 也不属于跨实现 contract。

[DX-REQ-0010](../../../requirements/0010-fix-restore-runtime-record.md) 已修复此前唯一的 material
limitation：restore 现在从 portable default provenance 补回 Python runtime 的
`requested_default`，恢复后 runtime read、link-parse 与 default-intent retry 均由回归测试覆盖。
`source_relation` 沿用 manifest provenance 仍是当前 design choice。当前没有已知的 Architecture
material limitation；其余 operating boundaries 见
[并发与恢复](concurrency-failures-and-recovery.md#5-known-limits)。

## 5. Test topology

[`tests/test_protocol.py`](../../../../impls/libs/python/tests/test_protocol.py) uses filesystem fixtures
and no Git managed state. [`tests/test_git_plugin.py`](../../../../impls/libs/python/tests/test_git_plugin.py)
uses real local Git repositories and calls the CLI composition surface.
[`python.yml`](../../../../.github/workflows/python.yml) runs
`python -m ruff check impls/libs/python` and `python -m pytest impls/libs/python/tests -vv` on Linux、macOS、
Windows and Python 3.11/3.12. Published Skill forward tests are separate installed-product evidence, not
substitutes for domain tests.

## 6. Prohibited regressions

| Regression | Boundary/evidence |
|---|---|
| moving ref refreshes existing install | recorded normalized selector/exact commit reused; moving branch tests。 |
| checkout 将现有 payload 以 moving ref 替代 manifest commit | `HookService._checkout_exact` 只使用 current manifest exact object；真实 post-checkout test。 |
| hidden dependency 被 remove 删除或因上轮 hidden 而忽略 | `preserved_hidden` no-op；每轮 hook 重读 runtime/parent manifest test。 |
| dependency recursively installs inside snapshot | outer runtime parent edges + portable mapping tests。 |
| copy/junction replaces unavailable symlink | native relative symlink only + `symlink_unsupported` test。 |
| dirty/unmanaged close deletes results | exact ownership + current Git status tests。 |
| cache cleanup uses root records or implicit call | standalone `CacheService` Git-registration tests。 |
| CLI/interface defines alternative domain semantics | Architecture model links + result/schema assertions。 |
