# GrDstProxyView — 目标纹理代理视图

> 源文件: `src/gpu/ganesh/GrDstProxyView.h`

## 概述

`GrDstProxyView` 封装了一个包含目标像素值的纹理代理视图及其从设备空间到纹理空间的整数坐标偏移。当 GPU 不支持 framebuffer fetch（帧缓冲读取）功能时，需要通过此类将当前渲染目标的内容复制到纹理中，以便在片段着色器或混合处理器 (XferProcessor) 中实现复杂混合效果。

## 架构位置

```
渲染管线
    └── GrOpsTask (操作任务)
        └── GrPipeline (渲染管线状态)
            └── GrDstProxyView (本文件 - 目标纹理视图)
                ├── GrSurfaceProxyView (纹理代理视图)
                └── GrXferProcessor (混合处理器)
```

`GrDstProxyView` 在 `GrPipeline` 中持有，用于在需要目标像素值参与混合计算时提供源数据。

## 主要类与结构体

### GrDstProxyView

值类型类，包含以下成员：

| 成员 | 类型 | 描述 |
|------|------|------|
| `fProxyView` | `GrSurfaceProxyView` | 纹理代理视图，指向包含目标像素的纹理 |
| `fOffset` | `SkIPoint` | 设备空间到纹理空间的整数偏移，默认为 `{0, 0}` |
| `fDstSampleFlags` | `GrDstSampleFlags` | 目标采样标志，默认为 `kNone` |

该类声明了 `sk_is_trivially_relocatable = std::true_type`，并通过 `static_assert` 验证所有成员均可平凡重定位，这允许在容器如 `SkTArray` 中使用高效的内存移动操作。

## 公共 API 函数

| 方法 | 签名 | 描述 |
|------|------|------|
| 默认构造 | `GrDstProxyView()` | 构造空视图 |
| 拷贝构造 | `GrDstProxyView(const GrDstProxyView&)` | 复制所有成员 |
| 赋值运算符 | `operator=` | 复制 proxyView、offset 和 sampleFlags |
| 相等比较 | `operator==` / `operator!=` | 比较所有三个成员 |
| `offset()` | `const SkIPoint&` | 返回纹理偏移量 |
| `setOffset()` | `void(const SkIPoint&)` 或 `void(int, int)` | 设置纹理偏移量 |
| `proxy()` | `GrSurfaceProxy*` | 获取底层表面代理指针 |
| `proxyView()` | `const GrSurfaceProxyView&` | 获取完整代理视图引用 |
| `setProxyView()` | `void(GrSurfaceProxyView)` | 设置代理视图，若为空则重置偏移 |
| `dstSampleFlags()` | `GrDstSampleFlags` | 获取目标采样标志 |
| `setDstSampleFlags()` | `void(GrDstSampleFlags)` | 设置目标采样标志 |

## 内部实现细节

1. **偏移自动重置**: 在 `setProxyView()` 中，若新设置的代理视图不包含有效代理（`proxy()` 返回 null），偏移量自动重置为 `{0, 0}`，避免悬挂偏移值。

2. **值语义**: 类实现了完整的拷贝构造和赋值语义。拷贝构造函数委托给赋值运算符实现。

3. **平凡可重定位**: 通过 trait 和 static_assert 确保类型可以安全地通过 `memcpy` 移动，这是 Skia 内部容器优化的关键。

## 依赖关系

- **`include/core/SkPoint.h`**: `SkIPoint` 整数坐标类型
- **`src/gpu/ganesh/GrSurfaceProxyView.h`**: 纹理代理视图
- **`include/private/gpu/ganesh/GrTypesPriv.h`**: `GrDstSampleFlags` 枚举
- **`include/private/base/SkTypeTraits.h`**: `sk_is_trivially_relocatable` trait

## 设计模式与设计决策

1. **数据传输对象 (DTO)**: `GrDstProxyView` 是一个简单的数据容器，将相关联的三个属性（代理视图、偏移、采样标志）打包在一起传递，减少函数参数数量。

2. **framebuffer fetch 替代方案**: 在不支持 `GL_EXT_shader_framebuffer_fetch` 或类似扩展的 GPU 上，需要先将目标内容读回纹理，再在着色器中采样该纹理实现混合。`GrDstProxyView` 就是这一机制的数据载体。

3. **偏移设计**: 偏移量支持目标纹理只复制渲染目标的局部区域，减少不必要的纹理拷贝和内存使用。

## 性能考量

- 类本身为轻量级值类型，拷贝成本低。
- `sk_is_trivially_relocatable` 允许在数组重新分配时使用 `memcpy` 代替逐元素拷贝。
- 真正的性能关键在于目标纹理拷贝操作本身——这发生在渲染管线的其他部分，不在本类中。当 framebuffer fetch 不可用时，这种拷贝是不可避免的开销。

## 相关文件

- `src/gpu/ganesh/GrSurfaceProxyView.h` — 纹理代理视图
- `src/gpu/ganesh/GrPipeline.h` — 渲染管线，持有 GrDstProxyView
- `src/gpu/ganesh/GrXferProcessor.h` — 混合处理器，使用目标纹理
- `include/private/gpu/ganesh/GrTypesPriv.h` — GrDstSampleFlags 定义
