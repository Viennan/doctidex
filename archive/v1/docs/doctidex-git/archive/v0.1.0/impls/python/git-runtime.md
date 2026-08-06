# doctidex-git 0.1.0 Python Git、Mount 与维护运行时

本篇解释 `whero.doctidex.git` 的内部对象和生命周期。CLI 使用者通常只需要
`mount_path`、声明 revision、有效 commit、可读状态和 maintenance root；实现维护者
需要理解这些公开概念如何映射到 bare repository、worktree、projection 和 state。

本篇是物理布局、state schema 和跨模块时序的权威说明。单个模块的调用契约分别见
[Git Context 与 State](git-context-and-state.md)、
[Source、Mount 与可读呈现](sources-mounts-and-projection.md)和
[Maintenance 实现](maintenance.md)，这里不重复代码示例。

## 1. 运行时目录

`state_home()` 按以下顺序选择内部状态根：

1. `WHERO_DOCTIDEX_STATE_DIR`；
2. `$XDG_CACHE_HOME/whero-doctidex`；
3. `~/.cache/whero-doctidex`。

`WHERO_DOCTIDEX_STATE_DIR` 主要用于测试和隔离运行。默认布局为：

```text
<state-home>/
├── sources/<sha256(raw-url)>/
│   ├── source.lock
│   ├── repo.git/
│   ├── revisions/<40-char-commit>/
│   └── maintenance/<timestamp-random-id>/
├── roots/<sha256(absolute-root-path)>/
│   ├── state.lock
│   ├── mount-operation.lock
│   ├── state.json
│   └── projections/
│       ├── .<projection-key>.lock
│       └── <sha256(mount-path-NUL-commit)>/
└── diagnostics/<diagnostic-id>.log
```

Hash 由字符串的 UTF-8 字节做 SHA-256。source identity 当前使用未经规范化的原始 URL
字符串，所以语义相同但文本不同的 URL 不共享 source directory。root identity 使用
`root.absolute()` 的字符串，不解析 symlink；通过不同 symlink 路径访问同一目录可能
形成不同 root state。

## 2. State store

每个宿主根有独立 `StateStore`。`state.json` 的内部 schema 为：

```json
{
  "version": 1,
  "root": "/work/host",
  "mounts": {
    "/.doctidex/mounts/design": {
      "url": "https://example.com/design.git",
      "selector": {"kind": "branch", "value": "main"},
      "effective_commit": "0123456789abcdef0123456789abcdef01234567",
      "presentation": "managed"
    }
  },
  "maintenance": {
    "1720000000-a1b2c3d4": {
      "path": "/cache/.../maintenance/1720000000-a1b2c3d4",
      "host_root": "/work/host",
      "mount_path": "/.doctidex/mounts/design",
      "url": "https://example.com/design.git",
      "base_commit": "0123456789abcdef0123456789abcdef01234567",
      "target_branch": "main"
    }
  }
}
```

### 2.1 顶层字段

| 字段 | 含义 |
|---|---|
| `version` | 内部 state schema 版本，当前固定补全为 `1`。没有迁移逻辑。 |
| `root` | 最近一次 state 更新时保存的宿主绝对路径；只读旧 state 时可能缺失。 |
| `mounts` | 以逻辑 `mount_path` 为 key 的有效读取状态。 |
| `maintenance` | 以内部随机 identifier 为 key 的开放维护上下文。 |

### 2.2 Mount record

| 字段 | 含义 |
|---|---|
| `url` | 声明中的原始 URL，用于确认 state 仍匹配当前声明。 |
| `selector.kind` | `commit`、`tag` 或 `branch`。 |
| `selector.value` | 对应声明值。 |
| `effective_commit` | 当前 presentation 应读取的完整 40 位 commit。 |
| `presentation` | 当前只写 `managed`，表示该 mount path 由本实现创建并可在 remove 时清理。 |

如果 URL 或 selector 与当前根 index 声明不同，`_matching_state` 把 record 当作不存在，
不会复用其中的 effective commit，也不会立即删除旧 record 对应的物理缓存。

### 2.3 Maintenance record

| 字段 | 含义 |
|---|---|
| `path` | 独立可写 worktree 的绝对路径。 |
| `host_root` | 创建该记录的宿主根，用于由显式 maintenance root 恢复宿主上下文。 |
| `mount_path` | 它来自哪个宿主 mount。 |
| `url` | 原始 source URL，用于 status、handoff 和 close。 |
| `base_commit` | open 时 mount 的有效 commit。 |
| `target_branch` | selector 是 branch 时为 branch 名；tag/commit 时为 `null`。它只是交付提示，不表示 worktree 已 checkout 该 branch。 |

