# 开发、测试与当前限制

本篇面向维护当前 Python 参考实现的开发者。这里的源码路径、editable 安装和内部环境
变量不应复制到发布给用户的 Skills。

## 1. 本地环境

仓库根 `.venv` 是本项目 Python 活动环境：

```bash
.venv/bin/python -m pip install -e 'impls/libs/python[test]'
```

distribution 配置位于 `impls/libs/python/pyproject.toml`。依赖为：

| 依赖 | 用途 |
|---|---|
| `ruamel.yaml>=0.18,<0.19` | round-trip frontmatter。 |
| `markdown-it-py>=3.0,<5` | CommonMark link token。 |
| `regex==2026.7.19` | 固定 VERSION1 Unicode filter 方言。 |
| `pytest>=8,<9` | 测试 extra。 |
| `ruff==0.16.0` | lint extra。 |

Python requirement 声明为 3.11 以上，但 `fcntl` 使当前 Git state/lock 实现实际上只支持
POSIX。

## 2. 验证命令

```bash
.venv/bin/python -m pytest impls/libs/python
.venv/bin/ruff check impls/libs/python
python3 /home/wiennan/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  impls/agent-plugins/doctidex-git
```

每个 Skill 还应运行：

```bash
python3 /home/wiennan/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  impls/agent-plugins/doctidex-git/skills/<skill-name>
```

测试通过 `WHERO_DOCTIDEX_STATE_DIR` 把 state 隔离到 pytest 临时目录，使用本地临时 Git
repositories，不访问远端。

## 3. 当前测试覆盖

`tests/test_protocol.py` 覆盖：

- mount namespace 规范化；
- VERSION1 Unicode regex search；
- YAML/正文 round-trip 与 link 提取；
- excluded traversal 剪枝和递归语义候选；
- malformed child index 与 atomic 内禁止文档；
- 普通 Markdown link 越界。

`tests/test_git_plugin.py` 覆盖：

- init 和根 Git ignore；
- 两个同 source/branch mount 的 lazy prepare；
- nested namespace 通过原生文件系统读取；
- `resolve --from` 对 mounted source 普通 link 与宿主 namespace 回边的选择；
- 普通嵌套根的 resolve 歧义与 cwd 精确选择；
- inspect 从宿主 cwd 保留 mount/source 双重上下文；
- sync dry-run/apply 与不同 mount 保留不同有效 commit；
- 独立 maintenance root、显式路径跨 cwd status/handoff/close 与有变化时禁止 close；
- protocol structure 与 plugin readiness 分离。

当前测试没有完整覆盖所有 CLI 字段、所有错误 code、远端认证/网络、并发、fallback
presentation、cursor 多列表语义或 state 损坏恢复。

## 4. 环境变量与外部程序

| 名称 | 当前行为 |
|---|---|
| `WHERO_DOCTIDEX_STATE_DIR` | 覆盖整个内部 state home；测试推荐使用。 |
| `XDG_CACHE_HOME` | 未设置专用 override 时决定 state base。 |
| `GIT_TERMINAL_PROMPT` | 未设置时由 runner 设为 `0`；调用环境显式值会保留。 |

实现直接调用 PATH 中的 `git`，当前没有启动时版本检查。Python 包安装成功不代表系统
Git 一定可用。

## 5. 新增或修改 CLI 字段时

字段变化会影响 agent surface。至少同步：

1. 返回 dict 的生产代码；
2. JSON 成功与 blocked 测试；
3. `cli-output.md` 的公共字段、nested schema 和对应 operation；
4. `cli-commands.md` 的副作用和网络说明；
5. `agent-interpretation.md` 中依赖该字段的决策；
6. 对应 Skill，前提是 agent 实际需要知道该变化；
7. `agent-git-plugin.md`，如果公开 surface 契约也发生变化。

不要只更新人读 renderer：JSON dict 是字段事实来源，人读输出从同一 payload 派生。

## 6. 当前已知限制

以下是当前代码事实，不是目标设计。修复后应同时更新本目录和测试。

### 6.1 CLI 与输出

