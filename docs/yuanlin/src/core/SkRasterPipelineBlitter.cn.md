# SkRasterPipelineBlitter

> 源文件: src/core/SkRasterPipelineBlitter.cpp

## 概述

`SkRasterPipelineBlitter` 是 Skia 中基于 Raster Pipeline 的 Blitter 实现，负责将着色器输出的像素数据高效地混合写入目标表面。它将着色、颜色过滤、混合和像素存储等操作编译成优化的管道，支持各种像素格式、混合模式和覆盖方式。该 Blitter 是 Skia 现代渲染路径的核心组件，通过动态管道生成和延迟编译技术实现了高性能的像素级操作。

## 架构位置

`SkRasterPipelineBlitter` 位于 Skia 渲染管道的最后阶段：

- **上层调用**: 由 `SkDraw`、`SkScan` 等扫描转换代码调用
- **平级关系**: 与 `SkA8Blitter`、`SkARGB32Blitter` 等其他 Blitter 实现并列
- **下层依赖**: 依赖 `SkRasterPipeline`、着色器（`SkShaderBase`）、混合器（`SkBlender`）、颜色过滤器等
- **特殊角色**: 是唯一能处理任意像素格式和复杂效果的通用 Blitter

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 用途 |
|------|---------|------|
| `SkRasterPipelineBlitter` | 继承自 `SkBlitter` | 基于管道的 Blitter 实现 |
| `EmptyImageGenerator` | 继承自 `SkImageGenerator` | 用于处理图像解码失败的占位符 |

### SkRasterPipelineBlitter 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDst` | `SkPixmap` | 目标像素图 |
| `fAlloc` | `SkArenaAlloc*` | 内存分配器（管道数据存储） |
| `fColorPipeline` | `SkRasterPipeline` | 颜色管道（着色器 + 颜色过滤 + 抖动） |
| `fBlendPipeline` | `SkRasterPipeline` | 混合管道（仅混合逻辑） |
| `fBlendMode` | `std::optional<SkBlendMode>` | 如果混合器是简单模式，存储该模式 |
| `fClipShaderBuffer` | `void*` | 裁剪着色器的 alpha 缓冲区 |
| `fCanDirectBlit` | `bool` | 是否可以使用快速直接填充 |
| `fDirectBlitPaintColor` | `SkColor4f` | 直接填充的颜色 |
| `fDirectBlitValue` | `std::optional<uint64_t>` | 预计算的直接填充值 |
| `fDstPtr` | `MemoryCtx` | 目标内存上下文（指针 + 步长） |
| `fMaskPtr` | `MemoryCtx` | 掩码内存上下文 |
| `fEmbossCtx` | `EmbossCtx` | 3D 掩码浮雕上下文 |
| `fMemset2D` | 函数指针 | memset 优化函数 |
| `fMemsetColor` | `uint64_t` | memset 的颜色值 |
| `fBlitRect` | `std::function<...>` | 编译后的矩形填充函数 |
| `fBlitAntiH` | `std::function<...>` | 编译后的抗锯齿水平线函数 |
| `fBlitMaskA8` | `std::function<...>` | 编译后的 A8 掩码函数 |
| `fBlitMaskLCD16` | `std::function<...>` | 编译后的 LCD 掩码函数 |
| `fBlitMask3D` | `std::function<...>` | 编译后的 3D 掩码函数 |
| `fCurrentCoverage` | `float` | 当前覆盖率（由管道读取） |
| `fDitherRate` | `float` | 抖动率（0.0 = 禁用） |

## 公共 API 函数

### 工厂函数

```cpp
// 主要创建入口
SkBlitter* SkCreateRasterPipelineBlitter(
    const SkPixmap& dst,              // 目标像素图
    const SkPaint& paint,             // 绘制参数
    const SkMatrix& ctm,              // 当前变换矩阵
    SkArenaAlloc* alloc,              // 内存分配器
    sk_sp<SkShader> clipShader,       // 裁剪着色器
    const SkSurfaceProps& props,      // 表面属性
    const SkRect& devBounds           // 设备坐标边界
);

// 可视化调试版本
SkBlitter* SkRasterPipelineVisualizer::CreateBlitter(
    const SkPixmap& output,
    const std::vector<DebugStage>& stages,
    const SkPaint&,
    const SkMatrix& ctm,
    SkArenaAlloc*,
    sk_sp<SkShader> clipShader,
    const SkSurfaceProps& props
);

// 使用预构建着色器管道
SkBlitter* SkCreateRasterPipelineBlitter(
    const SkPixmap& dst,
    const SkPaint& paint,
    const SkRasterPipeline& shaderPipeline,
    bool is_opaque,
    SkArenaAlloc* alloc,
    sk_sp<SkShader> clipShader
);
```

