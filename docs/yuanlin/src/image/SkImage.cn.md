# SkImage — Skia 图像基类实现

> 源文件: `src/image/SkImage.cpp`

## 概述

`SkImage.cpp` 是 Skia 图像抽象基类 `SkImage` 的核心实现文件。`SkImage` 是 Skia 中表示不可变图像的核心类型，提供了统一的接口来操作各种来源的图像数据（光栅位图、GPU 纹理、编码数据等）。

该文件实现了 `SkImage` 的公共 API，包括：
- **像素读取**: 同步和异步读取图像像素数据
- **图像缩放**: 创建缩放后的图像副本
- **着色器创建**: 将图像转换为着色器（用于图案填充等场景）
- **色彩空间操作**: 重新解释或转换图像的色彩空间
- **格式转换**: 在 GPU 纹理图像和光栅图像之间转换
- **Mipmap 管理**: 添加或生成多级纹理

该实现大量使用了 `as_IB(this)` 宏将 `SkImage*` 转换为内部的 `SkImage_Base*`，然后委托给子类的虚函数实现。

## 架构位置

```
Skia
├── include/core/
│   └── SkImage.h              // 公共 API 声明
├── src/image/
│   ├── SkImage.cpp            // 本文件：基类实现
│   ├── SkImage_Base.h         // 内部扩展基类
│   ├── SkImage_Raster.cpp     // 光栅图像子类
│   ├── SkImage_Lazy.cpp       // 延迟加载图像子类
│   └── ...
└── src/gpu/
    └── ganesh/image/          // GPU 图像子类
```

`SkImage` 位于 Skia 架构的核心层，被画布（Canvas）、录制器（Recorder）、着色器（Shader）等上层模块广泛使用。

## 主要类与结构体

### `SkImage`

- **继承**: 引用计数基类 `SkRefCnt`
- **成员变量**:
  - `fInfo` (`SkImageInfo`): 图像的元信息（尺寸、颜色类型、alpha 类型、色彩空间）
  - `fUniqueID` (`uint32_t`): 图像的唯一标识符
- **设计**: 使用 `SkImage_Base`（通过 `as_IB()` 宏访问）作为内部扩展接口，子类实现具体功能

## 公共 API 函数

### 构造函数

#### `SkImage::SkImage(const SkImageInfo& info, uint32_t uniqueID)`

- 初始化图像信息和唯一 ID。如果传入 `kNeedNewImageUniqueID`，则通过 `SkNextID::ImageID()` 生成新 ID

### 像素读取

#### `bool peekPixels(SkPixmap* pm) const`

- 零拷贝地访问图像像素（仅光栅图像支持）

#### `bool readPixels(GrDirectContext*, const SkImageInfo&, void*, size_t, int, int, CachingHint) const`

- 将图像像素读取到指定缓冲区，支持格式转换和区域读取

#### `void asyncRescaleAndReadPixels(...) const`

- 异步缩放并读取像素（通过回调返回结果）

#### `void asyncRescaleAndReadPixelsYUV420(...) const`

- 异步缩放并读取为 YUV420 格式

#### `void asyncRescaleAndReadPixelsYUVA420(...) const`

- 异步缩放并读取为 YUVA420 格式（含 alpha 通道）

#### `bool scalePixels(const SkPixmap& dst, const SkSamplingOptions&, CachingHint) const`

- 同步缩放读取像素到 `SkPixmap`

### 属性查询

| 方法 | 返回值 |
|------|--------|
| `colorType()` | 颜色类型 |
| `alphaType()` | Alpha 类型 |
| `colorSpace()` | 色彩空间指针 |
| `refColorSpace()` | 色彩空间智能指针 |
| `isAlphaOnly()` | 是否仅含 alpha 通道 |
| `hasMipmaps()` | 是否有 mipmap |
| `isProtected()` | 是否受保护 |

### 着色器创建

#### `sk_sp<SkShader> makeShader(...)` (4 个重载)

- 创建图像着色器，支持指定平铺模式、采样选项和局部矩阵
- 默认平铺模式为 `kClamp`

#### `sk_sp<SkShader> makeRawShader(...)` (4 个重载)

- 创建"原始"图像着色器，不进行色彩空间转换

### 图像转换

#### `sk_sp<SkImage> makeScaled(...)` (3 个重载)

- 创建缩放后的图像。如果目标尺寸与原始尺寸相同，直接返回原图像引用

#### `sk_sp<SkImage> makeRasterImage(GrDirectContext*, CachingHint) const`

