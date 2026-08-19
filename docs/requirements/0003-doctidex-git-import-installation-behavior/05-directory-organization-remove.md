# 需求 0003-05：Installation 目录组织与 remove 语义

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0003-05` |
| 状态 | `draft` |
| 日期 | 2026-08-20 |
| 父需求 | [需求 0003](overview.md) |
| 影响范围 | `import install/restore/remove`、`validate/repair`、`runtime.json` |

## 1. 需求意图

在阶段 4 基础上，将 Installation 目录组织收敛为 commit-hash 物理目录加 branch/tag 符号链接，
并实现 `ParentImporter` 关系和 remove 语义。

## 2. 设计目标

- 只有 commit-hash Installation 对应真实 Git worktree。
- branch/tag Installation 是同一 commit-hash 的语义化别名，`install-path` 为符号链接路径。
- owner 与 Installation 各自 RuntimeState 保持独立，不融合。
- `import remove` 在保证引用关系安全的前提下删除对象。

## 3. 数据模型

### 3.1 `ParentImporter`

`Installation.import_by_installations` 为 `ParentImporter` 列表，写入 `runtime.json`，不写入
`imports.json`。

```jsonc
{
  "install-id": "<OWNER-LEVEL-INSTALL-ID>",
  "importer-level": "owner",
  "sub-installation-ids": []
}
```

字段：

| 字段 | 含义 |
|---|---|
| `install-id` | 引入该目标 Installation 的 owner-level `install-id`。 |
| `importer-level` | `owner` 或 `installation`。 |
| `sub-installation-ids` | 当 `importer-level` 为 `installation` 时，记录 Installation 内匹配到该 commit-hash Installation 的子 Installation。 |

### 3.2 自身 owner-level 条目

owner 直接 `import install --commit` 创建的 commit-hash Installation，必须在
`import-by-installations` 中写入自身 owner-level 条目，防止其他 ParentImporter 被移除时连带
删除该直接安装对象。

## 4. 目录组织

```text
<owner>/.doctidex-git/imports/
└── github.com/
    └── owner/
        └── repo/
            ├── <COMMIT-HASH>/
            ├── <BRANCH> -> <COMMIT-HASH>
            └── <TAG> -> <COMMIT-HASH>