### Blitter 接口实现

```cpp
void blitH(int x, int y, int w) override;
void blitRect(int x, int y, int width, int height) override;
void blitAntiH(int x, int y, const SkAlpha[], const int16_t[]) override;
void blitAntiH2(int x, int y, U8CPU a0, U8CPU a1) override;
void blitAntiV2(int x, int y, U8CPU a0, U8CPU a1) override;
void blitV(int x, int y, int height, SkAlpha alpha) override;
void blitMask(const SkMask&, const SkIRect& clip) override;
std::optional<DirectBlit> canDirectBlit() override;
```

## 内部实现细节

### 管道构建策略

`SkRasterPipelineBlitter` 使用两阶段管道设计：

1. **颜色管道** (`fColorPipeline`):
   - 裁剪着色器（可选）
   - 主着色器
   - 颜色过滤器（可选）
   - 抖动（可选）

2. **混合管道** (`fBlendPipeline`):
   - 仅包含混合逻辑（SrcOver、Multiply 等）

完整管道在首次调用时动态组装：

```cpp
完整 blitRect 管道:
  [颜色管道]
  → clamp_if_normalized
  → load_dst (如果需要混合)
  → [混合管道]
  → clip_lerp (如果有裁剪着色器)
  → store
```

### 延迟编译机制

管道编译是延迟的（lazy）：

```cpp
void SkRasterPipelineBlitter::blitRect(int x, int y, int w, int h) {
    if (!fBlitRect) {  // 首次调用时编译
        SkRasterPipeline p(fAlloc);
        // ... 构建管道 ...
        fBlitRect = p.compile();  // 编译为机器码（JIT）或函数指针
    }
    fBlitRect(x, y, w, h);  // 直接调用编译后的函数
}
```

**优点**：
- 只为实际使用的方法生成代码
- 编译开销分摊到首次调用

### memset 优化路径

对于常量颜色 + Src 模式的简单情况，可以优化为 memset：

```cpp
// 检查条件
if (is_constant && blendMode == SkBlendMode::kSrc &&
    bytesPerPixel <= sizeof(uint64_t)) {

    // 运行管道生成一个像素的值
    SkRasterPipeline_<256> p;
    p.extend(fColorPipeline);
    p.append(SkRasterPipelineOp::store_..., &fMemsetColor);
    p.run(0, 0, 1, 1);

    // 设置 memset 函数
    switch (bytesPerPixel) {
        case 1: fMemset2D = [](SkPixmap* dst, int x, int y, int w, int h, uint64_t c) {
            memset(dst->writable_addr(x, y), c, w);
        }; break;
        case 2: fMemset2D = rect_memset16; break;
        case 4: fMemset2D = rect_memset32; break;
        case 8: fMemset2D = rect_memset64; break;
    }
}
```

### SrcOver 8888 快速路径

针对最常见的情况（SrcOver 混合到 RGBA_8888）有专门优化：

```cpp
if (fBlendMode == SkBlendMode::kSrcOver &&
    fDst.colorType() == kRGBA_8888_SkColorType &&
    !fDst.colorSpace() &&
    fDitherRate == 0.0f) {

    p.append(SkRasterPipelineOp::srcover_rgba_8888, &fDstPtr);
    // 融合了 blend + store，减少内存往返
}
```

### 抖动实现

根据目标格式选择抖动率：

