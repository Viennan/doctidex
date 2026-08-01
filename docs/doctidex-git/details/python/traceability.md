# Architecture 追踪矩阵

本页把语言无关 Architecture 映射到 Python producer、公共 consumer、实现说明和测试证据。
Architecture 仍是行为权威；本表只回答“当前代码在哪里落实、由谁消费、如何验证”。

| Architecture 权威 | 主要 producer | 公共 consumer | Details | 主要测试证据 |
|---|---|---|---|---|
| [用户接口](../../architecture/user-surface.md) | CLI dispatch、External/Worktree service | 三个 Published Skills、human/program CLI | [Package 与 CLI](package-results-and-cli.md)、[External](external.md) | `test_git_plugin.py` 的 native/managed 选择、旧 surface 拒绝与端到端场景 |
| [用户工作流](../../architecture/workflows.md) | `validate_protocol`、`ExternalService`、`WorktreeService` | Read/Maintenance Skills | [协议校验](protocol-validation.md)、[External](external.md)、[Worktree](worktrees-cache-and-testing.md) | scoped validation、install/link/restore/link-parse、dirty close、cache 生命周期 |
| [CLI](../../architecture/interfaces/cli.md) | `cli/main.py` parser/root dispatch | shell、agent、程序 | [Package 与 CLI](package-results-and-cli.md) | 参数互斥、默认 dry-run、nested root、source kind、revision failure 与 exit code |
| [JSON Schema](../../architecture/interfaces/cli-schema.md) | `results.py`、`errors.py`、各 service result builder | `--json` consumer | [Package 与 CLI](package-results-and-cli.md) | 测试 helper 对每个成功 operation 检查公共 envelope 与 required fields；cursor/blocked 单独覆盖 |
| [领域模型](../../architecture/domain-model.md) | document/root/result dataclass、portable/runtime records | CLI operation fields | 各模块页面的类型与全部属性段落 | manifest/record 自洽、selector identity、dependency summary、WorktreeItem 状态 |
| [子系统与生命周期](../../architecture/subsystems-and-lifecycles.md) | protocol/source/storage/external/worktree 分层 | CLI orchestrator | [Git 来源与状态](git-source-and-storage.md)及各领域页 | fixed commit、扁平 dependency/self edge、restore、symlink preflight、dirty/orphan preserve、cache recheck |
| [约束与失败](../../architecture/constraints-and-failures.md) | `DoctidexError`、Git sanitization、root/source lock | Skills 与 JSON consumer | [Package 与 CLI](package-results-and-cli.md)、[Git 来源与状态](git-source-and-storage.md) | broad ignore、tracked/path conflict、manifest/symlink damage、cursor invalid、active cache preserve |
| [Skill 系统](../../architecture/skill-system.md) | Overview、Read、Maintenance artifacts | installed agent | 本页不复制 Skill 用法 | Skill validators、plugin validator、独立 scoped/broken-link/worktree forward tests |
| [程序集成](../../architecture/interfaces/programmatic-integration.md) | versioned JSON renderer、pagination | subprocess JSON consumer | [Package 与 CLI](package-results-and-cli.md) | schema required-field set、稳定 query identity、分页 continuation 与状态变化拒绝 |

## 禁止偏离的证据

| 禁止行为 | 实现边界 | 证据 |
|---|---|---|
| 旧 mount/projection/maintenance surface | parser 与 package 不再导入旧模块 | 旧命令返回 `argument_invalid`；v0 文件仅在 archive |
| moving selector 刷新既有 install | runtime 保存 normalized selector 与 exact commit，重试从 record 构造 source | default/branch 移动后的 install ID、path、commit 不变 |
| install 内递归依赖 | parent edge 只写 outer owner root runtime | portable broken link 在 outer root 扁平安装后返回外层 `working_path` |
| copy/junction symlink fallback | link 只调用相对 `symlink_to`，capability 失败提前 blocked | `symlink_unsupported` 不改变 index、manifest 或 target |
| dirty/unmanaged destructive close | close 要求 exact record 且重新计算 Git state | dirty 与孤立 namespace path 均保留 |
| 隐式或不安全 cache 清理 | 独立 `cache clean` 只按 Git worktree metadata、默认 dry-run并二次分类 | valid registration preserved、prunable registration planned/removed |

当前没有稳定 Python import API。逻辑只读权限不是 sandbox，真实远端凭据/network 故障依赖
Git 的客观返回并在 CLI 边界清理；这些限制不改变 Architecture 的公共命令与 JSON 契约。
