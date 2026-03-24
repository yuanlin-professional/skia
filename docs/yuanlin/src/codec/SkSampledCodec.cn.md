# SkSampledCodec

> 源文件: src/codec/SkSampledCodec.h, src/codec/SkSampledCodec.cpp

## 概述

`SkSampledCodec` 是 Skia Android 图像解码框架的核心实现类，通过采样（sampling）技术实现图像的高效缩放解码。它继承自 `SkAndroidCodec`，为 Android 平台提供了优化的图像加载能力，能够在解码时直接生成缩小的图像，而无需先解码完整图像再缩放，从而显著减少内存使用和提升解码性能。

该类的设计理念是充分利用底层编解码器的原生缩放能力（如 JPEG 的硬件加速），当原生不支持时再通过行采样实现缩放。它支持子区域解码、增量解码和多种扫描线顺序，是 Android 平台图像加载的性能基石。

## 架构位置

`SkSampledCodec` 在 Skia 编解码器架构中的位置：

```
SkAndroidCodec (Android 编解码器抽象基类)
  ├── SkSampledCodec (采样实现 - 通用方案)
  └── [其他特化实现]
       └── 内部封装 SkCodec (标准解码器)
```

**与 SkCodec 的关系：**
- `SkAndroidCodec` 持有一个 `SkCodec` 指针
- `SkSampledCodec` 通过 `codec()` 访问底层解码器
- 优先使用 `SkCodec` 的原生缩放能力（如 JPEG 2/4/8 倍采样）
- 不支持时通过 `SkSampler` 实现采样

**在 Android 图像加载流程中的角色：**
1. **BitmapFactory** → `SkAndroidCodec`
2. **选择实现** → `SkSampledCodec`（大部分格式）
3. **执行解码** → 结合原生缩放 + 采样缩放
4. **输出** → 缩放后的位图

## 主要类与结构体

### SkSampledCodec

采样解码器的主实现类。

**继承关系：**
- 继承自 `SkAndroidCodec`
- 封装一个 `SkCodec` 实例

**核心方法：**

#### 公共接口（覆盖 SkAndroidCodec）

- `onGetSampledDimensions()`: 计算给定采样率下的输出尺寸
- `onGetSupportedSubset()`: 声明支持任意子区域（返回 true）
- `onGetAndroidPixels()`: 主解码入口，协调原生缩放和采样缩放

#### 私有方法

- `accountForNativeScaling()`: 优化采样率分解，充分利用原生缩放
- `sampledDecode()`: 实现基于采样的缩放解码

## 公共 API 函数

### 构造函数

```cpp
explicit SkSampledCodec(SkCodec* codec)
```

创建采样解码器，接管传入的 `SkCodec` 的所有权（通过 `SkAndroidCodec` 构造函数）。

**参数：**
- `codec`: 底层的标准解码器实例

### onGetSampledDimensions

```cpp
SkISize onGetSampledDimensions(int sampleSize) const override
```

计算给定采样率下的输出图像尺寸。考虑了原生缩放和采样的组合效果。

**参数：**
- `sampleSize`: 采样率（1 表示原始大小，2 表示宽高各缩小一半）

**返回值：** 输出图像的尺寸

**实现逻辑：**
1. 调用 `accountForNativeScaling()` 获取原生缩放后的尺寸
2. 对剩余的采样率应用 `SkCodecPriv::GetSampledDimension()`

### onGetSupportedSubset

```cpp
bool onGetSupportedSubset(SkIRect* desiredSubset) const override
```

声明支持任意子区域解码，直接返回 `true`。

### onGetAndroidPixels

```cpp
SkCodec::Result onGetAndroidPixels(const SkImageInfo& info,
                                   void* pixels,
                                   size_t rowBytes,
                                   const AndroidOptions& options) override
```

主解码函数，根据请求的尺寸、采样率和子区域执行优化的解码。

**参数：**
- `info`: 目标图像信息（尺寸、颜色类型等）
- `pixels`: 输出缓冲区
- `rowBytes`: 行字节数
- `options`: 解码选项（包含采样率和子区域）

**返回值：** 解码结果（`kSuccess`、`kIncompleteInput` 等）

**路径选择：**
1. **完整图像 + 原生支持** → 直接调用 `codec()->getPixels()`
2. **完整图像 + 不支持** → `sampledDecode()`
3. **子区域 + 原生支持** → 使用增量解码或扫描线解码
4. **子区域 + 不支持** → `sampledDecode()` 结合采样

