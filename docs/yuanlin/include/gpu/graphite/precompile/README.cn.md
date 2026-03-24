# include/gpu/graphite/precompile - Graphite 管线预编译框架

## 概述

`include/gpu/graphite/precompile` 目录包含 Graphite 渲染引擎的管线预编译（Precompilation）
框架。管线预编译是 Graphite 的一个重要特性，允许客户端在实际绘制之前提前创建 GPU 渲染管线，
从而避免在绘制时因即时编译（JIT compilation）导致的性能抖动。

预编译的核心思想是：客户端通过 `PaintOptions` 描述预期的绘制操作集合（包括着色器、混合器、
颜色滤镜、图像滤镜、遮罩滤镜的各种组合），结合 `RenderPassProperties`（描述渲染通道属性
如颜色类型、MSAA 等）和 `DrawTypeFlags`（描述绘制图元类型），调用 `Precompile()` 函数
生成所有可能的管线组合。

`PaintOptions` 是 `SkPaint` 的预编译模拟。它不关心具体的颜色值等绘制细节，只关心影响
管线编译的结构性属性。例如，两个不同颜色但相同着色器类型的绘制会使用同一个管线。

`PrecompileBase` 是所有可附加到 `PaintOptions` 的预编译对象的基类，其子类包括
`PrecompileShader`、`PrecompileBlender`、`PrecompileColorFilter`、
`PrecompileImageFilter` 和 `PrecompileMaskFilter`。每个子类提供了丰富的工厂方法，
对应 Skia 中各种 Effect 的预编译版本。

预编译可以在后台线程上执行。客户端通过 `Context::makePrecompileContext()` 获取一个线程安全
的 `PrecompileContext`，然后在任意线程上调用 `Precompile()` 函数。

## 架构图

```
include/gpu/graphite/precompile/
    |
    +-- Precompile.h               <-- 预编译入口函数
    |       |
    |       +-- Precompile()           (核心预编译函数)
    |       +-- RenderPassProperties   (渲染通道属性)
    |
    +-- PaintOptions.h             <-- SkPaint 的预编译模拟
    |       |
    |       +-- setShaders()
    |       +-- setColorFilters()
    |       +-- setBlenders()
    |       +-- setImageFilters()
    |       +-- setMaskFilters()
    |
    +-- PrecompileBase.h           <-- 预编译对象基类
    |       |
    |       +-- Type 枚举 (Blender, ColorFilter, ImageFilter, MaskFilter, Shader)
    |
    +-- PrecompileShader.h         <-- 预编译着色器
    +-- PrecompileBlender.h        <-- 预编译混合器
    +-- PrecompileColorFilter.h    <-- 预编译颜色滤镜
    +-- PrecompileImageFilter.h    <-- 预编译图像滤镜
    +-- PrecompileMaskFilter.h     <-- 预编译遮罩滤镜
    +-- PrecompileRuntimeEffect.h  <-- 预编译运行时效果
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `Precompile.h` | `Precompile()` 函数和 `RenderPassProperties` 结构体 |
| `PaintOptions.h` | `PaintOptions` - SkPaint 的预编译版本 |
| `PrecompileBase.h` | `PrecompileBase` - 所有预编译对象的基类 |
| `PrecompileShader.h` | `PrecompileShaders` 命名空间 - 各种着色器预编译工厂 |
| `PrecompileBlender.h` | `PrecompileBlenders` 命名空间 - 混合器预编译工厂 |
| `PrecompileColorFilter.h` | `PrecompileColorFilters` 命名空间 - 颜色滤镜预编译工厂 |
| `PrecompileImageFilter.h` | `PrecompileImageFilters` 命名空间 - 图像滤镜预编译工厂 |
| `PrecompileMaskFilter.h` | `PrecompileMaskFilters` 命名空间 - 遮罩滤镜预编译工厂 |
| `PrecompileRuntimeEffect.h` | 运行时效果（SkRuntimeEffect）的预编译支持 |

## 关键类与函数

### `Precompile()` 函数

```cpp
void Precompile(PrecompileContext* precompileContext,
                const PaintOptions& paintOptions,
                DrawTypeFlags drawTypes,
                SkSpan<const RenderPassProperties> renderPassProperties);
