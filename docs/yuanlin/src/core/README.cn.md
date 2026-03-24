# src/core - Skia 核心渲染引擎

## 概述

`src/core` 是 Skia 图形库的核心目录，包含了整个 2D 渲染引擎的基础实现。该目录拥有约 379 个源文件（`.cpp`、`.h`），构成了 Skia 最基本、最关键的绘图功能。从画布（Canvas）管理、路径（Path）计算、光栅化扫描（Scan）、像素混合（Blitter）到颜色空间转换、字体排版等，几乎所有软件渲染的核心逻辑都集中在此目录中。

Skia 最初由 Skia Inc. 开发，后于 2005 年被 Google 收购，成为 Android、Chrome、Flutter 等项目的底层图形引擎。`src/core` 中的代码可追溯至 2006 年 Android Open Source Project 的初始版本，经过近二十年的迭代优化，已经发展成为一个高度模块化、支持多后端（CPU、GPU Ganesh、GPU Graphite）的渲染核心。

`src/core` 作为 Skia 的"心脏"，提供了平台无关的渲染抽象层。上层 API（如 `SkCanvas`）通过 `SkDevice` 接口与不同的后端通信，而本目录主要实现了 CPU 软件渲染后端（`SkBitmapDevice`）。GPU 后端（如 Ganesh 和 Graphite）虽然有各自的 Device 实现，但它们仍然大量依赖 `src/core` 中定义的基础类型、路径处理、颜色空间管理和序列化基础设施。

本目录还包含了 Skia 的"录制-回放"（Record-Playback）机制，即 `SkPicture` 系统。该系统允许将绘图命令序列化为紧凑的二进制格式，可用于跨进程传递、延迟渲染或调试分析。此外，`SkRasterPipeline` 提供了一种高效的像素处理管线，通过运行时组合不同的处理阶段来避免组合爆炸问题。

## 架构图

```
                          +-------------------+
                          |    SkCanvas       |
                          | (绘图 API 入口)    |
                          +---------+---------+
                                    |
                      +-------------+-------------+
                      |                           |
               +------+------+           +--------+--------+
               | SkDevice    |           | SkPictureRecord |
               | (设备抽象)   |           | (命令录制)       |
               +------+------+           +--------+--------+
                      |                           |
          +-----------+-----------+       +-------+-------+
          |                       |       | SkPicture     |
   +------+------+       +-------+----+  | SkPictureData |
   |SkBitmapDevice|       | GPU Device |  | (序列化存储)   |
   |(CPU软件渲染) |       | (Ganesh/   |  +---------------+
   +------+------+       | Graphite)  |
          |              +------------+
   +------+------+
   | skcpu::Draw |
   | (绘图调度器) |
   +------+------+
          |
    +-----+-----+--------------------+
    |           |                    |
+---+---+ +----+----+        +------+------+
|SkScan | |SkBlitter|        |  SkStroke   |
|(扫描线 | |(像素写入)|        | (描边转换)   |
| 转换)  | +----+----+        +-------------+
+---+---+      |
    |     +----+----+----+
    |     |    |         |
    |  +--+--+ +--+--+ +-+------------+
    |  |A8   | |ARGB | |SkRasterPipeline|
    |  |Blit | |Blit | |Blitter        |
    |  +-----+ +-----+ |(通用管线混合)   |
    |                   +---------------+
    |
+---+-------------+
|  SkEdge         |
|  SkAnalyticEdge |
|  (边缘计算)      |
+---+-------------+
    |
+---+---+
|SkPath |-------> SkGeometry (贝塞尔曲线数学)
|SkPathData|
+(路径数据)+
```

## 目录结构

### 核心绘图系统（Canvas / Device / Draw）

| 文件 | 说明 |
|------|------|
| `SkCanvas.cpp` / `SkCanvasPriv.h` | 核心画布实现，管理绘图状态栈（save/restore）、变换矩阵、裁剪和图层 |
| `SkDevice.h` / `SkDevice.cpp` | 设备抽象基类，定义了所有后端必须实现的绘图接口 |
| `SkBitmapDevice.h` / `SkBitmapDevice.cpp` | CPU 软件渲染设备的具体实现 |
| `SkDraw.h` / `SkDraw.cpp` | 软件渲染的核心调度器，协调 Blitter、Scan、Clip 完成实际像素绘制 |
| `SkCanvas_Raster.cpp` | 创建基于光栅化的 Canvas 的辅助实现 |
| `SkOverdrawCanvas.cpp` | 过度绘制分析画布，用于性能调试 |

### 路径与几何（Path / Geometry）

