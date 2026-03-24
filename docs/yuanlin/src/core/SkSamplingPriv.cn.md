# SkSamplingPriv

> 源文件: src/core/SkSamplingPriv.h

## 概述

`SkSamplingPriv` 提供了图像采样选项(`SkSamplingOptions`)的私有扩展工具,包括旧版过滤质量的兼容性转换、各向异性过滤回退策略、序列化尺寸计算、以及采样优化判断。该模块主要服务于 Skia 内部的图像渲染管线,处理不同采样模式之间的转换和优化,同时维护与旧 API 的兼容性。

## 架构位置

`SkSamplingPriv` 位于 `src/core` 模块,作为采样系统的私有接口层:

- **公共层**: `SkSamplingOptions` 提供用户级采样配置 API
- **私有层**: `SkSamplingPriv` 提供内部工具和转换功能
- **上层**: `SkImage`、`SkShader`、`SkCanvas` 使用采样选项
- **下层**: GPU 后端根据采样选项配置纹理过滤
- **历史兼容**: 提供旧版 `SkFilterQuality` 枚举的转换支持

## 主要类与结构体

### SkLegacyFQ 枚举

| 属性 | 说明 |
|------|------|
| **类型** | 枚举(enum) |
| **枚举值** | `kNone_SkLegacyFQ`: 最近邻(0)<br>`kLow_SkLegacyFQ`: 双线性(1)<br>`kMedium_SkLegacyFQ`: 双线性 + mipmap(2)<br>`kHigh_SkLegacyFQ`: 双三次重采样(3) |

旧版过滤质量枚举,用于反序列化兼容。

### SkMediumAs 枚举

| 属性 | 说明 |
|------|------|
| **类型** | 枚举(enum) |
| **枚举值** | `kNearest_SkMediumAs`: Medium 质量使用最近邻 mipmap<br>`kLinear_SkMediumAs`: Medium 质量使用线性 mipmap |

控制 Medium 质量对应的 mipmap 模式。

### SkSamplingPriv (静态工具类)

| 属性 | 说明 |
|------|------|
| **继承关系** | 无继承关系,纯静态工具类 |
| **核心功能** | 序列化尺寸计算、优化判断、各向异性回退、旧版本转换 |

提供采样选项的私有工具方法。

## 公共 API 函数

### 序列化支持

```cpp
// 计算 SkSamplingOptions 序列化所需字节数
static size_t FlatSize(const SkSamplingOptions& options);
```

返回值:
- 各向异性: `sizeof(uint32_t)` (仅存储 maxAniso)
- 其他模式: `4 * sizeof(uint32_t)` (maxAniso + useCubic + filter/mipmap)

### 优化判断

```cpp
// 判断在单位矩阵下采样是否可忽略
static bool NoChangeWithIdentityMatrix(const SkSamplingOptions& sampling);
```

返回 true 的条件:
- 不使用立方重采样,或
- 使用立方重采样但 B == 0 (B 参数控制锐化程度)
- 各向异性过滤(假设对单位变换无影响)

### 各向异性回退

```cpp
// 为不支持各向异性的场景创建回退采样选项
static SkSamplingOptions AnisoFallback(bool imageIsMipped);
```

回退策略:
- 如果图像有 mipmap: 返回 `(Linear, Linear)` (双线性 + 线性 mipmap)
- 如果图像无 mipmap: 返回 `(Linear, None)` (双线性,无 mipmap)

设计原因:
- 各向异性可利用 mipmap 但不会创建 mipmap
- 回退不应触发 mipmap 生成(保持用户意图)

### 旧版本转换

```cpp
// 从旧版 SkFilterQuality 转换为 SkSamplingOptions
static SkSamplingOptions FromFQ(SkLegacyFQ fq,
                                SkMediumAs behavior = kNearest_SkMediumAs);
```

转换映射:

| SkLegacyFQ | SkSamplingOptions |
|------------|-------------------|
| kHigh_SkLegacyFQ | Cubic(1/3, 1/3) - Mitchell-Netravali 滤波器 |
| kMedium_SkLegacyFQ | (Linear, Nearest) 或 (Linear, Linear) |
| kLow_SkLegacyFQ | (Linear, None) - 双线性无 mipmap |
| kNone_SkLegacyFQ | (Nearest, None) - 最近邻 |

## 内部实现细节

### 序列化格式

`FlatSize` 计算逻辑:

**各向异性模式**:
```cpp
if (options.isAniso()) {
    return sizeof(uint32_t);  // 仅存储 maxAniso
}
```

**其他模式**:
```cpp
return sizeof(uint32_t)      // maxAniso (0 表示非各向异性)
     + sizeof(uint32_t)      // useCubic 布尔标志
     + 2 * sizeof(uint32_t); // 立方参数(B, C)或 filter/mipmap 枚举
```

### 单位矩阵优化

`NoChangeWithIdentityMatrix` 实现:
```cpp
return !sampling.useCubic || sampling.cubic.B == 0;
```

理论依据:
- 对于单位变换,最近邻和双线性采样不改变像素值
- 立方重采样默认会引入滤波效果
- 但当 B == 0 时,Mitchell-Netravali 滤波器退化为插值滤波器(无锐化)
- 参考: https://entropymine.com/imageworsener/bicubic/

### 各向异性回退策略

