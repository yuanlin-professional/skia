# SkShaderMaskFilter

> 源文件: `include/effects/SkShaderMaskFilter.h`

## 概述

`SkShaderMaskFilter` 是 Skia 图形库中的一个遮罩滤镜工厂类，用于将 `SkShader`（着色器）转换为 `SkMaskFilter`（遮罩滤镜）。该滤镜使用着色器生成的 Alpha 值来调制绘制操作的遮罩，从而实现基于着色器图案的遮罩效果。

> **已弃用（DEPRECATED）**: 该类已被标记为弃用。根据头文件中的注释，`ShaderMaskFilter` 将在未来的 Skia 版本中被完全移除。开发者应避免在新代码中使用此 API，并计划迁移现有使用该 API 的代码。

典型的应用场景包括：使用渐变着色器创建渐变透明遮罩、使用噪声着色器创建不规则边缘效果等。通过此类，可以使用任意着色器的输出作为遮罩来控制绘制内容的透明度。

## 架构位置

`SkShaderMaskFilter` 位于 Skia 的 effects 层，连接了着色器（Shader）和遮罩滤镜（MaskFilter）两个子系统：

```
应用层
  │
  ▼
┌──────────────────────────────────────────────┐
│  include/effects/SkShaderMaskFilter.h         │  ◄── 公共 API（本文件，已弃用）
│  class SkShaderMaskFilter                     │
│    └── Make(sk_sp<SkShader>)                  │
└───────────────────────┬──────────────────────┘
                        │ 创建
                        ▼
┌──────────────────────────────────────────────┐
│  src/effects/SkShaderMaskFilterImpl.h/.cpp    │  ◄── 内部实现
│  class SkShaderMaskFilterImpl                 │
│    : public SkMaskFilterBase                  │
│    ├── filterMask()   遮罩过滤逻辑            │
│    ├── asImageFilter() 转换为图像滤镜         │
│    └── fShader        内部持有的着色器        │
└───────────────────────┬──────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    SkShader       SkMaskFilter   SkImageFilter
   (输入着色器)   (遮罩滤镜接口) (可转换为图像滤镜)
```

在 Skia 的遮罩处理流程中，`SkMaskFilter` 作用于绘制形状的 Alpha 遮罩。`SkShaderMaskFilter` 通过将着色器渲染到位图上，然后与原始遮罩进行逐像素的 Alpha 混合来实现遮罩调制。

- **上游调用者**: 需要基于着色器生成遮罩效果的应用代码（如渐变遮罩、图案遮罩等）。
- **下游依赖**: `SkMaskFilter`（遮罩滤镜基类）、`SkShader`（着色器基类）、`SkImageFilter`（图像滤镜，用于 GPU 路径优化）。

## 主要类与结构体

### `SkShaderMaskFilter` 类（公共 API）

```cpp
class SK_API SkShaderMaskFilter {
public:
    static sk_sp<SkMaskFilter> Make(sk_sp<SkShader> shader);

private:
    static void RegisterFlattenables();
    friend class SkFlattenable;
};
```

| 成员 | 访问级别 | 类型 | 说明 |
|------|----------|------|------|
| `Make()` | public | 静态工厂方法 | 从着色器创建遮罩滤镜 |
| `RegisterFlattenables()` | private | 静态方法 | 注册序列化/反序列化支持 |

### 内部实现类 `SkShaderMaskFilterImpl`

该类定义于 `src/effects/SkShaderMaskFilterImpl.h`，继承自 `SkMaskFilterBase`：

```cpp
class SkShaderMaskFilterImpl : public SkMaskFilterBase {
public:
    explicit SkShaderMaskFilterImpl(sk_sp<SkShader> shader);

    SkMask::Format getFormat() const override;   // 返回 kA8_Format
    Type type() const override;                   // 返回 Type::kShader
    bool filterMask(...) const override;          // 核心遮罩过滤逻辑
    std::pair<sk_sp<SkImageFilter>, bool>
        asImageFilter(...) const override;        // 转换为图像滤镜
    void computeFastBounds(...) const override;   // 边界计算（不扩展）
    bool asABlur(BlurRec*) const override;        // 始终返回 false

private:
    sk_sp<SkShader> fShader;  // 内部持有的着色器
};
```

