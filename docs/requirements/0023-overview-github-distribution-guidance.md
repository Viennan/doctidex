# 需求 0023：在 doctidex-git Overview 保留 GitHub 分发安装指引

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0023` |
| 状态 | `approved` |
| 日期 | 2026-08-05 |
| 来源 | 用户要求创建新需求，在 `doctidex-git-overview` 中加入代码库安装指引，保留带 tag version 的 GitHub URL，并展示当前产品与协议版本；用户特别说明这属于当前产品的 GitHub 分发方式，不是开发信息。 |
| 细化关系 | 细化已批准的 [`DX-REQ-0022`](0022-optimize-doctidex-installation-guidance.md) 关于 Published Skill 不承载安装/版本信息的边界；本记录不改写该已批准历史。 |
| 实施授权 | 用户在同一请求中明确要求修改 overview Skill 文档；据此授权本记录涉及的当前 Architecture、Python Impls 表述、Published Skill 与回归测试对齐。 |
| 影响范围 | `doctidex-git-overview` 的代码库安装指引、四个 Published Skills 及其 command references、doctidex-git Skill system Architecture、产品 user-surface Architecture、Python variant 交付说明、release-surface 测试、repository review lens 和 Requirements 导航。 |
| 协议关系 | 不改变 [`doctidex` `v1.1.0` 协议](../../spec/overview.md)的结构、元信息、链接或符合性要求。 |

## 1. 已确认的意图

当前 README 已采用 GitHub VCS package URL，并以 `v<TARGET_DOCTIDEX_GIT_VERSION>` 选择与
`doctidex-git` 产品匹配的 tag。当前
plugin metadata 中的 `doctidex-git` 产品版本为 `1.0.0`，Python package metadata 也为
`1.0.0`；协议 authority [`spec/overview.md`](../../spec/overview.md) 的当前版本为 `v1.1.0`。

本记录与 0022 的 reciprocal link 尚未完成：已批准历史不能在没有额外授权时追加 backlink。
待用户另行授权后，可在 0022 增加指向本记录的 follow-up link；本轮保持 0022 不变，不把该
历史链接修订作为本需求的实现门槛。

已批准的 `DX-REQ-0022` 为了防止把已安装产品的使用 Skill 误写成开发教程，规定 Published
Skills 不重复版本、Git tag 或 package 安装信息。该规则过宽，导致 Overview 无法在自身被
直接从 GitHub 代码库获取、且 CLI 运行环境缺失时，说明当前产品由哪个代码库 tag 分发；这
些信息是安装后产品的 release identity 和获取入口，不是 editable install、源码开发、发布
或测试流程。

## 2. 当前设计

### 2.1 Overview 的受限分发入口

仅 `doctidex-git-overview` 增加一个明确标题的 distribution bootstrap 段落。它必须同时说明：

1. 当前 `doctidex-git` Skill/product metadata 版本 `1.0.0`；
2. 当前 `doctidex` 协议版本 `v1.1.0`；
3. 在已选兼容 `.venv` 中使用 GitHub HTTPS URL、匹配的 `v1.0.0` tag 和 `#subdirectory=impls/libs/python` 安装 Python distribution；
4. 该段只保留命令行文本，作为版本化产品分发 bootstrap；不要求 agent 自动执行，也不要求其创建/确认 tag、建立开发 checkout、运行测试或修改环境持久配置。

CLI 名称固定为 `doctidex-git`，Python distribution 名称固定为 `whero-doctidex`；四个
Published Skills 的命令示例直接使用 `doctidex-git`，不引入 `DOCTIDEX_GIT` 占位符。`DOCTIDEX_GIT_CACHE`
仍是独立的用户环境变量，不属于 CLI 名称。

Python package 命令采用 README 的 URL 形式并固定当前 tag：

```text
python -m pip install --no-input \
  "whero-doctidex @ git+https://github.com/Viennan/doctidex.git@v1.0.0#subdirectory=impls/libs/python"
```

