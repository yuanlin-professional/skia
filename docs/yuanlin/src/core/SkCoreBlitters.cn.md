# SkCoreBlitters

> 源文件
> - src/core/SkCoreBlitters.h

## 概述

`SkCoreBlitters` 是 Skia 光栅化渲染引擎的核心组件,定义了像素级绘制操作(blitting)的类层次结构。Blitter 是"位块传输器"(Bit Block Transfer),负责将几何形状、文本、图像等内容光栅化为像素并写入目标缓冲区,同时处理 Alpha 混合、抗锯齿、着色器等效果。

该头文件定义了多个 Blitter 类,针对不同的像素格式、绘制模式和性能需求进行特化优化。这些类形成了 Skia CPU 渲染的底层引擎,是连接高层绘图 API 和底层像素操作的桥梁。

## 架构位置

`SkCoreBlitters` 位于 Skia 光栅化渲染管线的核心层:

```
Skia Raster Rendering Pipeline
  ├─ High-Level Drawing
  │   └─ SkCanvas, SkDraw
  ├─ Scan Conversion
  │   └─ SkScan (路径扫描线化)
  ├─ Blitting Layer
  │   ├─ SkBlitter (基类,抽象接口)
  │   ├─ SkCoreBlitters ← 当前模块(核心实现)
  │   ├─ SkRasterPipelineBlitter (通用管线)
  │   └─ Platform-Specific Blitters
  └─ Pixel Operations
      ├─ SkBlitRow (行级位块传输)
      └─ SkOpts (SIMD 优化函数)
```

Blitter 将扫描转换的输出转化为实际的像素写入操作。

## 主要类与结构体

### SkRasterBlitter

**继承关系**:
- 基类: `SkBlitter`(纯虚基类)
- 派生类: 所有光栅 Blitter 的共同基类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fDevice | const SkPixmap | 目标设备像素映射(缓冲区+格式信息) |

**核心职责**: 提供对目标像素缓冲区的访问

### SkShaderBlitter

**继承关系**: `SkBlitter` → `SkRasterBlitter` → `SkShaderBlitter`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fShader | sk_sp<SkShader> | 着色器智能指针 |
| fShaderContext | SkShaderBase::Context* | 着色器上下文(遗留接口) |

**核心职责**: 使用着色器(渐变、图案等)填充像素

**析构函数**: 确保 `fShaderContext` 生命周期管理

### SkARGB32_Blitter

**继承关系**: `SkBlitter` → `SkRasterBlitter` → `SkARGB32_Blitter`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fColor | SkColor | 原始颜色值(ARGB) |
| fPMColor | SkPMColor | 预乘后的颜色 |
| fSrcA | SkAlpha | 源 Alpha 值 |

**核心职责**: 在 ARGB32 格式下使用纯色绘制

**优化特点**: 针对常见的 32 位 ARGB 格式优化

**虚函数覆盖**:
```cpp
void blitH(int x, int y, int width) override;
void blitAntiH(int x, int y, const SkAlpha antialias[], const int16_t runs[]) override;
void blitV(int x, int y, int height, SkAlpha alpha) override;
void blitRect(int x, int y, int width, int height) override;
void blitMask(const SkMask&, const SkIRect&) override;
void blitAntiH2(int x, int y, U8CPU a0, U8CPU a1) override;
void blitAntiV2(int x, int y, U8CPU a0, U8CPU a1) override;
```

### SkARGB32_Opaque_Blitter

**继承关系**: `SkBlitter` → `SkRasterBlitter` → `SkARGB32_Blitter` → `SkARGB32_Opaque_Blitter`

**特化条件**: 颜色完全不透明(Alpha = 0xFF)

**优化**:
- 跳过 Alpha 混合计算
- 使用更快的内存填充操作
- 部分函数使用 SIMD 优化

**新增接口**:
```cpp
std::optional<DirectBlit> canDirectBlit() override;
```

支持直接内存写入优化(无需读-改-写)。

### SkARGB32_Black_Blitter

**继承关系**: `SkBlitter` → ... → `SkARGB32_Opaque_Blitter` → `SkARGB32_Black_Blitter`

**特化条件**: 纯黑色(Color = 0xFF000000)

**优化**:
- 黑色抗锯齿更简单(直接设置 Alpha 通道)
- 某些操作等价于 Alpha 遮罩
- 进一步优化的内存填充

### SkARGB32_Shader_Blitter

