# 设计约束与失败模型

本文汇总所有实现都必须维持的跨工作流约束。协议规则仍以
[`spec/overview.md`](../../../../spec/overview.md) 为准。

## 1. 设计约束

### 1.1 协议与插件分层

- 插件不能修改 doctidex protocol 语义。
- root、mount namespace、完整 source tree、link root 和过滤边界按 protocol 解释。
- Git revision、root `.gitignore` readiness 和 maintenance lifecycle 是插件约定，不能
  被描述为 protocol requirement。

### 1.2 可读性

- mount 默认 lazy；声明存在时物理路径可以尚未出现。
- prepare 成功后，逻辑 mount path 必须可由普通 shell、编辑器、搜索器和 agent 文件
  工具直接读取。
- 某种内部 presentation 创建失败不能被转换成“必须使用专用 reader”的产品限制。
- 只有 source、revision、network 或 credentials 真实不可取得时，用户层才可报告读取
  受阻。

### 1.3 写入

- host mount path 是只读边界；source 修改必须进入 maintenance root。
- preview/apply 必须区分，省略 flag 不是破坏性授权。
- 不自动 commit、push、merge、reset、clean、移除 tracked content 或丢弃结果。
- protected 写入、Git index 改动、credentials、revision 选择和交付动作需要相应用户
  指示或授权。

### 1.4 网络

- context、inspect、resolve、ordinary validation 和状态查询默认离线。
- prepare 仅在本地没有所需对象时需要网络；sync dry-run 和 online check 可以 fetch。
- 网络动作必须由命令契约提前说明。失败不能破坏仍可用的 effective commit。

### 1.5 CLI 客观性

- CLI 不配置或调用 AI，不生成 index/log prose，不判断任务相关性。
- 同样输入、目录树状态和外部 Git 状态产生同样的结构化事实。
- semantic candidate 明确标记为需要 agent 判断，不能冒充 confirmed defect。

### 1.6 输出规模

- 所有 collection 默认有界，人读和 JSON 共享预算。
- collapse/summary 只使用路径、分组、计数、状态和严重度，不生成语义摘要。
- 截断必须返回完整总数、当前数量和 continuation；调用方优先缩小范围。

### 1.7 信息边界

- 用户错误只使用 root、path、mount、revision、maintenance、Git changes 和动作等公开
  概念。
- 不要求用户理解 cache key、worktree 管理、锁、projection 或 state schema。
- diagnostic ID 可以公开；详细 traceback 仅用于实现排障。

## 2. 失败结果必须回答的问题

每个 blocked result 必须使调用方能够回答：

1. 哪个 operation 未完成？
2. 哪个 root、path、mount、revision 或 maintenance result 受影响？
3. 哪些结果已经完成并仍可使用？
4. agent 现在可以执行什么安全动作？
5. 是否需要用户提供输入、权限或不可逆决定？

找不到上述任一信息时，错误契约仍不完整。

## 3. 失败分类

| 类别 | 示例 | Agent 动作 | 是否通常需要用户 |
|---|---|---|---|
| 输入/语法 | 缺参数、非法 internal path | 按契约修正一次 | 否 |
| 上下文 | root not found/ambiguous、错误 mount path | 选择 exact root/path | 歧义无法判断时是 |
| 协议结构 | frontmatter、filter、link boundary | 修确定性结构后复查 | 可能 |
| Plugin readiness | mount 未 ignore、已有 tracked content | 保留现场，处理 readiness | tracked index 是 |
| Lazy state | mount not prepared | 只在需要读取时 prepare | 网络/凭据不足时是 |
| Source access | auth、network、revision/source 无法取得 | 使用保留 commit 或请求输入 | 是 |
| Maintenance preservation | close 时仍有 changes | 保留 root，先 handoff/交付 | 是 |
| Unexpected failure | 未分类异常 | 记录 diagnostic ID，有限重试 | 重复后是 |

## 4. Partial Success

batch 和 multi-root 操作不是事务。顶层 blocked 表示至少一个目标未完成，不表示成功
items 被撤销。结果必须提供 `completed_count`、每项 payload、汇总 findings 和仍保留
内容。agent 按 root/source 分开报告，不为制造“全部成功”而回滚用户结果。

## 5. Human Escalation

以下情况不能由 agent 仅凭技术推断继续：

- 需要 credentials、repository access 或 network authorization；
- 多个 roots/revisions/sources 都合理且任务没有选择依据；
- 需要改变 Git index、commit、push、merge、reset、删除或丢弃结果；
- protected 内容缺少明确维护授权；
- source 不满足完整 doctidex root，需要用户选择其他 source；
- unexpected failure 在一次安全重试后重复出现。

升级时只报告用户决策所需的事实和可选动作，不转交内部 traceback 或缓存布局。

## 6. 安全验收

实现测试至少覆盖 preview 不写入、lazy state 不误报缺失、旧 effective commit 在 sync
失败后保留、mount path 不进入 tracked diff、maintenance changes 阻止 close、batch
partial result 保留，以及默认输出预算生效。
