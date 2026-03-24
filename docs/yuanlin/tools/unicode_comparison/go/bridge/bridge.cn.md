# bridge - SkUnicode CGo 桥接层

> 源文件: `tools/unicode_comparison/go/bridge/bridge.go`

## 概述

bridge.go 是 Skia Unicode 比较工具的 Go 语言桥接层，通过 CGo 调用 C++ 编写的 SkUnicode 库函数。它封装了文本属性计算（字素簇、换行、空白、词边界等）、大小写转换和句子分割等 Unicode 操作。

## 架构位置

位于 `tools/unicode_comparison/go/bridge/` 目录，是 Go 应用程序与 Skia C++ Unicode 实现之间的中间层。通过 CGo 的 LDFLAGS 链接 `libbridge` 共享库。

## 主要类与结构体

### `CodeUnitFlags` - 代码单元标志位枚举
包含 `kGraphemeStart`、`kSoftLineBreakBefore`、`kHardLineBreakBefore`、`kPartOfWhiteSpaceBreak`、`kWordBreak`、`kControl` 等标志。

### `SkString` / `IntPtr` - C 指针包装结构

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `PerfComputeCodeunitFlags(text)` | 计算文本代码单元标志并返回耗时 |
| `GetFlags(index)` | 获取指定索引的代码单元标志 |
| `GetSentences(text)` | 获取文本的句子边界位置数组 |
| `TrimSentence(text, length, limit)` | 在限制长度内修剪句子 |
| `FlagsToString(flags)` | 将标志位转换为可读字符串 |
| `ToUpper(str)` | 大写转换 |
| `InitUnicode(impl)` | 初始化指定的 Unicode 实现 |
| `CleanupUnicode()` | 清理 Unicode 资源 |

## 内部实现细节

- 使用 `C.CString` 将 Go 字符串转为 C 字符串，并用 `defer C.free` 确保释放
- `GetSentences` 使用 `unsafe.Slice` 将 C 数组转为 Go 切片
- `FlagsToString` 通过位运算将标志位映射到字符代码 (G/S/H/W/D/C)

## 依赖关系

- CGo 链接: `../../cpp/bridge.h`, `-lbridge`
- Go 标准库: `unsafe`

## 设计模式与设计决策

- **桥接模式**: 将 C++ API 包装为 Go 友好的接口
- **延迟释放**: 所有 C 字符串分配都使用 `defer C.free` 防止内存泄漏

## 性能考量

- CGo 调用存在固有开销（约 100ns/调用），但对于批量文本处理可忽略
- `PerfComputeCodeunitFlags` 直接返回计算耗时，用于性能对比

## 相关文件

- `tools/unicode_comparison/cpp/bridge.h` - C 桥接头文件
- `tools/unicode_comparison/go/extract_info/main.go` - 信息提取工具
