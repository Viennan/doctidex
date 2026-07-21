# 外部引用

协议状态：**v0.0.2 当前版本**。

## 模型

`External Reference` 把独立拥有的源映射到稳定逻辑路径。其投影只能是以下一种：

- `Mount`：完整暴露被引用的源；
- `View`：选择性暴露作为 `Whero Wiki` 或另一个 `View` 的源。

非 Whero 内容必须使用 `Mount`。从其他目录树引用 `Whero Wiki` 或 `View` 时必须使用外部引用系统；复制选中文件不是符合协议的投影方式。

## 声明

在 `Whero Wiki` 内部，应在最近的受维护、View-required 的 `index.md` 中声明引用：

```yaml
whero_external_references:
  - path: vendor/project
    projection: mount
    content: ordinary
    locator:
      kind: git-submodule
```

每项声明包含：

- `path`：相对于声明 index 的安全 POSIX 路径；
- `projection`：`mount` 或 `view`；
- `content`：`ordinary`、`whero-wiki` 或 `view`；
- `locator`：定位或恢复源所需的信息。

支持以下 locator 类型：

- `filesystem`：`kind: filesystem`、相对于声明 index 的 `path`，以及取值为 `file` 或 `directory` 的 `type`；
- `git`：`kind: git`、不含凭据的 `url`，以及作为完整 40 字符 commit ID 的可选已审阅 `revision`；
- `git-submodule`：从 `.gitmodules` 和父仓库 gitlink 获取源信息。

未知的声明或 locator 字段保留使用。包含不支持的值、不安全逻辑路径、格式错误 locator 或重叠 external-reference ancestor 的声明不符合协议。

`View` 还会在 `whero-wiki-view.md` 中记录源 locator、identity、请求的 selections、effective roots 和策略。因此，Wiki 外部的 View 也能独立恢复。

## Mount 规则

- 仅在 Git 传输不合适时使用相对符号链接 Mount。恢复时校验存在性和类型，并警告 v0.0.2 不对任意符号链接目标执行 hash 校验。
- 不受包含仓库控制的 Git Mount 应记录已清理的 remote 和可用的已审阅 revision。
- Git submodule 使用 `.gitmodules` 和 gitlink 作为传输事实来源。
- 普通 Mount 自动成为 `Preserved Boundary`。
- 每个 Mount 都只能整体暴露，无论其内容是普通内容、`Whero Wiki` 还是 `View`。选择任何可达后代都是合法的，程序自动将 effective root 提升为 Mount 根；调用方无需选择根或传入边界专用 flag。
- 被 Mount 的 `Whero Wiki` 保留独立校验和维护，但在 Mount 投影下不获得选择性披露能力。需要选择性披露时应使用 `View` 投影。选择被引用 View 内部的路径时，只能使用该 View 中已经 available 的内容，并且不生成子 View。

## 恢复

恢复是一项先规划、后校验的操作：

1. 读取声明和 View 元数据，不修改文件系统。
2. 把每个引用分类为存在且有效、存在但无效或缺失。
3. 在原位置校验 filesystem locator，不得静默替换为不同目标。
4. 对 Git locator 使用调用方提供的仓库存储位置或目标目录，获取已记录 remote 并校验已审阅 identity。
5. 先恢复 Mount，再恢复直接 source path 依赖这些 Mount 的 View。
6. 根据 View 元数据重建指向已记录直接 source 路径项的相对符号链接；不得 resolve source symlink，也不得从最终 Wiki 推断 source View 中 unavailable 的内容。

网络 fetch 和替换用户拥有的目标内容必须显式应用经过审阅的恢复计划。