| 成员 | 类型 | 说明 |
|------|------|------|
| `fShader` | `sk_sp<SkShader>` | 用于生成遮罩的着色器 |
| `filterMask()` | 虚方法 | 将着色器渲染结果应用于 A8 格式遮罩 |
| `asImageFilter()` | 虚方法 | 将遮罩滤镜转换为等价的图像滤镜 |
| `getFormat()` | 虚方法 | 返回 `SkMask::kA8_Format` |
| `computeFastBounds()` | 虚方法 | 快速边界计算（直接复制输入边界，不扩展） |
| `asABlur()` | 虚方法 | 始终返回 `false`（该滤镜不是模糊类型） |

## 公共 API 函数

### `SkShaderMaskFilter::Make()`

```cpp
static sk_sp<SkMaskFilter> Make(sk_sp<SkShader> shader);
```

**功能**: 将一个着色器包装为遮罩滤镜。着色器生成的 Alpha 值将用于调制绘制操作的遮罩。

**参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `shader` | `sk_sp<SkShader>` | 用于生成遮罩图案的着色器，不可为 nullptr |

**返回值**: `sk_sp<SkMaskFilter>` -- 遮罩滤镜对象。如果 `shader` 为 nullptr，返回 nullptr。

**使用示例**（已弃用，仅供参考）:

```cpp
#include "include/effects/SkShaderMaskFilter.h"
#include "include/effects/SkGradientShader.h"
#include "include/core/SkPaint.h"

// 创建一个径向渐变着色器作为遮罩
SkPoint center = SkPoint::Make(100, 100);
SkColor colors[] = { SK_ColorWHITE, SK_ColorTRANSPARENT };
auto gradientShader = SkGradientShader::MakeRadial(
    center, 100.0f, colors, nullptr, 2, SkTileMode::kClamp
);

// 将着色器包装为遮罩滤镜
SkPaint paint;
paint.setMaskFilter(SkShaderMaskFilter::Make(gradientShader));
paint.setColor(SK_ColorBLUE);
canvas->drawRect(SkRect::MakeXYWH(0, 0, 200, 200), paint);
```

此示例会绘制一个蓝色矩形，其 Alpha 值由径向渐变调制，产生从中心向外渐隐的效果。

## 内部实现细节

### Make() 工厂方法

```cpp
sk_sp<SkMaskFilter> SkShaderMaskFilter::Make(sk_sp<SkShader> shader) {
    return shader ? sk_sp<SkMaskFilter>(
        new SkShaderMaskFilterImpl(std::move(shader))) : nullptr;
}
```

实现非常简洁：验证着色器非空后，创建一个 `SkShaderMaskFilterImpl` 实例并用 `sk_sp` 包装返回。

### filterMask() 遮罩过滤

`filterMask()` 方法是核心遮罩处理逻辑，位于 `src/effects/SkShaderMaskFilterImpl.cpp`：

1. **格式检查**: 仅支持 `SkMask::kA8_Format`（8 位 Alpha 格式）的输入遮罩，其他格式直接返回 `false`
2. **位图渲染**: 创建一个与遮罩同尺寸的位图，将着色器渲染到位图上
3. **Alpha 提取**: 从渲染结果中提取 Alpha 通道值
4. **逐像素调制**: 使用辅助函数 `rect_memcpy` 将着色器的 Alpha 值与原始遮罩的 Alpha 值逐像素相乘
5. **结果输出**: 将调制后的 Alpha 数据写入目标遮罩

### 图像滤镜转换

`asImageFilter()` 方法可以将遮罩滤镜转换为等价的 `SkImageFilter`，这在 GPU 渲染路径中非常有用，因为图像滤镜可以更高效地在 GPU 上执行，避免了 CPU 位图渲染的开销。

### 序列化支持

通过 `RegisterFlattenables()` 注册 `SkShaderMaskFilterImpl` 的序列化处理程序：

```cpp
void SkShaderMaskFilter::RegisterFlattenables() {
    SK_REGISTER_FLATTENABLE(SkShaderMaskFilterImpl)
}
```

这使得该滤镜可以被保存到 `SkPicture` 中并在之后还原。序列化时会将内部着色器作为 `SkFlattenable` 对象写入缓冲区，反序列化时通过 `buffer.readShader()` 还原。

## 依赖关系

### 直接依赖

| 依赖文件 | 用途 |
|----------|------|
| `include/core/SkRefCnt.h` | 提供 `sk_sp` 智能指针 |
| `include/core/SkTypes.h` | 提供 `SK_API` 导出宏 |
| `SkMaskFilter` (前向声明) | 工厂方法的返回类型 |
| `SkShader` (前向声明) | 工厂方法的参数类型 |

