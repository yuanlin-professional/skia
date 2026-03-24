# SkDevice

> 源文件
> - src/core/SkDevice.h
> - src/core/SkDevice.cpp

## 概述

`SkDevice` 是 Skia 图形库中的核心抽象类,代表渲染目标的内部实现。它是 `SkCanvas` 的幕后执行者,负责将高层绘图命令转换为实际的像素操作或图形命令。每个 Canvas 层对应一个 Device,形成层级栈结构。

该类定义了完整的绘图操作接口,包括几何图形绘制、图像绘制、文本渲染、图像滤镜应用等。不同的后端(CPU、GPU、PDF 等)通过继承 SkDevice 实现各自的渲染策略。SkDevice 还管理设备的坐标系统、裁剪栈和像素访问。

## 架构位置

`SkDevice` 位于 Skia 架构的核心渲染层,是连接前端 API 和后端实现的关键抽象:

```
Skia Architecture
  ├─ Public API Layer
  │   └─ SkCanvas (用户绘图接口)
  ├─ Core Rendering Layer
  │   ├─ SkDevice ← 当前模块(渲染抽象基类)
  │   ├─ SkBaseDevice (基础设备实现)
  │   └─ Layer Stack Management
  └─ Backend Implementations
      ├─ SkBitmapDevice (CPU 光栅化)
      ├─ skgpu::ganesh::Device (Ganesh GPU)
      ├─ skgpu::graphite::Device (Graphite GPU)
      └─ SkPDFDevice (矢量文档)
```

SkCanvas 将绘图命令委托给当前活动的 SkDevice,Device 根据其类型选择合适的渲染路径。

## 主要类与结构体

### SkDevice

**继承关系**:
- 基类: `SkRefCnt` (引用计数)
- 派生类: `SkNoPixelsDevice`, `SkBitmapDevice`, GPU 设备等

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fInfo | SkImageInfo | 设备图像信息(尺寸、颜色类型、Alpha 类型、色彩空间) |
| fSurfaceProps | SkSurfaceProps | 表面属性(像素几何、文本渲染设置) |
| fLocalToDevice | SkM44 | 本地坐标到设备坐标的 4x4 变换矩阵 |
| fLocalToDevice33 | SkMatrix | 本地到设备的 3x3 变换矩阵(性能优化缓存) |
| fDeviceToGlobal | SkM44 | 设备坐标到全局坐标的变换 |
| fGlobalToDevice | SkM44 | 全局坐标到设备坐标的变换(fDeviceToGlobal 的逆) |
| fLocalToDeviceDirty | bool | 标记变换矩阵是否已修改 |

**核心职责**:
- 实现所有绘图操作的虚函数接口
- 管理设备的坐标系统和变换
- 维护裁剪栈(纯虚函数,由子类实现)
- 提供像素读写访问
- 支持图像滤镜和特殊图像处理

### SkNoPixelsDevice

**继承关系**: 继承自 `SkDevice`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fClipStack | STArray<4, ClipState> | 裁剪状态栈 |

**用途**:
- 无像素设备,用于记录绘图操作但不实际渲染
- 主要用于测试、边界计算、命令记录
- 保守地跟踪裁剪区域以响应查询

### ClipState (SkNoPixelsDevice 内部结构)

| 成员 | 类型 | 说明 |
|------|------|------|
| fClipBounds | SkIRect | 裁剪边界矩形 |
| fDeferredSaveCount | int | 延迟保存计数(优化栈操作) |
| fIsAA | bool | 是否抗锯齿裁剪 |
| fIsRect | bool | 裁剪区域是否为矩形 |

### SkAutoDeviceTransformRestore

RAII 辅助类,用于临时修改设备变换并自动恢复。

## 公共 API 函数

### 设备属性查询

```cpp
const SkImageInfo& imageInfo() const
int width() const / int height() const
bool isOpaque() const
SkIRect bounds() const
const SkSurfaceProps& surfaceProps() const
SkScalerContextFlags scalerContextFlags() const
```

获取设备的基本属性和配置信息。

### 像素访问

```cpp
bool writePixels(const SkPixmap& src, int x, int y)
bool readPixels(const SkPixmap& dst, int x, int y)
bool accessPixels(SkPixmap* pmap)
bool peekPixels(SkPixmap* pmap)
```

直接读写设备像素数据。`accessPixels` 提供可写访问,`peekPixels` 提供只读访问。

### 坐标变换

```cpp
const SkM44& localToDevice44() const
const SkMatrix& localToDevice() const
const SkM44& deviceToGlobal() const
const SkM44& globalToDevice() const
SkIPoint getOrigin() const  // 已弃用
bool isPixelAlignedToGlobal() const
SkM44 getRelativeTransform(const SkDevice& other) const
void setLocalToDevice(const SkM44& localToDevice)
void setGlobalCTM(const SkM44& ctm)
```

