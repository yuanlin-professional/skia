# SkBlitter_Sprite

> 源文件：src/core/SkBlitter_Sprite.cpp

## 概述

`SkBlitter_Sprite` 模块实现了 Skia 中的精灵（Sprite）混合器系统。精灵混合器用于快速绘制未缩放、未旋转的位图（如图标、贴图等），通过专门优化的路径绕过通用光栅化管线，实现显著的性能提升。

核心组件：
- `SkSpriteBlitter` 基类：定义精灵混合器接口
- `SkSpriteBlitter_Memcpy`：直接内存拷贝优化
- `SkRasterPipelineSpriteBlitter`：通用光栅管线回退
- `SkBlitter::ChooseSprite()`：智能选择最优混合器

## 架构位置

```
SkCanvas::drawBitmap()
  └── SkDraw::drawBitmap()
        └── SkBlitter::ChooseSprite()  (快速路径判断)
              ├── SkSpriteBlitter_Memcpy (最快)
              ├── SkSpriteBlitter_L32 (RGBA/BGRA 优化)
              └── SkRasterPipelineSpriteBlitter (通用回退)
```

精灵混合器是位图绘制的性能关键路径，仅在满足特定条件时启用。

## 主要类与结构体

### 1. SkSpriteBlitter（基类）

**继承关系：**`SkBlitter`

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| fSource | SkPixmap | 源位图数据 |
| fDst | SkPixmap | 目标位图数据 |
| fLeft | int | 绘制起始 X 坐标 |
| fTop | int | 绘制起始 Y 坐标 |
| fPaint | const SkPaint* | 绘制属性 |

**核心方法：**

| 方法 | 说明 |
|------|------|
| `setup()` | 初始化混合器状态 |
| `blitRect()` | 绘制矩形区域 |

### 2. SkSpriteBlitter_Memcpy

**功能：**直接内存拷贝优化，最快路径。

**适用条件：**
- 源和目标颜色类型相同
- 无颜色空间转换
- 无滤镜（遮罩、颜色、图像滤镜）
- Alpha = 255
- 混合模式为 `kSrc` 或 `kSrcOver`（且源不透明）

**性能：**比通用路径快 10~100 倍。

### 3. SkRasterPipelineSpriteBlitter

**功能：**使用光栅管线的通用实现，处理复杂颜色转换。

**支持特性：**
- 色彩空间转换
- Alpha-only 图像（颜色来自画笔）
- 透明度混合
- Clip 着色器

## 公共 API 函数

### 1. 选择精灵混合器

```cpp
SkBlitter* SkBlitter::ChooseSprite(const SkPixmap& dst,
                                   const SkPaint& paint,
                                   const SkPixmap& source,
                                   int left, int top,
                                   SkArenaAlloc* alloc,
                                   sk_sp<SkShader> clipShader)
```

**参数：**
- `dst`: 目标位图
- `paint`: 绘制属性
- `source`: 源位图
- `left, top`: 绘制位置
- `alloc`: 内存分配器
- `clipShader`: 裁剪着色器（可选）

**返回值：**
- 成功：专用混合器指针
- 失败：`nullptr`（调用者应回退到着色器路径）

**判断逻辑：**
```
如果 (未预乘 || 强制光栅管线 || 有遮罩滤镜):
    返回 nullptr
否则:
    尝试 Memcpy -> L32 优化 -> 光栅管线
```

### 2. 基类接口

```cpp
bool SkSpriteBlitter::setup(const SkPixmap& dst, int left, int top,
                             const SkPaint& paint)
```

**功能：**初始化混合器状态，存储绘制参数。

**返回值：**始终返回 `true`（当前实现）。

## 内部实现细节

### 1. Memcpy 优化实现

```cpp
void SkSpriteBlitter_Memcpy::blitRect(int x, int y, int width, int height) {
    char* dst = (char*)fDst.writable_addr(x, y);
    const char* src = (const char*)fSource.addr(x - fLeft, y - fTop);
    const size_t dstRB = fDst.rowBytes();
    const size_t srcRB = fSource.rowBytes();
    const size_t bytesToCopy = width << fSource.shiftPerPixel();

    while (height --> 0) {
        memcpy(dst, src, bytesToCopy);
        dst += dstRB;
        src += srcRB;
    }
}
```

**关键优化：**
- 直接 `memcpy` 逐行拷贝
- 计算字节数时使用位移而非乘法
- 指针递增优化循环

### 2. 光栅管线精灵混合器

```cpp
class SkRasterPipelineSpriteBlitter : public SkSpriteBlitter {
    bool setup(const SkPixmap& dst, int left, int top, const SkPaint& paint) override {
        SkRasterPipeline p(fAlloc);
        p.appendLoad(fSource.colorType(), &fSrcPtr);

        // Alpha-only 图像：使用画笔颜色
        if (SkColorTypeIsAlphaOnly(fSource.colorType())) {
            p.appendSetRGB(fAlloc, fPaintColor);
            p.append(SkRasterPipelineOp::premul);
        }

        // 色彩空间转换
        if (auto dstCS = fDst.colorSpace()) {
            auto srcCS = fSource.colorSpace() ?: sk_srgb_singleton();
            SkColorSpaceXformSteps(...).apply(&p);
        }

        // 透明度缩放
        if (fPaintColor.fA != 1.0f) {
            p.append(SkRasterPipelineOp::scale_1_float, &fPaintColor.fA);
        }

        // 创建最终混合器
        fBlitter = SkCreateRasterPipelineBlitter(fDst, paint, p, is_opaque, fAlloc, fClipShader);
        return fBlitter != nullptr;
    }
};
```