- 将 GPU 纹理图像转换为光栅图像（CPU 内存中的位图）

#### `sk_sp<SkImage> makeNonTextureImage(GrDirectContext*) const`

- 确保图像不在 GPU 纹理上

#### `sk_sp<SkImage> reinterpretColorSpace(sk_sp<SkColorSpace>) const`

- 重新解释图像的色彩空间（不转换像素数据，仅更改解释方式）

### Mipmap 操作

#### `sk_sp<SkImage> withMipmaps(sk_sp<SkMipmap>) const`

- 创建带有指定 mipmap 的图像副本

#### `sk_sp<SkImage> withDefaultMipmaps() const`

- 创建带有默认生成的 mipmap 的图像副本

## 内部实现细节

### `as_IB()` 转换宏

`as_IB(this)` 将 `const SkImage*` 转换为 `const SkImage_Base*`，以访问内部虚函数。这是 Skia 常见的模式：公共 API 定义在 `SkImage` 中，而内部实现细节在 `SkImage_Base` 中。

### 唯一 ID 生成

图像唯一 ID 通过 `SkNextID::ImageID()` 生成，保证全局唯一。用于缓存键和变化检测。

### 缩放实现

`makeScaled` 的实现策略：
1. 验证目标信息有效性
2. 若尺寸未变，直接返回自身引用（避免不必要的拷贝）
3. 创建目标尺寸的 surface
4. 使用 `kSrc` 混合模式在 surface 上绘制自身
5. 从 surface 生成图像快照

### YUV420 尺寸约束

异步 YUV420 读取要求目标尺寸的宽高都是偶数（`dstSize.width() & 0b1` 检查），这是 YUV 4:2:0 色度子采样的要求。

### Legacy API 兼容

部分 `readPixels` 重载被 `SK_IMAGE_READ_PIXELS_DISABLE_LEGACY_API` 宏保护，用于逐步移除不带 `GrDirectContext*` 参数的旧 API。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkImage.h` | 公共 API 声明 |
| `SkImage_Base.h` | 内部扩展基类 |
| `SkBitmap.h` | 位图操作 |
| `SkCanvas.h` | 图像缩放时绘制到 surface |
| `SkColorSpace.h` | 色彩空间管理 |
| `SkData.h` | 像素数据缓冲区 |
| `SkImageShader.h` | 创建图像着色器 |
| `SkMipmap.h` | Mipmap 管理 |
| `SkNextID.h` | 唯一 ID 生成 |
| `SkSurface.h` | 缩放时的渲染目标 |

## 设计模式与设计决策

1. **桥接模式**: `SkImage` (公共接口) 通过 `as_IB()` 委托给 `SkImage_Base` (实现接口)，将接口和实现分离
2. **不可变性**: `SkImage` 被设计为不可变的——所有"修改"操作都返回新的 `sk_sp<SkImage>`
3. **引用返回优化**: 当操作不改变图像时（如相同尺寸的缩放、相同色彩空间的重解释），直接返回自身引用 `sk_ref_sp(this)`
4. **多重载**: 着色器创建提供多种重载以适应不同的使用场景，默认使用 `kClamp` 平铺模式
5. **回调式异步 API**: `asyncRescaleAndReadPixels` 系列函数使用回调而非 future/promise，避免对异步框架的依赖
6. **渐进式 API 迁移**: 通过 `SK_IMAGE_READ_PIXELS_DISABLE_LEGACY_API` 宏控制旧 API 的可用性

## 性能考量

- **零拷贝 peekPixels**: 对于光栅图像，`peekPixels` 直接返回内部像素指针
- **尺寸检查短路**: `makeScaled` 和 `scalePixels` 在尺寸相同时直接返回，避免不必要的拷贝
- **异步读取**: `asyncRescaleAndReadPixels` 系列支持 GPU 异步操作，避免 CPU 等待
- **CachingHint**: 允许调用者控制是否缓存读取结果
- **Mipmap 复用**: `withMipmaps` 可以复用已有的 mipmap 数据

## 相关文件

- `include/core/SkImage.h` — 公共 API 声明
- `src/image/SkImage_Base.h` — 内部扩展基类
- `src/image/SkImage_Raster.cpp` — 光栅图像实现
- `src/image/SkImage_Lazy.cpp` — 延迟加载图像实现
- `src/shaders/SkImageShader.h` — 图像着色器
- `include/core/SkSurface.h` — 渲染表面
- `src/core/SkMipmap.h` — Mipmap 实现
