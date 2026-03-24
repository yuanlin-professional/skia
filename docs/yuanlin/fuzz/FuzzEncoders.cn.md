# 图像编码器模糊测试

> 源文件: `fuzz/FuzzEncoders.cpp`

## 概述

此文件对 Skia 的图像编码器（PNG、JPEG、WebP）进行模糊测试。使用随机像素数据和编码参数创建位图，然后尝试编码，以发现编码器中的边界情况和潜在缺陷。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，覆盖 `include/encode/` 下的编码器。

## 公共 API 函数

- `DEF_FUZZ(PNGEncoder, fuzz)` - libpng PNG 编码器模糊测试
- `DEF_FUZZ(PNGRustEncoder, fuzz)` - Rust PNG 编码器模糊测试
- `DEF_FUZZ(JPEGEncoder, fuzz)` - JPEG 编码器模糊测试
- `DEF_FUZZ(WEBPEncoder, fuzz)` - WebP 编码器模糊测试
- `DEF_FUZZ(_MakeEncoderCorpus, fuzz)` - 语料库生成辅助工具

## 内部实现细节

- 位图最大 512x512 像素，使用 N32 预乘色彩格式
- PNG: 随机 zlib 压缩级别 (0-9)
- Rust PNG: 随机压缩级别（Low/Medium/High）
- JPEG: 随机质量 (0-100)
- WebP: 随机质量 (0-100) 和有损/无损模式
- `_MakeEncoderCorpus` 将真实图像转换为模糊测试语料库格式

## 依赖关系

- `include/encode/SkPngEncoder.h`, `SkJpegEncoder.h`, `SkWebpEncoder.h`
- `include/encode/SkPngRustEncoder.h` (条件编译)

## 设计模式与设计决策

**参数空间覆盖**：每种编码器的可调参数都被随机化，确保覆盖各种参数组合。

## 性能考量

位图大小限制为 512x512 以平衡覆盖和速度。

## 相关文件

- `include/encode/` - 编码器头文件
