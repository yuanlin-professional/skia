# SkPaintPriv

> 源文件
> - src/core/SkPaintPriv.h
> - src/core/SkPaintPriv.cpp

## 概述

`SkPaintPriv` 是一个实用工具类,提供了 `SkPaint` 类的私有功能和内部辅助函数。该类主要用于 Skia 内部,封装了绘制优化、颜色计算、序列化和反序列化等高级功能。它不对外暴露公共 API,仅供 Skia 核心模块使用。

## 架构位置

`SkPaintPriv` 位于 Skia 核心模块的内部实现层,属于 `src/core` 目录。它作为 `SkPaint` 的辅助类,提供了一系列静态方法来处理与绘制相关的底层逻辑,包括不透明度检测、抖动判断、颜色过滤器处理以及序列化操作。

## 主要类与结构体

### SkPaintPriv

该类是一个纯静态工具类,不包含任何实例成员变量。

#### 枚举类型

| 枚举类型 | 说明 |
|---------|------|
| `ShaderOverrideOpacity` | 描述着色器覆盖的不透明度状态(无覆盖、不透明、非不透明) |
| `FlatFlags` | 序列化标志位,用于标记 paint 是否包含特效或字体信息 |
| `SrcColorOpacity` | 源颜色的不透明度状态(不透明、透明黑、透明 alpha、未知) |

#### 关键成员变量

无实例成员变量,仅包含静态方法。

## 公共 API 函数

### 静态方法

| 方法 | 功能 |
|------|------|
| `Overwrites()` | 判断绘制操作是否会覆盖所有受影响的像素 |
| `ShouldDither()` | 根据目标颜色类型和 paint 状态判断是否应启用抖动 |
| `ComputeLuminanceColor()` | 计算 paint 的亮度颜色,用于字形遮罩缓存 |
| `Flatten()` | 将 SkPaint 序列化到缓冲区 |
| `Unflatten()` | 从缓冲区反序列化 SkPaint |
| `RemoveColorFilter()` | 将颜色过滤器折叠到着色器或颜色中 |

### Overwrites 方法

```cpp
static bool Overwrites(const SkPaint* paint, ShaderOverrideOpacity overrideOpacity);
```

该方法保守地判断使用给定 paint 绘制是否会完全覆盖受影响的像素。它考虑了 paint 的 alpha 值、混合模式、着色器不透明度和颜色过滤器的影响。

### ShouldDither 方法

```cpp
static bool ShouldDither(const SkPaint& p, SkColorType dstCT);
```

判断是否应对给定的 paint 和目标颜色类型启用抖动。对于 565 或 4444 格式总是启用抖动,其他格式仅在 paint 包含非常量内容时启用。

### ComputeLuminanceColor 方法

```cpp
static SkColor ComputeLuminanceColor(const SkPaint& paint);
```

计算用于字形遮罩缓存的亮度颜色。如果 paint 包含复杂着色器,返回中性灰色(0.5, 0.5, 0.5)。

## 内部实现细节

### 序列化格式

`Flatten` 和 `Unflatten` 方法使用 `pack_v68` 和 `unpack_v68` 函数实现紧凑的序列化格式。序列化数据包含 32 位打包字段,结构如下:

```
flags  :  8 bits  // 抗锯齿、抖动等标志
blend  :  8 bits  // 混合模式(0xFF 表示自定义混合器)
cap    :  2 bits  // 线帽样式
join   :  2 bits  // 线连接样式
style  :  2 bits  // 填充样式
filter :  2 bits  // 保留位(曾用于滤镜质量)
flat   :  8 bits  // 扁平化标志
```

### 混合模式不透明度判断

`blend_mode_is_opaque` 函数将混合模式转换为混合系数,并根据源颜色不透明度类型判断混合结果是否不透明。关键判断逻辑:

- 如果目标系数为 `kZero`,结果总是不透明
- 如果目标系数为 `kISA` 且源不透明,结果不透明
- 如果目标系数为 `kSA` 且源透明,结果不透明

### 颜色过滤器移除

`RemoveColorFilter` 方法通过以下方式处理颜色过滤器:

1. 如果存在着色器,创建 `SkColorFilterShader` 包装原着色器和过滤器
2. 如果仅有颜色,直接应用过滤器到颜色值
3. 最后将颜色过滤器设置为 nullptr

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPaint` | 主要操作的对象类 |
| `SkBlendMode` | 混合模式判断 |
| `SkColorFilter` | 颜色过滤器处理 |
| `SkShader` | 着色器操作 |
| `SkWriteBuffer/SkReadBuffer` | 序列化支持 |
| `SkColorSpace` | 颜色空间转换 |

### 被依赖的模块

`SkPaintPriv` 被以下模块使用:

- 渲染后端(栅格化、GPU 渲染)
- SkPicture 序列化系统
- 字形缓存系统
- 绘制优化模块

## 设计模式与设计决策

### 静态工具类模式

`SkPaintPriv` 采用纯静态方法设计,避免实例化开销。所有方法都是无状态的,便于在多线程环境中安全调用。

### 保守策略

`Overwrites` 方法采用保守策略,即在不确定时返回 false。这确保了渲染正确性,避免因错误判断导致的视觉错误,代价是可能错过某些优化机会。

### 版本化序列化

序列化方法使用版本标记(如 `pack_v68`),支持向后兼容。通过 `SkSafeRange` 和 `kSkBlenderInSkPaint` 等版本检查,确保旧数据可以正确读取。

### 颜色过滤器折叠优化

`RemoveColorFilter` 方法将颜色过滤器提前应用,减少运行时计算。这是一种典型的预计算优化策略,特别适用于静态内容。

## 性能考量

### 亮度颜色缓存

`ComputeLuminanceColor` 支持字形缓存系统根据亮度值复用字形遮罩,避免重复生成相同视觉效果的字形。

### 抖动判断优化

`ShouldDither` 方法快速判断是否需要抖动,避免在不必要的情况下启用抖动算法。抖动是计算密集型操作,正确判断能显著提升性能。

### 序列化压缩

序列化格式采用位打包技术,将多个字段压缩到 32 位整数中,减少存储空间和传输开销。仅在需要时才序列化复杂对象(如着色器、过滤器)。

### 混合模式快速路径

通过 `blend_mode_is_opaque` 提前判断混合结果的不透明性,渲染器可以跳过某些混合计算或采用更快的代码路径。

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `include/core/SkPaint.h` | 公共 Paint API 定义 |
| `src/core/SkPaintDefaults.h` | Paint 默认值定义 |
| `src/core/SkWriteBuffer.h` | 序列化写入接口 |
| `src/core/SkReadBuffer.h` | 序列化读取接口 |
| `src/effects/colorfilters/SkColorFilterBase.h` | 颜色过滤器基类 |
| `src/shaders/SkColorFilterShader.h` | 颜色过滤着色器 |
| `src/shaders/SkShaderBase.h` | 着色器基类 |
| `src/core/SkColorSpacePriv.h` | 颜色空间私有功能 |
| `src/core/SkPicturePriv.h` | Picture 序列化支持 |