管理设备的坐标系统。设备有三个坐标空间:
1. **本地空间**: 绘图命令的原始坐标
2. **设备空间**: 设备像素坐标(可能带原点偏移)
3. **全局空间**: 根设备(Canvas)的坐标空间

### 裁剪操作 (纯虚函数)

```cpp
virtual SkIRect devClipBounds() const = 0
virtual void pushClipStack() = 0
virtual void popClipStack() = 0
virtual void clipRect(const SkRect&, SkClipOp, bool aa) = 0
virtual void clipRRect(const SkRRect&, SkClipOp, bool aa) = 0
virtual void clipPath(const SkPath&, SkClipOp, bool aa) = 0
virtual void clipRegion(const SkRegion&, SkClipOp) = 0
void clipShader(sk_sp<SkShader>, SkClipOp)
virtual void replaceClip(const SkIRect&) = 0
```

裁剪栈管理,支持矩形、圆角矩形、路径、区域和着色器裁剪。

### 绘图操作 (纯虚函数)

```cpp
virtual void drawPaint(const SkPaint&) = 0
virtual void drawPoints(SkCanvas::PointMode, SkSpan<const SkPoint>, const SkPaint&) = 0
virtual void drawRect(const SkRect&, const SkPaint&) = 0
virtual void drawOval(const SkRect&, const SkPaint&) = 0
virtual void drawRRect(const SkRRect&, const SkPaint&) = 0
virtual void drawPath(const SkPath&, const SkPaint&) = 0
virtual void drawImageRect(...) = 0
virtual void drawVertices(const SkVertices*, sk_sp<SkBlender>, const SkPaint&, bool) = 0
virtual void drawMesh(const SkMesh&, sk_sp<SkBlender>, const SkPaint&) = 0
```

核心绘图接口,所有绘图操作最终调用这些函数。

### 文本渲染

```cpp
void drawGlyphRunList(SkCanvas*, const sktext::GlyphRunList&, const SkPaint&)
virtual sk_sp<sktext::gpu::Slug> convertGlyphRunListToSlug(...)
virtual void drawSlug(SkCanvas*, const sktext::gpu::Slug*, const SkPaint&)
```

文本渲染接口,支持字形列表和 Slug(预处理的文本对象)。

### 特殊图像操作

```cpp
virtual sk_sp<SkSpecialImage> snapSpecial(const SkIRect& subset, bool forceCopy = false)
virtual void drawSpecial(SkSpecialImage*, const SkMatrix&, const SkSamplingOptions&, const SkPaint&, ...)
virtual void drawCoverageMask(const SkSpecialImage*, const SkMatrix&, const SkSamplingOptions&, const SkPaint&)
void drawDevice(SkDevice*, const SkSamplingOptions&, const SkPaint&)
void drawFilteredImage(const skif::Mapping&, SkSpecialImage*, SkColorType, const SkImageFilter*, ...)
```

处理图像滤镜、遮罩和设备合成。

### 设备创建

```cpp
virtual sk_sp<SkDevice> createDevice(const CreateInfo&, const SkPaint*)
virtual sk_sp<SkSurface> makeSurface(const SkImageInfo&, const SkSurfaceProps&)
```

创建子设备用于 saveLayer 操作。

## 内部实现细节

### 坐标系统管理

SkDevice 维护三层变换:
1. **localToDevice**: 从绘图调用的本地坐标到设备像素坐标
2. **deviceToGlobal**: 从设备坐标到全局 Canvas 坐标(支持非轴对齐)
3. **globalToDevice**: deviceToGlobal 的逆矩阵

当 Canvas 创建层(saveLayer)时,新设备的 deviceToGlobal 可能包含平移和旋转,允许设备在全局空间中任意定位。

### 坐标系设置

```cpp
void setDeviceCoordinateSystem(const SkM44& deviceToGlobal,
                               const SkM44& globalToDevice,
                               const SkM44& localToDevice,
                               int bufferOriginX, int bufferOriginY)
```

统一配置设备的坐标系统,包括缓冲区原点偏移。

### 延迟裁剪优化 (SkNoPixelsDevice)

SkNoPixelsDevice 实现延迟裁剪保存计数(`fDeferredSaveCount`):
- `pushClipStack()` 时仅增加计数,不立即创建新栈项
- 只有在实际修改裁剪时才创建新栈项
- 减少无效 save/restore 的开销

### 文本渲染处理

