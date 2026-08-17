# Root、ownership 与 path 模型

> 归档状态：`format-illegal`。本页是 DX-REQ-0015 前的历史文档基线，不定义当前产品。

本篇定义 doctidex-git 中容易被混淆的边界：协议解释 root、managed state owner、content
来源和宿主 Git repository。所有 workflow 必须先明确这些 identity，再决定读取或写入位置。

## 1. 四个独立边界

| 边界 | Identity | 负责 | 不负责 |
|---|---|---|---|
| Doctidex Root | root index 所在 filesystem path | `/` 解释、configuration、reachability、validation coverage | Git identity、source identity、写权限。 |
| Owner Root | 持有 managed install/link/worktree records 的 selected root | managed path、runtime ownership、root mutation boundary | source 内容 ownership、协议符合性。 |
| Content Root | 当前路径实际内容所属的 doctidex root 或 installed repository root | repository-relative suffix、portable mapping 的解释起点 | outer owner 的写 authority。 |
| Host Git Repository | 唯一包含 owner root 的 Git working tree | tracking、ignore、manifest/link delivery state | doctidex root 选择、source commit。 |

它们可以重合、嵌套或分离。任何模型都不得由一个边界自动推导另一个边界；每条关系必须由
path containment、Git facts、manifest/runtime record 或明确输入证明。

## 2. RootContext 与选择

RootContext 包含 root path 与 root index path。选择过程接收 operation、explicit root、default
path 和可选 `must_contain`：

1. Explicit root 必须自身拥有可读取且声明 root marker 的 index；不能把任意子目录提升为 root。
   初始 root 无法形成 `RootContext` 时在 selection 阶段 blocked。Validation 选中 root 后若扫描
   发现 root facts 已失效，再以 protocol finding 和 `scan_complete` 表达本次观察。
2. 未显式提供时，从 default/input path 向上发现全部包含候选。
3. `must_contain` 过滤不能拥有 operation target 的候选。
4. 零候选返回 not found；多候选返回完整 candidates 和 user decision；唯一候选才成为 selected
   root。
5. selection 只在本次 invocation 中有效，不形成 session 或未来默认值。

## 3. Path 类型

| Path | 表达 | 约束 |
|---|---|---|
| Filesystem path | host absolute path | 只用于实际 I/O 和用户可观察 location。 |
| Root-internal path | 以 `/` 开头 | 相对 selected doctidex root；不得包含词法逃逸。 |
| Root-relative path | 无前导 `/` 的 POSIX path | manifest/runtime/index 中的 portable owner-root location。 |
| Repository-relative path | `.` 或 normalized POSIX path | 相对 installed Git repository root；不能越 repository。 |
| Presentation path | owner root 内用户选择的 symlink 路径 | 必须由 responsible index 导航并服从 host Git tracking boundary。 |
| Managed internal path | owner root 的 `/.doctidex` namespace member | 由工具分配，不能被调用方当成稳定命名 API。 |

Root-internal input 先按协议 path-segment 规则词法规范化：重复 `/`、`.` 和仍可在 root 内消去的
`..` 可以出现在 input 中，但 canonical identity 不保留这些 segment；从空 root stack 继续弹出、
反斜线等平台 separator 混用或规范化后越界均 blocked。Root-relative、repository-relative、
manifest target 与 presentation target 是已规范化的 stored identity，输入时不得含空 segment、
`.` 或 `..`。Symlink input 的 identity 以 symlink 自身的词法位置为起点，target 是否存在是独立
状态，不能在 root/owner 选择前自动 dereference。

## 4. Ownership 证明

Managed object 只有在以下事实一致时才获得 ownership：owner root、stable ID、root-internal
path、runtime/portable record、source identity 以及当前 filesystem/Git fact。单有 path naming、
symlink target、cache object 或目录位于 `.doctidex` 下都不足以证明 ownership。

Ownership 状态分为：

- `managed-complete`：identity、record 和 physical object 自洽；允许对应 workflow 操作。
- `managed-incomplete`：identity 可识别但一部分 record/object 缺失；只允许诊断和有限恢复。
- `unmanaged`：没有 ownership 证据；工具不得 adopt、replace 或 cleanup。
- `ambiguous`：多个 owner 都合理；需要用户指定 exact root。

## 5. 写入边界

Root mutation boundary 只串行同一 owner root 的 frontmatter、ignore、manifest、runtime、install
和 worktree publication。它不覆盖 network/source object preparation，也不构成跨 Git
repository 事务。Host Git Coordinator 可以观察 tracking 和 ignore，但不得 stage、commit、
reset 或改写无关规则。

Root、ownership 和 path 模型被 external、worktree 与 result 模型共同消费；它不依赖具体
source/cache realization。
