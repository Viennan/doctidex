# 程序集成

doctidex-git `v1.0.0` 唯一稳定程序接口是启动 CLI 并消费 `--json`。Python import、内部
records 和物理 storage path 不承诺兼容。精确 argv 与 schema 分别由 [CLI](cli.md) 和
[CLI JSON Schema](cli-schema.md) 定义；本篇只说明程序如何组合调用、分页、幂等和兼容
处理，不重新定义字段。

## 1. 调用顺序

```text
构造精确 argv 与 cwd
  -> 使用 --json 调用
  -> 解析单个 JSON object
  -> 验证 schema_version
  -> 先按 status 分支，再按 operation 分支
  -> 消费 operation 专属字段
  -> 处理 findings/candidates/collection
  -> 重试前保留 changed/result
```

调用方为每次 invocation 保存 cwd、argv、selected root、operation、exit code 和 result；
不能假定进程记住上次 root。

## 2. 成功与失败

1. 先看 `status`。blocked 时只依赖 common envelope 和已出现的可靠 operation fields。
2. 再看 `operation`，按对应 required schema 解析 ok/warning payload。
3. validate 继续看 coverage/scopes、protocol/scan/semantic；不能用 status 或 exit code 代替，
   也不能把 scoped pass 缓存或显示成全根符合。
4. link-parse 先按 `mapping_origin` 和 `target_state` 分支；
   `dependency_not_installed` 是正常可选依赖状态，不按 error 重试，`owner_install_missing`
   才进入 restore 路径，available 使用外层 `working_path`。
5. cache clean 先确认 `root` 为 null，再按 `state` 和三个 worktree counts 分支；planned 才
   能进入授权后的 apply，preserved 是完成的保护结果，不能按 transient error 自动重试。
6. 读取 findings 的 stable code，不匹配 message。
7. `requires_user` 非 null 时停止自动重试，向上层请求对应决定。
8. 重试前保存 `changed`、`result` 和仍可用 paths，不能假设 blocked 已回滚。

## 3. Dry-run 与 apply

程序集成把 external mutation 建模为两个独立调用：

```text
dry-run -> 审阅 source/commit/install 或 link/manifest/Git tracking/planned
        -> 获得授权
        -> 使用相同 root/source/revision/dependency-parent 或 source/target 执行 apply
        -> 验证实际 changed、固定 commit 与恢复清单状态
```

apply 前 root/index/target/manifest/Git tracking 改变会 conflict；调用方重新 dry-run，而不是强行覆盖。dry-run
可能访问 network，但不会为 apply 保留隐式授权或保证 remote 不变；apply result 的
resolved commit 才是发布基准。

cache cleanup 使用独立的同 URL 调用对：

```text
cache clean dry-run -> 审阅 source ID、linked/valid/prunable counts 与 planned state
                    -> 获得 operator 授权
                    -> 以相同 URL apply
                    -> 接受 removed，或按 preserved/conflict 重新决策
```

两次调用之间的 counts 不是 reservation。apply 在 source mutation boundary 内重新分类；
出现有效 worktree 或并发变化时保留 cache。程序集成不得访问内部 cache path，也不得因
`changed` 为空否认 `state: removed`。

## 4. 分页

调用方原样传回 `next_cursor`，保持 operation、root、规范化 scope/filter、limit 与命令模式。validate
可以重复提供原始 scope 参数，但其规范化结果必须与第一页相同；调用次序或冗余路径不同而
规范化集合相同仍是同一查询。每页累计
`collection.lists` 的 returned，直到 truncated false。external restore 还必须保持同一
dry-run/apply mode；manifest 内容改变会令 cursor invalid，而已恢复载荷不会。cursor invalid 时从第一页重新获取并
以稳定 item identity 去重；不得解析 token 或猜测 offset。

## 5. 幂等性

- validate、link-parse、list 是 read-only，可在 state 不变时安全重复；dependency install 后
  重跑同一 link-parse 可以从 `dependency_not_installed` 变为 available，并返回外层路径。
- install apply 的同 root/source/normalized selector 重试复用稳定 install ID/path；不同
  selector 即使 commit 相同也使用不同 install。link apply 的同 target/同 mapping 重试复用
  已完成状态。
- install 同 key 永不重新解析已记录 branch/default branch；dependency-only 可由普通 install
  原地提升为 direct，direct 不降级。
- restore 只补齐 manifest 中缺失的 exact install；匹配项 unchanged，既有 link 不被重写。
- worktree open 每次成功都在 selected root 的 `/.doctidex` 下创建新隔离现场，不是幂等命令；调用方先 list 或检查
  reuse_candidate_count。
- close 对已关闭 path 返回 worktree_unmanaged，不把手工目录当作成功清理。
- cache clean dry-run 在 source state 不变时可重复；apply 成功删除后再次调用返回
  `cache_source_not_found`，调用方可把它视为“当前无需再清理”，但不能记录第二次 removed。

## 6. 兼容性

- `schema_version` major 不识别时停止；同 major 的新增 optional fields 可忽略。
- required field 缺失、类型变化、未知 operation 或未知 enum 值应显式兼容失败。
- 不依赖 JSON key order、人读 label、message 文案或 diagnostic ID 格式。
- credentials、internal storage 和 traceback 不应出现在 payload；发现时按安全错误处理。
- `cache_clean` 是稳定 operation，即使 Published Skills 当前不暴露它；程序集成不能以
  Skill 路由表作为 CLI operation allowlist。

## 7. 不提供的接口

没有稳定 Python service/dataclass API、state-file API、watch/stream/subscription、跨命令
transaction 或 server session。调用方使用原生文件和 Git APIs 读取/修改返回路径，而不
反推 doctidex-git 内部 checkout、object store 或 lock 命令。

程序也可以完全不调用 external/worktree 命令并使用原生 Git API；受管 schema 不定义或
限制这些外部工作流。
