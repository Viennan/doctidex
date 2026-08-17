# 需求 0001：定义 doctidex v2 目录树外观

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0001` |
| 状态 | `approved` |
| 日期 | 2026-08-07 |
| 来源 | 用户要求创建第一个需求，定义 doctidex v2 目录树应该是什么样子 |
| 影响范围 | doctidex v2 目录树的入口文件、`index.md` 出现位置与正文、`boundary-set`、根入口 frontmatter、普通内容和 Markdown link |
| 文档性质 | 当前需求记录 |

本文记录 doctidex v2 目录树外观的定义需求。当前已确认的第一步是对 v1 的目录树结构
要求做减负，并将第一阶段的结构约束固定下来。

## 1. 需求意图

需要明确一个目录树在什么条件下可以被识别为 doctidex v2，以及人、agent 和程序从目录
树外观上能够看到哪些稳定结构。当前目标不是继续继承 v1 的全部目录树要求，而是先完成
结构减负：规范要求的核心入口收敛为 `index.md`，其 frontmatter 必须保留 `type`、
`doctidex.type` 和 `doctidex.root`。`index.md` 可以
按需出现在目录树的任意位置，且其祖先路径不要求连续出现 `index.md`。

v2 规范只强制要求根目录下的 `index.md` 入口及其三个 frontmatter 字段；目录树仍可承载
其他普通内容。`boundary-set` 可以标识当前目录树的 escape 节点；路径越过节点后，当前
目录树的规则不再适用。

## 2. 目标与范围

### 2.1 当前已确认的第一步

- 本需求以 v1 的目录树结构要求为减负对象，不直接照搬 v1 的完整结构。
- 第一阶段的目录树规范只保留 `index.md` 这一核心入口。
- 根入口 `index.md` 的 frontmatter 必须保留以下字段：
  - 顶层 `type`；
  - `doctidex.type`；
  - `doctidex.root`。
- `boundary-set` 是当前目录树 escape 节点的抽象集合；v2 定义其语义，但不在 frontmatter
  中定义用于存储或声明该集合的字段。
- 越过 `boundary-set` 节点后，当前目录树的 link、`index.md` 等规则不再适用；节点后的
  路径可以是任意目录树。
- 当前目录树内的 Markdown 文档仍可以 link 到越过任一 `boundary-set` 节点后可达的任意文档。
- `index.md` 可以按需出现在目录树的任意位置。
- 一个 `index.md` 的祖先路径不要求连续存在 `index.md`。
- 虽然位置不受强制限制，但不建议将 `index.md` 放置在具有自有规范或频繁变化的临时性目录
  中，例如某些工具的配置目录、源码目录或临时工作区。
- `index.md` 正文需要提供满足渐进式披露、导航和查询所需的信息。
- 需要进行信息分层时，可以在子代目录的合适位置建立新的 `index.md`，避免单一文件中的
  索引信息过于杂乱并分散注意力。
- `index.md` 正文没有固定的组织格式。
- 第一阶段不扩展上述规则之外的目录树结构定义。

### 2.2 非目标

实现代码、校验器、CLI 和 Skills 的修改不属于本需求的定义内容；本需求对应的 Architecture
草案见 [doctidex v2 目录树外观规范](../architecture/doctidex-v2-directory-tree.md)。

## 3. 受影响的产品表面

| 表面 | 预期影响 | 当前状态 |
|---|---|---|
| v2 目录树结构定义 | 规定根入口、`index.md` 正文、`boundary-set`、frontmatter、普通内容承载方式和 Markdown link | 已确定 |
| v2 协议/模型文档 | 承载本阶段的规范性结构约束 | [Architecture 草案](../architecture/doctidex-v2-directory-tree.md) |

## 4. 已确认的设计决策

### 4.1 最小有效目录树

当前已确认的最小结构如下：

```text
<doctidex-root>/
└── index.md
```

`index.md` 的基础 frontmatter 固定为以下字段和值：

```yaml
type: index
doctidex:
  type: index
  root: true
```

第一阶段的上述要求均为 doctidex v2 的规范约束。

### 4.2 `index.md` 的出现位置

根入口之外，`index.md` 可以按需出现在目录树内的任意位置。其出现不要求从根目录到该
文件所在目录的每一级目录都包含 `index.md`；任意祖先目录可以不含 `index.md`。

```text
<doctidex-root>/
├── index.md
└── guide/
    └── topic/
        └── index.md