**继承关系**: `SkBlitter` → `SkRasterBlitter` → `SkShaderBlitter` → `SkARGB32_Shader_Blitter`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fBuffer | SkPMColor* | 临时缓冲区,存储着色器输出 |
| fProc32 | SkBlitRow::Proc32 | 不透明像素的行级混合函数 |
| fProc32Blend | SkBlitRow::Proc32 | 半透明像素的行级混合函数 |
| fShadeDirectlyIntoDevice | bool | 是否可以直接着色到设备 |

**核心职责**:
- 调用着色器生成颜色
- 使用优化的行级混合函数应用到设备
- 支持直接着色优化(避免临时缓冲)

**析构函数**: 释放临时缓冲区

## 公共 API 函数

### SkCreateRasterPipelineBlitter (工厂函数)

```cpp
SkBlitter* SkCreateRasterPipelineBlitter(
    const SkPixmap& device,
    const SkPaint& paint,
    const SkMatrix& ctm,
    SkArenaAlloc* alloc,
    sk_sp<SkShader> clipShader,
    const SkSurfaceProps& props,
    const SkRect& devBounds)
```

创建基于光栅管线(SkRasterPipeline)的通用 Blitter。

**参数**:
- `device`: 目标设备像素映射
- `paint`: 绘制属性(颜色、着色器、混合模式等)
- `ctm`: 当前变换矩阵
- `alloc`: 内存分配器(用于 Blitter 对象和临时缓冲区)
- `clipShader`: 可选的裁剪着色器
- `props`: 表面属性(抖动、像素几何等)
- `devBounds`: 设备空间的绘制边界

**返回值**: 分配在 `alloc` 上的 Blitter 指针

**用途**: 当没有专用优化 Blitter 时使用通用管线

```cpp
SkBlitter* SkCreateRasterPipelineBlitter(
    const SkPixmap& device,
    const SkPaint& paint,
    const SkRasterPipeline& shaderPipeline,
    bool shader_is_opaque,
    SkArenaAlloc* alloc,
    sk_sp<SkShader> clipShader)
```

使用预构建的着色器管线创建 Blitter。

**参数**:
- `shaderPipeline`: 预构建的光栅管线(包含着色和 Paint Alpha 调制)
- `shader_is_opaque`: 着色器输出是否不透明

**优化**: 跳过管线构建步骤,直接使用提供的管线

## 内部实现细节

### Blitter 选择策略

Skia 根据绘制属性自动选择最优 Blitter:

1. **特殊情况优先**:
   - 纯黑色 → `SkARGB32_Black_Blitter`
   - 不透明纯色 → `SkARGB32_Opaque_Blitter`
   - 半透明纯色 → `SkARGB32_Blitter`

2. **着色器路径**:
   - 遗留着色器接口 → `SkARGB32_Shader_Blitter`
   - 现代着色器 → `SkRasterPipelineBlitter`

3. **通用回退**: 所有复杂情况使用 `SkRasterPipelineBlitter`

### 抗锯齿混合算法

`blitAntiH` 处理带覆盖率的像素:

```cpp
void SkARGB32_Blitter::blitAntiH(int x, int y,
                                 const SkAlpha aa[], const int16_t runs[]) {
    uint32_t* device = fDevice.writable_addr32(x, y);
    for (;;) {
        int count = *runs++;
        if (count <= 0) break;

        SkAlpha alpha = *aa++;
        if (alpha == 0) {
            device += count;  // 完全透明,跳过
        } else if (alpha == 255) {
            sk_memset32(device, fPMColor, count);  // 完全覆盖
            device += count;
        } else {
            // 部分覆盖,逐像素混合
            for (int i = 0; i < count; ++i) {
                *device = blend_pixel(fPMColor, *device, alpha);
                device++;
            }
        }
    }
}
```

**RLE 编码**: `runs` 数组压缩连续相同覆盖率的像素

### 行级位块传输优化

`SkARGB32_Shader_Blitter` 使用优化的行函数:

```cpp
void SkARGB32_Shader_Blitter::blitH(int x, int y, int width) {
    SkASSERT(width > 0);
    uint32_t* device = fDevice.writable_addr32(x, y);

    if (fShadeDirectlyIntoDevice) {
        fShaderContext->shadeSpan(x, y, device, width);
    } else {
        fShaderContext->shadeSpan(x, y, fBuffer, width);
        fProc32(device, fBuffer, width, 255);  // 使用 SIMD 优化的混合
    }
}
```