`AnisoFallback` 逻辑:
```cpp
auto mm = imageIsMipped ? SkMipmapMode::kLinear : SkMipmapMode::kNone;
return SkSamplingOptions(SkFilterMode::kLinear, mm);
```

设计考量:
- **不触发 mipmap 生成**: 如果原图无 mipmap,回退也不使用 mipmap
- **保持质量**: 各向异性通常用于高质量渲染,回退到双线性
- **性能平衡**: 避免在不支持各向异性的平台上过度计算

### 立方重采样参数

`FromFQ` 使用 Mitchell-Netravali 滤波器:
```cpp
SkCubicResampler{1/3.0f, 1/3.0f}
```

这是 Mitchell-Netravali 论文中推荐的"平衡"参数:
- B = 1/3: 控制尖锐度
- C = 1/3: 控制振铃(ringing)
- 提供锐利与平滑的良好平衡

### Medium 质量行为

`FromFQ` 的 `behavior` 参数:
- **kNearest_SkMediumAs**: mipmap 使用最近邻(更快,略低质量)
- **kLinear_SkMediumAs**: mipmap 使用线性插值(更好质量,稍慢)

默认使用 `kNearest_SkMediumAs` 以平衡性能和质量。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkSamplingOptions.h | 公共采样选项定义 |
| SkReadBuffer | 反序列化支持 |
| SkWriteBuffer | 序列化支持 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| SkImage | 图像绘制时的采样配置 |
| SkShader | 着色器采样模式 |
| SkCanvas | drawImage* 方法的采样参数 |
| GPU 后端 | 纹理过滤器设置 |
| 序列化系统 | Picture/SkDrawable 序列化 |

## 设计模式与设计决策

### 静态工具类模式

纯静态方法,无状态:
- 避免不必要的实例化
- 明确表示功能是独立的工具函数
- 与 `SkSamplingOptions` 的职责分离

### 旧版本兼容层

保留 `SkLegacyFQ` 枚举和转换函数:
- 支持旧版本序列化数据的读取
- 允许旧 API 迁移到新 API
- 隔离历史包袱,不污染公共 API

### 回退策略模式

`AnisoFallback` 提供优雅降级:
- 检测能力后选择最佳替代方案
- 保持用户意图(不自动生成 mipmap)
- 平衡质量和性能

### 编译期常量

Bicubic 滤波器常量定义:
```cpp
static constexpr int kBicubicFilterTexelPad = 2;
```
用于计算双三次滤波所需的纹理边界扩展。

## 性能考量

### 单位矩阵快速路径

`NoChangeWithIdentityMatrix` 允许跳过不必要的采样:
- 当变换矩阵为单位矩阵且采样无效果时,直接使用原像素
- 避免纹理采样和滤波计算
- 在 UI 渲染(无缩放)场景下常见

### 各向异性回退开销

`AnisoFallback` 避免昂贵的各向异性计算:
- 在不支持的硬件上降级为双线性(快得多)
- 避免软件模拟各向异性(可能非常慢)

### 序列化尺寸优化

`FlatSize` 根据模式返回精确大小:
- 各向异性仅需 4 字节
- 避免过度分配序列化缓冲区
- 减少 Picture 文件大小

### Mipmap 生成控制

`AnisoFallback` 不触发自动 mipmap 生成:
- Mipmap 生成是昂贵操作(需要额外内存和计算)
- 尊重用户原始选择(如果用户未提供 mipmap,可能有理由)

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkSamplingOptions.h | 公共采样选项定义 |
| include/core/SkImage.h | 图像绘制使用采样选项 |
| include/core/SkShader.h | 着色器采样配置 |
| src/core/SkReadBuffer.h | 序列化输入 |
| src/core/SkWriteBuffer.h | 序列化输出 |
| src/image/SkImage.cpp | 图像绘制实现 |
| src/gpu/ganesh/GrTextureEffect.h | GPU 纹理采样效果 |

## 常量定义

### kBicubicFilterTexelPad

```cpp
static constexpr int kBicubicFilterTexelPad = 2;
```

**用途**: 双三次滤波需要在源矩形周围额外采样的纹理像素数量。

**原因**:
- 双三次滤波使用 4x4 的采样核
- 需要在目标像素周围 2 个纹理像素(每侧)
- GPU 后端需要扩展纹理边界以避免边缘伪影

## 使用场景示例

### 旧代码迁移

```cpp
// 旧 API:
SkPaint paint;
paint.setFilterQuality(kHigh_SkFilterQuality);

// 新 API 等效:
SkSamplingOptions sampling = SkSamplingPriv::FromFQ(kHigh_SkLegacyFQ);
canvas->drawImage(image, x, y, sampling, &paint);
```

### 各向异性回退

```cpp
SkSamplingOptions requested(/*aniso=*/8);

if (!gpuSupportsAniso) {
    bool hasMips = image->hasMipmaps();
    SkSamplingOptions actual = SkSamplingPriv::AnisoFallback(hasMips);
    // 使用 actual 进行绘制
}
```

### 优化判断

```cpp
SkMatrix ctm = canvas->getTotalMatrix();
if (ctm.isIdentity() &&
    SkSamplingPriv::NoChangeWithIdentityMatrix(sampling)) {
    // 快速路径: 直接复制像素,无需采样
    blitPixels(image);
} else {
    // 常规路径: 应用采样
    drawWithSampling(image, sampling);
}
```
