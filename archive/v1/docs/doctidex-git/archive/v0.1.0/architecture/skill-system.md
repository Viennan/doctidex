# doctidex-git 0.1.0 Skill 系统设计

Skill 是 `doctidex-git` 面向 agent 的公开使用层。它们为已安装产品编写，目标是让
agent 不读源码、不读 implementation docs、也不靠命令试错即可完成工作。

## 1. 分层

| Skill | 职责 | 典型结果 |
|---|---|---|
| Guide | 共享心智模型、术语、CLI 语法、结果、网络和安全基线；路由专项工作流 | agent 能选择正确的下一 Skill。 |
| Setup | 创建、接管或修正一个 Git 管理的根 | 最小结构、候选语义工作和验证。 |
| Read | 渐进导航、link/path 辅助和 lazy mount 恢复 | 原生工具可读路径和来源上下文。 |
| Mount | 声明、列出、准备、移除和显式同步 Git mounts | 声明与 effective commit 状态。 |
| Maintain | 在一个明确根中维护内容、index 和 log | 单根 diff、语义决定和验证。 |
| Workspace | 复用同 revision scope、按需打开 mounted source 维护根并协调多根任务 | 兼容 scope 分组、逐 scope 边界和 handoff。 |
| Validate | 分离结构、语义候选和插件就绪检查 | 三个独立结果域。 |
| Review | 只读审阅单根或多根结果 | findings、语义结论和用户 Git 动作。 |

实际使用文本位于
[`impls/agent-plugins/doctidex-git/skills/`](../../../../../impls/agent-plugins/doctidex-git/skills/)。
Architecture 只定义分工和约束，不复制具体 Skill 的完整命令教程。

## 2. 阅读链

```text
Guide (条件性读取一次)
  -> 一个任务专项 Skill
      -> 仅在工作流跨界时路由另一个专项 Skill
```

阅读链必须显式、无环。共享内容只在 Guide 定义；专项 Skill 定义自己新增的术语和
工作流。Guide 与一个相关专项 Skill 应足以完成单一支持场景。

## 3. 用户信息充分性

专项 Skill 引入一条命令时，必须说明：

- 精确调用形式和占位符类型；
- 必填、可选、互斥和重复参数；
- 省略值、cwd 和根选择行为；
- 读写、联网、dry-run/apply 和 batch 影响；
- agent 决策所需的输出字段和 collection 行为；
- 常见 blocked code、可执行恢复和必须升级给用户的情况。

Skill 不能要求 agent 通过 `--help` 试错、阅读 Python 代码或查看内部 state 才理解这些
信息。可以链接 Guide 避免重复，但不能省略本工作流特有的约束。

## 4. 用户信息边界

Skill 可以说明逻辑 root、mount、revision、effective commit、working path、maintenance
root、root relation、maintenance reuse、状态和动作。不得说明 source key、缓存布局、
worktree 管理命令、锁、projection 或仓库比较算法。实现技术变化不应迫使 Skill 用户
改变心智模型。

“维护根路径”是用户完成工作所需的信息，因此可以公开；“它在内部如何创建和登记”
不属于 Skill。

## 5. 原生工具自由

Skill 不提供仅仅包装成熟 `read/tree/find/git diff` 能力的工具，也不要求所有浏览经过
CLI。CLI 可以提供 doctidex 特有的 root、scope、link、mount、revision、validation 和
bounded collection 事实；agent 再用自身工具读写现场。

Read Skill 尤其是导航建议而非访问网关。普通同根路径可以直接推导，`resolve` 只在
link root、mount namespace 或 lazy 状态需要消歧时使用。

## 6. 客观 CLI 与主观 Agent

CLI 必须确定性且不调用 AI。agent 负责：

- 决定任务相关内容和维护顺序；
- 撰写 index 描述、目录摘要和 log 记录；
- 判断 semantic candidate 是否构成真实缺口；
- 审阅内容质量、Git diff 和交付影响。

CLI 可以解析、校验、格式化调用方已提供的内容或报告候选，但不能替 agent 生成这些
语义结论。

## 7. 输出与失败

Skill 应默认选择精确 PATH 或单个 mount，检查 `collection` 后再分页，不能习惯性把
limit 提到最大。失败指引必须说明未完成操作、受影响对象、已保留结果、当前动作和
是否需要用户输入；不可恢复错误应直接向用户反馈，而不是暴露内部诊断过程。

## 8. 发布校验

每次 Skill 变化都应检查 frontmatter、agent metadata、阅读链、命令契约、内部术语
泄漏和 containing plugin。实现文档可以用于维护者验证 Skill 准确性，但发布后的
Skill 不能依赖实现文档存在。
