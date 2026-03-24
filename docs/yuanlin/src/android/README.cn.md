# src/android - Android 平台特定功能模块

## 概述

`src/android` 目录包含 Skia 图形库中专门为 Android 平台提供的功能实现。该模块的代码主要服务于 Android 系统框架（Android Framework），提供了一系列 Android 特有的工具函数、动画图像支持以及性能追踪集成。这些功能大多通过条件编译宏（如 `SK_BUILD_FOR_ANDROID_FRAMEWORK`）进行平台隔离。

该模块的核心组件包括：`SkAndroidFrameworkUtils` 工具类，提供了 Android 框架所需的特殊画布操作（如模板裁剪、SaveBehind、剪裁重置等）；`SkAnimatedImage` 类，提供了对 GIF、WebP、HEIF 等动画图像格式的完整解码和播放支持；以及 Perfetto 追踪集成，用于 Android 系统级性能分析。

`SkAnimatedImage` 是该模块中功能最复杂的组件。它实现了完整的动画帧管理逻辑，包括帧间依赖处理、多种帧处理方法（保留/恢复为背景/恢复为前一帧）、循环控制、采样缩放以及图像方向处理。它使用三帧缓冲机制（显示帧、解码帧、恢复帧）来优化内存使用和解码性能。

`SkAndroidFrameworkUtils` 提供的接口较为特殊，许多函数直接访问 Skia 内部私有 API（如 `SkCanvas::only_axis_aligned_saveBehind`、`SkCanvas::internal_private_resetClip` 等），这些接口仅供 Android 系统框架使用，不属于 Skia 的公共 API。

## 架构图

```
+------------------------------------------------------------------+
|                    Android Framework 层                            |
|        (HWUI, RenderThread, 系统级图形管线)                       |
+------------------------------------------------------------------+
        |                    |                    |
        v                    v                    v
+----------------+  +------------------+  +---------------------+
| SkAndroid-     |  | SkAnimatedImage  |  | Perfetto 追踪集成    |
| Framework-     |  | (动画图像解码    |  | (性能分析数据收集)   |
| Utils          |  |  与播放)         |  |                     |
+-------+--------+  +--------+---------+  +---------------------+
        |                    |
        v                    v
+----------------+  +------------------+
| SkCanvas       |  | SkAndroidCodec   |
| (内部私有API)  |  | (编解码器接口)   |
+----------------+  +------------------+
        |                    |
        v                    v
+----------------+  +------------------+
| SkDevice       |  | SkCodec          |
| SkSurface      |  | (底层解码实现)   |
+----------------+  +------------------+
```

## 目录结构

```
src/android/
  BUILD.bazel                                  -- Bazel 构建配置
  SkAndroidFrameworkUtils.cpp                  -- Android 框架工具函数实现
  SkAnimatedImage.cpp                          -- 动画图像解码与播放实现
  SkAndroidFrameworkPerfettoStaticStorage.cpp  -- Perfetto 追踪静态存储

相关公共头文件:
  include/android/SkAndroidFrameworkUtils.h    -- 框架工具函数声明
  include/android/SkAnimatedImage.h            -- 动画图像类声明
  include/android/SkCanvasAndroid.h            -- Android Canvas 扩展
  include/android/SkImageAndroid.h             -- Android Image 扩展
  include/android/SkSurfaceAndroid.h           -- Android Surface 扩展
  include/android/AHardwareBufferUtils.h       -- AHardwareBuffer 工具
  include/android/GrAHardwareBufferUtils.h     -- GPU AHardwareBuffer 工具
```

## 关键类与函数

### SkAndroidFrameworkUtils（框架工具类）
- **位置**: `src/android/SkAndroidFrameworkUtils.cpp`, `include/android/SkAndroidFrameworkUtils.h`
- **职责**: 提供 Android 框架所需的特殊 Skia 操作

#### 核心方法

- `clipWithStencil(SkCanvas*)` -- 使用模板缓冲区进行裁剪（仅 Ganesh GPU 后端）
  - 调用 `canvas->rootDevice()->android_utils_clipWithStencil()`
  - 用于 Android HWUI 的硬件加速渲染管线