tag 的创建、发布以及依赖远程 tag 的后续操作不属于本需求的测试或生命周期门槛；文档只记录
当前产品所使用的 selector 形式和 release identity。

### 2.2 信息边界

Overview 是四个 Published Skills 中唯一可以承载上述受限分发段落的 Skill。Mentions、Read
和 Maintenance 仍只描述已安装产品的工作流，不重复 package 安装、tag、版本或发布信息。
Overview 也不得扩展为 `.venv` 创建、editable install、源码开发、发布、tag 核验、测试、
维护验证或自动安装教程；缺少 CLI runtime 时仍应报告现有 prerequisite，由 operator 决定安装。分发段落只保留
命令行文本，不用辩解性文字替代其产品元数据语义。

Skill system Architecture 和产品 user-surface Architecture 必须明确记录该例外，避免后续维护
按一般“非开发边界”将它删除。Python Impls 只说明该 variant 如何装配此受限入口，不复制教程。

## 3. 实施影响

实现修改 `doctidex-git-overview/SKILL.md`，加入 Skill/product metadata 与协议版本、在已选 `.venv` 中执行的带 tag
package 安装命令和不自动执行边界。修改 Skill system 与产品 user-surface
Architecture，使 Overview 例外成为当前 authority；修改 Python variant 交付说明，避免其仍宣称
所有 Published Skill 都不能包含安装指引。

release-surface 测试改为验证：Overview 必须保留上述受限段落与当前版本/tag；其余三个 Skill 继续
排除 package、运行时安装、开发、发布、tag 确认、测试和维护验证信息。README 的参数化 tag URL
保持不变，不把未核实的远程 release tag 当成本次 forward test 前提。

## 4. 验收标准

1. Overview 明确写出 `doctidex-git` Skill/product metadata 当前版本 `1.0.0` 与 doctidex 协议当前版本 `v1.1.0`。
2. Overview 说明 CLI 依赖兼容 Python 环境；安装命令使用 `https://github.com/Viennan/doctidex.git@v1.0.0#subdirectory=impls/libs/python`、`whero-doctidex` 和 `--no-input`。
3. 四个 Published Skills 及其 references 的 CLI 示例统一使用原始命令名 `doctidex-git`，不出现 `DOCTIDEX_GIT` 占位符；`DOCTIDEX_GIT_CACHE` 仍可作为环境变量出现。
4. Skill system 与产品 Architecture 明确：Overview 的受限 GitHub distribution bootstrap 是唯一例外；其他 Published Skills 不承载这些信息，且 Overview 不得变成开发/发布/测试教程。
5. Python Impls 对该受限入口的描述与 Architecture、source metadata、README 和 Published Skill 一致。
6. release-surface 测试和 repository review lens 保护 Overview 的版本/tag/路径/产品分发入口；review 不得仅因该段出现版本或安装命令就将其判定为开发信息并要求删除；Mentions、Read、Maintenance 仍不得引入 package 或运行时安装和开发信息。
7. 文档链接、中文逻辑组织、Published Skill metadata、协议结构和 `git diff --check` 均通过适用验证；不执行、不等待也不以远程 `git+URL@v1.0.0` 安装 forward test 作为本需求状态门槛。

## 5. 实施记录

2026-08-05 已完成 Overview、Skill system Architecture、产品 user-surface Architecture、Python Impls
表述和 release-surface 测试对齐。当前实现保留 README 的参数化 tag 安装形式，并在 Overview 顶部保留
`doctidex-git` Skill/product metadata `1.0.0`、protocol `v1.1.0`，以简洁的 selected-`.venv` package
命令固定 `v1.0.0` selector；未修改已批准的 `DX-REQ-0022`，也未将远程 tag 存在性或 release-specific
安装 forward test 作为验收条件。后续评论已吸收到上述最小描述、版本元数据和 user-surface 保留规则中。