```

核心预编译入口。组合 paintOptions 中的所有选项和渲染通道属性，生成并编译所有可能的管线。

### `RenderPassProperties` 结构体

```cpp
struct RenderPassProperties {
    DepthStencilFlags   fDSFlags;       // 深度/模板标志
    SkColorType         fDstCT;          // 目标颜色类型
    sk_sp<SkColorSpace> fDstCS;          // 目标颜色空间
    bool                fRequiresMSAA;   // 是否需要 MSAA
};
```

### `PaintOptions` 类

```cpp
class PaintOptions {
    void setShaders(SkSpan<const sk_sp<PrecompileShader>>);
    void setColorFilters(SkSpan<const sk_sp<PrecompileColorFilter>>);
    void setBlenders(SkSpan<const sk_sp<PrecompileBlender>>);
    void setImageFilters(SkSpan<const sk_sp<PrecompileImageFilter>>);
    void setMaskFilters(SkSpan<const sk_sp<PrecompileMaskFilter>>);
    void setBlendModes(SkSpan<const SkBlendMode>);
    void setDither(bool);
    void setClipShaders(SkSpan<const sk_sp<PrecompileShader>>);
};
```

如果 PaintOptions 有 2 个着色器选项和 2 个混合器选项，则会预编译 2x2=4 种管线组合。

### `PrecompileBase` 基类

```cpp
class PrecompileBase : public SkRefCnt {
    enum class Type { kBlender, kColorFilter, kImageFilter, kMaskFilter, kShader };
    Type type() const;
    int numCombinations() const;  // 此对象及其子项的组合总数
};
```

### `PrecompileShaders` 命名空间（部分工厂方法）

```cpp
namespace PrecompileShaders {
    sk_sp<PrecompileShader> Color();
    sk_sp<PrecompileShader> Blend(SkSpan<const SkBlendMode>, ...);
    sk_sp<PrecompileShader> Image(ImageShaderFlags = kAll, ...);
    sk_sp<PrecompileShader> LinearGradient();
    sk_sp<PrecompileShader> RadialGradient();
    sk_sp<PrecompileShader> SweepGradient();
    sk_sp<PrecompileShader> ConicalGradient();
    sk_sp<PrecompileShader> LocalMatrix(SkSpan<const sk_sp<PrecompileShader>>);
    sk_sp<PrecompileShader> ColorFilter(SkSpan<const sk_sp<PrecompileShader>>, ...);
    sk_sp<PrecompileShader> Blur();
    sk_sp<PrecompileShader> YUVImage(ImageShaderFlags = kAll, ...);
    // ... 更多
}
```

### `PrecompileColorFilters` 命名空间（部分工厂方法）

```cpp
namespace PrecompileColorFilters {
    sk_sp<PrecompileColorFilter> Matrix();
    sk_sp<PrecompileColorFilter> Blend();
    sk_sp<PrecompileColorFilter> HSLAMatrix();
    sk_sp<PrecompileColorFilter> Lighting();
    sk_sp<PrecompileColorFilter> Compose(SkSpan<const sk_sp<PrecompileColorFilter>>, ...);
}
```

## 依赖关系

- **上游依赖**: `include/gpu/graphite/GraphiteTypes.h`, `include/gpu/graphite/PrecompileContext.h`
- **上游依赖**: `include/core/SkRefCnt.h`, `include/core/SkBlendMode.h`
- **下游扩展**: `include/gpu/graphite/vk/precompile/` (Vulkan 特有预编译着色器)
- **实现代码**: `src/gpu/graphite/precompile/`

## 相关文档与参考

- `include/gpu/graphite/` - Graphite 引擎主目录
- `include/gpu/graphite/PrecompileContext.h` - 预编译上下文
- `include/gpu/graphite/vk/precompile/` - Vulkan YCbCr 预编译着色器
- Skia 预编译文档: https://skia.org/docs/user/api/
