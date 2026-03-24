# include/private - Skia 私有头文件

## 概述

`include/private` 目录包含 Skia 内部使用的私有头文件，这些头文件不属于 Skia 的公共 API，但对于 Skia 的内部实现以及少数特权嵌入者（如 Chromium 和 Android Framework）是必需的。这些头文件随时可能发生变化，外部开发者不应直接依赖它们。

该目录涵盖了多个功能领域：编码图像信息处理、路径引用管理、增益图（Gainmap）HDR 渲染支持、JPEG 元数据处理、XMP 元数据解析以及 SkSL 着色器语言的采样描述。这些组件为 Skia 的编解码器、路径系统、HDR 图像管线和 GPU 着色器编译器提供关键的基础设施支持。

本目录还包含三个重要子目录：`base`（底层基础设施）、`chromium`（Chromium 专用接口）和 `gpu`（GPU 后端私有类型），分别为不同的功能模块提供专门的私有头文件。

本目录中的代码涉及到 Skia 的核心内部架构，修改时需特别谨慎，因为它们被 Skia 的多个子系统广泛引用。

## 目录结构

```
include/private/
├── base/                        # 底层基础设施（内存、线程、容器等）
├── chromium/                    # Chromium 浏览器专用私有接口
├── gpu/                         # GPU 后端私有头文件
│   ├── ganesh/                  # Ganesh GPU 后端私有类型
│   └── vk/                      # Vulkan 私有头文件
├── SkEncodedInfo.h              # 编码图像的颜色和 Alpha 信息描述
├── SkExif.h                     # EXIF 元数据解析与写入
├── SkGainmapInfo.h              # 增益图（Gainmap）HDR 渲染参数
├── SkGainmapShader.h            # 增益图着色器，用于将增益图应用到基础图像
├── SkHdrMetadata.h              # HDR 元数据（内容光照级别、色度坐标等）
├── SkIDChangeListener.h         # ID 变更监听器，用于缓存失效通知
├── SkJpegGainmapEncoder.h       # JPEG 增益图（UltraHDR）编码器
├── SkJpegMetadataDecoder.h      # JPEG 元数据解码器（EXIF、ICC、增益图）
├── SkPathRef.h                  # 路径数据的内部引用计数存储
├── SkPixelStorage.h             # 像素存储的抽象基类
├── SkSLSampleUsage.h            # SkSL 片段处理器的采样方式描述
├── SkWeakRefCnt.h               # 弱引用计数基类
├── SkXmp.h                      # XMP 元数据解析接口
├── BUILD.bazel                  # Bazel 构建文件
└── OWNERS                       # 代码审查所有者
```

## 关键类与函数

### 编码与元数据
- **`SkEncodedInfo`**: 描述编码图像的颜色类型（如 `kGray_Color`、`kRGB_Color`、`kRGBA_Color`）和 Alpha 类型（如 `kOpaque_Alpha`、`kUnpremul_Alpha`），是编解码器内部使用的核心结构。
- **`SkExif::Metadata`**: 存储 EXIF 元数据，包括图像方向（`fOrigin`）、HDR 余量（`fHdrHeadroom`）、分辨率和像素尺寸。提供 `Parse()` 和 `WriteExif()` 函数。
- **`SkJpegMetadataDecoder`**: 从 JPEG 文件中提取 EXIF、ICC 配置文件和 ISO 21496-1 增益图元数据。
- **`SkXmp`**: XMP 元数据解析接口，支持 Adobe HDR 增益图和 Apple HDR 增益图参数提取。

### HDR 与增益图
- **`SkGainmapInfo`**: 增益图渲染参数结构体，定义了从 SDR 到 HDR 的映射参数，包括 `fGainmapRatioMin`、`fGainmapRatioMax`、`fGainmapGamma` 等。遵循 Adobe 增益图技术规范。
- **`SkGainmapShader`**: 创建将增益图应用到基础图像的着色器，根据显示器的 HDR/SDR 比率计算最终输出。
- **`skhdr::ContentLightLevelInformation`**: 内容光照级别元数据，包含最大内容光照级别（MaxCLL）和最大帧平均光照级别（MaxFALL）。
- **`SkJpegGainmapEncoder`**: 将基础图像和增益图编码为 UltraHDR JPEG 格式。

