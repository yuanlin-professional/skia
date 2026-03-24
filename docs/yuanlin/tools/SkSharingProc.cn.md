# SkSharingProc - 图像序列化共享机制

> 源文件:
> - [tools/SkSharingProc.h](../../tools/SkSharingProc.h)
> - [tools/SkSharingProc.cpp](../../tools/SkSharingProc.cpp)

## 概述

SkSharingProc 提供了一种在多个子 SkPicture 之间共享图像的序列化/反序列化机制。它确保相同的图像（通过 `uniqueID` 识别）只被序列化一次，后续引用只存储文件内 ID。该组件主要设计用于 Android 平台上配合 MultiPictureDocument（MSKP 格式），解决多帧文档中图像重复序列化的问题。

## 架构位置

位于 `tools/` 目录下，属于工具层的序列化辅助组件。它通过 Skia 的 `SkSerialProcs` 回调机制集成到序列化/反序列化流程中，被 MSKPPlayer、调试器等工具使用。

## 主要类与结构体

### `SkSharingSerialContext`
序列化上下文，管理图像到文件内 ID 的映射关系。

- `fNonTexMap` - 从图像 uniqueID 到非纹理副本的映射（THashMap）
- `fDirectContext` - GPU 上下文指针，用于纹理图像的栅格化
- `fImageMap` - 从原始图像 uniqueID 到文件内 ID 的映射

### `SkSharingDeserialContext`
反序列化上下文，维护已反序列化图像的有序列表。

- `fImages` - 按遇到顺序存储的唯一图像列表

### `SkSharingContext` 命名空间
提供序列化和反序列化的核心函数。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `collectNonTextureImagesFromPicture()` | 收集 SkPicture 中引用的纹理图像的栅格化副本 |
| `setDirectContext()` | 设置 GPU 上下文 |
| `serializeImage()` | 序列化回调函数，首次编码为 PNG，后续仅写入文件内 ID |
| `deserializeImage()` | 反序列化回调函数，根据数据大小判断是 ID 引用还是内联图像 |

## 内部实现细节

- **序列化策略**：首次遇到图像时使用 `SkPngEncoder` 编码为 PNG，并分配递增的文件内 ID。后续遇到相同 uniqueID 的图像时，仅写入 4 字节的 ID。
- **纹理图像处理**：`collectNonTextureImagesFromPicture` 在每帧结束时遍历 SkPicture，将 GPU 纹理图像转换为栅格图像，避免序列化时纹理已释放。
- **编码失败容错**：如果 PNG 编码失败，创建一个 10x10 的洋红色占位图像。
- **反序列化识别**：通过数据大小判断——若为 4 字节（`sizeof(uint32_t)`）则为 ID 引用，否则为完整 PNG 数据。使用 `SkPngDecoder` 解码并延迟初始化。

## 依赖关系

- **Skia 核心**：SkImage、SkData、SkSerialProcs、SkPicture、SkCanvas、SkBitmap
- **编解码**：SkPngEncoder、SkPngDecoder、SkCodec
- **内部数据结构**：skia_private::THashMap
- **GPU**（可选）：GrDirectContext

## 设计模式与设计决策

- **上下文对象模式**：将状态封装在上下文结构体中，通过 `void*` 传递给序列化回调。
- **向后兼容**：反序列化支持内联图像模式，即使文件中所有图像都是完整编码也能正确处理。
- **二阶段处理**：可选的纹理收集阶段 + 必须的序列化阶段，适应 Android 端 GPU 纹理生命周期。

## 性能考量

- **去重优化**：通过 uniqueID 哈希映射避免重复编码大图像，显著减小 MSKP 文件大小。
- **PNG 编码开销**：每个唯一图像仅编码一次，后续为 O(1) 的 ID 查找。
- **栅格化副本**：`makeRasterImage` 可能有内存开销，但确保了序列化的正确性。

## 相关文件

- `tools/MSKPPlayer.h` / `.cpp` - 使用此模块进行 MSKP 反序列化
- `include/core/SkSerialProcs.h` - 序列化回调接口定义
- `include/docs/SkMultiPictureDocument.h` - MSKP 文档格式
- `include/encode/SkPngEncoder.h` - PNG 编码器
