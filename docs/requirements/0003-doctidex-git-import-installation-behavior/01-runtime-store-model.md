# 需求 0003-01：扩展 RuntimeStore 模型

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0003-01` |
| 状态 | `implemented` |
| 日期 | 2026-08-20 |
| 父需求 | [需求 0003](overview.md) |
| 影响范围 | `Installation`、`runtime.json`、`RuntimeState`、`import query` |


## 详细内容

### 4.3 `import-by-installations` 关系

`import-by-installations` 描述一个 Installation 与间接引入它的 Installation 之间的关系：

```jsonc
{
  "install-id": "<OWNER-LEVEL-INSTALL-ID>",
  // 运行时字段：不写入 imports.json，但运行过程中写入 runtime.json
  "import-by-installations": [
    {
      "install-id": "<OWNER-LEVEL-INSTALL-ID>",
      "importer-level": "owner",
      "sub-installation-ids": []
    },
    {
      "install-id": "<OWNER-LEVEL-INSTALL-ID>",
      "importer-level": "installation",
      "sub-installation-ids": ["<INSTALLATION-LEVEL-INSTALL-ID>"]
    },
    {
      "install-id": "<SAME-OWNER-LEVEL-INSTALL-ID>",
      "importer-level": "owner",
      "sub-installation-ids": []
    }
  ]
}
```

字段含义：

| 字段 | 含义 |
|---|---|
| `install-id` | owner 的 RuntimeStore 中目标 Installation 的 `install-id`。 |
| `import-by-installations` | 由 `ParentImporter` 对象组成的动态列表。 |
| `ParentImporter.install-id` | 引入该目标 Installation 的 owner-level Installation `install-id`。 |
| `ParentImporter.importer-level` | `owner` 表示由 owner 直接引入；`installation` 表示由某个 Installation 间接引入。 |
| `ParentImporter.sub-installation-ids` | 当 `importer-level` 为 `installation` 时有意义，记录该 Installation 内通过 `import restore` 匹配到该 owner-level commit-hash Installation 的 Installation-level `install-id`。 |

当 owner 直接使用 `import install --commit` 创建 commit-hash Installation 时，必须在该
Installation 的 `import-by-installations` 中增加一个自身 owner-level 条目：

- `install-id` 等于该 commit-hash Installation 自身的 `install-id`。
- `importer-level` 为 `owner`。
- `sub-installation-ids` 为空。

该自身条目的作用是阻止其他 `ParentImporter` 被 remove 时连带删除这个直接安装的 commit-hash
Installation。

`import-by-installations` 不是需要被 tracked 的字段，但仍是运行过程中需要保存到
`runtime.json` 的 untracked runtime state。它不写入 `imports.json`；状态加载和保存时应序列化到
`runtime.json`，`import query` 等只读命令可以在结果中输出该字段。

### 阶段 1：扩展 RuntimeStore 模型

1. 在运行时 `Installation` 视图中增加动态字段 `import-by-installations`。
2. 保持 `imports.json` 不变；在 `runtime.json` 中增加 `import-by-installations` 的 untracked
   运行数据。
3. 更新 `RuntimeStore` 状态重建和 `RuntimeModelView`，从 owner 状态与 `runtime.json` 恢复该
   动态字段。
4. 更新 `import query` 结果，使该字段可以在只读查询中输出。

检查点：`import-by-installations` 不写入 `imports.json`，但会写入 `runtime.json` 并在查询结果
中输出。

