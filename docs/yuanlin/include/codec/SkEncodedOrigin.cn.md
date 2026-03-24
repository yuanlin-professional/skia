# SkEncodedOrigin

> 源文件: `include/codec/SkEncodedOrigin.h`

## 概述

SkEncodedOrigin 模块定义了图像 EXIF 方向标记的处理逻辑,提供了从 EXIF Orientation 值到 Skia 变换矩阵的转换工具。该模块解决了数码相机、手机等设备拍摄的照片由于传感器方向导致的显示问题,是正确渲染 JPEG、TIFF 等带 EXIF 元数据图像的关键组件。

## 架构位置

该模块位于 Skia Codec 子系统的顶层工具模块,与图像解码流程紧密集成。它为 SkCodec 及其派生类(如 SkJpegCodec)提供方向矫正能力,同时被上层 UI 框架(如 Android 图像加载库)用于自动旋转处理。

## 核心类型定义

### SkEncodedOrigin 枚举

定义符合 EXIF 2.2 规范的 8 种图像方向。

**枚举值映射表**:

| 枚举值 | EXIF 值 | 描述 | 变换 |
|--------|---------|------|------|
| kTopLeft_SkEncodedOrigin | 1 | 默认方向,无需变换 | 无 |
| kTopRight_SkEncodedOrigin | 2 | 水平翻转 | 沿 Y 轴镜像 |
| kBottomRight_SkEncodedOrigin | 3 | 旋转 180 度 | 旋转 180° |
| kBottomLeft_SkEncodedOrigin | 4 | 垂直翻转 | 沿 X 轴镜像 |
| kLeftTop_SkEncodedOrigin | 5 | 转置(先 X 轴镜像,再逆时针 90°) | 转置矩阵 |
| kRightTop_SkEncodedOrigin | 6 | 顺时针旋转 90 度 | 旋转 90° CW |
| kRightBottom_SkEncodedOrigin | 7 | 转置并 X 轴镜像(先 X 轴镜像,再顺时针 90°) | 反转置矩阵 |
| kLeftBottom_SkEncodedOrigin | 8 | 逆时针旋转 90 度 | 旋转 90° CCW |

**常用别名**:
- `kDefault_SkEncodedOrigin`: 指向 kTopLeft_SkEncodedOrigin
- `kLast_SkEncodedOrigin`: 指向 kLeftBottom_SkEncodedOrigin,用于边界检查

## 核心函数

### `SkEncodedOriginToMatrix`

将 EXIF 方向转换为正向变换矩阵。

```cpp
static inline SkMatrix SkEncodedOriginToMatrix(SkEncodedOrigin origin, int w, int h)
```

**功能**: 生成将源矩形 `[0, 0, w, h]` 变换到正确方向的矩阵。

**参数**:
- `origin`: EXIF 方向枚举值
- `w`: 源图像宽度
- `h`: 源图像高度

**返回值**: 3x3 仿射变换矩阵

**矩阵详解**:
| 方向 | 矩阵(行优先) | 说明 |
|------|--------------|------|
| kTopLeft | `[1,0,0; 0,1,0; 0,0,1]` | 单位矩阵 |
| kTopRight | `[-1,0,w; 0,1,0; 0,0,1]` | X 轴翻转,平移 w |
| kBottomRight | `[-1,0,w; 0,-1,h; 0,0,1]` | 中心旋转 180° |
| kBottomLeft | `[1,0,0; 0,-1,h; 0,0,1]` | Y 轴翻转,平移 h |
| kLeftTop | `[0,1,0; 1,0,0; 0,0,1]` | 转置 |
| kRightTop | `[0,-1,w; 1,0,0; 0,0,1]` | 顺时针 90° |
| kRightBottom | `[0,-1,w; -1,0,h; 0,0,1]` | 转置后翻转 |
| kLeftBottom | `[0,1,0; -1,0,h; 0,0,1]` | 逆时针 90° |

### `SkEncodedOriginToMatrixInverse`

返回逆向变换矩阵,用于将屏幕坐标映射回原始图像坐标。

```cpp
static inline SkMatrix SkEncodedOriginToMatrixInverse(SkEncodedOrigin origin, int w, int h)
```

**应用场景**:
- 触摸事件坐标转换
- 图像编辑中的选区映射
- ROI(感兴趣区域)提取

**特殊性质**: 对于镜像和 180° 旋转,逆矩阵与正矩阵相同(自逆运算)。

### `SkEncodedOriginSwapsWidthHeight`

判断给定方向是否交换图像宽高。

```cpp
static inline bool SkEncodedOriginSwapsWidthHeight(SkEncodedOrigin origin)
```

**实现逻辑**: 当 `origin >= kLeftTop_SkEncodedOrigin` 时返回 true(即 EXIF 值 5-8)。

**用途**:
- 预分配画布尺寸
- UI 布局计算
- 缩略图生成

**示例**:
```cpp
// 原始图像 800x600
int displayWidth = SkEncodedOriginSwapsWidthHeight(origin) ? 600 : 800;
int displayHeight = SkEncodedOriginSwapsWidthHeight(origin) ? 800 : 600;
```

## 内部实现细节

### 矩阵构造优化
所有变换矩阵通过 `SkMatrix::MakeAll` 静态方法直接构造,避免运行时计算:
```cpp
// 顺时针 90° 的矩阵构造
return SkMatrix::MakeAll( 0, -1, w,  // [cos(90°), -sin(90°), tx]
                          1,  0, 0,  // [sin(90°),  cos(90°), ty]
                          0,  0, 1); // [      0,         0,  1]
```

