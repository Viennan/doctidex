# doctidex-git 0.1.0 Python 参考实现当前限制

本篇只记录当前代码事实，不代表 Architecture 的目标设计。限制修复后应同步更新代码、
测试、相关 Details，以及确实改变公共行为时的 Architecture 和 Skills。

## 1. CLI 与输出

- `--depth` 被限制到 0..32，但未参与遍历或裁剪。
- 同一 cursor offset 应用于 payload 中所有顶层列表，没有 collection-specific cursor。
- `mount_sync.changed` 是 boolean；其他多数 operation 的 `changed` 是路径数组。
- write command 不传 dry-run 或 apply 时默认 preview，但输出不都含 `applied`。
- parser 与全局整数解析错误不保证 JSON。
- blocked 人读输出只展示第一个 finding 并隐藏 details；复杂失败必须用 JSON。
- `status: warning` 且 plugin readiness blocked 当前退出 0；只有 protocol fail 退出 1。

## 2. 协议解析与校验

- link 校验只检查可解析路径是否越过 link root，不检查目标存在、anchor、推荐形式或
  跨 mount 目标有效性。
- link 与语义候选只理解 CommonMark `link_open`；非标准扩展、图片、裸路径和 prose
  reference 不进入机器判断。
- `validate_filter_conditions` 在过滤字段不是 list 时引用未定义的 `field`，当前会成为
  `unexpected_failure`，而不是 `filter_not_list` finding。
- malformed child index 在路径上下文中暂由父 index 负责，只有完整 validation 报错。
- prepare 只确认 source 根 index 存在且 root marker 为真，不要求 source 整体通过校验。

## 3. Git 就绪与 Source

- 根 `.gitignore` 检查在 Git 返回相对 source path 时按进程 cwd 解析；从宿主子目录运行
  可能误判正确根规则。
- source cache identity 仍是原始 URL 文本，等价 URL 可能重复 clone。root relation 只
  额外识别 Git common directory、精确 remote URL 和可解析的相同本地路径；镜像、fork、
  等价但文本不同的 remote URL 会保守返回 unknown。
- HTTP(S) userinfo 被拒绝；其他 Git URL 的校验和公开清理有限。
- Git 错误分类依赖英文 stderr substring，本地化输出可能落入 `git_failed`。
- online check 和批量 sync 按 mount 顺序解析，同源 mount 可能重复 fetch。

## 4. State 与生命周期

- 非法或不可读 state 静默退回空状态，没有自动恢复、告警或 orphan 扫描。
- root identity 不解析 symlink，同一物理根的不同访问路径可能得到不同 store。
- 没有 garbage collection；已删除或失配声明留下的共享数据不自动清理。
- maintenance record 路径丢失时，status 返回空 changes 和 `ready`，没有 unavailable 状态。
- file lock 无超时，等待状态不进入 CLI。
- worktree/projection 创建与 state 保存不是事务，异常可能留下未登记资源。

## 5. 可读呈现

- symlink 失败后的 fallback 是 managed directory；后续 sync 当前拒绝替换普通目录。
- source symlink 被重建为解析后的绝对 target，可能离开 source root，没有额外边界检查。
- hard link 与 chmod 只防误写，不构成安全隔离。
- fallback、跨文件系统 hard-link、Windows 和 symlink 权限现场缺少完整自动化测试。

## 6. 语义与 Surface

- CLI 不读取任务意图、不排序候选，也不形成内容质量结论。
- `inspect` 为生成 semantic candidates 会运行整根 validation，没有增量索引。
- `context.mode` 由路径字符串片段判断，不验证声明或 namespace root 本身。
- `check` 不返回 protocol library 的 `mount_count`；handoff findings 不含独立 readiness
  finding。
- Python import surface、内部 state 文件和物理路径都没有稳定兼容承诺。
