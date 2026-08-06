# 操作安全、结果与恢复

本页拥有所有 major workflow 共用的 operation discipline：独立 invocation、plan/apply、observable
result、partial success、concurrency、interruption、diagnostic 和 transient worksite artifact。精确 CLI
grammar 和 JSON field names 见 [CLI](interfaces/cli.md) 与 [JSON schema](interfaces/cli-schema.md)；
具体 lock primitive、temp-file name、fsync、polling、Git command order 和 exception rendering 属于 Impls。

## 1. 调用、计划与授权

每个 CLI invocation 独立。cwd、ROOT、SOURCE、PATH、WORKTREE、limit、cursor、dry-run/apply 不会保存为
下一次默认。read-only query 可以重复；mutation 使用两阶段 user decision：

```text
dry-run
  -> 读取 root/source/target/manifest/tracking/reference 与 planned effect
  -> user 或上层系统授权
  -> 同一 semantic input 的 apply
  -> 重新观察实际 changed/affected/preserved result
```

dry-run 不保留 remote、source、root、manifest、reference 或 lock reservation。apply 在现状变化时可以
conflict/blocked；调用方重新 dry-run，不得为取得成功覆盖新发现的 path、link、hook、user change 或
foreign state。`requires_user` 非 null 时停止自动重试并交给对应决策者。

## 2. 可观察结果与失败边界

所有 operation 返回 one-shot result：先按 `status` 分支，再按 `operation` 读取 payload，最后使用
stable finding/code、affected object、action 和 `requires_user` 决定下一步。human message 与 diagnostic
ID 不能取代 machine contract。

| result fact | meaning | caller rule |
|---|---|---|
| `ok` | required operation outcome 已确定，没有阻断。 | 仍读取 result/changed/collection，而不只看 exit 0。 |
| `warning` | operation 可以完成但有 preserved/partial/diagnostic fact。 | 读取 item finding，不能把 warning 当自动 retry 或 full success。 |
| `blocked` | input、state、permission、conflict、compatibility 或 user decision 阻止安全完成。 | 保留现场，执行 action 或等待 user；不能从 message 猜修复。 |
| `changed` | 已确认写入/移除的 path/artifact。 | 审阅其是否需要 native Git delivery；空列表不一定否认 logical result。 |
| `affected` | 受保护、损坏、冲突或保留的 object/path evidence。 | 用于定位和下一次同 identity 重观测。 |
| collection + cursor | bounded listing/query。 | 消费 returned/total/truncated，opaque cursor 原样传回；identity/state 变化从第一页开始。 |

`partial_success` 表示可独立确认的一部分 effect 已经发生，绝不表示 rollback。remove reference block、
hidden preservation、cache preserved、worktree changed/unavailable 和 hook item blocked 都是有意义的
安全结果，而不是 bug 的同义词。

## 3. 发布、并发与恢复

external（包括 link/rebind/unlink）、hook、worktree 和 cache mutation 可以同时涉及 owner-root configuration、payload、host Git、
shared source cache 或 hook artifact。这些资源没有全局 transaction。共同安全约束是：

1. 一个 variant 只在能证明 selected owner/source identity 时改变 managed state；
2. 任何 conflict、interrupt 或 identity mismatch 都优先保留现有 files/artifacts；
3. 后续操作重新读取当前 observable state，以 exact install ID/worktree path/source/base commit/manifest
   identity 为锚，而非推断先前计划仍有效；
4. 不能确定 effect 时 result 报告 `affected` / preserved evidence，而不是宣称 unmodified 或 completed；
5. 不同 root 没有 cross-repository transaction；每个 root 的 validation、review、delivery 和 recovery
   分别进行。

| 现场 | 可观察含义 | recovery / handoff |
|---|---|---|
| payload 变更但 manifest/runtime/link 未全同步 | partial publication 或 interrupted state。 | 保留 path/record，按 exact identity 重观测；无法证明时 blocked，不删补齐。 |
| manifest/runtime invalid 或 inconsistent | configuration 无法作为 automatic action input。 | preserve、恢复 versioned manifest 或由 explicit user repair；不要用 empty config 覆盖。 |
| hook payload 已切换但 provenance 未完全同步 | exact commit 可用，但 metadata result 不完整。 | hook 下次重观测并报告；不改写 fixed manifest commit。 |
| hidden path/record 不一致 | dependency state 未安全完成。 | 保留 Git/payload/runtime evidence，只在 identity 可证明时 reconcile。 |
| worktree path/registration unavailable | user data、move 或 failed publication evidence。 | 保留 record，返回 `worktree_unavailable`，交给 native Git/operator。 |
| source/cache concurrent change | eligibility/identity 已过期。 | preserve，重新 dry-run/observe；不强制 delete。 |

Architecture 定义这些 recovery choices，而不是要求所有 variant 使用同一个 write atomicity algorithm。

## 4. 诊断、锁与临时产物

下列文件/目录可能在 user-surface 工作现场被观察到。它们不是需要用户编辑的 configuration，但
Architecture reader 必须能解释其类别和安全使用方式：

| artifact | producer / purpose | consumer / safe handling |
|---|---|---|
| diagnostic log with opaque ID | unexpected failure 的 best-effort maintenance artifact。 | human/agent 报告 operation + ID；maintainer 可读，program 不解析 traceback 作为 public schema。 |
| root/source/hook lock | mutation coordination 或 active operation evidence。 | 等待、重观测或返回 conflict; 不手动删除来绕开另一个 operation。 |
| cache-private coordination container | cache realization 可能保留的空或未激活 support namespace。 | 它本身不表示 active lock、cache candidate 或 deletion authority；保留它，只有可识别 active lock 才按等待/重观测处理。 |
| same-resource temporary publication file | pending atomic publication support。 | 不作为 complete configuration；中断后以 owner record/payload consistency 决定 preserve/diagnose。 |
| native Git worktree/cache registration | third-party Git ownership data。 | native Git 或 explicitly supported surface 处理；doctidex-git 不伪造/盲删。 |

temp directory layout、lock name/timeout、diagnostic path、traceback format 和 filesystem syscall 是
Impls mechanics。只要它们不改变上表的 active/incomplete/preserve semantics，Architecture 无需列出
每一 byte 或 execution branch。

## 5. 变体接手与完整性边界

一个 incoming variant 在遇到失败/中断现场时，必须能够从 Architecture 判断：哪些 configuration/artifact
可以读、转换、保留、reject；哪个 user-visible code/action 合适；何时停止要求用户决定。它不需要推导
当前 variant 的 lock acquisition、exception stack、temporary-object lifecycle 或 retry loop。

因此 Architecture 的 completeness test 是“能正确实现 input/default、result/failure、recovery、handoff
与 safety boundary”，不是“能重建当前 source 的全部 execution”。更具体的 component ownership 和
source/test evidence 由每个 Impls variant 说明。
