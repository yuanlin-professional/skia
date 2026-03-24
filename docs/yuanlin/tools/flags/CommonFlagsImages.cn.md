# CommonFlagsImages - 图像文件收集工具

> 源文件: `tools/flags/CommonFlagsImages.cpp`

## 概述

CommonFlagsImages 是 Skia 工具链中用于收集和枚举图像文件的实用模块。它提供了一个核心函数 `CollectImages`，能够根据命令行参数指定的路径（文件或目录）扫描并收集所有支持格式的图像文件路径。该模块支持多种常见图像格式（BMP、GIF、JPG、PNG、WEBP 等），以及可选的 RAW 相机格式。

## 架构位置

该文件属于 Skia 工具链的命令行标志（flags）子系统，位于 `tools/flags/` 目录。它为各种测试工具和基准程序提供统一的图像输入收集功能。

## 主要类与结构体

本文件不定义类或结构体，仅在 `CommonFlags` 命名空间中实现功能函数。

## 公共 API 函数

### `CommonFlags::CollectImages`
```cpp
bool CollectImages(const CommandLineFlags::StringArray& images, TArray<SkString>* output);
```
- **功能**: 遍历命令行传入的图像路径列表，将有效的图像文件路径收集到输出数组中
- **参数**: `images` - 包含路径的字符串数组；`output` - 输出图像路径的目标数组
- **返回值**: 成功返回 `true`，路径不存在或目录中无图像时返回 `false`
- **行为**: 若路径是目录，则扫描该目录中所有支持格式的文件；若路径是文件，则直接添加

## 内部实现细节

- 支持的基础格式：bmp, gif, jpg, jpeg, png, webp, ktx, astc, wbmp, ico
- 在非 Windows 平台上额外支持大写扩展名变体（如 BMP, GIF 等）
- 当定义了 `SK_CODEC_DECODES_RAW` 时支持 RAW 格式：arw, cr2, dng, nef, nrw, orf, raf, rw2, pef, srw
- 使用 `SkOSFile::Iter` 迭代目录中特定扩展名的文件
- 使用 `SkOSPath::Join` 拼接目录和文件名路径

## 依赖关系

- `src/core/SkOSFile.h` - 文件系统操作（存在性检查、目录判断、目录迭代）
- `src/utils/SkOSPath.h` - 路径拼接工具
- `tools/flags/CommonFlags.h` - 命名空间和标志系统声明
- `skia_private::TArray` - 动态数组容器

## 设计模式与设计决策

- **命名空间组织**: 使用 `CommonFlags` 命名空间集中管理所有通用标志处理函数，避免全局名称冲突
- **平台条件编译**: 在 Windows 平台上省略大写扩展名，因为 Windows 文件系统默认不区分大小写
- **可扩展的格式列表**: RAW 格式通过编译开关控制，允许按需裁剪编解码器支持

## 性能考量

- 扩展名列表采用静态 C 字符串数组，无运行时构造开销
- 目录扫描按扩展名逐个迭代，对于扩展名种类较多的场景，每个扩展名需要一次完整的目录遍历

## 相关文件

- `tools/flags/CommonFlags.h` - CollectImages 函数声明
- `tools/flags/CommonFlagsConfig.cpp` - GPU 配置相关标志
- `src/core/SkOSFile.h` - 底层文件系统抽象