| 文件 | 说明 |
|------|------|
| `SkPath.cpp` / `SkPathPriv.h` | 路径核心实现，包含移动、直线、二次/三次贝塞尔曲线操作 |
| `SkPathBuilder.cpp` | 路径构建器，提供流式 API 构造路径 |
| `SkPathData.h` / `SkPathData.cpp` | 路径底层数据存储（控制点和动词数组） |
| `SkPathEffect.cpp` / `SkPathEffectBase.h` | 路径效果基类（虚线、角效果等） |
| `SkPathMeasure.cpp` | 沿路径测量长度和位置 |
| `SkPathRaw.h` / `SkPathRawShapes.h` | 原始路径数据表示及形状分析 |
| `SkGeometry.h` / `SkGeometry.cpp` | 贝塞尔曲线数学工具（求根、切割、旋转角计算） |
| `SkCubicClipper.h` / `SkCubicClipper.cpp` | 三次曲线裁剪 |
| `SkLineClipper.h` / `SkLineClipper.cpp` | 线段裁剪 |
| `SkEdgeClipper.h` / `SkEdgeClipper.cpp` | 通用边缘裁剪器 |
| `SkStroke.h` / `SkStroke.cpp` | 路径描边转换（将描边转为填充路径） |
| `SkStrokeRec.cpp` | 描边参数记录 |
| `SkContourMeasure.cpp` | 轮廓测量 |

### 光栅化与扫描（Scan / Edge / Blitter）

| 文件 | 说明 |
|------|------|
| `SkScan.h` / `SkScan.cpp` | 扫描线转换的主入口，提供填充和描边的光栅化 |
| `SkScan_Path.cpp` | 路径填充的扫描线转换 |
| `SkScan_AAAPath.cpp` | 超采样抗锯齿（Analytic AA）路径扫描 |
| `SkScan_AntiPath.cpp` | 传统抗锯齿路径扫描 |
| `SkScan_Antihair.cpp` | 细线（发丝线）抗锯齿扫描 |
| `SkScan_Hairline.cpp` | 细线（1像素宽）扫描 |
| `SkEdge.h` / `SkEdge.cpp` | 边缘数据结构，将曲线近似为扫描线友好的线段 |
| `SkAnalyticEdge.h` / `SkAnalyticEdge.cpp` | 解析式抗锯齿边缘 |
| `SkEdgeBuilder.h` / `SkEdgeBuilder.cpp` | 从路径构建边缘列表 |
| `SkBlitter.h` / `SkBlitter.cpp` | Blitter 基类，负责将像素实际写入内存 |
| `SkBlitter_A8.cpp` / `SkBlitter_A8.h` | Alpha8 格式 Blitter |
| `SkBlitter_ARGB32.cpp` | ARGB32 格式 Blitter |
| `SkBlitter_Sprite.cpp` | 精灵（无变换位图）Blitter |
| `SkCoreBlitters.h` | 核心 Blitter 类型声明 |
| `SkRasterPipelineBlitter.cpp` | 基于 SkRasterPipeline 的通用 Blitter |
| `SkBlitRow_D32.cpp` | 32 位目标的行级像素操作 |
| `SkBlitMask.h` / `SkBlitMask_opts.cpp` | 遮罩混合操作 |

### 像素处理管线（Raster Pipeline）

| 文件 | 说明 |
|------|------|
| `SkRasterPipeline.h` / `SkRasterPipeline.cpp` | 核心管线框架，支持运行时动态组合像素处理阶段 |
| `SkRasterPipelineOpList.h` | 所有管线操作的枚举定义 |
| `SkRasterPipelineOpContexts.h` | 管线操作的上下文数据结构 |
| `SkRasterPipelineBlitter.cpp` | 将管线接入 Blitter 系统 |
| `SkRasterPipelineContextUtils.h` | 管线上下文工具函数 |

### 裁剪系统（Clip）

| 文件 | 说明 |
|------|------|
| `SkRasterClip.h` / `SkRasterClip.cpp` | 光栅裁剪，封装 BW（SkRegion）和 AA（SkAAClip）两种模式 |
| `SkRasterClipStack.h` | 光栅裁剪栈 |
| `SkAAClip.h` / `SkAAClip.cpp` | 抗锯齿裁剪区域 |
| `SkClipStack.h` / `SkClipStack.cpp` | 裁剪栈，管理 save/restore 语义下的裁剪状态 |
| `SkClipStackDevice.h` / `SkClipStackDevice.cpp` | 基于裁剪栈的设备抽象 |
| `SkRegion.cpp` / `SkRegion_path.cpp` | 整数像素精度的区域操作（并集、交集、差集） |

### 画笔与效果（Paint / Effect）