## 内部实现细节

### accountForNativeScaling - 原生缩放优化

该方法是性能优化的核心，负责分解采样率以充分利用 JPEG 的硬件加速。

**算法逻辑：**

```cpp
输入：sampleSize = 16
JPEG 支持：2, 4, 8 倍原生缩放

步骤 1：检查是否整除 8
  16 / 8 = 2, 余数 0
  → 使用原生缩放 8 倍
  → 剩余采样 2 倍

输出：
  nativeSampleSize = 8
  sampleSize = 2（更新为剩余采样）
  preSampledSize = 原始尺寸 / 8
```

**特殊优化：**
- `sampleSize = 2/4/8` → 完全由 libjpeg 处理，无需额外采样
- `sampleSize = 16` → libjpeg 8 倍 + 采样 2 倍
- `sampleSize = 6` → libjpeg 2 倍 + 采样 3 倍

### sampledDecode - 采样解码核心

当原生解码器不支持目标尺寸时，该方法实现基于行采样的缩放解码。

**流程概览：**

1. **参数计算**
   ```cpp
   // 调整采样率（考虑原生缩放）
   accountForNativeScaling(&sampleSize, &nativeSampleSize)

   // 计算子区域（如果有）
   subsetX = options.fSubset->x() / nativeSampleSize
   subsetY = options.fSubset->y() / nativeSampleSize

   // 计算实际采样率
   sampleX = subsetWidth / info.width()
   sampleY = subsetHeight / info.height()
   ```

2. **增量解码路径**（优先）
   ```cpp
   startIncrementalDecode(nativeInfo, pixels, rowBytes, ...)
   sampler = codec()->getSampler(true)
   sampler->setSampleX(sampleX)
   sampler->setSampleY(sampleY)
   incrementalDecode(&rowsDecoded)
   ```

3. **扫描线解码路径**（备选）
   - **kTopDown_SkScanlineOrder**（自上而下）：
     ```cpp
     skipScanlines(startY)  // 跳到起始行
     for (y = 0; y < dstHeight; y++) {
         getScanlines(pixelPtr, 1, rowBytes)  // 读取一行
         skipScanlines(sampleY - 1)           // 跳过采样间隔
     }
     ```

   - **kBottomUp_SkScanlineOrder**（自下而上）：
     ```cpp
     for (y = 0; y < nativeSize.height(); y++) {
         srcY = nextScanline()
         if (IsCoordNecessary(srcY, sampleY, dstHeight)) {
             dstY = GetDstCoord(srcY, sampleY)
             getScanlines(pixels + dstY * rowBytes, 1, rowBytes)
         } else {
             skipScanlines(1)
         }
     }
     ```

### 子区域解码策略

**完整流程示例（原生支持的子区域）：**

```
原始图像: 800x600
sampleSize: 2
子区域: (100, 100, 400, 400)

步骤 1：计算缩放后尺寸
  scaledSize = 400x300

步骤 2：计算缩放后子区域
  scaledSubsetX = 100 / 2 = 50
  scaledSubsetY = 100 / 2 = 50
  scaledSubsetWidth = 400 / 2 = 200
  scaledSubsetHeight = 400 / 2 = 200

步骤 3：解码路径选择
  增量解码：
    subset = (50, 50, 200, 200)
    startIncrementalDecode(scaledInfo, ...)
    incrementalDecode()

  扫描线解码（fallback）：
    subset = (50, 0, 200, 300)  // Y 方向全高
    startScanlineDecode(scaledInfo, ...)
    skipScanlines(50)
    getScanlines(pixels, 200, rowBytes)
```

### 不完整输入处理

当输入流不完整时，填充未解码区域：

```cpp
// 计算已解码行数
int rowsDecoded = ...;

// 填充剩余行
codec()->fillIncompleteImage(
    info, pixels, rowBytes,
    options.fZeroInitialized,
    dstHeight, rowsDecoded
);

return SkCodec::kIncompleteInput;
```

## 依赖关系

### 直接依赖

- **SkAndroidCodec**: 父类，定义 Android 解码接口
- **SkCodec**: 底层标准解码器
- **SkSampler**: 采样器接口，用于行采样
- **SkCodecPriv**: 编解码器内部工具函数

### 间接依赖

- **SkSwizzler**: 通过 `SkSampler` 使用，执行像素格式转换和采样
- **SkImageInfo**: 图像元数据
- **SkIRect**: 矩形区域

### 被依赖关系