### 开关语句穷举
使用 `switch` 语句穷举所有 8 种情况,编译器可优化为跳转表,避免分支预测失败。无 `default` 分支,未匹配时调用 `SK_ABORT`,确保 Debug 构建中快速发现错误。

### 内联优化
所有函数声明为 `static inline`,在 Release 构建中完全内联,消除函数调用开销。典型场景下矩阵查找仅耗费数个 CPU 周期。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/core/SkMatrix.h | 提供 SkMatrix 类和构造方法 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkCodec | 解码时应用方向变换 |
| SkJpegCodec | 从 EXIF 元数据读取方向信息 |
| SkAndroidCodec | Android 图片加载器自动方向矫正 |
| SkImageDecoder | 图像解码器基类使用方向信息 |

## 设计模式与设计决策

### 纯函数设计
所有函数无副作用,输入相同时输出必定相同。这种设计:
- 线程安全,无需同步
- 易于测试和验证
- 支持编译期常量折叠

### 标准兼容性
严格遵循 EXIF 2.2 PDF 规范(www.exif.org/Exif2-2.PDF),确保与所有标准兼容的相机/软件互操作。枚举值直接对应 EXIF Orientation 标签值,无需映射表。

### 头文件完整实现
所有实现在头文件中完成,利用 inline 特性避免链接期依赖。这对于模板密集的 Skia 架构至关重要,减少了编译单元间的耦合。

## 性能考量

### 零运行时开销
- 矩阵系数预先计算,不涉及三角函数或浮点运算
- 编译器可内联所有函数,消除调用栈
- `switch` 语句可优化为 O(1) 跳转表

### 内存效率
- 枚举类型占用 4 字节
- 矩阵结果通常存储为 9 个 float(36 字节)
- 无动态内存分配

### 缓存友好
- 小型函数体适合 CPU 指令缓存
- 数据结构紧凑,减少 cache miss

## 典型使用场景

### 解码时自动矫正
```cpp
// JPEG 解码器中
SkEncodedOrigin origin = readExifOrientation(stream);
SkMatrix transform = SkEncodedOriginToMatrix(origin, width, height);
canvas->concat(transform);
codec->getPixels(info, pixels, rowBytes);
```

### 缩略图生成
```cpp
// 计算缩略图尺寸
int thumbW = 200, thumbH = 150;
if (SkEncodedOriginSwapsWidthHeight(origin)) {
    std::swap(thumbW, thumbH);
}
SkBitmap thumbnail;
thumbnail.allocPixels(SkImageInfo::Make(thumbW, thumbH, ...));
```

### 触摸事件转换
```cpp
// UI 层触摸点到图像坐标
SkMatrix inverse = SkEncodedOriginToMatrixInverse(origin, w, h);
SkPoint imagePoint;
inverse.mapPoints(&imagePoint, &touchPoint, 1);
```

## 边界情况处理

### 无效方向值
对于不在 1-8 范围内的值,`SK_ABORT` 会终止程序(Debug 模式)或产生未定义行为(Release 模式)。调用者应确保输入有效性:
```cpp
SkEncodedOrigin origin = clampOrientation(exifValue);
if (origin < kTopLeft_SkEncodedOrigin || origin > kLast_SkEncodedOrigin) {
    origin = kDefault_SkEncodedOrigin;
}
```

### 零尺寸图像
当 `w=0` 或 `h=0` 时,生成的矩阵在数学上仍然有效,但实际应用中应在调用前检查:
```cpp
if (width > 0 && height > 0) {
    SkMatrix m = SkEncodedOriginToMatrix(origin, width, height);
}
```

## 平台相关说明

### Android 集成
Android Framework 中 `ExifInterface` 类的 `TAG_ORIENTATION` 值可直接转换为 `SkEncodedOrigin`:
```java
// Java 层
int exifOrientation = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, 1);
// 传递到 Native 层后直接使用
```

### iOS/macOS
Core Graphics 使用不同的方向模型(CGImagePropertyOrientation),需要映射:
```cpp
SkEncodedOrigin fromCGOrientation(CGImagePropertyOrientation cgOrigin) {
    static const SkEncodedOrigin map[] = { /* 映射表 */ };
    return map[cgOrigin];
}
```

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkMatrix.h | 提供矩阵类型定义 |
| include/codec/SkCodec.h | 使用 SkEncodedOrigin 作为图像属性 |
| src/codec/SkJpegCodec.cpp | 从 JPEG EXIF 解析方向 |
| src/android/SkBitmapRegionCodec.cpp | Android 区域解码中应用方向 |
| src/ports/SkImageGeneratorCG.cpp | macOS/iOS Core Graphics 桥接 |

## 注意事项

### EXIF 优先级
- EXIF 方向仅在图像元数据中存在时有效
- 某些编辑软件可能清除 EXIF 信息,导致方向丢失
- 用户手动旋转应更新 EXIF 标签以保持一致性

### 性能权衡
- 解码时变换(transform-on-decode): 内存占用小,但每次显示需重新变换
- 解码后旋转(rotate-after-decode): 增加内存拷贝,但渲染时无需额外计算
- Skia 默认采用前者,适合内存受限环境