### 实现依赖

| 依赖文件 | 用途 |
|----------|------|
| `src/effects/SkShaderMaskFilterImpl.h` | 内部实现类声明 |
| `src/effects/SkShaderMaskFilterImpl.cpp` | 遮罩过滤核心逻辑实现 |
| `src/core/SkMaskFilterBase.h` | 遮罩滤镜基类 |
| `src/core/SkMask.h` | 遮罩数据结构定义 |
| `include/core/SkCanvas.h` | 内部用于将着色器渲染到位图 |
| `include/effects/SkImageFilters.h` | 用于 `asImageFilter()` 转换 |

### 被依赖关系

- `src/ports/SkGlobalInitialization_default.cpp` -- 全局初始化中注册序列化支持
- `src/gpu/ganesh/GrFragmentProcessors.cpp` -- Ganesh GPU 后端的片段处理器转换

## 设计模式与设计决策

### 桥接模式

`SkShaderMaskFilter` 实现了着色器和遮罩滤镜之间的桥接。着色器通常用于定义颜色和纹理，而遮罩滤镜用于修改绘制形状的 Alpha 遮罩。该类将着色器的输出（具体是 Alpha 通道）"桥接"到遮罩滤镜的输入。

### 工厂模式

与 Skia 中其他效果类一致，使用静态工厂方法 `Make()` 并返回基类智能指针。这种设计隐藏了内部实现类 `SkShaderMaskFilterImpl`，使得调用方仅依赖 `SkMaskFilter` 基类接口。

### 弃用策略

该类被标记为弃用（DEPRECATED），原因可能包括：
- 遮罩滤镜子系统整体正在被简化或重构
- 着色器遮罩的功能可以通过其他更通用的机制（如 `SkRuntimeEffect` 或混合模式）实现
- `filterMask()` 中基于位图的实现在 GPU 渲染路径中效率不高

头文件注释明确说明："ShaderMaskFilters will be deleted entirely in an upcoming Skia release"。

### Flattenable 注册机制

`RegisterFlattenables()` 是 Skia 序列化框架的一部分。通过 `friend class SkFlattenable` 声明和私有注册方法，确保序列化机制可以访问内部实现，同时不暴露给外部用户。在 `src/ports/SkGlobalInitialization_default.cpp` 中统一进行注册调用。

## 性能考量

- **CPU 瓶颈**: `filterMask()` 的实现涉及将着色器渲染到临时位图中，然后逐像素读取 Alpha 值。对于大面积遮罩区域，这可能成为性能瓶颈
- **内存分配**: 每次遮罩过滤都需要分配临时位图（与遮罩同尺寸），增加了内存分配开销和 GC 压力
- **GPU 路径优化**: 通过 `asImageFilter()` 转换为图像滤镜后，可以在 GPU 上更高效地执行，避免 CPU 回读
- **边界不扩展**: `computeFastBounds()` 直接将输入边界复制为输出边界（`*dst = src`），不引入额外的边界扩展，避免不必要的像素处理
- **仅支持 A8 格式**: `filterMask()` 仅处理 8 位 Alpha 格式的遮罩，对其他格式直接返回失败，避免了不必要的格式转换开销
- **弃用考量**: 鉴于该 API 已被弃用，不建议在性能敏感的新代码中使用此类。应考虑使用 `SkRuntimeEffect` 或图像滤镜组合等替代方案

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/effects/SkShaderMaskFilter.h` | 本文件，公共 API 声明（已弃用） |
| `src/effects/SkShaderMaskFilterImpl.h` | 内部实现类声明 |
| `src/effects/SkShaderMaskFilterImpl.cpp` | 遮罩过滤核心逻辑实现 |
| `src/core/SkMaskFilterBase.h` | 遮罩滤镜基类 |
| `src/core/SkMask.h` | 遮罩数据结构 |
| `include/core/SkMaskFilter.h` | `SkMaskFilter` 公共接口 |
| `include/core/SkShader.h` | `SkShader` 公共接口 |
| `include/core/SkFlattenable.h` | 序列化框架基类 |
| `src/gpu/ganesh/GrFragmentProcessors.cpp` | Ganesh GPU 后端集成 |
| `src/ports/SkGlobalInitialization_default.cpp` | 全局序列化注册 |
