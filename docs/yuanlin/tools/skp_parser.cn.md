# skp_parser - SKP 文件 JSON 解析器

> 源文件: `tools/skp_parser.cpp`

## 概述

`skp_parser` 将 SKP (Skia Picture) 文件解析为 JSON 格式输出。它使用 DebugCanvas 回放 SKP 中的绘图命令,然后将其序列化为人类可读的 JSON。还支持提取 SKP 中嵌入的二进制 blob(如图像)。

## 架构位置

属于 Skia 的调试和分析工具链。

## 公共 API 函数

- **`main(argc, argv)`**:
  - 单参数: 输出 SKP 的 JSON 表示
  - 双参数: 提取指定 data URL 的二进制数据

## 内部实现细节

- 使用 `DebugCanvas` 回放 SKP 记录的绘图命令
- 通过 `UrlDataManager` 管理二进制 blob(编号为 `data/0`, `data/1` 等)
- JSON 使用 `SkJSONWriter::Mode::kPretty` 美化输出
- Windows 平台支持二进制输出模式(`_O_BINARY`)

## 依赖关系

- `tools/debugger/DebugCanvas.h` - 调试画布
- `tools/UrlDataManager.h` - URL 数据管理
- `src/utils/SkJSONWriter.h` - JSON 序列化

## 设计模式与设计决策

- **两种模式**: JSON 导出和二进制提取共用同一入口
- **NullCanvas**: 使用空画布避免实际渲染开销

## 性能考量

JSON 序列化和 DebugCanvas 回放是主要开销。大型 SKP 可能产生大量 JSON 输出。

## 相关文件

- `tools/get_images_from_skps.cpp` - SKP 图像提取
- `tools/debugger/` - 调试器相关代码