| 文件 | 说明 |
|------|------|
| `SkPaint.cpp` / `SkPaintPriv.h` | 画笔实现，封装颜色、描边、着色器、滤镜等绘图属性 |
| `SkBlendMode.cpp` / `SkBlendModePriv.h` | 混合模式实现 |
| `SkBlendModeBlender.h` / `SkBlendModeBlender.cpp` | 混合模式封装为 SkBlender 对象 |
| `SkBlenderBase.h` | Blender 基类 |
| `SkColorFilter.cpp` / `SkColorFilterPriv.h` | 颜色滤镜基础 |
| `SkMaskFilter.cpp` / `SkMaskFilterBase.h` | 遮罩滤镜基类（模糊等） |
| `SkBlurMaskFilterImpl.h` / `SkBlurMaskFilterImpl.cpp` | 高斯模糊遮罩滤镜实现 |
| `SkBlurMask.h` / `SkBlurMask.cpp` | 模糊遮罩计算 |
| `SkBlurEngine.h` / `SkBlurEngine.cpp` | 模糊引擎抽象 |
| `SkGaussFilter.h` / `SkGaussFilter.cpp` | 高斯滤波器核计算 |
| `SkImageFilter.cpp` / `SkImageFilter_Base.h` | 图像滤镜基类 |
| `SkImageFilterTypes.h` / `SkImageFilterTypes.cpp` | 图像滤镜坐标空间和类型系统 |
| `SkRuntimeEffect.cpp` / `SkRuntimeEffectPriv.h` | SkSL 运行时效果（自定义着色器/颜色滤镜/混合器） |
| `SkRuntimeBlender.h` / `SkRuntimeBlender.cpp` | 运行时自定义混合器 |

### 颜色与颜色空间（Color / ColorSpace）

| 文件 | 说明 |
|------|------|
| `SkColor.cpp` / `SkColorData.h` | 颜色表示和颜色数据工具 |
| `SkColorSpace.cpp` / `SkColorSpacePriv.h` | 颜色空间管理 |
| `SkColorSpaceXformSteps.h` / `SkColorSpaceXformSteps.cpp` | 颜色空间转换步骤（解预乘、线性化、色域矩阵、编码） |
| `SkColorTable.cpp` | 颜色查找表 |
| `SkConvertPixels.h` / `SkConvertPixels.cpp` | 像素格式转换 |

### 图像与位图（Image / Bitmap / Pixmap）

| 文件 | 说明 |
|------|------|
| `SkBitmap.cpp` | 位图实现，封装像素数据和元信息 |
| `SkBitmapCache.h` / `SkBitmapCache.cpp` | 位图缩放缓存 |
| `SkPixelRef.cpp` / `SkPixelRefPriv.h` | 像素引用，管理像素数据的生命周期 |
| `SkPixelStorage.cpp` | 像素存储基类（SkPixelRef 和 TextureProxy 的公共父类） |
| `SkPixmap.cpp` / `SkPixmapDraw.cpp` | 像素图的读写操作 |
| `SkMipmap.h` / `SkMipmap.cpp` | Mipmap 层级生成与管理 |
| `SkMipmapAccessor.h` / `SkMipmapAccessor.cpp` | Mipmap 级别访问器 |
| `SkMipmapBuilder.h` / `SkMipmapBuilder.cpp` | Mipmap 构建器 |
| `SkImageInfo.cpp` / `SkImageInfoPriv.h` | 图像元信息（宽、高、颜色类型、Alpha 类型） |
| `SkSpecialImage.h` / `SkSpecialImage.cpp` | 内部使用的特殊图像，用于图像滤镜处理 |

### 录制与回放（Record / Picture）

| 文件 | 说明 |
|------|------|
| `SkPicture.cpp` / `SkPicturePriv.h` | Picture 核心实现与序列化/反序列化 |
| `SkBigPicture.h` / `SkBigPicture.cpp` | 完整 Picture 实现（包含命令、位图、图片引用） |
| `SkPictureRecord.h` / `SkPictureRecord.cpp` | 将 Canvas 绘图命令录制为 Picture |
| `SkPictureRecorder.cpp` | Picture 录制器的公开 API |
| `SkPictureData.h` / `SkPictureData.cpp` | Picture 的内部数据存储 |
| `SkPicturePlayback.h` / `SkPicturePlayback.cpp` | Picture 回放（将录制的命令重新绘制到 Canvas） |
| `SkPictureFlat.h` / `SkPictureFlat.cpp` | Picture 对象扁平化 |
| `SkRecord.h` / `SkRecord.cpp` | 底层命令记录存储 |
| `SkRecordCanvas.h` / `SkRecordCanvas.cpp` | 将 Canvas 操作录制到 SkRecord |
| `SkRecordDraw.h` / `SkRecordDraw.cpp` | 将 SkRecord 中的命令绘制到 Canvas |
| `SkRecordOpts.h` / `SkRecordOpts.cpp` | 录制命令的优化遍历 |
| `SkRecords.h` / `SkRecords.cpp` | 所有录制命令类型的定义 |

