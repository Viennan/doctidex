# 需求 0003-04：重实现 Installation RuntimeStore/Transaction/ModelView

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0003-04` |
| 状态 | `approved` |
| 日期 | 2026-08-20 |
| 父需求 | [需求 0003](overview.md) |
| 影响范围 | `installation.py`、`InstallationRuntimeStore`、`InstallationRuntimeModelView` |


## 详细内容

### 4.4 Installation 命令运行环境

核心要求不是强制引入单一的 `InstallationTransaction` 囊括所有抽象，而是为 Installation 上下文
构建一套命令运行环境，使允许运行的命令获得与普通 `RuntimeStore`/`RuntimeTransaction` 相同的
支撑能力。

实现形式保持开放：

- 可以是一个或多个事务适配对象、模型视图、路径映射器或 Store 包装层的组合。
- 可以直接复用现有 `RuntimeStore`、`RuntimeTransaction` 以及已经积累的相关工具，在不重写命令
  业务逻辑的前提下加入 Installation 上下文映射。
- 是否引入名为 `InstallationTransaction` 的类、以及它承担多少职责，由实施决定，不作为本需求
  的固定约束。

该运行环境必须满足以下行为要求：

- 对允许命令暴露与普通 `RuntimeStore`/`RuntimeTransaction` 相同的入口，例如
  `read_only_transaction()`、`write_transaction()` 以及允许命令实际使用的其他事务入口。
- 命令模块优先仍按普通 repos 的方式调用这些入口，避免随意增加 `if installation:` 之类的上下文
  分支。
- 在运行环境内部，将 Installation 自身坐标映射到 owner 坐标，将 Installation 本地
  `install-id`/Ref 映射到 owner-level Installation/Ref，并将 owner-level 状态映射为
  Installation 可见视图。
- Installation 事务 `__enter__` 应在取得 owner 文件锁后，根据
  `InstallationContext.install_path` 匹配 owner RuntimeStore 中的 Installation，并校验其仍然
  存在；阶段 2 只负责记录 `install_path`，不提前读取或校验。
- 写事务中的状态更新和物理副作用必须落在 owner 的工作区；读事务返回的模型视图应让命令认为
  自己在读取当前 Installation 的普通模型，但路径和数据已经过映射。
- `Installation` 增加可选运行时字段 `presentation_path`，类型为文件系统绝对路径；仅由
  `InstallationRuntimeModelView` 填写。若结果中出现该字段，使用者应优先通过它访问
  Installation；不会改写原始 `install-path`。
- 命令参数和命令主流程优先不做大规模变化；当某些代码路径难以通过现有接口透明映射时，允许
  新建共同的环境抽象，并对已有实现做出必要调整，而不是在每个命令中散落临时的上下文特判。
- 本需求当前只要求为第 4.2 节允许运行的命令提供该运行环境；被禁止的命令在进入运行环境之前
  失败。

### 4.5 Installation 内 `import restore`

当命令位于 Installation `A` 内且执行 `import restore --install-id <B-local-id>` 时，命令分发层
仍然复用现有的 `import restore` 工作流，但其 `RuntimeStore` 参数替换为 Installation 上下文命令
运行环境提供的适配对象。

该运行环境优先复用现有 restore 主流程；仅在难以通过环境抽象透明处理的路径上，才调整已有实现。
需要完成以下映射：

- 把 `--install-id` 从 Installation 本地身份映射到 owner-level Installation 身份；映射规则为
  按 `(git-url, commit-hash)` 在 owner 的 **commit-hash Installation** 中匹配。Installation 自身
  `imports.json` 中的 branch/tag 形式 revision，必须使用其记录的 commit-hash 参与匹配，而不是
  去匹配 owner 中的 branch/tag Installation。
- 把目标 Installation 的 owner 实际物理路径填入 `presentation_path`；原始 `install-path` 保持
  Installation 自身声明不变。
- 把 restore 写事务中的 Installation 状态更新提交到 owner 的 RuntimeStore，而不是 Installation
  自身的 `.doctidex-git`。
- 对不存在或 owner 中已有匹配记录的情况，沿用现有 restore 的成功、no-op 或错误语义。在当前
  架构下，`git-url + commit-hash` 唯一标识一个 commit-hash Installation（排除 branch/tag），因此
  不需要处理多个候选。
- restore 最终返回 Installation-level 结果，并在需要时提供 `presentation_path`；不替换
  `install-path`。

restore 仍然通过 owner 的 `GitCache` 获取 Git object，并遵守既有
[需求 0002-05](0002-doctidex-git-cli-v2/05-import.md) 中只使用已记录 commit、不重新解析
branch/tag 的规则。


### 4.6 Installation 内查询命令

在 Installation 上下文内，查询命令优先调用现有查询工作流，并使用 Installation 上下文命令运行
环境提供的只读视图。查询实现原则上不增加 owner/Installation 分支，由运行环境完成数据映射；
仅在难以透明处理的路径上允许调整已有查询实现：

- `import query` 从运行环境的只读视图中读取候选 Installation 和 Ref；候选结果保持
  Installation-level 身份，原始 `install-path` 不变。需要访问 owner 实际路径时，在
  `presentation_path` 中提供。
- `import query` 可以继续输出动态字段 `import-by-installations`，该字段仍只存在于运行时视图，
  不来自持久化文件。
- `boundary-set parse` 继续调用现有解析逻辑；运行环境先把输入路径映射到 owner 坐标系，再使用
  owner 的完整 `boundary-set` 视图解析，最后将结果映射回命令可见形式。
- 查询命令不得修改 CacheStore、RuntimeStore、Installation 文件或边界集合。

路径转换必须拒绝越过仓库边界的路径，避免把 Installation 内路径解释为 owner 的任意文件系统
路径。

### 阶段 4：重实现 InstallationRuntimeStore/Transaction 与 InstallationRuntimeModelView

阶段 4 在阶段 3 拆分完成的基础上，重实现 Installation 侧运行环境。核心是保持 owner 与
Installation 各自 RuntimeState 独立，通过新的 `InstallationRuntimeModelView` 在查询时完成映射，
不再构造融合 RuntimeState。

#### 4.1 双独立视图

`InstallationRuntimeStore` 同时准备：

- owner `RuntimeStore` / `RuntimeModelView`；
- Installation 自身的无锁只读 `RuntimeStore` / `RuntimeModelView`；
- `InstallationContext` 提供的 `owner_root` 与 `install_path`。

两者 RuntimeState 互不投影、互不合并。

#### 4.2 新增 `InstallationRuntimeModelView`

`InstallationRuntimeModelView` 是新的核心查询入口：

```text
command query
   |
   v
