# SkImage_GaneshYUVA - Ganesh YUVA 图像

> 源文件: `src/gpu/ganesh/image/SkImage_GaneshYUVA.h`, `src/gpu/ganesh/image/SkImage_GaneshYUVA.cpp`

## 概述

`SkImage_GaneshYUVA` 是 Ganesh GPU 后端中 YUVA 格式图像的实现。它包装 1 到 4 个 GPU 纹理平面（Y、U、V、A），在着色器中执行 YUV 到 RGB 的颜色空间转换。初始时直接使用多平面纹理进行渲染；当需要扁平化图像时（如 `readPixels`），会创建并缓存一个 RGB 代理用于后续渲染。

## 架构位置

```
SkImage (公共 API)
    |
SkImage_GaneshBase (Ganesh 图像基类)
    |
SkImage_GaneshYUVA (本文件)
    |
GrYUVATextureProxies (1-4 平面纹理代理)
    |
GrFragmentProcessor (YUV->RGB 着色器转换)
```

## 主要类与结构体

### `SkImage_GaneshYUVA`

继承自 `SkImage_GaneshBase`，标记为 `final`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fYUVAProxies` | `GrYUVATextureProxies` (mutable) | YUVA 纹理代理集合 |
| `fFromColorSpace` | `sk_sp<SkColorSpace>` | 源色彩空间（用于颜色转换） |
| `fOnMakeColorSpaceTarget/Result` | mutable 缓存 | `onMakeColorSpace` 结果缓存 |

### 常量

```cpp
static constexpr auto kAssumedColorType = kRGBA_8888_SkColorType;
```

YUVA 图像假定的扁平化颜色类型。

### `ColorSpaceMode` 枚举（私有）

```cpp
enum class ColorSpaceMode { kConvert, kReinterpret };
```

区分色彩空间转换和重解释两种模式。

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `textureSize()` | 返回所有平面纹理的总大小 |
| `onHasMipmaps()` | 检查所有平面是否都有 MipMap |
| `onIsProtected()` | 检查是否有任何平面受保护 |
| `asView()` | 获取 RGB 纹理视图（按需扁平化） |
| `asFragmentProcessor()` | 创建多平面 YUV->RGB 的 FragmentProcessor |
| `flush()` | 刷新所有平面代理 |
| `setupMipmapsForPlanes()` | 为所有平面生成 MipMap |
| `onMakeColorTypeAndColorSpace()` | 创建色彩空间转换后的新图像 |
| `onReinterpretColorSpace()` | 重新解释色彩空间 |

## 内部实现细节

### 按需扁平化

首次调用 `asView()` 时，如果只需要纹理视图（而非 FragmentProcessor），会将 YUVA 平面渲染到单个 RGB 纹理并缓存。后续调用直接返回缓存的 RGB 视图。

### FragmentProcessor 直接渲染

当通过 `asFragmentProcessor()` 使用时，YUVA 平面直接传递给着色器，无需中间 RGB 纹理，性能更优。

### 色彩空间转换缓存

`onMakeColorTypeAndColorSpace()` 的结果被缓存在 `fOnMakeColorSpaceTarget/Result` 中，避免重复创建相同转换的图像实例。

## 依赖关系

- **上游依赖**: `SkImage_GaneshBase`、`GrYUVATextureProxies`。
- **着色器依赖**: `GrFragmentProcessor`（YUVA 采样和色彩转换）。
- **被依赖**: `SkImages::TextureFromYUVATextures()` 等工厂函数。

## 设计模式与设计决策

1. **延迟扁平化**: 尽可能保持 YUVA 多平面格式，仅在必要时转换为 RGB。
2. **双路径渲染**: FragmentProcessor 路径（零拷贝多平面）和 View 路径（扁平化 RGB）。
3. **色彩空间感知**: 支持从 YUVA 数据的原始色彩空间到目标色彩空间的转换。

## 性能考量

- `asFragmentProcessor` 避免了 YUVA->RGB 的中间纹理拷贝，是最高效的渲染路径。
- MipMap 需要为每个平面分别生成和管理。
- 色彩空间转换结果被缓存，避免重复计算。

## 相关文件

- `src/gpu/ganesh/image/SkImage_GaneshBase.h` - Ganesh 图像基类
- `src/gpu/ganesh/GrYUVATextureProxies.h` - YUVA 纹理代理管理
- `include/core/SkYUVAInfo.h` - YUVA 格式信息