### 字体与文本（Font / Glyph / Strike）

| 文件 | 说明 |
|------|------|
| `SkFont.cpp` / `SkFontPriv.h` | 字体配置（大小、缩放、倾斜等） |
| `SkFontMgr.cpp` | 字体管理器 |
| `SkFontDescriptor.h` / `SkFontDescriptor.cpp` | 字体描述符，用于序列化字体标识 |
| `SkScalerContext.h` / `SkScalerContext.cpp` | 字形缩放上下文，驱动平台字体引擎生成字形 |
| `SkGlyph.h` / `SkGlyph.cpp` | 字形数据（度量、图像、路径） |
| `SkGlyphRunPainter.h` / `SkGlyphRunPainter.cpp` | 字形运行绘制器 |
| `SkStrike.h` / `SkStrike.cpp` | 字形缓存（Strike），存储 SkScalerContext 的输出 |
| `SkStrikeCache.h` / `SkStrikeCache.cpp` | 全局字形缓存管理 |
| `SkStrikeSpec.h` / `SkStrikeSpec.cpp` | Strike 规格，描述字形缓存的查找键 |
| `SkTypeface.cpp` / `SkTypefaceCache.h` | 字体类型面和类型面缓存 |
| `SkMaskGamma.h` / `SkMaskGamma.cpp` | 文本遮罩 Gamma 校正 |

### 序列化与缓存（Serialization / Cache）

| 文件 | 说明 |
|------|------|
| `SkReadBuffer.h` / `SkReadBuffer.cpp` | 二进制反序列化读缓冲 |
| `SkWriteBuffer.h` / `SkWriteBuffer.cpp` | 二进制序列化写缓冲 |
| `SkWriter32.h` / `SkWriter32.cpp` | 32 位对齐的内存写入器 |
| `SkFlattenable.cpp` | 可序列化对象基础设施 |
| `SkResourceCache.h` / `SkResourceCache.cpp` | 全局资源缓存（位图、Mipmap 等） |
| `SkCachedData.h` / `SkCachedData.cpp` | 可缓存数据基类 |
| `SkStream.cpp` | 流式 I/O |
| `SkData.cpp` | 不可变数据块 |

### CPU 优化（SIMD / Opts）

| 文件 | 说明 |
|------|------|
| `SkOpts.h` / `SkOpts.cpp` | CPU 特性检测与函数指针替换框架 |
| `SkCpu.h` / `SkCpu.cpp` | CPU 特性检测 |
| `SkBitmapProcState.h` / `SkBitmapProcState.cpp` | 位图采样处理状态 |
| `SkBitmapProcState_opts.cpp` / `_opts_ssse3.cpp` / `_opts_lasx.cpp` | 位图处理 SIMD 优化变体 |
| `SkBlitRow_opts.cpp` / `_opts_hsw.cpp` / `_opts_lasx.cpp` | 行像素混合 SIMD 优化变体 |
| `SkMemset.h` / `SkMemset_opts_avx.cpp` / `_opts_erms.cpp` | 内存填充 SIMD 优化 |
| `SkSwizzler_opts.cpp` / `_opts_hsw.cpp` / `_opts_ssse3.cpp` | 像素通道重排 SIMD 优化 |
| `Sk4px.h` | 4 像素 SIMD 操作封装 |

### 数学与工具（Math / Utility）

| 文件 | 说明 |
|------|------|
| `SkMatrix.cpp` / `SkMatrixPriv.h` | 3x3 变换矩阵 |
| `SkMatrixInvert.h` / `SkMatrixInvert.cpp` | 矩阵求逆 |
| `SkM44.cpp` | 4x4 变换矩阵（支持 3D 变换） |
| `SkRect.cpp` / `SkRectPriv.h` | 矩形基础操作 |
| `SkRRect.cpp` / `SkRRectPriv.h` | 圆角矩形 |
| `SkPoint.cpp` / `SkPointPriv.h` | 点和向量 |
| `SkChecksum.h` / `SkChecksum.cpp` | 校验和/哈希计算 |
| `SkTHash.h` | 高性能开放寻址哈希表 |
| `SkLRUCache.h` | LRU 缓存模板 |
| `SkRTree.h` / `SkRTree.cpp` | R-Tree 空间索引，用于 Picture 加速 |

## 关键类与函数

