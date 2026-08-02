# 并发、publication 与 recovery

本篇定义所有 write workflows 的资源顺序和失败后可恢复状态。具体 lock primitive、temporary
file 和 Git command 属于 Impls；Architecture 只规定必须保持的行为。

## 1. Mutation domains

| Domain | 串行对象 | 允许并行 |
|---|---|---|
| Source mutation | 同 canonical source 的 object update、worktree create/remove、cache clean | 不同 canonical sources。 |
| Root mutation | 同 owner root 的 frontmatter、ignore、manifest、runtime、install/link/worktree publication | 不同 owner roots。 |
| Install identity | 同 install key 的 role/parents/publication | 不同 selector keys，可共享 readonly objects。 |
| Result observation | 同 query identity 的 state fingerprint | independent read-only queries。 |

全局资源顺序是 source preparation -> root revalidation/publication。Network/object acquisition
不得在 root mutation boundary 内等待；任何实现不得反向先持有 root 再等待 source。

## 2. Publication units

以下 effects 各自独立：Git object acquisition、frontmatter、host ignore、portable manifest、
runtime record、install/worktree creation、symlink、diagnostic 与 caller-authored prose/Git index。
单文件可原子替换不等于 workflow 原子。

Reader-safe publication 原则：

1. 尽量在持锁前完成无副作用 preflight。
2. Apply 进入 boundary 后重查 identity、occupancy、tracking 与 expected state。
3. Publication 顺序应缩短不一致窗口，并让任一中间状态可以由 records、filesystem 与 Git facts
   重新诊断；Architecture 不固定跨资源的唯一先后顺序。
4. Record 只能在自身 required fields 足以自洽验证时发布。
5. 删除先证明 ownership 与当前 state，再移除 physical object，最后移除 ownership record。

## 3. Conflict 与 cancellation

Plan 后 state 改变返回 conflict，不覆盖 concurrent result。Cancellation 停止启动新 publication
unit；已完成 effects 保留。Result 列出 changed、affected、preserved state 与有限 retry。不同
root/source 的独立 success 不因另一项失败回滚。`cache clean --auto` 是同一规则下的 source-candidate
batch：enumeration 不是全局 lock 或 snapshot，每个 source lock 内的 recheck 独立完成，先前 candidate
的 success 不因后续 candidate blocked/conflict 而回滚。

Agent 对同 root 的并行文档编辑不受 CLI mutation boundary 保护；协调者必须分配不重叠的
ownership 或串行集成。

## 4. Recovery matrix

| 中断位置 | 可观察状态 | 安全下一步 |
|---|---|---|
| objects prepared、root 未变 | existing root unchanged | 以同 identity 重试 apply。 |
| boundary/ignore 已写、payload 缺失 | internal namespace 已可解释 | 重试同 install；不回退无关 frontmatter。 |
| payload 已建、record 缺失 | orphan/incomplete managed evidence | 诊断 identity；不得自动 delete/adopt。 |
| runtime 已写、manifest 缺失 | direct recovery 不完整 | 重试同 direct publication；保留 payload。 |
| mapping/symlink 只有一侧已写 | record 与 presentation 不一致 | 保留两侧证据；以同 mapping 重试或由用户修复，不跟随未证实 target。 |
| remove payload 已移除、per-install record 尚在 | record 指向 missing install，shared cache/root layout 未变 | 以同 Install ID 重试 remove；重新证明没有 target reference 后仅补齐 record removal。 |
| worktree 已建、record 缺失 | Git registration/orphan path | 保留并报告；用户确认前不 cleanup。 |
| cache apply 前 eligibility 改变 | source still present | conflict 后重新 dry-run。 |

## 5. Destructive boundary

Cleanup 只作用于 exact、in-scope、ownership 可证明且当前状态允许删除的对象。Dirty、unmanaged、
ambiguous、unknown registration 或 damaged record 一律保留并报告。恢复过程不将“回到计划状态”
解释为丢弃用户结果的授权。
