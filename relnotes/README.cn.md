# Skia 发布说明 (Release Notes)

本目录包含即将发布的里程碑版本的发布说明。

本目录中的所有 Markdown（`*.md`）文件都被视为发布说明——本文件（`README.md`）除外。作为发布流程的一部分，这些文件的内容将被插入到 `RELEASE_NOTES.md` 中，然后这些文件将被删除。

发布分支工具会自动完成此聚合操作，更详细的说明请参见 https://skia.googlesource.com/buildbot/+/refs/heads/main/sk/。

## Markdown 支持

发布说明可以自由使用 Markdown 语言的几乎所有功能。但是，由于它们会被插入到更大的发布说明文件中，因此应遵循以下准则。

1. 不要引用 `relnotes` 目录中的任何本地文件。

   例如不要使用 `![Tooltip](image.png)` 这样的写法。

   允许引用 URL。
2. 不要使用[标题](https://www.markdownguide.org/basic-syntax/#headings)。
   顶层发布说明文件（RELEASE_NOTES.md）中每个里程碑版本使用一个标题。
3. 不要以[星号](https://www.markdownguide.org/basic-syntax/#unordered-lists)或其他前导标记开头。这些会由脚本自动插入。
4. 生成发布说明时，里程碑版本之间会自动插入水平分隔线。
