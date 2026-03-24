# get_images_from_skps - SKP 图像提取工具

> 源文件: `tools/get_images_from_skps.cpp`

## 概述

`get_images_from_skps` 从 SKP (Skia Picture) 文件中提取所有嵌入的图像,可选地测试解码和写入磁盘。支持处理单个 SKP 文件或整个目录,使用 MD5 去重避免重复提取相同图像。最终输出统计 JSON(失败数、不支持数、成功数)。

## 架构位置

属于 Skia 工具链中的 SKP 分析和图像提取工具。

## 主要类与结构体

- **`Sniffer`**: 图像嗅探器,通过 SkPicture 的反序列化回调接收图像数据

## 公共 API 函数

- **`main()`**: 解析命令行参数,处理 SKP 文件/目录
- **`get_images_from_file()`**: 从单个 SKP 文件提取图像

## 内部实现细节

- 使用 `SkDeserialProcs::fImageProc` 回调在反序列化时拦截图像数据
- MD5 去重: 通过 `THashSet<SkMD5::Digest>` 跟踪已处理的图像
- 支持多种编码格式检测(BMP/GIF/ICO/JPEG/PNG/DNG/WBMP/WEBP)
- 命令行标志: `--testDecode`, `--writeImages`, `--writeFailedImages`, `--failuresJsonPath`

## 依赖关系

- `include/codec/SkCodec.h` - 图像解码
- `include/core/SkPicture.h` - SKP 反序列化
- `src/core/SkMD5.h` - 哈希去重
- `src/utils/SkJSONWriter.h` - JSON 输出

## 设计模式与设计决策

- **回调拦截**: 利用 SkPicture 的反序列化回调优雅地提取嵌入图像
- **MD5 去重**: 避免同一图像在多个 SKP 中重复提取

## 性能考量

MD5 计算和可选的解码测试是主要开销。THashSet 提供 O(1) 去重查找。

## 相关文件

- `tools/skp_parser.cpp` - SKP 解析和 JSON 导出