- **SkAndroidCodec::MakeFromCodec**: 工厂函数创建实例
- **Android BitmapFactory**: 通过 JNI 调用

## 设计模式与设计决策

### 适配器模式

`SkSampledCodec` 作为适配器，将标准的 `SkCodec` 接口适配为 Android 特有的采样解码接口。

### 策略模式

根据底层编解码器的能力动态选择解码策略：
- 原生缩放优先策略（JPEG）
- 采样缩放备选策略（通用）
- 增量解码 vs 扫描线解码

### 模板方法模式

定义解码的标准流程，由底层 `SkCodec` 实现具体步骤。

### 设计决策

1. **JPEG 特殊优化**：
   - 仅 JPEG 支持原生缩放（2/4/8 倍）
   - 硬编码在 `accountForNativeScaling()` 中
   - 理由：JPEG 是 Android 最常用的格式，硬件加速收益大

2. **两阶段缩放**：
   - 原生缩放 → 采样缩放
   - 减少内存带宽和计算量

3. **增量解码优先**：
   - 优先尝试 `startIncrementalDecode`
   - 失败时回退到扫描线解码
   - 增量解码更灵活，支持渐进式加载

4. **子区域限制**：
   - 自下而上扫描不支持子区域
   - 需要完整图像信息才能正确映射

5. **采样器延迟创建**：
   - 只有在需要采样时才调用 `getSampler(true)`
   - 避免不必要的初始化开销

## 性能考量

### 优化策略

1. **原生缩放优化**：
   - JPEG 2 倍采样：解码速度提升 ~75%
   - JPEG 4 倍采样：解码速度提升 ~90%
   - 内存减少：1/4 到 1/64

2. **行跳过优化**：
   - 自上而下扫描使用 `skipScanlines()`
   - 避免解码和丢弃不需要的行

3. **内存访问模式**：
   - 逐行处理，缓存友好
   - 子区域解码减少输出缓冲区大小

4. **分支预测优化**：
   - 增量解码路径优先（现代编解码器常支持）
   - 完整图像路径优先（最常见场景）

### 性能瓶颈

- **自下而上扫描**：需要跳过大量行，效率低
- **小采样率（如 1.5 倍）**：无法利用原生缩放，需完整采样
- **子区域 + 采样**：需要多次坐标计算和跳过操作

### 内存使用

- **原生缩放**：中间缓冲区仅为缩放后大小
- **采样解码**：单行缓冲区（由 `SkSwizzler` 管理）
- **子区域**：仅分配目标区域大小的缓冲区

### 典型场景性能

| 场景 | 采样率 | 性能 |
|------|--------|------|
| JPEG 缩略图 | 8 | 最快（原生） |
| JPEG 列表图 | 4 | 很快（原生） |
| PNG 缩略图 | 8 | 快（采样） |
| WebP 列表图 | 2 | 中等（采样） |
| BMP 子区域 | 2 | 较慢（无原生支持） |

## 相关文件

### 核心文件

- `include/codec/SkAndroidCodec.h`: 父类定义
- `include/codec/SkCodec.h`: 底层解码器接口
- `src/codec/SkSampler.h/cpp`: 采样器抽象基类
- `src/codec/SkSwizzler.h/cpp`: 采样器具体实现

### 辅助文件

- `src/codec/SkCodecPriv.h`: 编解码器私有工具
  - `GetScaleFromSampleSize()`: 采样率转缩放比例
  - `GetSampledDimension()`: 计算采样后尺寸
  - `IsCoordNecessary()`: 判断行是否需要解码
  - `GetDstCoord()`: 计算目标行坐标
- `src/base/SkMathPriv.h`: 数学工具（`SkTDivMod`）

### 特定格式解码器

- `src/codec/SkJpegCodec.h/cpp`: JPEG 解码器（支持原生缩放）
- `src/codec/SkPngCodec.h/cpp`: PNG 解码器
- `src/codec/SkWebpCodec.h/cpp`: WebP 解码器

### Android 集成

- `platform_tools/android/apps/skia/src/main/cpp/`: Android JNI 绑定
- `client_utils/android/BitmapRegionDecoder.cpp`: 区域解码器

### 测试文件

- `tests/CodecTest.cpp`: 编解码器单元测试
- `tests/AndroidCodecTest.cpp`: Android 特定测试
- `dm/DMSrcSink.cpp`: 图像解码基准测试

### 工厂文件

- `src/codec/SkAndroidCodec.cpp`: `MakeFromCodec()` 工厂函数