### SkCanvas
- **文件**: `SkCanvas.cpp`，公开头文件位于 `include/core/SkCanvas.h`
- **职责**: 作为 Skia 的主要绘图 API 入口，管理绘图状态栈（矩阵变换、裁剪区域、图层），并将绘图命令分派到底层 SkDevice。
- **关键方法**:
  - `drawRect()` / `drawPath()` / `drawOval()` / `drawRRect()` -- 基础几何形状绘制
  - `drawImage()` / `drawPicture()` -- 图像和录制内容绘制
  - `save()` / `restore()` / `saveLayer()` -- 状态栈管理和图层创建
  - `translate()` / `scale()` / `rotate()` / `concat()` -- 变换矩阵操作
  - `clipRect()` / `clipPath()` / `clipRRect()` -- 裁剪区域设置
  - `internalSaveLayer()` -- 内部图层创建，处理 SkImageFilter
  - `internalDrawDeviceWithFilter()` -- 内部带滤镜的设备绘制

### SkDevice
- **文件**: `SkDevice.h` / `SkDevice.cpp`
- **职责**: 所有渲染后端的抽象基类。SkCanvas 中的每个图层对应一个 SkDevice 实例。它定义了绘图操作的虚函数接口，并管理设备坐标变换。
- **关键方法**:
  - `drawPaint()` / `drawRect()` / `drawPath()` -- 虚拟绘图接口
  - `localToDevice()` / `deviceToGlobal()` -- 坐标变换查询
  - `writePixels()` / `readPixels()` -- 像素直接访问
  - `accessPixels()` / `peekPixels()` -- 像素数据访问
  - `onCreateDevice()` -- 为 saveLayer 创建子设备
  - `imageInfo()` / `surfaceProps()` -- 设备元信息

### SkBitmapDevice
- **文件**: `SkBitmapDevice.h` / `SkBitmapDevice.cpp`
- **职责**: SkDevice 的 CPU 软件渲染实现。持有一个 SkBitmap 作为像素后端，通过 `skcpu::Draw` 完成实际光栅化。
- **关键方法**:
  - `drawPaint()` / `drawRect()` / `drawPath()` / `drawPoints()` -- 对应 SkDevice 虚函数
  - `Create()` -- 静态工厂方法

### skcpu::Draw
- **文件**: `SkDraw.h` / `SkDraw.cpp`
- **职责**: 软件渲染的核心调度器。它是一个轻量级上下文对象，配置了目标像素图、变换矩阵和裁剪区域。其主要工作是分析绘图原语和 SkPaint，选择并配置最高效的 SkBlitter。
- **关键方法**:
  - `drawPaint()` / `drawRect()` / `drawOval()` / `drawRRect()` / `drawPath()` -- 各种基元绘制
  - `drawPathCoverage()` -- 绘制路径覆盖（遮罩）
  - `ComputeRectType()` -- 根据画笔和矩阵判断矩形的最优绘制方式
  - `paintMasks()` / `drawBitmap()` -- `BitmapDevicePainter` 接口实现

### SkBlitter
- **文件**: `SkBlitter.h` / `SkBlitter.cpp`
- **职责**: 像素写入的抽象基类。负责将像素实际写入目标内存，处理裁剪和抗锯齿。
- **关键方法**:
  - `blitH()` -- 水平行像素写入（纯虚函数）
  - `blitAntiH()` -- 水平行抗锯齿像素写入（纯虚函数）
  - `blitV()` -- 垂直列像素写入
  - `blitRect()` -- 矩形区域填充
  - `blitAntiRect()` -- 带左右边缘 Alpha 混合的矩形写入
  - `blitMask()` -- 遮罩混合（主要用于文本渲染）
  - `Choose()` -- 静态工厂，根据目标格式和画笔属性选择最优 Blitter

### SkRasterPipeline
- **文件**: `SkRasterPipeline.h` / `SkRasterPipeline.cpp`
- **职责**: 提供廉价的运行时像素处理管线组合。通过将不同处理阶段链接在一起，避免了 {N 目标格式} x {M 源格式} x {K 混合模式} 的组合爆炸。
- **关键方法**:
  - `append()` -- 添加处理阶段
  - `extend()` -- 追加另一管线的所有阶段
  - `run()` -- 在 2D 范围内运行管线
  - `compile()` -- 编译管线为可调用的 thunk，摊销设置开销

### SkScan
- **文件**: `SkScan.h` / `SkScan.cpp` / `SkScan_Path.cpp` / `SkScan_AAAPath.cpp`
- **职责**: 扫描线转换。将几何形状（路径、矩形、线段）转化为像素级的扫描线调用，传递给 SkBlitter。
- **关键方法**:
  - `FillPath()` / `AntiFillPath()` -- 路径填充（BW / AA）
  - `FillRect()` / `AntiFillRect()` -- 矩形填充
  - `HairLine()` / `AntiHairLine()` -- 细线绘制
  - `HairPath()` / `AntiHairPath()` -- 细线路径绘制
  - `PathRequiresTiling()` -- 判断路径是否需要分块处理