```

## 5. `import install` / `import restore`

- 查找或创建 commit-hash Installation；新建时设为 untracked，已存在时保持原状态。
- branch/tag 时：
  - 解析 selector 得到 commit-hash。
  - 确保 commit-hash 物理 worktree 存在。
  - 创建或更新 selector 符号链接。
  - 创建或更新 branch/tag Installation。
  - 在 commit-hash Installation 的 `import-by-installations` 中加入对应 ParentImporter。
- commit selector 时：
  - 直接创建/复用 commit-hash Installation。
  - 写入自身 owner-level ParentImporter 条目。

## 6. `import remove`

- 删除 branch/tag Installation 时，先移除 selector 符号链接，再从 commit-hash Installation 的
  `import-by-installations` 中移除对应 ParentImporter。
- commit-hash Installation 只有在以下条件同时满足时才物理删除：
  - `import-by-installations` 为空，或仅包含自身 owner-level 条目。
  - 无关联 branch/tag、Ref 或 Markdown link 阻塞。
- tracked Installation 在 `import-by-installations` 非空时只迁移为 untracked，不物理删除。
- 目标不存在时保持 no-op。
- `import remove --auto` / `--untracked` 应包含 owner 直接安装的 commit-hash Installation。

## 7. `validate` / `repair`

- validate 检查：
  - branch/tag `install-path` 是符号链接，且目标正确。
  - commit-hash `install-path` 是真实目录。
  - 没有损坏的 selector 链接。
- repair 恢复：
  - 符号链接指向错误时修复。
  - 缺失 commit-hash worktree 时补建。
  - 清理不再被引用的 commit-hash 目录。

## 8. 阶段 5 完成标准

- branch/tag 重解析不破坏仍被使用的旧 commit-hash Installation。
- remove 不删除仍被间接 import 的物理目录。
- validate/repair 能处理新的符号链接目录组织。
- 所有相关测试通过。

## 9. 对现有设计实现的影响面

| 模块/流程 | 影响 |
|---|---|
| `imports.py::_install_resolved` | branch/tag 和 commit selector 的目录创建逻辑需拆分。 |
| `imports.py::_install_path` | branch/tag 与 commit-hash 路径生成需保持兼容。 |
| `imports.py::remove` | 需要区分 selector 符号链接删除与 commit-hash 物理删除。 |
| `store/runtime.py::_reindex` | `_installations_by_commit` 只索引 commit-hash Installation。 |
| `store/model_view.py` | 需提供 `installations_for_commit` 并处理列表结果。 |
| `installation.py::InstallationRuntimeModelView` | 需要基于 `ParentImporter` 做 commit-hash 反查。 |
| `validate.py` / `repair.py` | 需要识别符号链接 selector 与真实 commit-hash worktree。 |
| 测试 | 既有 branch/tag 测试需按新目录组织更新。 |

### 9.1 基于当前代码的具体影响

当前代码的关键路径如下：

- `store/runtime.py::RuntimeTransaction._reindex()`
  - 现在 `_installations_by_commit` 是 `dict[(git_url, commit_hash), Installation]`，所有
    Installation 都会写入。
  - 阶段 5 需要改为仅 commit selector 写入；`(git-url, commit-hash)` 唯一确定一个 commit-hash
    Installation。

- `store/model_view.py::RuntimeModelView.installation_for_commit()`
  - 当前返回单个 `Installation`。
  - 需要改为 `installations_for_commit()`；先取唯一 commit-hash Installation，再读取其
    `import_by_installations` 反查 branch/tag。

- `imports.py::_install_resolved()`
  - branch/tag 当前直接使用 selector 路径作为真实 Git worktree。
  - 阶段 5 需要拆出 commit-hash 物理 worktree 准备、selector 符号链接创建、两个 Installation
    记录维护。

- `imports.py::_prepare_install_path()` / `_inspect_worktree()`
  - 当前假设 `install-path` 是真实目录。
  - 改为 selector 符号链接后，需要区分“selector 路径”和“commit-hash 路径”。

- `imports.py::remove()`
  - 当前只按选中的 Installation 做阻塞检查并删除。
  - 阶段 5 需要先删 selector 符号链接，再决定是否删除 commit-hash Installation。

- `installation.py::InstallationRuntimeModelView._mapped_installation()`
  - 当前通过 `owner_view.installation_for_commit()` 取单个 owner Installation。
  - 需要适配 `installations_for_commit()`，并筛选 commit-hash 记录。

- `model_view.py::scan_managed_symlinks()` / `scan_markdown_links()`
  - 当前按 boundary-set 跳过边界外路径；所有 Installation 均位于 boundary 外，因此在当前架构下
    不会被扫描。阶段 5 不要求修改这两个函数。

- `repair.py::_align_installation()`
  - 当前 `repo_path_to_fs(store.git_root, installation.install_path)` 会直接操作 selector 路径。
  - 需要改为对 commit-hash Installation 使用物理目录，对 branch/tag Installation 使用符号链接。

- `validate.py` 的 work-model 和 content diagnostics
  - 需要新增 selector 符号链接、commit-hash 物理目录、ParentImporter 关系一致性检查。

## 10. 未考虑到的问题与待明确设计

1. `presentation_path` 已在前序子需求解决，阶段 5 不涉及。
2. `installations_for_commit` 通过唯一 commit-hash Installation 的
   `import_by_installations` 反查 branch/tag。
3. commit-hash Installation 同时被 owner 直接安装和被 branch/tag 引用时，remove 的关系计算
   顺序仍待明确。
4. `import remove --auto` / `--untracked` 包含 commit-hash 直接安装对象。
5. branch/tag selector 含 `/` 时，符号链接路径与 commit-hash 路径如何共存。
6. `validate` 对损坏符号链接和缺失物理目录的优先级如何。
7. `runtime.json` 中 `import-by-installations` 采用顶层 map 还是随 untracked Installation
   记录保存。
8. 自身 owner-level 条目与 branch/tag 引入条目同为 `importer-level: owner` 时，如何通过
   `install-id` 区分。
9. branch/tag 重解析到新 commit 时，旧 commit-hash Installation 的 ParentImporter 条目应何时
   移除，新 commit-hash Installation 的条目应何时添加。
10. `import track` 作用于 commit-hash Installation 时，tracked/untracked 投影与
    `import-by-installations` runtime 数据如何保持一致。
11. `import ref` 使用 branch/tag Installation 时，引用源应指向 selector 符号链接还是解析后的
    commit-hash 物理目录。
12. branch/tag 与 commit-hash Installation 的派生 `boundary-set` 是否都保留，还是只保留
    commit-hash 物理目录。
13. `worktree create --install-id` 使用 branch/tag Installation 时，基准路径如何解析。
14. Git worktree 注册信息、`.git` 文件和物理目录删除顺序。
15. 是否迁移或兼容旧的非符号链接 Installation 状态。
16. 新增哪些稳定错误码处理损坏/不一致的 selector 符号链接。