读取到不存在、非法 JSON 或非 mapping state 时，当前实现静默回到空的 version 1 state。
这可以恢复基本操作，但可能使已有 presentation 或 maintenance worktree 失去登记；代码
当前没有自动重建或垃圾回收。

State 更新持有 `state.lock`，在同目录写临时 JSON、`fsync` 后 `os.replace`。JSON 使用
缩进 2、key 排序并以换行结尾。

## 3. Git 命令边界

`git.runner.git()` 使用 `subprocess.run` 执行系统 `git`，捕获 stdout/stderr，不使用
shell。环境未显式设置 `GIT_TERMINAL_PROMPT` 时补为 `0`；如果调用环境已经设置该
变量，代码保留其值。

失败文本按简单 substring 分类：

| 分类 | code | 用户层含义 |
|---|---|---|
| credentials/permission | `git_auth_required` | 需要仓库访问权限。 |
| DNS/连接/超时 | `git_network_unavailable` | 当前网络不可用；已有有效 commit 时可继续读旧结果。 |
| ref/object 不存在 | `git_revision_unavailable` | selector 不能解析。 |
| 其他 Git 错误 | `git_failed` | 需要检查 Git 现场后重试显式操作。 |

该分类依赖 Git 英文错误片段；未命中时统一为 `git_failed`，不会把原始 stderr 放进
普通 CLI 输出。

## 4. Source repository

`SourceRepository(url)` 表示一个原始 URL 对应的共享 Git object store：

| 属性 | 路径/含义 |
|---|---|
| `directory` | `<state>/sources/<url-hash>`。 |
| `repository` | `repo.git` bare repository。 |
| `revisions` | 按 commit 存放只读 worktree。 |
| `maintenance` | 按任务 identifier 存放可写 worktree。 |

### 4.1 Ensure

`ensure()` 在 `source.lock` 下检查 `repo.git`。不存在时执行：

```text
git clone --bare <url> <repo.git>
```

已有目录被直接视为 repository；当前没有额外执行 bare/config/remote 完整性检查。

### 4.2 Revision selector

`RevisionSelector` 有两个字段：

| 字段 | 含义 |
|---|---|
| `kind` | `branch`、`tag` 或 `commit`。 |
| `value` | 用户声明的非空字符串。 |

Git mount 中 `revision` 必须是只含上述一个 key 的 mapping。`src_path` 被显式拒绝。

解析表达式为：

| kind | fetch refspec | rev-parse expression |
|---|---|---|
| `branch` | `+refs/heads/V:refs/remotes/origin/V` | `refs/remotes/origin/V^{commit}` |
| `tag` | `+refs/tags/V:refs/tags/V` | `refs/tags/V^{commit}` |
| `commit` | 原值 `V` | `V^{commit}` |

`resolve(selector, refresh)` 在 source lock 内完成：

1. ensure bare repository；
2. `refresh` 为真，或本地 rev-parse 失败时 fetch；
3. `rev-parse --verify <expression>^{commit}`；
4. 只接受长度恰好为 40 的输出。

prepare 使用 `refresh=False`，能从现有 object/refs 解析时不访问远端。sync 与 online
check 使用 `refresh=True`。固定 commit 若已有保存的 effective commit，sync 直接复用
旧值；没有保存值时仍尝试 fetch 声明 commit。

### 4.3 Revision view

`revision_view(commit)` 的目标固定为 `revisions/<commit>`。已存在目录只有在其 `HEAD`
恰好等于该 commit 时才复用，否则报 `revision_view_unavailable`。新 view 通过：

```text
git --git-dir <repo.git> worktree add --detach <view> <commit>
```

创建后递归清除普通文件和目录的所有写 bit；symlink 和名为 `.git` 的文件跳过。这个
“只读”用于防止 agent 误写，不是安全边界：拥有文件的 OS 用户仍可 chmod。

同一原始 URL 的不同 selector 共享 bare objects；解析到同一 commit 时命中同一 view；
不同 commit 具有不同 view，因此可以同时读取。

## 5. Git mount 声明

Git 层把基础 `MountDeclaration` 与 `RevisionSelector` 合成 `GitMount`。只处理
`type: git`；其他 mount type 对基础协议计数可见，但不出现在 Git mount list。