```cpp
switch (dst.colorType()) {
    case kARGB_4444_SkColorType:
        fDitherRate = 1/15.0f;   // 4 位精度
        break;
    case kRGB_565_SkColorType:
        fDitherRate = 1/63.0f;   // 5-6 位精度
        break;
    case kRGBA_8888_SkColorType:
        fDitherRate = 1/255.0f;  // 8 位精度
        break;
    case kRGBA_1010102_SkColorType:
        fDitherRate = 1/1023.0f; // 10 位精度
        break;
    // 浮点格式不抖动
    case kRGBA_F16_SkColorType:
        fDitherRate = 0.0f;
        break;
}

if (fDitherRate > 0.0f) {
    colorPipeline->append(SkRasterPipelineOp::dither, &fDitherRate);
}
```

### 掩码处理

支持三种掩码格式：

1. **A8 掩码** (最常见):
```cpp
p.append(SkRasterPipelineOp::lerp_u8, &fMaskPtr);
```

2. **LCD16 掩码** (子像素抗锯齿):
```cpp
p.append(SkRasterPipelineOp::lerp_565, &fMaskPtr);
// RGB 三个通道独立覆盖
```

3. **3D 掩码** (浮雕效果):
```cpp
p.append(SkRasterPipelineOp::emboss, &fEmbossCtx);
p.append(SkRasterPipelineOp::lerp_u8, &fMaskPtr);
```

### 裁剪着色器集成

裁剪着色器产生 alpha 值，有两种应用方式：

1. **Scale 模式**（预乘覆盖率）:
```cpp
p.append(SkRasterPipelineOp::scale_native, fClipShaderBuffer);
```

2. **Lerp 模式**（后插值）:
```cpp
p.append(SkRasterPipelineOp::lerp_native, fClipShaderBuffer);
```

选择取决于混合模式：

```cpp
if (SkBlendMode_ShouldPreScaleCoverage(blendMode, rgb_coverage)) {
    // 使用 scale
} else {
    // 使用 lerp
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRasterPipeline` | 管道构建和执行 |
| `SkShaderBase` | 着色器接口 |
| `SkBlenderBase` | 混合器接口 |
| `SkColorFilterBase` | 颜色过滤器 |
| `SkColorSpaceXformSteps` | 颜色空间转换 |
| `SkArenaAlloc` | 内存分配 |
| `SkBlendModePriv` | 混合模式私有接口 |
| `SkOpts` | SIMD 优化的 memset |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkDraw` | 选择并使用 Blitter |
| `SkScan` | 扫描转换时调用 Blitter |
| `SkDevice` | 设备层的绘制操作 |

## 设计模式与设计决策

### 1. 延迟编译（Lazy Compilation）

管道仅在首次使用时编译：
- **优点**: 避免为未使用的路径生成代码
- **权衡**: 首次调用有轻微延迟

### 2. 管道分离策略

将颜色生成和混合分离为两个管道：
- **优点**: 可以在不同上下文中重用颜色管道
- **优点**: 简化管道的条件组装逻辑

### 3. 多级优化策略

从快到慢的优化回退：
1. Direct blit（memset）
2. 专用融合操作（`srcover_rgba_8888`）
3. 通用管道

### 4. 工厂方法模式

使用多个 `Create` 静态方法而非构造函数：
- 允许返回 `nullptr` 表示不支持
- 可以在创建时进行复杂的管道构建

### 5. 可选特性组合

使用可选成员变量表示特性：
- `fClipShaderBuffer`: 有裁剪着色器时非空
- `fBlendMode`: 混合器是简单模式时有值
- `fMemset2D`: 可以优化为 memset 时非空

### 6. 函数式编程风格

编译后的管道是纯函数（无副作用），状态通过上下文传递：

```cpp
std::function<void(size_t x, size_t y, size_t w, size_t h)> fBlitRect;
```

## 性能考量

### 1. 管道重用

编译后的管道可以重复调用，分摊编译成本：

```cpp
// 首次调用编译
blitter->blitRect(0, 0, 100, 100);  // 编译 + 执行
// 后续调用直接执行
blitter->blitRect(0, 100, 100, 100); // 仅执行
```

### 2. 内存布局优化

`MemoryCtx` 结构简单（指针 + 步长），缓存友好：

```cpp
struct MemoryCtx {
    void* pixels;  // 8 字节
    int stride;    // 4 字节
};  // 总共 12 字节（对齐到 16）
```

### 3. SIMD 友好的数据流

管道一次处理多个像素（通常 4-16 个），充分利用 SIMD：

```
传统循环:  for (x) { pixel[x] = blend(shader(x), dst[x]); }
管道方式:  process_16_pixels(shader, blend, dst);
```

### 4. 分支消除

使用函数指针而非运行时分支：

```cpp
// 慢：每次 blit 都要判断
void blitRect(...) {
    if (has_clip_shader) {
        // ...
    }
}

