# 需求 0003-03：拆分 model_view 与事务/视图构造

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0003-03` |
| 状态 | `approved` |
| 日期 | 2026-08-20 |
| 父需求 | [需求 0003](overview.md) |
| 影响范围 | `store/model_view.py`、`markdown_links.py`、`managed_symlinks.py`、`RuntimeStore` |


## 详细内容

### 阶段 3：拆分 `model_view.py` 并调整事务/视图构造

1. 将 `RuntimeModelView` 移到 `store` 中，与 `RuntimeTransaction` 及其变体同层管理。
2. 让 `RuntimeTransaction` 及其变体提供成员方法创建对应 `RuntimeModelView`，命令不再直接
   `RuntimeModelView(transaction)`。
3. 将 Markdown link 解析、仓库内受管 symlink 扫描等逻辑拆到独立模块，便于复用和测试。
4. 新增“无锁只读” `RuntimeTransaction` 变体，用于读取 Installation 自身的 RuntimeState。

检查点：命令模块改为通过 transaction 成员方法创建 model view；`model_view.py` 不再混杂 link、
symlink 与核心 RuntimeModelView。

### 6.6 命令实现保持普通 repos 视图

Installation 命令运行环境必须提供与普通 `RuntimeStore`/`RuntimeTransaction` 一致的调用面，使
允许命令的业务逻辑优先不因当前处于 Installation 上下文而增加分支。命令模块原则上不通过
`isinstance`、全局标志或额外参数判断 owner 与 Installation；上下文差异应集中在运行环境、模型
视图和分发层。对难以通过现有接口透明处理的代码路径，允许新建共同的环境抽象，并对已有实现做
必要调整。

如果某个允许命令使用了未由运行环境支持的底层入口，该命令应转换为稳定错误，而不是修改命令
实现来绕过映射。当前范围只覆盖允许运行的命令。运行环境实现允许直接复用
`RuntimeStore`/`RuntimeTransaction` 及既有工具，是否引入单一 `InstallationTransaction` 类不构成
验收条件。