`drawGlyphRunList` 检测是否包含 RSXForm(旋转缩放变换),如果有则调用 `simplifyGlyphRunRSXFormAndRedraw`,将每个字形分别变换并重绘。这是因为标准字形渲染不直接支持 RSXForm。

### 图像滤镜执行

`drawFilteredImage` 创建图像滤镜后端(Backend),配置滤镜上下文(Context),执行滤镜并将结果绘制到设备。它使用 `skif::` 命名空间的图像滤镜框架。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkCanvas.h | Canvas 接口和常量 |
| include/core/SkImageInfo.h | 图像格式描述 |
| include/core/SkMatrix.h / SkM44.h | 变换矩阵 |
| include/core/SkPaint.h | 绘图属性 |
| include/core/SkSurfaceProps.h | 表面属性 |
| src/core/SkSpecialImage.h | 特殊图像处理 |
| src/core/SkImageFilter_Base.h | 图像滤镜 |
| src/text/GlyphRun.h | 文本字形列表 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkCanvas | 所有绘图命令委托给 Device |
| SkBitmapDevice | CPU 光栅化设备实现 |
| skgpu::ganesh::Device | Ganesh GPU 后端 |
| skgpu::graphite::Device | Graphite GPU 后端 |
| SkPDFDevice | PDF 文档生成 |
| SkRecorder | 命令记录设备 |

## 设计模式与设计决策

### 设计模式

1. **策略模式**: SkDevice 定义统一接口,不同后端实现不同渲染策略
2. **模板方法模式**: 提供默认实现(如 `drawRegion`),子类可选择性覆盖
3. **RAII 模式**: `SkAutoDeviceTransformRestore` 自动恢复变换
4. **空对象模式**: `SkNoPixelsDevice` 作为无操作设备,简化测试和边界计算

### 设计决策

**为何使用三层坐标系统**:
- **灵活性**: 支持非轴对齐的层,允许旋转和透视变换
- **精度**: 避免累积浮点误差,全局坐标可独立于设备坐标
- **优化**: 快速计算设备间相对变换,用于合成

**为何缓存 localToDevice33**:
- 许多操作只需要 3x3 矩阵(2D 变换)
- 避免每次调用 `asM33()` 的转换开销
- 现代 Skia 主要使用 4x4 矩阵,但保留 3x3 接口兼容性

**虚函数设计权衡**:
- 裁剪和绘图函数都是纯虚函数,强制子类实现
- 但提供默认实现的辅助函数(如 `drawDRRect` 调用 `drawPath`)
- 平衡灵活性和易用性

**setImmutable() 接口**:
- 标记设备内容不再改变,允许后端优化(如 GPU 纹理共享)
- 不强制执行,子类根据能力选择性实现

**useDrawCoverageMaskForMaskFilters()**:
- 新的遮罩滤镜渲染路径,使用 Alpha 遮罩和 `drawCoverageMask`
- 逐步替代旧的直接遮罩滤镜处理,提供更统一的实现

## 性能考量

### 优化策略

1. **脏标记**: `fLocalToDeviceDirty` 避免不必要的子类通知
2. **矩阵缓存**: 同时维护 SkM44 和 SkMatrix 形式
3. **快速路径**: 提供默认实现,常见操作无需虚函数调用开销
4. **延迟操作**: SkNoPixelsDevice 的延迟裁剪保存
5. **SIMD 友好**: 坐标变换使用 SkM44,利于向量化

### 性能特征

- **虚函数开销**: 每个绘图调用至少一次虚函数,但相对于实际渲染可忽略
- **坐标变换**: 高频操作,已充分优化(内联、SIMD)
- **内存占用**: 每个设备约 200 字节基础开销,加上像素缓冲区

### 潜在瓶颈

- **层栈深度**: 过多 saveLayer 调用导致设备栈增长,增加内存和合成开销
- **变换更新**: 频繁的 setLocalToDevice 可能触发子类重计算(如 GPU 路径缓存失效)
- **像素访问**: `readPixels`/`writePixels` 可能涉及格式转换和 CPU-GPU 传输

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkCanvas.h | 使用者 | Canvas 将绘图委托给 Device |
| src/core/SkBitmapDevice.h | 子类 | CPU 光栅化实现 |
| include/gpu/ganesh/SkSurfaceGanesh.h | 子类 | Ganesh GPU 设备 |
| include/gpu/graphite/Device.h | 子类 | Graphite GPU 设备 |
| src/pdf/SkPDFDevice.h | 子类 | PDF 矢量输出 |
| src/core/SkSpecialImage.h | 依赖 | 图像滤镜中间结果 |
| src/core/SkImageFilter_Base.h | 依赖 | 图像滤镜应用 |
| src/utils/SkNWayCanvas.h | 使用者 | 多设备广播 Canvas |