InstallationRuntimeModelView
   |-- Installation RuntimeModelView（本地）
   |-- owner RuntimeModelView（owner）
   `-- 路径 / install-id / commit-hash 动态映射
```

典型查询流程：

1. 从 Installation RuntimeModelView 查询本地 `install-id`，得到本地 `git-url` 与
   `commit-hash`。
2. 用 `(git-url, commit-hash)` 在 owner RuntimeModelView 中匹配 commit-hash Installation。
3. 命中后，以 Installation-level 结果为主体，保持 `install-path` 不变；仅在其上设置
   `presentation_path` 为 owner 中的实际物理路径，其余字段保持 Installation 声明的结果。
4. 未命中时，按既有查询语义返回空结果或对应错误；不构造融合状态。

#### 4.3 读写事务分离

- `InstallationReadOnlyTransaction` 供 `import query`、`boundary-set parse` 等只读命令使用。
- `InstallationWriteTransaction` 供 `import restore` 使用，虽然名称是 write，但只修改 owner
  RuntimeStore；Installation 自身仍保持只读。
- Installation 自身的 JSON 解析失败直接报 `installation.context.unavailable`，不触发 owner
  repair。

#### 4.4 命令接入

- 接入 `import query`、`boundary-set parse` 和 `import restore`，保持命令主体流程尽量不变。
- `import restore` 的 write 只修改 owner，物理产物落在 owner 的 `/.doctidex-git/imports/`。

检查点：

- owner 与 Installation RuntimeState 不融合。
- 查询结果来自 `InstallationRuntimeModelView`。
- `StoreCoordinator` 仍只管理 owner 锁、repair 和 GitCache。

### 6.3 只读保证

允许运行的命令只能读取 Installation 自身文件，并只能在 owner 的 RuntimeStore 中写入。若发现
需要写 Installation 自身的情况，命令必须失败，不得静默降级或忽略。