```

上例中的 `guide/` 不含 `index.md`，不会妨碍 `guide/topic/index.md` 出现或被读取。

位置选择仍应考虑目录的稳定性和既有约定。不建议将 `index.md` 放置在具有自有规范或频繁
变化的临时性目录中，例如某些工具的配置目录、源码目录或临时工作区；该建议不改变
`index.md` 可以按需出现在任意位置的规则。

### 4.3 `index.md` 正文职责

`index.md` 正文是 user surface 的导航和查询入口，必须提供足够的信息支持渐进式披露、
导航和查询。正文可以根据内容规模，在子代目录的合适位置增加 `index.md` 进行分层；
建立子代 `index.md` 是按需选择，不是每个目录的固定要求。

`index.md` 的导航 link 遵循以下规则：

| 规则 | 要求 |
|---|---|
| 覆盖范围 | 不要求覆盖范围内的所有文档，也不要求追求客观的 link 覆盖率。已有文档自身提供有效导航时，可以直接复用，不必为达到覆盖率额外重复链接。 |
| 重复出现 | 没有一个文档 link 只能出现一次的要求。同一 link 可以多次出现在其 ancestor `index.md` 中，只要有助于导航或查询。 |
| 导航与关键文档 | `index.md` 可以链接一个已有导航性质的文档，也可以额外链接其中的关键文档，只要有助于导航或查询。 |
| 链接范围 | link 通常指向 `index.md` 所在范围内的文档，这是最佳实践；link 也可以指向其他范围内的文档。 |

`index.md` 正文没有固定的组织格式。

### 4.4 `boundary-set` 规则

`boundary-set` 是当前 doctidex 目录树中 escape 节点（目录）的抽象集合。v2 定义该集合及
其边界语义，但不在 frontmatter 中定义用于存储或声明它的字段，也不规定其他具体声明机制。
集合中的每个节点标识当前目录树的 escape 边界；路径越过该节点后，当前目录树的 link、
`index.md` 和其他结构规则不再适用。边界节点后的路径可以是任意目录树，包括另一个
doctidex 目录树或其子目录树。边界只界定当前目录树规则的适用范围，不限制当前目录树内
Markdown 文档建立跨界 link；这些文档仍可以 link 到越过任一 `boundary-set` 节点后可达的
任意外部文档。

### 4.5 目录树 Markdown 文档的 link 规则

以下 link 规则适用于当前 doctidex 目录树规则有效范围内的所有 Markdown 文档，不仅适用于
`index.md`：

所有这些 Markdown 文档都可以使用 Markdown link 配合常用 anchor 链接目标文档和目录。

| 规则 | 要求 |
|---|---|
| 路径根 | 以 `/` 开头的 link path 以当前所在 doctidex 目录树的根目录作为根目录解释。 |
| 路径表达 | 鼓励使用相对路径简化 link 表达。 |

#### 4.5.1 结构化 link 注释

结构化 link 注释附着于单个 Markdown link，使用 HTML 注释承载 `doctidex` YAML 映射，支持
flow mapping 和 block mapping：

结构化 link 注释的格式、出现位置和字段语义由本节定义。

```markdown
[External](/external/guide.md)
<!-- doctidex: {cross-boundary-point: /external} -->
```

```markdown
[External](/external/guide.md)
<!-- doctidex:
  cross-boundary-point: /external
-->
```

注释位于 link 后的连续 HTML 注释序列中；link 与首个注释、相邻注释之间可以只有空白，
遇到其他内容时关联结束。`doctidex` 后的 YAML 必须是无重复键的映射。一个 link 的关联序列最多包含一个 `doctidex` 注释；其他注释
可以与它共存。为支持渐进式读取，`doctidex` 注释应放在序列首位。

`cross-boundary-point` 字段定义如下：

| 字段 | 要求与语义 |
|---|---|
| `cross-boundary-point` | 路径字符串，形式为 link path 中包含该 `boundary-set` 节点的路径前缀；该节点属于包含 link 所在文档的 doctidex 目录树。 |

## 5. 依赖与相关记录

目前没有已确认的 Requirement 依赖、细化、取代或后续关系。确定关系后，必须在相关记录
两端添加可导航链接。

## 6. 验收标准

第一阶段在满足以下条件时视为定义完成：

1. 需求明确记录 v2 第一阶段相对于 v1 的目录树结构减负目标。
2. 需求明确记录 `index.md` 为当前保留的核心入口。
3. 需求明确记录根入口 frontmatter 仅保留顶层 `type`、`doctidex.type`、`doctidex.root` 三项必需字段；v2 不在 frontmatter 中定义 `boundary-set` 字段。
4. 需求确认 `index.md` 是强制入口、普通内容可以共存，并记录三个字段的固定取值和类型。
5. 需求明确实现代码、测试和 Skills 不属于本阶段目录树外观定义。
6. 需求明确 `index.md` 可以按需出现在目录树的任意位置。
7. 需求明确一个 `index.md` 的祖先路径不要求连续存在 `index.md`。
8. 需求明确 `index.md` 的位置选择建议：不建议放置在具有自有规范或频繁变化的临时性目录中，
   例如某些工具的配置目录、源码目录或临时工作区；该建议不构成位置禁令。
9. 需求明确 `index.md` 正文必须支持渐进式披露、导航和查询，并允许按需使用子代 `index.md` 分层。
10. 需求明确 `index.md` 专属的导航 link 覆盖范围、重复出现、导航文档与关键文档之间的关系，
   以及 link 通常同范围但不禁止跨范围的规则。
11. 需求明确 `index.md` 正文没有固定组织格式。
12. 需求明确当前 doctidex 目录树规则有效范围内的所有 Markdown 文档都可以使用 Markdown link
   配合常用 anchor，并适用以下路径规则：以 `/` 开头的 link path 使用当前 doctidex 目录树根目录，
   同时鼓励使用相对路径。
13. 需求明确 `boundary-set` 的抽象集合语义、escape 节点语义，以及越过节点后的任意目录树边界；当前树内 Markdown 文档仍可 link 到任意边界外文档，并明确 v2 不在 frontmatter 中定义其字段或声明格式。
14. 需求明确结构化 link 注释的 HTML/YAML 格式、link 后的关联位置、单个 `doctidex` 注释
   限制，并保留 `cross-boundary-point` 字段。

## 7. 实施与状态

本记录目前为 `approved`，内容已完成第一阶段的需求定义；后续实现工作另行处理。
