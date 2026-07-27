# Source、Mount 与可读呈现

本篇说明 Python 参考实现如何把根 index 中的 Git mount 声明落实为可复用 source、按
commit 读取视图和宿主可读路径。公共生命周期见
[Architecture 子系统与生命周期](../../architecture/subsystems-and-lifecycles.md)；本文
只描述代码设计。

## 1. 模块关系

```text
git.setup -----------------------------> protocol.document + git.context
git.mounts -> protocol.mounts/paths ----> git.repository
     |                                      |
     +-> git.context + git.state            +-> git.runner + git.state
     +-> git.projection --------------------+
```

| 模块 | 职责 | 不负责 |
|---|---|---|
| `git.repository` | 共享 Git object、解析 selector、创建按 commit 视图和维护 worktree。 | mount 声明、宿主路径或公开 payload。 |
| `git.projection` | 为一个宿主构造不可嵌套 namespace 的只读镜像并发布到 mount path。 | 获取 Git object、选择 commit。 |
| `git.mounts` | 扩展 Git 声明、串联 add/remove/prepare/sync、维护 effective state。 | 生成文档语义或执行用户 Git 交付。 |
| `git.setup` | 预览或建立最小 doctidex 根与 ignore 规则。 | 生成 index 正文、准备 mount 或联网。 |

## 2. `git.repository`

### 2.1 `RevisionSelector`

不可变 dataclass，属性 `kind` 与 `value`。`kind` 只能由上层约束为 `commit/tag/branch`；
`as_dict()` 返回公共 `{kind, value}`。类本身不验证空值。

### 2.2 `SourceRepository`

| 属性 | 含义 |
|---|---|
| `url` | 声明中的原始 URL 或本地路径，也是共享 identity。 |
| `directory` | 该 source 的内部根。 |
| `repository` | `repo.git` bare repository。 |
| `revisions` | 按 commit 保存只读 worktree 的目录。 |
| `maintenance` | 独立可写 worktree 的父目录。 |

| 方法 | 主要行为 |
|---|---|
| `ensure()` | 在 source lock 下确保 bare clone 存在。 |
| `resolve(selector, refresh)` | 必要时 fetch，按 selector 表达式解析为严格 40 位 commit。 |
| `revision_view(commit)` | 复用 HEAD 相同的视图，否则 detached add 并递归去除 write bits。 |
| `open_maintenance(commit, identifier)` | 创建新的 detached、可写 worktree。 |
| `remove_maintenance(path)` | 由 bare repository 执行 `worktree remove`。 |

branch 解析到 `refs/remotes/origin/<value>`，tag 解析到 `refs/tags/<value>`，commit 使用
原值。branch/tag fetch 使用明确 refspec；commit 直接 fetch selector。`refresh=False`
仅在本地无法解析时 fetch，`refresh=True` 强制 fetch。

同一 URL 共享 bare objects；同一 commit 共享 revision view；maintenance open 每次都
使用新 identifier，因此写入互不影响。去除 write bits 只防误写，不是安全沙箱。

```python
from whero.doctidex.git.repository import RevisionSelector, SourceRepository

repository = SourceRepository("https://example.test/docs.git")
commit = repository.resolve(RevisionSelector("branch", "main"), refresh=False)
read_only_root = repository.revision_view(commit)
```

## 3. `git.projection`

### 3.1 `build_projection(root, mount_path, source, commit)`

projection key 是 `stable_key(mount_path + NUL + commit)`，作用域位于宿主 `StateStore`
目录。同一宿主、mount path 和 commit 可直接复用；不同 mount path 即使 commit 相同也
各自构建，以绑定正确的宿主 namespace。

镜像规则：普通文件优先 hard link；目录递归建立；`.git` 跳过；source symlink 当前
重建为解析后的绝对 target；source 自有 `.doctidex/mounts` 被宿主 namespace 替换；
递归目录注入回到同一宿主 namespace 的入口。完成后递归清除 write bits，再用 rename
发布。临时构建失败会清理。

### 3.2 `present_projection(...)`

把 projection 发布到 `<root>/<mount-path>`。未登记目标已有内容时抛
`mount_path_occupied`。默认使用临时 symlink + `os.replace`；symlink 不可用时 fallback
为保留 symlink、复制普通目录项的 managed directory。两种方式都失败时包装为
`mount_unreadable`。