URL 校验当前要求：

- 非空、单行；
- HTTP(S) URL 不得包含 username/password；
- 本地路径和其他 Git URL 形式允许交给 Git 解释。

`public_url()` 对具有 scheme/netloc 且含 `@` 的 URL 移除 userinfo。无 scheme 的文本
原样返回。state 和 source identity 仍使用原始 URL；清理只作用于公开输出。

## 6. Git ignore 就绪状态

`root_gitignore_status(root)` 先用 `git rev-parse --show-toplevel` 找到 Git worktree。
不在 Git worktree 内时返回：

```json
{"status": "not_applicable", "ignored": false, "tracked": []}
```

在 Git 内时，它对 `<root>/.doctidex/mounts/.doctidex-ignore-probe` 执行
`git check-ignore -v --no-index`，并要求命中的 source file 恰好是根目录自己的
`.gitignore`。父级 `.gitignore`、全局 ignore 和 `.git/info/exclude` 即使能忽略路径，
也不会令 `ignored` 为真。

随后 `git ls-files` 查找 mount 目录下的 tracked path。字段为：

| 字段 | 含义 |
|---|---|
| `status` | 根规则覆盖且无 tracked 内容时 `ready`，否则 `blocked`。 |
| `ignored` | 是否由根 `.gitignore` 覆盖。 |
| `ignore_file` | 期望生效的根 `.gitignore` 路径；不在 Git 时缺失。 |
| `tracked` | Git index 中 mount namespace 下的路径列表。 |

`ensure_root_gitignore` 只识别去除两侧空白后完全等于 `/.doctidex/mounts/` 的行；缺少
时追加该精确行，保留已有内容并确保前置换行。

## 7. Mount 生命周期

### 7.1 List

`list()` 对每个 Git mount 查找匹配 state，并检查逻辑 destination 是否存在或是
symlink。只有同时存在 effective commit 和 destination 才返回 `ready/readable`；其他
情况统一为 `not_prepared`，即使 state 中仍保存 commit。

### 7.2 Add

add 依次检查 mount path、URL、已有声明重叠和 Git ignore 就绪状态。dry-run 返回
有效计划。apply 重新加载根 index，以 round-trip mapping 追加：

```yaml
- type: git
  url: <url>
  revision:
    <kind>: <value>
  mount_path: <path>
```

它不访问 source，成功状态始终为 `not_prepared`。

### 7.3 Remove

remove 递归扫描宿主根 `*.md`，跳过路径字符串中含 `.doctidex/mounts` 的文件，并仅
检查 CommonMark link target 是否以 mount path 开头。存在引用时阻止操作。

apply 从根 index 删除原始 mapping；只有 state 中登记该 mount 时才移除逻辑
presentation，然后删除 state record。它不删除 shared bare repository、revision view
或 projection 缓存。

### 7.4 Prepare

prepare 的完整顺序为：

1. 要求精确声明的 Git mount；
2. 要求根 Git ignore 状态 `ready`；
3. 查找 URL/selector 匹配的 state record；
4. 没有 effective commit 时解析 selector；
5. 创建或复用 revision view；
6. 验证 view 根有 `index.md` 且 `doctidex.root is True`；
7. 构建 projection；
8. 呈现到逻辑 mount path；
9. 保存 effective commit。

### 7.5 Sync

sync 先计算 old/new commit。解析失败且 old 存在时，blocked result 会说明旧 commit
仍可读。dry-run 在得到 new 后返回，不替换 presentation。apply 只有在 old/new 不同
时检查 Git ignore、验证源、构建并替换 projection，最后更新 state。

不指定 mount path 时，prepare/sync 对所有 Git mounts 顺序执行。单项失败不会撤销
前面成功项，批量结果记录 completed/total 和逐项 payload。

## 8. Projection 与 presentation

### 8.1 Projection key

projection 归属于宿主 root state，key 为 `sha256(mount_path + NUL + commit)`。因此同一
commit 挂到不同逻辑路径时使用不同 projection；这使每个 projection 都能绑定宿主
唯一 namespace。

### 8.2 目录镜像

构建逻辑为：

- 普通文件用 hard link，不复制内容；
- 普通目录递归创建；
- `.git` 被跳过；
- source symlink 被重建为指向其 `resolve(strict=False)` 的绝对 target；
- source 自有 `.doctidex` 被复制，但其 `mounts` 条目被替换；
- 每个递归目录都注入 `.doctidex/mounts` symlink，指向起始宿主的 namespace；
- 完成后递归清除 projection 普通文件和目录的写 bit。