### SkPath
- **文件**: `SkPath.cpp`，公开头文件 `include/core/SkPath.h`
- **职责**: 2D 矢量路径，由线段和贝塞尔曲线组成。支持填充规则（Winding/EvenOdd）、边界计算、序列化。
- **关键构造**: 内部通过 `sk_sp<SkPathData>` 实现写时复制（Copy-on-Write）语义。

### SkPaint
- **文件**: `SkPaint.cpp`，公开头文件 `include/core/SkPaint.h`
- **职责**: 描述"如何绘制"的属性集合，包括颜色、描边宽度、线帽/线连接样式、着色器、颜色滤镜、遮罩滤镜、混合模式等。

### SkColorSpaceXformSteps
- **文件**: `SkColorSpaceXformSteps.h` / `SkColorSpaceXformSteps.cpp`
- **职责**: 描述从源颜色空间到目标颜色空间的转换管线。按需组合以下步骤：解预乘 -> 线性化 -> 源 OOTF -> 色域矩阵变换 -> 目标 OOTF -> 编码 -> 预乘。
- **关键方法**:
  - `apply(float[4])` -- 对单个颜色值执行转换
  - `apply(SkRasterPipeline*)` -- 将转换步骤追加到光栅管线

### SkStrike / SkStrikeCache
- **文件**: `SkStrike.h` / `SkStrikeCache.h`
- **职责**: 字形缓存系统。SkStrike 缓存特定字体/大小/变换下的字形度量、位图和路径。SkStrikeCache 管理全局 Strike 缓存池。
- **关键方法**:
  - `SkStrike::digestFor()` -- 查找或创建字形摘要
  - `SkStrike::prepareForImage()` / `prepareForPath()` -- 准备字形的图像或路径数据
  - `SkStrikeCache::findOrCreateStrike()` -- 查找或创建匹配的 Strike

## 依赖关系

### 上游依赖（本模块依赖的模块）

- **`include/core/`**: 公开 API 头文件（SkCanvas.h、SkPaint.h、SkPath.h、SkBitmap.h、SkImage.h 等），定义了面向用户的类型接口
- **`include/private/base/`**: 内部基础工具（SkAssert、SkTemplates、SkMutex、SkTArray 等）
- **`src/base/`**: 底层工具库（SkArenaAlloc 内存分配器、SkVx SIMD 向量封装、SkAutoMalloc 自动内存管理、SkMathPriv 数学工具）
- **`modules/skcms/`**: 颜色管理系统，提供 ICC 配置文件解析和颜色空间转换函数
- **`src/sksl/`**: SkSL 着色器语言编译器，被 `SkRuntimeEffect` 使用
- **`src/shaders/`**: 着色器实现（如 `SkImageShader`、`SkLocalMatrixShader`、`SkRuntimeShader`）
- **`src/effects/`**: 效果实现（如 `SkColorFilterBase`、`SkRuntimeColorFilter`）

### 下游被依赖（依赖本模块的模块）

- **`src/gpu/ganesh/`**: Ganesh (OpenGL/Vulkan) GPU 后端，依赖 core 的路径、画笔、颜色空间等基础类型
- **`src/gpu/graphite/`**: Graphite（新一代 GPU 后端），同样依赖 core 基础设施
- **`src/image/`**: 图像子系统（SkSurface_Base、SkImage 实现）
- **`src/text/`**: 文本排版子系统（GlyphRun、StrikeForGPU）
- **`src/pdf/`** / **`src/svg/`**: PDF 和 SVG 后端
- **`src/utils/`**: 实用工具（SkPatchUtils 等）
- **`src/ports/`**: 平台特定实现（字体引擎封装等）
- **`include/core/`**: 公开 API 的内联实现依赖 core 的私有头文件

### 外部依赖（第三方库）

- **skcms**: Skia 自带的颜色管理库，用于颜色空间转换和 ICC 配置文件处理
- **标准 C++ 库**: `<cmath>`、`<algorithm>`、`<memory>`、`<functional>`、`<atomic>` 等

## 设计模式分析

### 工厂模式（Factory Pattern）

`SkBlitter::Choose()` 是典型的工厂方法。它根据目标像素格式（A8、ARGB32 等）、画笔属性（是否有着色器、颜色滤镜、混合模式）和裁剪状态，动态选择最高效的 Blitter 子类实例。`SkBitmapDevice::Create()` 同样是工厂方法，根据 SkImageInfo 创建设备。