**fProc32**: 指向平台特定的 SIMD 实现(SSE, NEON, AVX 等)

### DirectBlit 优化

当满足以下条件时可使用直接写入:
- 不透明颜色或着色器
- 无混合模式(或 SrcOver + 不透明)
- 完全覆盖(Alpha = 255)

```cpp
std::optional<DirectBlit> SkARGB32_Opaque_Blitter::canDirectBlit() {
    return DirectBlit{fPMColor};
}
```

扫描转换器可直接写入颜色,跳过 Blitter 调用。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkPixmap.h | 目标设备像素映射 |
| include/core/SkPaint.h | 绘制属性 |
| src/core/SkBlitter.h | Blitter 基类 |
| src/core/SkBlitRow.h | 行级混合函数 |
| src/shaders/SkShaderBase.h | 着色器基类和上下文 |
| src/core/SkRasterPipeline.h | 光栅管线框架 |
| include/core/SkColor.h | 颜色类型定义 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| src/core/SkScan.cpp | 扫描转换调用 Blitter |
| src/core/SkDraw.cpp | 高层绘图委托给 Blitter |
| src/core/SkBlitter.cpp | Blitter 选择逻辑 |
| src/effects/ | 效果应用使用 Blitter |

## 设计模式与设计决策

### 设计模式

1. **模板方法模式**: 基类定义接口,子类实现特化逻辑
2. **策略模式**: 不同 Blitter 实现不同的绘制策略
3. **工厂模式**: `SkCreateRasterPipelineBlitter` 创建合适的实例
4. **继承层次优化**: 渐进式特化,共享公共代码

### 设计决策

**为何使用继承而非组合**:
- 性能:虚函数调用比函数指针略快
- 代码共享:公共功能在基类实现
- 类型安全:编译时检查接口完整性

**特化类的必要性**:
- 纯色绘制比着色器快 10-100 倍
- 不透明颜色跳过 Alpha 混合,快 2-3 倍
- 黑色的特殊优化减少计算量

**为何保留遗留着色器接口**:
- 向后兼容性:旧代码依赖 `SkShaderBase::Context`
- 渐进式迁移:新代码使用 SkRasterPipeline
- 性能对比:某些简单着色器旧接口更快

**行级处理的优势**:
- SIMD 友好:连续像素可向量化
- 缓存友好:利用空间局部性
- 减少函数调用:批量处理降低开销

**临时缓冲区的权衡**:
- 优点:解耦着色和混合,灵活性高
- 缺点:额外内存和拷贝开销
- 优化:检测可直接着色的情况,跳过缓冲

## 性能考量

### 优化策略

1. **类型特化**: 为常见格式(ARGB32)和模式(纯色、不透明)专门优化
2. **SIMD 加速**: 使用平台特定的行级混合函数
3. **内联热点**: 小函数内联减少调用开销
4. **直接写入**: 不透明内容跳过读-改-写
5. **RLE 编码**: 压缩抗锯齿覆盖率数据

### 性能特征

| Blitter 类型 | 相对性能 | 适用场景 |
|-------------|---------|----------|
| SkARGB32_Black_Blitter | 最快 | 纯黑色绘制 |
| SkARGB32_Opaque_Blitter | 很快 | 不透明纯色 |
| SkARGB32_Blitter | 快 | 半透明纯色 |
| SkARGB32_Shader_Blitter | 中等 | 简单着色器 |
| SkRasterPipelineBlitter | 慢 | 复杂效果 |

**典型开销**(每像素):
- 纯色不透明:~0.5ns
- 纯色半透明:~2ns
- 着色器:~10-50ns
- 光栅管线:~20-100ns

### 瓶颈分析

- **内存带宽**: 大面积填充受限于 RAM 速度
- **着色器复杂度**: 渐变、图案等计算开销大
- **混合模式**: 非标准混合需要额外计算
- **抗锯齿**: RLE 解码和逐像素混合增加开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkBlitter.h | 基类 | Blitter 抽象接口 |
| src/core/SkBlitter.cpp | 使用者 | Blitter 选择和创建逻辑 |
| src/core/SkBlitRow.h | 依赖 | 行级混合函数接口 |
| src/core/SkRasterPipeline.h | 依赖 | 光栅管线框架 |
| src/core/SkScan.cpp | 使用者 | 扫描转换器 |
| src/opts/SkBlitRow_opts.h | 依赖 | SIMD 优化实现 |
| src/core/SkDraw.cpp | 使用者 | 高层绘图接口 |