- `SafetyNetLog(const char* bugNumber)` -- 记录安全漏洞修复日志
  - 仅在 `SK_BUILD_FOR_ANDROID_FRAMEWORK` 下编译
  - 使用 `android_errorWriteLog(0x534e4554, bugNumber)` 向系统日志写入

- `getSurfaceFromCanvas(SkCanvas*)` -- 从画布获取关联的 SkSurface
  - 调用 `canvas->getSurfaceBase()` 内部方法

- `SaveBehind(SkCanvas*, const SkRect*)` -- 保存画布背景
  - 调用 `canvas->only_axis_aligned_saveBehind(subset)`
  - 用于 Android 的阴影绘制优化

- `ResetClip(SkCanvas*)` -- 重置裁剪区域
  - 调用 `canvas->internal_private_resetClip()`

- `getBaseWrappedCanvas(SkCanvas*)` -- 获取最内层的基础画布
  - 沿 `SkPaintFilterCanvas` 链向下遍历，找到最终的非过滤画布

- `ShaderAsALinearGradient(SkShader*, LinearGradientInfo*)` -- 将着色器解析为线性渐变信息
  - 使用 `SkShaderBase::asGradient()` 分析着色器
  - 返回渐变的颜色、偏移、端点和平铺模式

### SkAnimatedImage（动画图像类）
- **位置**: `src/android/SkAnimatedImage.cpp`, `include/android/SkAnimatedImage.h`
- **继承**: `SkDrawable`
- **职责**: 管理动画图像（GIF、WebP、HEIF等）的帧解码和播放

#### 工厂方法
- `Make(unique_ptr<SkAndroidCodec>)` -- 从编解码器创建动画图像
- `Make(unique_ptr<SkAndroidCodec>, SkImageInfo, SkIRect cropRect, sk_sp<SkPicture> postProcess)` -- 带自定义参数创建

#### 核心方法
- `decodeNextFrame()` -- 解码下一帧，返回帧持续时间（毫秒），`kFinished` 表示动画结束
- `reset()` -- 重置到第一帧
- `getCurrentFrame()` -- 获取当前帧的 SkImage（含裁剪和后处理）
- `getCurrentFrameSimple()` -- 获取当前帧的原始 SkImage
- `onDraw(SkCanvas*)` -- 在画布上绘制当前帧
- `setRepetitionCount(int)` -- 设置循环次数
- `setFilterMode(SkFilterMode)` -- 设置采样滤波模式

#### 内部帧管理（Frame 结构体）
- `fDisplayFrame` -- 当前显示帧
- `fDecodingFrame` -- 解码工作帧
- `fRestoreFrame` -- 恢复帧（用于 RestorePrevious 处理方法）

#### 关键属性
- `fCodec` -- 底层 SkAndroidCodec 编解码器
- `fDecodeInfo` -- 解码图像信息
- `fCropRect` -- 裁剪矩形
- `fPostProcess` -- 后处理 SkPicture
- `fMatrix` -- 变换矩阵（处理方向、缩放、裁剪偏移）
- `fFrameCount` -- 总帧数
- `fRepetitionCount` / `fRepetitionsCompleted` -- 循环计数
- `fSampleSize` -- 采样大小

### Perfetto 追踪集成
- **位置**: `src/android/SkAndroidFrameworkPerfettoStaticStorage.cpp`
- **条件编译**: `SK_ANDROID_FRAMEWORK_USE_PERFETTO`
- **功能**: `PERFETTO_TRACK_EVENT_STATIC_STORAGE()` 宏为 Perfetto 追踪系统提供静态存储

## 依赖关系

### 外部依赖
- **Android NDK/SDK**: `<log/log.h>`（日志系统，仅 Android 框架构建）
- **Perfetto**: 追踪事件库（条件编译）

