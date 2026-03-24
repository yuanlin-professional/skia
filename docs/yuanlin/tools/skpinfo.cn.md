# skpinfo.cpp - SKP 文件信息检查工具

> 源文件: [tools/skpinfo.cpp](../../tools/skpinfo.cpp)

## 概述

`skpinfo` 是一个命令行工具，用于检查和验证 Skia Picture（SKP）文件的完整性和元数据。SKP 文件是 Skia 绘图命令的序列化格式，用于记录和回放渲染操作。此工具可以打印 SKP 文件的版本号、裁剪矩形（cull rect）和内部标签信息，其主要用途是检测 SKP 文件在录制过程中是否被截断。工具通过不同的返回码指示检测结果。

## 架构位置

该工具位于 Skia 的工具层（`tools/`），是一个独立的命令行应用程序。它直接使用 Skia 核心库的 SKP 解析 API（`SkPicture`、`SkPictureData`），不依赖渲染后端。工具在 CI 系统中用于验证测试 SKP 文件的有效性，也可供开发者在调试 SKP 录制问题时手动使用。

## 主要类与结构体

本文件不定义新的类，但使用以下 Skia 核心类型：

- **`SkFILEStream`**：文件输入流，用于读取 SKP 文件
- **`SkPictInfo`**：SKP 文件头信息结构，包含版本号和裁剪矩形
- **`SkFontDescriptor`**：字体描述符，用于反序列化 SKP 中的字体数据
- **`CommandLineFlags`**：Skia 命令行参数解析框架

**命令行标志**：
- `-i/--input`：输入 SKP 文件路径
- `-v/--version`：是否显示版本号（默认 true）
- `-c/--cullRect`：是否显示裁剪矩形（默认 true）
- `-f/--flags`：是否显示标志（默认 true）
- `-t/--tags`：是否显示标签信息（默认 true）
- `-q/--quiet`：静默模式

**返回码**：
| 返回码 | 常量 | 含义 |
|--------|------|------|
| 0 | `kSuccess` | 文件有效 |
| 1 | `kTruncatedFile` | 文件被截断 |
| 2 | `kNotAnSKP` | 不是有效的 SKP 文件 |
| 3 | `kInvalidTag` | 包含无效标签 |
| 4 | `kMissingInput` | 缺少输入文件 |
| 5 | `kIOError` | I/O 错误 |

## 公共 API 函数

| 函数 | 参数 | 返回值 | 描述 |
|------|------|--------|------|
| `main(argc, argv)` | 命令行参数 | 返回码 (0-5) | 解析并验证 SKP 文件 |

## 内部实现细节

1. **文件头验证**：使用 `SkPicture_StreamIsSKP()` 验证文件是否为有效的 SKP 格式并提取 `SkPictInfo`。
2. **元数据显示**：输出版本号和裁剪矩形（`fCullRect` 的四个分量）。
3. **数据块遍历**：读取 `hasData` 布尔值后，循环读取标签-大小对：
   - **`SK_PICT_READER_TAG`**：读取器数据块
   - **`SK_PICT_FACTORY_TAG`**：工厂数据块
   - **`SK_PICT_TYPEFACE_TAG`**：字体数据块（chunkSize 表示字体数量而非字节数），逐个反序列化 `SkFontDescriptor`
   - **`SK_PICT_PICTURE_TAG`**：子 picture 引用（因格式限制提前退出）
   - **`SK_PICT_BUFFER_SIZE_TAG`**：缓冲区大小信息
4. **截断检测**：在每个读取操作后检查是否成功，stream 的 `move()` 操作前预先检查剩余空间。

## 依赖关系

- **Skia 核心**：`SkPicture`、`SkStream`、`SkPictureData`、`SkPicturePriv`、`SkFontDescriptor`
- **Skia 工具**：`CommandLineFlags`（命令行解析）
- **C++ 标准库**：基本 I/O

## 设计模式与设计决策

- **渐进式验证**：工具采用边读边验证的策略，在每次读取操作后立即检查错误，能精确定位截断位置。
- **非完整反序列化**：工具不尝试完整反序列化 SKP 文件（那是 `SkPicture::MakeFromStream` 的工作），而是只做结构级验证，更快更轻量。
- **提前退出策略**：遇到 `SK_PICT_PICTURE_TAG` 时提前退出，因为子 picture 的大小信息不以字节为单位存储（注释标记为 TODO）。
- **静默模式**：`-q` 标志支持在脚本中使用时仅依赖返回码判断结果，不产生不必要的输出。
- **结构化返回码**：6 种不同的返回码使调用脚本能准确区分不同的错误类型。

## 性能考量

- 工具只读取文件头和标签结构，跳过实际数据块内容（通过 `stream.move(chunkSize)`），速度很快。
- 对大文件（数百 MB 的 SKP）也能快速完成，因为不需要读取全部内容。
- 字体反序列化（`SkFontDescriptor::Deserialize`）是最耗时的操作，但通常字体数量有限。

## 相关文件

- `include/core/SkPicture.h`：SKP 文件的核心 API
- `src/core/SkPictureData.h`：SKP 数据块定义和标签常量
- `src/core/SkPicturePriv.h`：SKP 私有辅助函数（如 `SkPicture_StreamIsSKP`）
- `src/core/SkFontDescriptor.h`：字体描述符序列化/反序列化
- `tools/flags/CommandLineFlags.h`：命令行标志框架