注入 namespace 使原生文件工具沿 mounted content 遇到后续
`.doctidex/mounts/...` 时回到宿主唯一 mount 表。projection 通过临时目录构建，并用
`os.replace` 发布；相同 key 已存在时直接复用。

### 8.3 Presentation

默认在 `<host-root>/<mount-path>` 创建临时目录 symlink，再原子替换为指向 projection
的 symlink。symlink 创建失败时，fallback 使用保留 symlink、对普通文件 hard link 的
`copytree` 目录。

首次 prepare 若 destination 已有任何内容，会报 `mount_path_occupied`。替换已登记的
presentation 时，当前实现只安全替换 symlink；已存在的普通目录会被拒绝，即使它是
之前 fallback 产生的 managed 目录。该行为列在当前限制中。

若两种呈现方式都失败，返回 `mount_unreadable`。remove 只在 `managed=True` 时删除
symlink 或整棵 destination，避免清理未登记的用户内容。

## 9. Maintenance root

### 9.1 Scope

`maintenance scope` 用 `inspect_path` 把输入归并为：

- `host_root`：当前宿主本身可写；
- `mounted_source`：host mount 只读，并附带 relation、reuse 与必要时的 open action。

同一宿主或同一 mount 的多个输入去重。base commit 对宿主取当前 `HEAD`，对 mount 取
state 中 effective commit，可以为 `null`。host item 还返回当前 symbolic branch；mount
item 返回 declared revision 和 branch selector 对应的 target branch。结果是本次调用时
的观察，不含计划分配状态；重复调用不会保存或覆盖调用者的计划。

调用者先依据 `root_relation` 和 `maintenance_reuse` 选择兼容的 host root 或已有
maintenance root。reuse 过滤 source/base commit 不匹配、路径已丢失及已知 target branch
冲突的候选；任一 branch 未知时仍交给调用者按交付意图决定。只有不存在可复用范围，
或调用者明确需要隔离时，才对 mounted source 执行 `maintenance open`。最终范围及其
执行边界由调用者维护，`scope()` 不在 state 中登记这一决策。

### 9.2 Open

open 要求 effective commit 已存在。identifier 为秒级 Unix timestamp 加 8 位随机
hex。内部执行 detached worktree add，写入 maintenance record，并返回
`maintenance_root`/`writable_root`。branch selector 的 `target_branch` 只用于提醒最终
交付目标；worktree 仍是 detached HEAD。

### 9.3 Status

不传 maintenance root 时返回宿主 state 登记的全部上下文；传入时按绝对路径精确
过滤。每条新 record 保存 `host_root`，state 顶层也在写入时保存 root；CLI 可扫描
登记，用显式路径定位所属宿主 state，所以调用不要求保留 open 时的 cwd。目录不存在
时 changes 为空并显示 `ready`，当前不会单独报告“登记存在但路径丢失”。

### 9.4 Handoff

handoff 必须选中恰好一个 record。它要求维护根直接含可解析 `index.md`，然后：

1. 运行完整 protocol validation；
2. 读取 Git porcelain changes；
3. 检查该维护根自己的 `.gitignore` 就绪状态；
4. 为非 index/log change 添加语义候选；
5. 返回独立的协议、语义、插件就绪和 Git 结果。

它不 commit、push、merge 或更新宿主 selector。

显式 maintenance root 与 status 使用同一所属宿主定位；省略参数时则只检查 cwd 所选
宿主的 records。

### 9.5 Close

close 同样要求恰好一个 record。只要 `git status --porcelain` 非空，就返回
`maintenance_has_changes` 并保留 worktree。clean 时用 bare repository 执行
`git worktree remove`，随后删除 state record。

## 10. 锁与非原子边界

| 锁 | 保护范围 |
|---|---|
| `source.lock` | 同一原始 URL 的 clone、fetch、revision/maintenance worktree 操作。 |
| `state.lock` | 单宿主 `state.json` 读写。 |
| `mount-operation.lock` | 单宿主 add/remove/prepare/sync。 |
| projection lock | 单个 mount-path/commit projection 构建。 |

锁使用阻塞式 `fcntl.flock(LOCK_EX)`，没有超时和公开等待状态。跨多个 source、多个
mount 或多个 doctidex 根没有总事务；失败时以每个已完成结果为准。