### 内部依赖
- `src/core` -- `SkDevice`, `SkCanvas`（画布和设备内部 API）
- `src/codec` -- `SkCodecPriv`, `SkPixmapUtilsPriv`（图像解码内部工具）
- `src/image` -- `SkSurface_Base`, `SkImage_Raster`
- `src/shaders` -- `SkShaderBase`（着色器分析）
- `include/codec` -- `SkAndroidCodec`, `SkCodec`（编解码器接口）
- `include/effects` -- `SkGradient`（渐变效果）
- `include/utils` -- `SkPaintFilterCanvas`（画布过滤器链遍历）
- `include/core` -- `SkPicture`, `SkPictureRecorder`, `SkPixelRef`

### 被依赖
- Android 系统框架 HWUI 渲染引擎
- Android 应用通过 Android SDK 间接使用

## 设计模式分析

### 三帧缓冲策略（Triple Frame Buffer）
`SkAnimatedImage` 使用三个 Frame 结构（显示帧、解码帧、恢复帧）来管理帧依赖。这种策略确保在需要 RestorePrevious 处理方法时不会覆盖可能被后续帧依赖的前一帧数据。帧之间通过 `std::swap` 进行零拷贝交换。

### 延迟复制（Copy-on-Write）
`Frame::init()` 方法在位图的 PixelRef 被外部持有时才进行实际复制（`OnInit::kRestoreIfNecessary`），避免不必要的内存拷贝。

### 外观模式（Facade）
`SkAndroidFrameworkUtils` 充当了一个外观类，将 Skia 内部的多个私有 API 整合为一组 Android 框架专用的简洁接口。

### 策略模式（Strategy）
动画图像的帧处理方法（`DisposalMethod::kKeep`、`kRestoreBGColor`、`kRestorePrevious`）决定了帧间的依赖关系和缓冲区管理策略，在 `decodeNextFrame()` 中通过不同的代码路径实现。

## 数据流

### 动画图像播放流程
```
SkAnimatedImage::Make(codec)
    |
    v
构造函数:
  1. 计算方向矩阵 (SkEncodedOriginToMatrix)
  2. 计算采样大小 (computeSampleSize)
  3. 计算缩放矩阵
  4. 分配解码缓冲区
  5. decodeNextFrame() -- 解码第一帧
    |
    v
播放循环:
  decodeNextFrame()
    |
    +---> computeNextFrame() -- 计算下一帧索引
    |       +---> 检查循环计数
    |       +---> 处理帧结束
    |
    +---> getFrameInfo() -- 获取帧信息
    |
    +---> 帧依赖分析:
    |       +---> 无依赖帧 --> 直接解码到 fDecodingFrame
    |       +---> 有依赖帧 --> 从 fDecodingFrame/fDisplayFrame/fRestoreFrame 选择先验帧
    |       +---> RestorePrevious --> 保存恢复帧
    |
    +---> fCodec->getAndroidPixels() -- 实际解码
    |
    +---> swap(fDecodingFrame, fDisplayFrame) -- 交换显示帧
    |
    +---> 返回帧持续时间（毫秒）
    |
    v
onDraw(canvas):
  1. getCurrentFrameSimple() -- 获取当前帧图像
  2. canvas->clipRect(bounds) -- 裁剪区域
  3. canvas->concat(fMatrix) -- 应用变换
  4. canvas->drawImage() -- 绘制图像
  5. canvas->drawPicture(fPostProcess) -- 后处理（可选）
```

## 相关文档与参考

- **Android HWUI**: Android 硬件加速 UI 渲染引擎
- **SkAndroidCodec**: `include/codec/SkAndroidCodec.h` -- Android 编解码器接口
- **SkCodec**: `include/codec/SkCodec.h` -- 底层编解码器
- **SkDrawable**: `include/core/SkDrawable.h` -- SkAnimatedImage 的基类
- **Perfetto**: https://perfetto.dev/ -- Android 性能追踪框架
- **图像方向处理**: `SkEncodedOrigin` -- EXIF 方向标志处理
- **帧处理方法**: `SkCodecAnimation::DisposalMethod` -- 动画帧处理策略枚举