### 路径与内存管理
- **`SkPathRef`**: 路径的内部数据存储，管理路径的点、动词和圆锥体权重数组。支持路径类型识别（椭圆、圆角矩形、弧线等）。
- **`SkPixelStorage`**: 像素数据存储块的抽象基类，作为 SkImage 和 SkSurface 的像素内存来源，子类型包括 `kTextureProxy` 和 `kPixelRef`。
- **`SkWeakRefCnt`**: 扩展 `SkRefCnt` 的弱引用计数类，支持 `weak_ref()`、`weak_unref()` 和 `try_ref()` 操作。
- **`SkIDChangeListener`**: 当对象的生成 ID 失效时通知缓存系统，支持监听器的注册、注销和批量触发。

### 着色器语言
- **`SkSL::SampleUsage`**: 描述片段处理器被父级采样的方式，包括 `kPassThrough`（透传坐标）、`kUniformMatrix`（统一矩阵变换）、`kFragCoord`（片段坐标）和 `kExplicit`（显式坐标）。

### JPEG 编码与多图格式
- **`SkJpegGainmapEncoder::EncodeHDRGM()`**: 将基础图像和增益图编码为 UltraHDR 格式的 JPEG 文件。接受基础图像的 `SkPixmap`、增益图的 `SkPixmap` 以及 `SkGainmapInfo` 渲染参数。
- **`SkJpegGainmapEncoder::MakeMPF()`**: 生成多图格式（Multi Picture Format）的 JPEG 文件，可将多张图像打包到单个文件中。
- **`SkJpegMetadataDecoder::Segment`**: 表示 JPEG 文件中的一个段（segment），包含标记字节和参数数据。

### HDR 元数据详解
- **`skhdr::MasteringDisplayColorVolume`**: 母版显示色彩体积元数据，定义了内容创作时所用显示器的色域和亮度范围。
- **`skhdr::ContentLightLevelInformation::parse()`**: 从 AV1/H.265 二进制编码中解析内容光照级别信息。
- **`skhdr::ContentLightLevelInformation::serialize()`**: 将内容光照级别信息序列化为标准二进制格式。

### 路径类型识别
- **`SkPathIsAType`**: 路径形状标识枚举，包括 `kGeneral`（通用路径）、`kOval`（椭圆）、`kRRect`（圆角矩形）等。GPU 后端在检测到特定形状时可以采用更优化的渲染策略。
- **`SkPathRectInfo`/`SkPathOvalInfo`/`SkPathRRectInfo`**: 路径形状查询结果结构体，包含几何参数、方向和起始索引。

## 依赖关系

- **上游依赖**: `include/core/`（SkRefCnt、SkColorSpace、SkData、SkImageInfo 等）、`include/codec/`（SkEncodedOrigin）、`include/encode/`（SkJpegEncoder）、`modules/skcms/`（色彩管理）
- **下游消费者**: `src/codec/`（编解码器实现）、`src/core/`（核心路径和图像处理）、`src/gpu/`（GPU 后端）、`include/private/chromium/`（Chromium 集成）
- **子目录**: `base/`（底层工具库）、`chromium/`（Chromium 接口）、`gpu/`（GPU 私有类型）
- **HDR 管线**: `SkGainmapInfo` -> `SkGainmapShader` -> GPU 着色器渲染；`SkJpegMetadataDecoder` -> `SkXmp` -> `SkGainmapInfo`（元数据提取流程）
- **路径管线**: `SkPathRef` <- `SkIDChangeListener`（路径变更通知）-> 缓存系统

## 相关文档与参考

- [Skia 公共 API 文档](https://skia.org/docs/)
- [Adobe Gainmap 技术规范](https://helpx.adobe.com/camera-raw/using/gain-map.html) - 增益图渲染算法的详细说明
- [ISO 21496-1](https://www.iso.org/standard/81079.html) - 增益图元数据标准
- [Apple HDR Gainmap](https://developer.apple.com/documentation/appkit/images_and_pdf/applying_apple_hdr_effect_to_your_photos) - Apple HDR 效果规范
- [UltraHDR 格式](https://developer.android.com/media/platform/ultrahdr) - Android UltraHDR JPEG 规范
- `include/core/` - Skia 公共核心头文件
- `include/private/base/` - 底层基础设施文档
- `include/private/chromium/` - Chromium 专用接口文档
- `include/private/gpu/` - GPU 私有头文件文档

## 使用注意事项

本目录中的头文件被标记为"私有"，这意味着：

1. **API 稳定性不保证**: 这些头文件的接口可能在任何 Skia 版本更新中发生不兼容的变化，包括类重命名、函数签名变更和整个头文件的删除。
2. **仅限内部使用**: 仅供 Skia 内部代码、Chromium 浏览器和 Android Framework 使用。第三方应用不应依赖这些接口。
3. **包含路径约定**: 引用这些头文件时使用完整路径，如 `#include "include/private/SkPathRef.h"`，以区别于公共 API 头文件。
