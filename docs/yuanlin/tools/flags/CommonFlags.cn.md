# CommonFlags 通用命令行标志辅助

> 源文件: `tools/flags/CommonFlags.h`

## 概述

此头文件定义了 Skia 测试和工具程序中通用的命令行标志辅助函数。目前仅提供一个用于从命令行指定的目录中收集图片路径的辅助函数 `CollectImages`。该文件属于 Skia 工具层的命令行解析基础设施，服务于需要处理图片输入的各种测试和基准工具。

## 架构位置

- 所属模块：`tools/flags/`（命令行标志工具）
- 角色：命令行参数处理辅助库
- 上层消费者：Skia 的 dm（测试运行器）、bench（基准测试）等工具
- 依赖基础：`tools/flags/CommandLineFlags.h`

## 主要类与结构体

### `CommonFlags` 命名空间
包含通用的命令行标志辅助函数，避免全局命名空间污染。

## 公共 API 函数

### `CommonFlags::CollectImages`
```cpp
bool CollectImages(const CommandLineFlags::StringArray& dir,
                   skia_private::TArray<SkString>* output);
```

**功能：** 从命令行标志指定的目录中收集图片文件路径。

**参数：**
- `dir`：命令行中指定的文件/目录路径数组
- `output`：用于存储收集到的图片路径的输出数组

**返回值：**
- 如果指定的文件/目录不存在，返回 false
- 如果指定目录中没有支持的图片类型，返回 false
- 如果指定的是单个文件，无论文件类型都返回 true（假定用户有意测试此文件）
- 否则返回 true

**设计要点：**
- 单文件模式不检查文件类型，给予用户最大灵活性
- 目录模式只收集 Skia 支持的图片格式

## 内部实现细节

- 头文件使用 `#pragma once` 防护而非传统的 include guard
- 依赖 `SkString` 作为路径字符串类型
- 依赖 `skia_private::TArray` 作为动态数组容器

## 依赖关系

- `include/core/SkString.h`：Skia 字符串类
- `include/private/base/SkTArray.h`：Skia 私有动态数组
- `tools/flags/CommandLineFlags.h`：命令行标志基类，提供 `StringArray` 类型

## 设计模式与设计决策

- **命名空间封装**：使用 `CommonFlags` 命名空间而非类，适合无状态的工具函数集合
- **验证与容错**：对文件/目录存在性和图片类型进行验证，但对单文件保持宽松策略
- **最小接口**：当前仅暴露一个函数，保持接口简洁

## 性能考量

- `CollectImages` 涉及文件系统操作（目录遍历），在大目录下可能有 I/O 开销
- 使用 `TArray` 而非 `std::vector`，与 Skia 内部容器保持一致
- 此函数通常仅在程序初始化时调用一次，性能影响可忽略

## 相关文件

- `tools/flags/CommandLineFlags.h` - 命令行标志解析框架
- `tools/flags/CommonFlags.cpp` - 此头文件的实现
- `dm/DMSrcSink.cpp` - 使用 `CollectImages` 的测试运行器

### 使用示例

典型的使用场景是在命令行测试工具中指定一个包含测试图片的目录：

```
./dm --images /path/to/test/images
```

该函数会递归遍历目录，收集所有 Skia 支持的图片格式（PNG、JPEG、WebP、BMP、GIF 等）。