- `--depth` 被解析并限制到 0..32，但未参与任何遍历或裁剪。
- 同一 `--cursor` offset 应用于 payload 中所有顶层列表，没有 collection-specific cursor。
- `mount_sync.changed` 是 boolean；其他多数 operation 的 `changed` 是路径数组。
- write command 不传 `--dry-run` 或 `--apply` 时默认不 apply，但输出并不都含
  `applied`。
- argparse 和全局整数解析发生在统一错误处理之前，`--json` 不能保证参数错误为 JSON。
- blocked 人读输出只展示第一个 finding，并隐藏 `details`；复杂失败必须用 JSON。
- `status: warning` 且 `plugin_readiness: blocked` 当前退出 0；只有 protocol fail 退出 1。

### 6.2 协议校验

- link 校验只检查可解析路径是否越过 link root，不检查文件存在、anchor、推荐形式或
  跨 mount 目标有效性。
- link/语义候选只理解 CommonMark `link_open`；非标准扩展、图片、裸路径和 prose
  reference 不进入机器判断。
- `validate_filter_conditions` 处理“过滤字段本身不是 list”时，错误消息引用了未定义的
  `field` 变量。当前会被顶层转换为 `unexpected_failure`，而不是预期的
  `filter_not_list` finding。
- malformed child index 在路径上下文计算中暂由父 index 负责，只有完整 validation
  才报告子文件错误。
- source prepare 只确认 source 根 index 存在且 `doctidex.root is True`，不会在呈现前
  要求 source 整体 `protocol_structure: pass`。

### 6.3 Git 就绪与 URL

- 根 `.gitignore` 的 `git check-ignore -v` source 是相对路径时，代码用进程 cwd 而非
  Git worktree 解析它。从宿主子目录运行命令可能把正确根规则误判为未覆盖。
- source identity 是原始 URL 文本，没有 canonicalization；等价 URL 可能重复 clone。
- HTTP(S) 内嵌 credentials 被拒绝；其他 Git URL 形式主要交给 Git，公开 URL 清理也
  只处理具有 scheme/netloc 的 userinfo。
- Git 错误分类依赖英文 stderr substring；本地化或不同 Git provider 文案可能落入
  `git_failed`。
- online check 和无路径 batch sync 对每个 mount 顺序调用 resolve；即使 source 相同，
  当前也可能重复 fetch，没有实现跨 selector fetch batch。

### 6.4 State 与生命周期

- 非法或不可读 `state.json` 静默退回空 state，没有自动恢复、告警或 orphan 扫描。
- root identity 不解析 symlink；同一物理根的不同访问路径可能使用不同 state store。
- 没有 garbage collection：已删除声明留下的 bare objects、revision views、projections
  和失配 record 不自动清理。
- maintenance record 指向的目录丢失时，`maintenance status` 返回空 changes 和
  `state: ready`，没有专门 unavailable 状态。
- file locks 无超时，等待状态不进入 CLI。

### 6.5 Projection

- symlink presentation 失败后的 fallback 是普通 managed 目录；后续 sync 当前拒绝替换
  已存在普通目录，因此 fallback mount 可能无法直接更新。
- source symlink 在 projection 中被重建为其解析后的绝对 target，可能离开 source root；
  当前没有额外边界验证。
- hard link 与 chmod 的“只读”不构成安全沙箱；同一 OS 用户可以改变权限。
- presentation fallback、跨 filesystem hard-link 失败、Windows 和各类 symlink 权限现场
  尚无自动化测试。

### 6.6 语义和 agent surface

- CLI 不读取任务意图，不对候选排序，也不形成内容质量结论。
- `inspect` 为生成 semantic candidates 会运行整根 protocol validation，尚无增量索引。
- `context.mode` 通过路径字符串片段判断，不校验声明或 exact namespace root。
- `check` 不返回 protocol library 的 `mount_count`，handoff 的 findings 也不加入独立
  plugin readiness finding。

## 7. 诊断文件

未预期异常由 `write_diagnostic` 写入：

```text
<state-home>/diagnostics/<12-char-id>.log
```

文件包含 Python traceback。CLI 只返回 12 位 `diagnostic_id`。诊断可能含内部路径，
只用于开发排障，不应原样写入 doctidex 内容或普通 agent 回复。