// 快：编译时确定
if (has_clip_shader) {
    p.append(clip_op);
}
fBlitRect = p.compile();  // 生成无分支代码
```

### 5. 覆盖率预乘优化

某些混合模式可以预乘覆盖率：

```cpp
// 慢：dst = lerp(dst, blend(src, dst), coverage)
// 快：dst = blend(src * coverage, dst)
```

通过 `SkBlendMode_ShouldPreScaleCoverage` 判断。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkBlitter.h` | 基类 | Blitter 抽象接口 |
| `src/core/SkRasterPipeline.h` | 核心依赖 | 管道系统 |
| `src/core/SkRasterPipelineOpList.h` | 操作定义 | 所有管道操作 |
| `src/core/SkRasterPipelineOpContexts.h` | 上下文定义 | 操作的数据结构 |
| `src/core/SkRasterPipelineVizualizer.h` | 调试工具 | 管道可视化 |
| `src/shaders/SkShaderBase.h` | 依赖 | 着色器基类 |
| `src/core/SkBlenderBase.h` | 依赖 | 混合器基类 |
| `src/effects/colorfilters/SkColorFilterBase.h` | 依赖 | 颜色过滤器基类 |
| `src/core/SkColorSpaceXformSteps.h` | 依赖 | 颜色空间转换 |
| `src/base/SkArenaAlloc.h` | 内存管理 | 快速内存分配器 |

## 典型使用场景

### 场景 1: 简单纯色填充

```cpp
SkPaint paint;
paint.setColor(SK_ColorRED);
paint.setBlendMode(SkBlendMode::kSrc);

// 创建 Blitter
SkBlitter* blitter = SkCreateRasterPipelineBlitter(
    dst, paint, SkMatrix::I(), &alloc, nullptr, props, bounds);

// 由于是常量颜色 + Src 模式，会使用 memset 优化
blitter->blitRect(0, 0, 100, 100);  // 实际执行 memcpy
```

### 场景 2: 带着色器和混合的复杂绘制

```cpp
SkPaint paint;
paint.setShader(SkGradientShader::MakeLinear(...));
paint.setColorFilter(SkColorFilters::Matrix(...));
paint.setBlendMode(SkBlendMode::kMultiply);
paint.setDither(true);

SkBlitter* blitter = SkCreateRasterPipelineBlitter(
    dst, paint, ctm, &alloc, nullptr, props, bounds);

// 完整管道: 渐变 → 颜色矩阵 → 抖动 → load_dst → multiply → store
blitter->blitRect(10, 10, 200, 100);
```

### 场景 3: 抗锯齿边缘

```cpp
uint8_t coverage[] = {0, 64, 128, 192, 255, 192, 128, 64};
int16_t runs[] = {1, 1, 1, 1, 1, 1, 1, 1, 0};

blitter->blitAntiH(x, y, coverage, runs);
// 使用 lerp_u8 应用覆盖率
```

### 场景 4: LCD 文本渲染

```cpp
SkMask mask;
mask.fFormat = SkMask::kLCD16_Format;
// ... 设置掩码数据 ...

blitter->blitMask(mask, clipRect);
// 使用 lerp_565 实现子像素抗锯齿
```

### 场景 5: 带裁剪着色器的绘制

```cpp
auto clipShader = SkShaders::Blend(SkBlendMode::kDstIn,
                                    SkShaders::Color(SK_ColorWHITE),
                                    SkShaders::MakeFractalNoise(...));

SkBlitter* blitter = SkCreateRasterPipelineBlitter(
    dst, paint, ctm, &alloc, clipShader, props, bounds);

// 管道末尾会应用裁剪着色器的 alpha
blitter->blitRect(0, 0, 100, 100);
```