### 策略模式（Strategy Pattern）

`SkRasterPipeline` 是策略模式的出色体现。每个管线阶段（stage）是一个独立的策略，可以在运行时自由组合。例如，源颜色加载、颜色空间转换、混合模式应用、目标存储等都是独立的策略，通过 `append()` 组合成完整的像素处理流程。

`SkOpts` 模块同样体现了策略模式：通过函数指针数组，在运行时根据 CPU 特性替换默认实现为 SIMD 优化版本（SSE2 -> SSSE3 -> HSW/AVX2 -> LoongArch LASX 等）。

### 模板方法模式（Template Method Pattern）

`SkDevice` 定义了一系列虚函数（`drawRect()`、`drawPath()` 等），子类（`SkBitmapDevice`、`ganesh::Device`、`graphite::Device`）提供具体实现。`SkCanvas` 调用 SkDevice 的这些方法，形成了经典的模板方法结构。

`SkImageFilter_Base` 中的 `filterImage()` 方法也是类似模式，子类实现 `onFilterImage()` 提供具体的滤镜逻辑。

### 组合模式（Composite Pattern）

`SkClipStack` 使用组合模式管理裁剪元素。裁剪操作可以是矩形、圆角矩形、路径或着色器，它们通过集合运算（交集、差集）组合在一起，形成最终的裁剪区域。

`SkPicture` 中的绘图命令（`SkRecords` 定义的各类命令）也构成了一种组合：一个 Picture 可以包含子 Picture 和子 Drawable，形成树状结构。

### 观察者模式（Observer Pattern）

`SkIDChangeListener` 实现了一种轻量级的观察者模式，当对象（如 SkPixelRef）的内容发生变化时，通过 changeListeners 通知依赖方（如缓存）进行失效处理。

`SkMessageBus` 是一个进程内的消息总线，用于广播资源变更通知（例如当 SkPixelRef 发生变化时通知 SkResourceCache 清除相关缓存条目）。

### 写时复制（Copy-on-Write）

`SkPath` 使用 `sk_sp<SkPathData>` 实现写时复制。路径对象的复制仅增加引用计数，只有在实际修改时才会创建独立的数据副本。这使得路径在大量传递时保持高效。

### 享元模式（Flyweight Pattern）

`SkStrike`（字形缓存）和 `SkResourceCache` 实现了享元模式。相同的字形数据在不同的文本绘制调用之间共享，通过 `SkStrikeSpec`（描述字体、大小、矩阵等）作为查找键。

## 数据流

### 基本绘制流程（以 drawRect 为例）

```
用户调用 SkCanvas::drawRect(rect, paint)
    |
    v
SkCanvas 检查裁剪、应用快速拒绝测试
    |
    v
SkCanvas 将调用分派到当前 SkDevice::drawRect()
    |
    v
SkBitmapDevice::drawRect() 创建 skcpu::Draw 上下文
    |
    v
skcpu::Draw::drawRect() 分析 paint 和矩阵
    |-- 如果是简单填充，使用快速路径
    |-- 如果需要描边，通过 SkStroke 转为填充路径
    v
skcpu::Draw 调用 SkBlitter::Choose() 选择 Blitter
    |
    v
SkScan::FillRect() 或 SkScan::AntiFillRect()
将矩形转为扫描线，逐行调用 Blitter::blitH()
    |
    v
SkBlitter 子类将像素写入目标 SkPixmap
```

### 路径绘制的数据流

```
SkPath -> SkEdgeBuilder（构建边缘列表）
    |
    v
SkEdge / SkAnalyticEdge（将曲线近似为线段）
    |
    v
SkScan::FillPath()（按扫描线排序边缘）
    |
    v
对每条扫描线：计算边缘交点，确定填充范围
    |
    v
调用 SkBlitter::blitH() 或 blitAntiH()
    |
    v
SkRasterPipelineBlitter 组合管线：
  着色器(shader) -> 颜色空间转换 -> 颜色滤镜 -> 混合模式 -> 写入目标
```

### Picture 录制与回放

```
录制阶段：
SkPictureRecorder::beginRecording()
    -> 创建 SkRecordCanvas（或 SkPictureRecord）
    -> 用户在此 Canvas 上绘图
    -> 每个操作被记录为 SkRecords 中的命令对象
    -> finishRecordingAsPicture() 构建 SkBigPicture

回放阶段：
SkCanvas::drawPicture(picture)
    -> SkPicturePlayback::draw()
    -> SkRecordDraw() 遍历 SkRecord，对每个命令调用 SkCanvas 对应方法
    -> 可选：利用 SkBBoxHierarchy（R-Tree）跳过不在裁剪范围内的命令
```

