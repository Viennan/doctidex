# Python variant user surface

本篇说明 Python `1.0.0` artifact 如何安装、暴露入口，以及 human、agent、program 在这一
variant 下应怎样使用。共同能力和命令语义仍以 [Architecture](../../architecture/index.md)
为权威；本篇只定义 Python packaging/runtime 条件下的最佳接入方式。

## 1. 安装与前置条件

Python variant 需要：

- CPython `3.11` 或更高版本；当前 CI 验证 `3.11` 与 `3.12`；
- 可从 subprocess 调用的 Git executable；需要 external URL 时由 Git 自己提供 credentials；
- 支持安装 package 的 Python environment；
- external link 成功路径需要 filesystem symlink capability，缺失时不会使用 copy/junction
  fallback。

已发布 artifact 的安装应产生 `doctidex-git` console script。仓库本地开发使用项目根
`.venv` 和 editable install：

```text
.venv/bin/python -m pip install -e impls/libs/python
```

这是 repository-maintenance 入口，不应出现在 Published Skills。安装不会自动修改任何
doctidex root；root state 只由调用方后续选择的 apply/open/close operation 改变。

## 2. Human 使用画面

Human 在 shell 中直接调用 `doctidex-git`，可以使用 human summary 探索，但涉及自动化、
精确审阅或 bug report 时使用 `--json`。典型循环是：

1. 确定 cwd 或显式 exact root；
2. 运行 read-only command 或默认 dry-run；
3. 检查 status、findings、affected、network 和 planned changes；
4. 提供 credentials、root、revision、tracking 或 write authority 等缺失决定；
5. 对同一 intent 使用 `--apply`，或改用原生 Git/file tools；
6. 审阅 root changes，并由原生 Git 完成 stage/commit/push。

Human 不需要 import Python modules，也不应编辑 cache、manifest/runtime JSON 或 lock 来绕过
blocked result。unexpected failure 只公开 diagnostic ID；内部 traceback 位于用户 cache，
用于实现维护而不是正常操作决策。

要移除已知 install 时，Human/Program 传回精确 `install_id`，先审阅 `external remove INSTALL_ID`
的 dry-run，再在具备删除授权时使用 `--apply`。只有 presentation path 时应先运行
`external link-parse PATH --json` 并使用返回的 `install_id`；`dependency_parent_install_id` 是
dependency installation 的 parent，不是 remove target。

Human/Program 可以以 `cache clean --url URL` 审阅一个已知 source，或以
`cache clean --auto` 审阅本机所有 recognized source-cache candidate。两种模式都默认 dry-run；
auto 的 JSON 只返回 opaque source ID、每项 outcome 和 aggregate counts，不能依赖或推导内部
cache path/source URL。存在 preserved 或 blocked item 时，先审阅各 item finding；其他 eligible
candidate 不会被回滚，随后可显式重复 `--auto --apply`。

## 3. Agent 使用画面

Agent 的安装后入口是三个 Published Skills：

1. Overview 只读一次，获得 root、selector、managed/native、JSON、pagination 与授权模型；
2. Read 负责渐进导航和 broken symlink diagnosis；
3. Maintenance 负责 validation、external 与 worktree 工作流；
4. 普通 read/search/edit/diff/delivery 继续使用原生工具。

Skills 与 Python console script 必须作为一个交付 surface 保持版本一致。Agent 不读取本
Impls 才能完成任务；Impls 只向 maintainer 解释 Skills 的命令契约由哪些 package components
和 tests 支撑。`cache clean` 是 human/program operator surface，不由 Published Skills 路由。

## 4. Program 使用画面

Program 使用 subprocess，而不是 Python import API：

```python
import json
import subprocess

completed = subprocess.run(
    ["doctidex-git", "validate", root, "--scope", "/docs", "--json"],
    text=True,
    capture_output=True,
    check=False,
)
payload = json.loads(completed.stdout)
if payload["schema_version"] != "1.0":
    raise RuntimeError("unsupported doctidex-git schema")
```

Program 必须：

- 检查 schema major、exit code、status 和 operation；
- 读取 common envelope 的全部 decision fields，而不是只看 stdout 非空或 exit 0；
- 对每个 collection 读取 total/returned/truncated，并原样续传 cursor；
- 在 query/root/state identity 变化或 `cursor_invalid` 后从第一页重启；
- 把 `requires_user` 转交 human/agent，不自动假定 apply、root、revision 或 conflict resolution；
- 不解析非稳定 human output，不读取 private runtime/cache，不依赖 `whero.doctidex.*` internals。

## 5. Variant-specific 选择

| 选择 | Python realization | 用户影响 |
|---|---|---|
| Stable API | console script + JSON schema | subprocess 是跨语言集成边界；当前不能承诺 in-process imports。 |
| YAML/Markdown | `ruamel.yaml` round-trip + `markdown-it-py` CommonMark | frontmatter comments/order 与 link parsing 不靠 ad hoc string processing。 |
| Git | argument-array subprocess，`GIT_TERMINAL_PROMPT=0` | credentials 交给 Git helper；CLI 不弹交互 prompt。 |
| Paths | `pathlib`、Git absolute path output | Linux/macOS/Windows 共享逻辑；root-absolute 与 filesystem absolute 明确分离。 |
| Publication | same-directory temporary file、`fsync`、`os.replace`；directory lock | 单文件/单边界可原子，完整 workflow 仍可能部分成功。 |
| Symlink | 原生 relative directory symlink | capability 不足时 apply 前 blocked，不复制内容。 |

## 6. 失败与下一步

安装或 invocation 不存在时先检查 environment 与 console entry point，不通过 import private
module 规避。Git 不存在、network/credentials/revision 失败时保留 root state，并按 finding
处理外部依赖。平台不能创建 symlink 时保留原 target/index/manifest，报告 capability failure。

测试、coverage、variant choices 与 material limitation 见
[Architecture coverage](architecture-coverage-and-tests.md)；component
入口从 [Python Impls index](index.md#component-realization)进入，跨 component publication 见
[并发、失败与恢复](concurrency-failures-and-recovery.md)。