**管线阶段：**
1. 加载源像素
2. Alpha-only 处理（如果需要）
3. 色彩空间转换
4. 透明度缩放
5. 混合到目标

### 3. 源指针计算技巧

```cpp
size_t bpp = fSource.info().bytesPerPixel();
fSrcPtr.pixels = (char*)fSource.writable_addr(-fLeft+x, -fTop+y)
                 - bpp * x
                 - bpp * y * fSrcPtr.stride;
```

**目的：**使光栅管线可以从任意坐标 `(x, y)` 开始读取，而无需每次重新计算偏移。

### 4. 未实现的混合器方法

```cpp
void SkSpriteBlitter::blitH(int x, int y, int width) {
    SkDEBUGFAIL("how did we get here?");
    this->blitRect(x, y, width, 1);  // 回退到 blitRect
}
```

精灵混合器仅实现 `blitRect()`，其他方法不应被调用（由 `SkDraw` 保证）。

### 5. 色彩空间处理

```cpp
auto srcCS = fSource.colorSpace();
if (!srcCS || SkColorTypeIsAlphaOnly(fSource.colorType())) {
    srcCS = sk_srgb_singleton();  // 默认为 sRGB
}
```

未标记的图像和 Alpha-only 图像统一视为 sRGB。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkBlitter` | 基类接口 |
| `SkPixmap` | 位图数据抽象 |
| `SkRasterPipeline` | 像素处理管线 |
| `SkColorSpaceXformSteps` | 色彩空间转换 |
| `SkArenaAlloc` | 内存分配 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `SkDraw` | 调用 `ChooseSprite()` |
| `SkCanvas` | 通过 `SkDraw` 间接使用 |

## 设计模式与设计决策

### 1. 策略模式

不同混合器实现相同接口，运行时选择最优策略：

```cpp
if (SkSpriteBlitter_Memcpy::Supports(...))
    blitter = alloc->make<SkSpriteBlitter_Memcpy>(...);
else if (...)
    blitter = ChooseL32(...);
else
    blitter = alloc->make<SkRasterPipelineSpriteBlitter>(...);
```

### 2. 工厂方法模式

`ChooseSprite()` 根据条件选择混合器类型。

### 3. 模板方法模式

`SkSpriteBlitter` 定义 `blitRect()` 框架，子类实现具体算法。

### 4. 快速失败原则

```cpp
if (source.alphaType() == kUnpremul_SkAlphaType) {
    return nullptr;  // 尽早拒绝不支持的格式
}
```

### 5. Arena 分配策略

所有混合器在 `SkArenaAlloc` 上分配，批量释放，避免逐个析构开销。

## 性能考量

### 1. 性能对比（相对通用路径）

| 混合器 | 相对性能 | 适用场景 |
|--------|---------|---------|
| Memcpy | 100× | 相同格式、无混合 |
| L32 优化 | 10-50× | RGBA/BGRA 混合 |
| 光栅管线 | 2-10× | 色彩空间转换 |
| 通用路径 | 1× | 着色器、滤镜等 |

### 2. Memcpy 优化的关键

```cpp
memcpy(dst, src, bytesToCopy);  // CPU 高度优化的内存拷贝
```

现代 CPU 对 `memcpy` 优化极佳（SIMD、预取、流式写入）。

### 3. 内存访问模式

**扫描线顺序：**精灵混合器按行处理，充分利用缓存局部性。

**预取：**虽然代码中无显式预取，但硬件预取器可识别连续访问模式。

### 4. 光栅管线开销

```
管线构建: ~100-500 ns
执行: ~每像素 2-10 ns
```

管线构建是一次性成本，大图像时可摊销。

### 5. 性能陷阱

**未对齐访问：**虽然 `memcpy` 可处理，但对齐的行字节数更快。

**小矩形：**设置开销相对较大，建议批量绘制。

**色彩空间转换：**即使在精灵路径中，也可能显著影响性能。

## 相关文件

| 文件 | 关系 | 说明 |
|-----|------|------|
| src/core/SkBlitter.h | 基类 | 混合器接口 |
| src/core/SkCoreBlitters.h | 平级优化 | L32 等优化混合器 |
| src/core/SkRasterPipeline.h | 管线实现 | 像素处理管线 |
| src/core/SkDraw.cpp | 调用者 | 位图绘制路径 |
| include/core/SkPixmap.h | 数据类型 | 位图抽象 |
| include/core/SkPaint.h | 绘制属性 | 画笔配置 |
