# blob_cache_sim - 文本 Blob 缓存模拟器

> 源文件: `tools/blob_cache_sim.cpp`

## 概述

`blob_cache_sim` 是一个命令行工具,用于分析和模拟 Skia 远程字形缓存中的文本 Blob 缓存行为。它读取 SkTextBlobTrace 文件,计算基于 Blob ID、位置和颜色的缓存键,统计唯一键和总请求的比率,并将 trace 渲染为 PNG 图像进行可视化。

## 架构位置

属于 Skia 工具链中的分析调试工具,服务于文本渲染缓存优化。

## 主要类与结构体

无类定义。使用 `SkTextBlobTrace::Record` 记录结构。

## 公共 API 函数

- **`main()`**: 读取 trace 文件,计算缓存统计,渲染可视化 PNG

## 内部实现细节

- 缓存键(64位)由 blobID(高32位)+ 位置量化(6位)+ 颜色量化(9位)构成
- 位置量化: x/y 各取 SkFixed 的 3 位(13位右移)
- 颜色量化: RGB 各取高 3 位(5位右移)
- 仅对 fast bypass 路径的 blob 建立缓存(fill style, 无 path effect/mask filter)

## 依赖关系

- `include/private/chromium/SkChromeRemoteGlyphCache.h` - 远程字形缓存
- `tools/text/SkTextBlobTrace.h` - Blob trace 读取
- `include/encode/SkPngEncoder.h` - PNG 编码

## 设计模式与设计决策

- **量化缓存键**: 对位置和颜色进行量化以增加缓存命中率
- **可视化输出**: 自动渲染 PNG 辅助理解 trace 内容

## 性能考量

使用 unordered_map 存储缓存键,O(1) 查找。处理大型 trace 时内存使用与唯一键数量成正比。

## 相关文件

- `tools/text/SkTextBlobTrace.h` - Blob trace 格式
