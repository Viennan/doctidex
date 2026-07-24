# doctidex Git Agent Plugin 实现细节

状态：Draft，非规范性内部实现文档

本文档描述 [`agent-git-plugin.md`](agent-git-plugin.md) 当前 Python 参考实现的内部
组织。前者定义 agent 可见 surface；本文档用于维护程序代码，不应作为 Skill 使用
前置知识，也不向正常 CLI 输出增加内部路径、对象键、锁或 projection 类型。

## 1. 代码与适配层

实现分成三层：

```text
impls/
├── agent-plugins/
│   └── doctidex-git/
│       ├── skills/                 # 通用 agent 工作流
│       └── .codex-plugin/          # Codex 发现与展示适配
├── libs/python/
│   ├── pyproject.toml
│   └── whero/doctidex/
│       ├── protocol/               # 不依赖 Git 的协议解析与校验
│       ├── git/                    # Git mount、projection 与维护上下文
│       └── cli/                    # doctidex-git 公共命令和输出
└── docs/
    ├── agent-git-plugin.md         # agent surface 方案
    └── agent-git-plugin-implementation.md
```

`whero` 使用 PEP 420 namespace package，不创建 `whero/__init__.py`，以允许其他分发
包共同提供 `whero.*`。Python 分发名是 `whero-doctidex`，import 根是
`whero.doctidex`，公共命令入口是 `doctidex-git`。

Skills 不依赖某个 agent 产品的私有文件工具，agent 可以继续使用自身的读取、搜索、
编辑和 Git 能力。Codex 优化仅位于 `.codex-plugin/plugin.json` 与各 Skill 的
`agents/openai.yaml`，包括发现元数据、显示名称和默认提示。其他支持 Agent Skills
的运行环境可以直接复用 Skill 正文和 CLI。

## 2. 协议层

`whero.doctidex.protocol` 负责：

- 使用 `ruamel.yaml` round-trip 模式解析和更新 frontmatter，保留未知字段、顺序、
  引号与未修改正文；
- 使用 `markdown-it-py` 提取标准 Markdown link；非标准扩展仍由 agent 理解，不会因
  CLI 无法解析而直接判定协议失败；
- 规范化绝对内部路径，处理 `.`、`..` 和不可嵌套 mount namespace；
- 计算宿主范围、来源、负责 index/log 和可重叠的 atomic/protected 属性；
- 分离 `protocol_structure` 与 `semantic_review`。

Regex 使用固定版本第三方 `regex` 包的 `VERSION1 | UNICODE` 模式。输入为相对于负责
index 的规范化完整路径，统一使用 `/`，执行非锚定 search，默认区分大小写。实现不
绑定系统动态库，也不使用 Python `re` 模拟另一个方言。

协议校验会剪枝 excluded 与 mount 内容。atomic 内容不参与普通递归符合性检查，但会
单独检查其中是否出现被禁止的 `index.md` 或 `log.md`。

## 3. Git source 与 revision 视图

默认内部状态根位于 XDG cache；测试可以通过 `WHERO_DOCTIDEX_STATE_DIR` 隔离状态。
内部大致组织为：

```text
<state>/
├── sources/<url-hash>/
│   ├── repo.git/                   # 同一 source 共享的 bare object repository
│   ├── revisions/<commit>/         # 按 commit 复用的只读 worktree
│   └── maintenance/<id>/           # 独立可写 worktree
└── roots/<root-hash>/
    ├── state.json                  # mount 有效 commit 与维护上下文
    └── projections/<key>/          # 与宿主 mount namespace 相关的只读呈现
```

URL hash 只用于内部定位。正常输出只显示清理过凭据的 source URL、声明 revision 和
有效 commit。HTTP(S) mount URL 不接受内嵌凭据；访问凭据交给 Git credential
provider。

首次 prepare 创建或复用 bare repository，解析 selector，再创建 commit worktree。
同一 source 的不同 revision 共享 objects；解析到同一 commit 时共享同一只读
worktree。branch/tag 只在显式 sync 时 fetch 并重新解析。commit selector 已有有效
commit 时不重复解析。

## 4. Lazy projection

声明添加不访问 source。prepare 成功后才创建宿主相关 projection，并把声明的逻辑
mount path 映射到 projection。

projection 递归创建目录并对普通文件使用 hard link，避免复制 source 内容。每个呈现
目录中的逻辑 `.doctidex/mounts` 指回起始宿主唯一 mount namespace，使原生文件工具
访问 `mount-a/path/.doctidex/mounts/mount-b` 时得到宿主 `mount-b`。Git 元数据不进入
projection。

正常路径使用目录符号链接把 mount path 指向 projection；若该映射方式不可用，实现
尝试使用只读目录和 hard link 呈现。切换有效 commit 只替换当前 mount 的呈现，其他
仍引用旧 commit 的 mount 保持原结果。

mount path 的物理内容必须由根 `.gitignore` 中的规则覆盖且不能包含 tracked 内容。
实现只移除自己登记的呈现，不删除未识别目录或文件。

## 5. 维护上下文

`maintenance open` 从 mount 有效 commit 创建新的 detached worktree，并把可访问路径
作为任务必需信息返回。它不复用只读 revision worktree，不切换用户当前分支，也不
改变宿主 mount。

handoff 分别返回该根的 Git status、协议结构与语义候选。close 只移除 clean
worktree；存在变化时返回 `maintenance_has_changes` 并保留路径。commit、push、merge
和 selector 更新均由 agent 说明并交给用户授权。

## 6. 并发与原子性

- 每个 source 使用文件锁串行 clone、fetch 和 `git worktree` 管理；
- 每个宿主根串行 mount 声明、prepare 与 sync 操作；
- 每个 projection key 单独加锁，并通过临时目录加原子 rename 发布；
- `state.json` 使用文件锁、临时文件、`fsync` 和原子 replace 更新；
- 多根维护不是原子事务，任何已产生结果都保留并逐根报告。

内部锁等待和复用命中不进入正常 CLI 输出。Git、网络、凭据、revision 或用户工作区
问题才映射为 agent 可决策的用户层诊断。

## 7. 输出预算

CLI 在解析命令前统一提取 `--json`、`--limit`、`--depth` 和 `--cursor`，所以这些
选项可以位于命令任意位置。默认列表上限为 100，显式 limit 上限为 1000。预算递归
应用于嵌套列表；截断时返回 total、returned、目录计数摘要与下一页 cursor。人读和
JSON 输出共享同一份预算后数据。

CLI 不调用模型、不生成 index/log 内容、不形成语义结论。`check` 的三个结果域为：

- `protocol_structure`：确定性的协议结构；
- `semantic_review`：需要 agent 阅读判断的候选；
- `plugin_readiness`：Git ignore、tracked mount 内容和 Git 扩展状态。

## 8. 安装与验证

项目根 `.venv` 是仓库 Python 活动环境：

```bash
.venv/bin/python -m pip install -e 'impls/libs/python[test]'
.venv/bin/python -m pytest impls/libs/python
```

Plugin 与 Skill 还需分别运行 `plugin-creator` 的 `validate_plugin.py` 和
`skill-creator` 的 `quick_validate.py`。集成测试使用临时本地 Git repositories 和
隔离状态目录，不访问远端。
