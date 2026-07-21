# 一致性

协议状态：**v0.0.2 当前版本**。

## 一致性 Profile

`Full Wiki` profile 校验完整自有内容、已声明边界、框架结构和 source identity。`View` profile 校验可读材料、View 元数据、effective roots，以及指向直接 source 路径项的相对链接，并将未选择内容视为 unavailable。

校验必须输出稳定诊断代码和结构化路径上下文。修改命令必须能够在应用变更前生成完整 dry plan。

## 版本身份

`spec/` 中的文件描述 v0.0.2 协议。一致的 Wiki identity 与 View metadata document 设置 `format_version: "0.0.2"`。View metadata 使用 `whero-wiki-view.md` 和 `whero_view`；View-required framework document 使用 `whero_view_required`；View 校验 profile 为 `view`。

随附工具只实现这一版本身份。缺失或不同的 `format_version`、不同的 View status filename 或替代身份字段，都不能标识符合 v0.0.2 的 Wiki 或 View。

## 必需测试面

一致性测试覆盖：

- Wiki 和 View identity；
- 外部引用声明和恢复规划；
- 穿过边界的合法 selection 和自动 whole-root 提升；
- View of View 的 availability 限制和直接 source symlink 链；
- `views.md` 中的 source-path 与 collapse 矩阵；
- 精确和 pattern-preserved boundary；
- 相对链接解析、图检查和 View unavailable 报告；
- 严格的 v0.0.2 identity 与 framework field 校验；
- 预检原子性、Git identity、source relocation 和恢复。

英文与中文协议树必须具有相同的相对文件名。协议变更必须在同一个产品变更中更新两个语言版本。
