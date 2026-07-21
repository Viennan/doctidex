# 链接

协议状态：**v0.0.2 当前版本**。

## 内部链接

Whero 维护文档正文中指向同一所有权 `Whero Wiki` 内其他文档的链接，必须使用标准相对 Markdown 目标，并从链接文档解析。保留 fragment，并根据 Markdown 标题或显式 HTML anchor 进行校验。

不得创建类似 URI 的 Wiki-root 目标、Wiki-root absolute 或文件系统 absolute 目标。工具可以接受 Wiki-root-relative 路径作为便捷的调用输入，但写入 Markdown 时必须相对于目标文档生成链接。

链接不会隐式跨越 `External Reference` 所有权边界。文档可以链接到逻辑 Mount 或 View 路径，但解析时使用拥有该文档的 Wiki 或 View，并遵循边界。

## Collected Source

不得仅为符合维护文档链接风格而重写 collected prose。经过授权的本地化工作流只能修复链接目标，或添加维护协议定义的准确 unresolved marker。

## View

在 `View` 中指向未选择内容的链接是合法链接，应报告为 unavailable 而不是 missing。跟随或检查链接不会自动扩增 View；只有调用方明确请求扩增时，链接目标才成为 `Selection`。当直接 source 本身是 View 时，只能选择该 source View 中当前 available 的路径；不得绕过 source View 从最终 Wiki 获取 unavailable 的内容。
