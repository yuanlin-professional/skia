# OverwriteLine.h - 终端行覆写工具常量

> 源文件: [tools/OverwriteLine.h](../../tools/OverwriteLine.h)

## 概述

此头文件定义了一个跨平台的终端行覆写常量 `kSkOverwriteLine`，用于在命令行工具中实现进度指示器、状态更新等需要在同一行反复更新输出的功能。不同操作系统的终端模拟器使用不同的控制序列来清除当前行，该常量通过条件编译为每个目标平台选择正确的序列，使得后续输出能干净地覆盖之前的内容。

## 架构位置

该头文件属于 Skia 工具层（`tools/`）的基础设施部分，为各种命令行工具（如 dm、nanobench、skpinfo 等）提供终端输出控制能力。它是一个极其轻量的工具组件，不依赖 Skia 核心库的任何头文件或类型。

在 Skia 工具生态中的使用场景：
- **dm**（测试工具）：显示测试进度
- **nanobench**（基准测试工具）：显示基准测试进度
- **其他命令行工具**：任何需要就地更新输出的场景

## 主要类与结构体

本文件不包含类或结构体，仅定义一个静态常量字符串指针：

### `kSkOverwriteLine`

```cpp
static const char* kSkOverwriteLine;
```

根据平台条件编译为不同值：

| 平台 | 宏条件 | 值 | 机制 |
|------|--------|-----|------|
| Windows | `SK_BUILD_FOR_WIN` | `"\r<79个空格>\r"` | 回车 + 空格物理覆盖 + 回车 |
| iOS | `SK_BUILD_FOR_IOS` | `"\r"` | 仅回车（不清除残留字符） |
| Linux/macOS/其他 | 默认 | `"\r\033[K"` | 回车 + ANSI Erase-in-Line |

## 公共 API 函数

无函数定义。使用方式为将此常量作为输出前缀：

```cpp
// 进度更新示例
printf("%s正在处理: %d/%d", kSkOverwriteLine, current, total);

// 配合 SkDebugf 使用
SkDebugf("%sBenchmark: %.2f ms", kSkOverwriteLine, elapsed);
```

## 内部实现细节

### Windows 实现分析
```cpp
"\r                                                                               \r"
```
使用 79 个空格字符物理覆盖当前行内容。这种方法虽然粗糙，但在旧版 Windows 命令提示符（cmd.exe）中是最可靠的，因为 cmd.exe 在 Windows 10 1511 版本之前不支持 ANSI 转义序列。79 个空格通常足以覆盖标准终端宽度（80 列）的内容。

### iOS 实现分析
```cpp
"\r"
```
仅使用回车符将光标移到行首。iOS 环境下（通常是 Xcode 控制台或嵌入式环境）可能不完全支持 ANSI 转义，因此采用最保守的方案。缺点是不会清除当前行的残留字符。

### POSIX 实现分析
```cpp
"\r\033[K"
```
- `\r`：回车，将光标移到行首
- `\033[K`：ANSI CSI 序列 "Erase in Line"（擦除行内容），清除从光标到行尾的所有字符

这是最优雅的实现，适用于支持 ANSI 转义的现代终端。

### Include Guard
使用 `#ifndef OverwriteLine_DEFINED` / `#define OverwriteLine_DEFINED` 的经典 include guard 模式。

## 依赖关系

- **无头文件依赖**：不包含任何其他头文件
- **构建系统宏**：依赖 Skia 构建系统定义的平台检测宏：
  - `SK_BUILD_FOR_WIN`：Windows 平台
  - `SK_BUILD_FOR_IOS`：iOS 平台
  - 这些宏通常由 `include/core/SkTypes.h` 或构建系统（GN/CMake）定义

## 设计模式与设计决策

- **条件编译**：使用 `#ifdef` / `#elif` / `#else` 预处理器指令实现跨平台适配，这是 C/C++ 中处理平台差异的经典模式。

- **静态常量在头文件中**：使用 `static const char*` 声明。`static` 关键字确保每个包含此头文件的翻译单元（.cpp 文件）有独立的副本，避免链接时的多重定义错误。

- **最大兼容性策略**：每个平台使用该平台上最可靠的方案，而非追求统一的 ANSI 方案。Windows 的空格填充虽不优雅但最可靠。

- **纯头文件实现**：无需对应的 .cpp 文件，作为仅有常量的头文件直接被包含。

- **优先级顺序**：Windows 检查在 iOS 之前，确保 Windows 平台不会意外匹配到其他分支。

## 性能考量

- 这是一个编译时常量字符串，无运行时性能开销。
- Windows 上的空格填充方案在输出时写入约 80 字节，开销可忽略。
- ANSI 序列方案仅写入 4 字节（`\r\033[K`），更高效。
- 在高频更新场景（如每帧更新进度），终端 I/O 可能成为瓶颈，但这与本常量无关。
- Windows 上的 79 个空格假设终端宽度不超过 80 列，对更宽的终端可能不完全覆盖。

## 相关文件

- `tools/flags/CommandLineFlags.h`：Skia 命令行工具的参数解析框架
- `dm/DMSrcSink.cpp`：dm 测试工具中使用此常量显示测试进度
- `bench/nanobench.cpp`：基准测试工具中的进度显示
- Skia 的各种命令行工具（dm、nanobench、viewer、skpinfo 等）
