# Python 开发与测试

本篇面向维护 Python 参考实现的开发者。仓库路径、editable 安装和内部环境变量不得
复制到发布给用户的 Skills。当前代码缺口单独见[已知限制](known-limitations.md)。

## 1. 本地环境

使用仓库根 `.venv`：

```bash
.venv/bin/python -m pip install -e 'impls/libs/python[test]'
```

distribution 配置在 `impls/libs/python/pyproject.toml`。运行要求 Python 3.11+，但 state
lock 使用 `fcntl`，当前 Git 场景实际上要求 POSIX。系统 PATH 还必须提供 Git；包安装
不会验证 Git 版本。

| 依赖 | 用途 |
|---|---|
| `ruamel.yaml>=0.18,<0.19` | round-trip frontmatter。 |
| `markdown-it-py>=3.0,<5` | CommonMark link token。 |
| `regex==2026.7.19` | VERSION1 Unicode filter 方言。 |
| `pytest>=8,<9` | test extra。 |
| `ruff==0.16.0` | lint extra。 |

## 2. 验证命令

```bash
.venv/bin/python -m pytest impls/libs/python
.venv/bin/ruff check impls/libs/python
python3 /home/wiennan/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  impls/agent-plugins/doctidex-git
```

每个变更 Skill 还需运行仓库环境提供的 Skill validator。validator 的本机路径属于开发
环境，不应写进 Skill。

测试通过 `WHERO_DOCTIDEX_STATE_DIR` 把 state 隔离到 pytest 临时目录，并使用本地临时
Git repositories，不访问远端。

## 3. 测试地图

`tests/test_protocol.py` 覆盖：mount namespace 规范化、VERSION1 regex、文档
round-trip、CommonMark link、excluded 剪枝、递归语义候选、malformed child index、
atomic 内禁止文档和 link 越界。

`tests/test_git_plugin.py` 覆盖：init/ignore、同源多 mount lazy prepare、namespace 回边
读取、resolve `--from`、嵌套根歧义、inspect 双重上下文、独立 effective commit sync、
maintenance 跨 cwd 生命周期、changes 阻止 close、根自引用同/different commit、nested
root 保守 unknown、已有同 source/base commit scope 复用，以及 protocol/readiness 分域。

当前缺失覆盖集中列在[已知限制](known-limitations.md)，尤其是远端认证/网络、并发、
fallback presentation、cursor 多列表和 state 损坏恢复。

## 4. 环境变量与诊断

| 名称 | 当前行为 |
|---|---|
| `WHERO_DOCTIDEX_STATE_DIR` | 覆盖整个内部 state home；测试推荐使用。 |
| `XDG_CACHE_HOME` | 未设置专用 override 时决定 state base。 |
| `GIT_TERMINAL_PROMPT` | 未设置时由 runner 设为 `0`；调用环境显式值保留。 |

未预期异常写入 `<state-home>/diagnostics/<12-char-id>.log`，内容是 Python traceback。
CLI 只返回 `diagnostic_id`。诊断可能含内部路径，不应原样写入 doctidex 内容或普通用户
回复。

## 5. 变更同步范围

修改 CLI 命令或字段时至少同步：

1. producer、parser、dispatch 和 service；
2. JSON 成功、warning、blocked 与 pagination 测试；
3. [CLI 用户接口](../../architecture/interfaces/cli.md)；
4. [CLI 结果契约](../../architecture/interfaces/cli-schema.md)；
5. 依赖该行为的 Architecture 工作流；
6. agent 实际需要知道时的对应 Skill；
7. [Python CLI 详情](cli-and-rendering.md)及相关模块文档。

不要只更新人读 renderer。修改协议解释、mount 生命周期或 Skill surface 时，也要按
AGENTS.md 的层级边界同步相应 Architecture、Details、Skills 和测试。

## 6. 新测试的组织

- 协议纯函数和目录遍历优先放 `test_protocol.py`，不引入 Git state。
- Git 生命周期放 `test_git_plugin.py`，每个测试使用独立 root、source 和 state home。
- 成功断言同时检查公共结果和文件现场；失败断言检查 code、保留结果和下一步。
- write 命令同时覆盖 preview 不写与 apply 写入。
- collection 场景断言总数、当前页、truncated 和 opaque cursor，而非内部 token 编码。
- 修复已知限制时先增加能复现旧行为的回归测试，再更新文档中的限制条目。