### 颜色空间转换数据流

```
源像素 (sRGB, premul)
    |
    v
解预乘 (unpremul)  -- 如果源是预乘的
    |
    v
线性化 (linearize) -- 应用源传输函数（如 sRGB gamma）的逆
    |
    v
源 OOTF           -- 如果源有光电/电光转换（如 PQ/HLG HDR）
    |
    v
色域矩阵变换      -- 3x3 列主矩阵，源色域 -> 目标色域
    |
    v
目标 OOTF         -- 如果目标有光电/电光转换
    |
    v
编码 (encode)     -- 应用目标传输函数（如 sRGB gamma）
    |
    v
预乘 (premul)     -- 如果目标需要预乘格式
    |
    v
目标像素 (Display-P3, premul)
```

## 平台特定说明

### CPU 架构优化

`src/core` 包含大量 CPU 架构特定的优化文件，通过 `SkOpts` 框架在运行时选择最佳实现：

- **x86/x86-64**: 支持 SSE2（基线）、SSSE3、HSW（Haswell/AVX2）优化
  - `SkBitmapProcState_opts_ssse3.cpp` / `SkBlitRow_opts_hsw.cpp` / `SkSwizzler_opts_hsw.cpp`
  - `SkMemset_opts_avx.cpp` / `SkMemset_opts_erms.cpp`（Enhanced REP MOVSB/STOSB）
- **LoongArch**: 支持 LASX（LoongArch Advanced SIMD Extension）
  - `SkBitmapProcState_opts_lasx.cpp` / `SkBlitRow_opts_lasx.cpp` / `SkSwizzler_opts_lasx.cpp`
- **ARM**: 通过 `SkCpu.h` 检测 NEON 等特性

### musttail 优化

`SkRasterPipeline.h` 中定义了 `SK_HAS_MUSTTAIL` 宏，在支持 `[[clang::musttail]]` 的平台上启用尾调用优化，这对管线性能至关重要。该优化在以下平台被禁用：
- Emscripten（WebAssembly）
- ARM32
- LoongArch
- PowerPC
- Windows 上的 Android Framework 构建（由于已知崩溃问题 crbug.com/1505442）

### 平台字体引擎集成

`SkScalerContext` 是 Skia 与平台字体引擎的桥梁。各平台提供不同的子类实现：
- macOS/iOS: CoreText（位于 `src/ports/`）
- Windows: DirectWrite（位于 `src/ports/`）
- Linux/Android: FreeType（位于 `src/ports/`）

`SkTypeface_remote.h` 支持远程字体代理，用于 Chrome 的沙箱架构中跨进程访问字体。

## 设计要点与注意事项

### 线程安全

- `SkResourceCache` 的全局实例通过静态方法访问时是线程安全的（内部加锁），但单独的实例不是
- `SkStrike` 使用 `SkMutex`（`fStrikeLock`）保护对字形数据的并发访问，方法上标注了 `SK_ACQUIRE` / `SK_RELEASE_CAPABILITY` / `SK_REQUIRES` 等线程注解
- `SkPicture` 的 unique ID 使用 `std::atomic` 生成，保证全局唯一

### 内存管理

- `SkArenaAlloc`（来自 `src/base/`）在 core 中被广泛使用，用于高效的临时对象分配（如 Blitter、管线上下文）
- `sk_sp<T>` 智能指针用于引用计数对象的生命周期管理
- `SkCachedData` 支持可丢弃内存（DiscardableMemory），允许系统在内存压力下回收缓存

### 全局初始化

`SkGlobalInitialization_core.cpp` 通过 `SkFlattenable::RegisterFlattenablesIfNeeded()` 完成核心类型的注册，包括 Effects 和 ImageFilters 的反序列化工厂注册。此初始化使用 `SkOnce` 保证只执行一次。

## 相关文档与参考

- [Skia 官方文档](https://skia.org/docs/)
- [Skia API 参考](https://api.skia.org/)
- [SkCanvas 概述](https://skia.org/docs/user/api/skcanvas_overview/)
- [SkPaint 概述](https://skia.org/docs/user/api/skpaint_overview/)
- [Skia 渲染管线 (Raster Pipeline)](https://skia.org/docs/dev/design/pipeline/)
- `include/core/` -- 公开 API 头文件目录
- `src/base/` -- 底层基础工具库
- `src/shaders/` -- 着色器实现
- `src/effects/` -- 效果实现
- `src/gpu/ganesh/` -- Ganesh GPU 后端
- `src/gpu/graphite/` -- Graphite GPU 后端
- `src/text/` -- 文本排版子系统
- `src/image/` -- 图像子系统
