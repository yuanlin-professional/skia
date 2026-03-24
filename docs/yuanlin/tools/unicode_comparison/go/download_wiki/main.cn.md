# download_wiki - Wikipedia 页面下载工具

> 源文件: `tools/unicode_comparison/go/download_wiki/main.go`

## 概述

download_wiki/main.go 从维基百科下载指定语言的页面内容，将其按章节和句子分割为小型文本文件，作为 Unicode 实现比较的测试数据集。支持 25 种语言（包括中文、阿拉伯语、俄语等），可配置下载数量和文本长度限制。

## 架构位置

位于 `tools/unicode_comparison/go/download_wiki/` 目录，是比较工具链的数据准备阶段。

## 主要类与结构体

无自定义类型。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `downloadLocalPagesBySections(...)` | 下载页面并按章节/句子拆分为文件 |
| `main()` | 入口，解析参数并执行下载循环 |

## 内部实现细节

- 使用 `go-wiki` 第三方库访问 Wikipedia API
- 通过 `bridge.GetSentences` 利用 ICU 进行句子边界检测
- `bridge.TrimSentence` 确保单个文本不超过 `textLimit`
- 默认支持的 25 种语言按 Wiki 页面数量降序排列
- 重试机制：失败时减少 `attempt` 计数器

## 依赖关系

- `github.com/trietmn/go-wiki` - Wikipedia API
- `go.skia.org/skia/tools/unicode_comparison/go/bridge` - SkUnicode 桥接
- `go.skia.org/skia/tools/unicode_comparison/go/helpers` - 辅助函数

## 设计模式与设计决策

- **多语言支持**: 硬编码语言列表覆盖主要 Unicode 使用场景
- **句子级分割**: 使用 ICU 句子边界检测确保文本在语义边界处断开

## 性能考量

- 网络 I/O 是主要瓶颈；支持批量下载以减少 API 调用次数

## 相关文件

- `tools/unicode_comparison/go/bridge/bridge.go` - 桥接层
- `tools/unicode_comparison/go/extract_info/main.go` - 信息提取