`replace_managed` 只表示上层记录认为旧目标由插件管理；当前实现仍拒绝替换普通目录，
因此 fallback presentation 后续 sync 存在限制。

### 3.3 `remove_presentation(...)`

只有 `managed=True` 才删除目标；symlink 用 unlink，普通目录用 `rmtree`。该保护避免
remove 误删没有 state 归属的用户内容。

## 4. `git.mounts`

### 4.1 对象

`GitMount` 是不可变 dataclass：`declaration` 保存协议层 `MountDeclaration`，`selector`
保存 Git revision；`mount_path` 和 `url` 属性转发 declaration。

`GitMountService` 属性：`context` 为宿主 `RootContext`，`root` 为其路径，`store` 为宿主
`StateStore`。service 只处理 `type: git`，其他 mount type 留给协议层。

### 4.2 声明转换与公开 URL

`mounts()` 调用 `read_mounts` 后验证 URL、禁止 `src_path`、要求 revision 恰好包含一个
非空 `commit/tag/branch`。`public_url()` 只移除带 scheme URL 的 userinfo；内部 identity
仍是原字符串。HTTP(S) 内嵌 credentials 被拒绝，其他 URL 主要交给 Git 判断。

### 4.3 方法契约

| 方法 | 写入 | 网络 | 关键结果/约束 |
|---|---|---|---|
| `list()` | 否 | 否 | 声明与 state 必须 URL/selector 匹配；effective commit 且目标存在才 ready。 |
| `add(..., apply)` | apply 写根 index | 否 | 检查路径重叠和 readiness；不 prepare。 |
| `remove(path, apply)` | apply 写 index、移除受管目标和 record | 否 | 先扫描宿主 CommonMark links；不回收共享 source。 |
| `prepare(path)` | 写内部资源与 effective record | 按需 | 复用 effective commit，验证 source root，构建并发布可读路径。 |
| `sync(path, apply)` | apply 且 commit 改变时切换 | 通常是 | old/new 分离；失败时保留旧 effective 说明。 |
| `effective(path)` | 否 | 否 | 返回精确 GitMount 与匹配 record 的 commit。 |

add/remove/prepare/sync 由 `_serialized` 以宿主 `mount-operation.lock` 串行化。list、mounts
和 effective 不持该操作锁，只在读取 state 时使用 state lock。

`_matching_state` 只在 mount path、原始 URL 和 selector 都一致时命中；声明更新会使旧
record 自然失效。`_save_effective` 保存 `url/selector/effective_commit/presentation`。

remove 引用扫描递归宿主 `*.md`，跳过 mount namespace，只检查 CommonMark link target
是否以目标 mount path 开头。它不是完整语义引用分析。

```python
from pathlib import Path

from whero.doctidex.git.mounts import GitMountService
from whero.doctidex.protocol.tree import require_root

context = require_root(Path("/workspace/docs"), operation="mount_list")
service = GitMountService(context)
items = service.list()                 # 只读、本地
prepared = service.prepare(items[0]["mount_path"])
```

## 5. `git.setup`

`initialize(path, apply)` 负责 init 编排：选择已有精确根或以 requested directory 建立新
根，要求 Git worktree，加载或创建根 document，调用 `_ensure_index_structure` 补最小
frontmatter，调用 `ensure_root_gitignore` 补精确 ignore，并生成直接子项语义候选。

`_ensure_index_structure` 维护 `type`、`doctidex.type/root/excludes`，确保 mount exclude，
根路径本身含 `.git` 时再补 `.git` exclude。非法的非列表 excludes 当前会替换成列表。
`_has_required_gitignore` 只用于规划变化。apply false 不写任何文件。

setup 不生成 index body，不 commit，不 prepare mount，也不访问网络。

## 6. 生命周期与错误边界

prepare 顺序、projection namespace 和 state record 的完整图见
[Git Runtime](git-runtime.md)。关键非事务边界是：可读路径发布与 state 保存是相邻但
独立步骤；批量 mount 逐项提交；共享 source 不在 remove 时回收。调用者必须以返回的
逐项结果为准，不能假定跨 mount 原子性。
