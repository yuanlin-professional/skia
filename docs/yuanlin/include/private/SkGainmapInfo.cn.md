# SkGainmapInfo

> 源文件: `include/private/SkGainmapInfo.h`

## 概述

SkGainmapInfo 定义了 Gainmap 渲染参数结构体,用于描述如何将 Gainmap 应用到基础图像以实现 HDR 渲染。Gainmap 技术允许在单个图像文件中同时存储 SDR 和 HDR 表示,并根据显示器能力动态适配。该结构体遵循 Adobe Gainmap 技术规范和 ISO 21496-1 标准。

## 架构位置

SkGainmapInfo 位于 Skia HDR 图像处理的核心层,作为 Gainmap 元数据的标准表示。它被图像编解码器、着色器系统和元数据处理模块广泛使用,是 Skia HDR 工作流的关键数据结构。该结构体定义在 `include/private` 目录,作为内部 API 供 Skia 各模块共享。

## 主要类与结构体

### SkGainmapInfo 结构体

完整的 Gainmap 渲染参数集合,定义了如何将 Gainmap 应用到基础图像。

**关键成员变量**:

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|---------|------|
| fGainmapRatioMin | SkColor4f | {1, 1, 1, 1} | Gainmap 的最小增益比率(RGB 分量) |
| fGainmapRatioMax | SkColor4f | {2, 2, 2, 1} | Gainmap 的最大增益比率(RGB 分量) |
| fGainmapGamma | SkColor4f | {1, 1, 1, 1} | Gainmap 编码的 Gamma 值(RGB 分量) |
| fEpsilonSdr | SkColor4f | {0, 0, 0, 1} | SDR 计算的数值稳定性参数 |
| fEpsilonHdr | SkColor4f | {0, 0, 0, 1} | HDR 计算的数值稳定性参数 |
| fDisplayRatioSdr | float | 1.0 | SDR 显示的参考亮度比 |
| fDisplayRatioHdr | float | 2.0 | HDR 显示的参考亮度比 |
| fBaseImageType | BaseImageType | kSDR | 基础图像类型(SDR 或 HDR) |
| fType | Type | kDefault | Gainmap 编码类型 |
| fGainmapMathColorSpace | sk_sp<SkColorSpace> | nullptr | Gainmap 计算的颜色空间 |

**注意**: SkColor4f 的 alpha 通道通常未使用,设为 1.0。

### BaseImageType 枚举

指定基础图像是 SDR 还是 HDR。

```cpp
enum class BaseImageType {
    kSDR,  // 基础图像是标准动态范围
    kHDR,  // 基础图像是高动态范围
};
```

**说明**:
- **kSDR**: Gainmap 用于将 SDR 图像提升到 HDR
- **kHDR**: Gainmap 用于将 HDR 图像降级到 SDR

数学公式会根据基础图像类型选择不同的方向。

### Type 枚举

指定 Gainmap 的编码类型。

```cpp
enum class Type {
    kDefault,  // 标准 Gainmap 编码
    kApple,    // Apple HDR 效果编码
};
```

**类型说明**:

| 类型 | 描述 | 转换需求 |
|------|------|----------|
| kDefault | 符合标准规范的 Gainmap | 无需转换 |
| kApple | Apple 设备使用的编码格式 | 需要转换为 kDefault 类型 |

**Apple 类型**:
- 原始规范: [Apple HDR Effect Documentation](https://developer.apple.com/documentation/appkit/images_and_pdf/applying_apple_hdr_effect_to_your_photos)
- 转换方法: [Conversion Document](https://docs.google.com/document/d/1iUpYAThVV_FuDdeiO3t0vnlfoA1ryq0WfGS9FuydwKc)

## Gainmap 渲染数学

SkGainmapInfo 头文件中详细描述了 Gainmap 的数学公式。

### 权重计算

首先计算 Gainmap 应用权重 W,基于显示器的 HDR/SDR 比率 H:

```
W = clamp((log(H) - log(fDisplayRatioSdr)) /
          (log(fDisplayRatioHdr) - log(fDisplayRatioSdr)), 0, 1)
```

**含义**:
- 当 H ≤ fDisplayRatioSdr 时,W = 0,显示纯 SDR
- 当 H ≥ fDisplayRatioHdr 时,W = 1,显示纯 HDR
- 当 H 在中间时,W 在 [0, 1] 之间,平滑插值

### Gainmap 值转换

将从 Gainmap 图像采样的像素值 G(范围 [0, 1])转换为对数空间的增益 L:

```
L = mix(log(fGainmapRatioMin), log(fGainmapRatioMax), pow(G, fGainmapGamma))
```

**逐步解释**:
1. `pow(G, fGainmapGamma)`: 应用 Gamma 解码
2. `log(fGainmapRatioMin)` 和 `log(fGainmapRatioMax)`: 定义对数空间的范围
3. `mix(...)`: 在对数空间线性插值

**RGB 分量独立**: 每个颜色通道使用独立的参数,支持色彩自适应。

### 最终像素计算

根据基础图像类型,应用不同的混合公式:

**SDR 基础图像** (fBaseImageType == kSDR):
```
D = (B + fEpsilonSdr) * exp(L * W) - fEpsilonHdr
```

**HDR 基础图像** (fBaseImageType == kHDR):
```
D = (B + fEpsilonHdr) * exp(L * (W - 1)) - fEpsilonSdr
```

**符号说明**:
- B: 基础图像像素值(线性光照空间)
- D: 输出像素值
- W: 权重(0 到 1)
- L: 对数增益(RGB 向量)
- epsilon: 数值稳定性参数,避免 log(0) 或除以零

**注意**: log() 和 exp() 的底数不影响结果(只要一致使用),通常使用自然对数。

## 公共 API 函数

### `bool isUltraHDRv1Compatible() const`
- **功能**: 检查参数是否兼容 UltraHDR v1 格式
- **参数**: 无
- **返回值**: true 表示可以编码为 UltraHDR v1,false 表示不兼容
- **说明**: UltraHDR v1 对参数有特定限制(如单一 Gamma、特定范围等)

### `static bool ParseVersion(const SkData* data)`
- **功能**: 检查数据是否包含支持的 ISO 21496-1 版本
- **参数**: `data` - 包含版本信息的二进制数据
- **返回值**: 支持的版本返回 true,不支持返回 false
- **说明**: 当前支持 ISO 21496-1 版本 0

### `static bool Parse(const SkData* data, SkGainmapInfo& info)`
- **功能**: 从 ISO 21496-1 格式的二进制数据解析 Gainmap 参数
- **参数**:
  - `data`: ISO 21496-1 编码的元数据
  - `info`: 输出参数,解析结果写入此结构体
- **返回值**: 解析成功返回 true,失败返回 false
- **说明**:
  - 如果元数据指示使用基础图像的色彩原色,fGainmapMathColorSpace 设为 nullptr
  - 否则设为 sRGB(默认值,应由解码器覆盖)

### `static sk_sp<SkData> SerializeVersion()`
- **功能**: 序列化 ISO 21496-1 版本 0 的版本结构
- **参数**: 无
- **返回值**: 包含版本信息的 SkData
- **说明**: 仅包含版本信息,不包含实际参数

### `sk_sp<SkData> serialize() const`
- **功能**: 将 Gainmap 参数序列化为 ISO 21496-1 版本 0 格式
- **参数**: 无
- **返回值**: 包含完整元数据的 SkData
- **说明**: 包含版本信息和所有渲染参数

### 运算符重载

#### `bool operator==(const SkGainmapInfo& other) const`
- **功能**: 比较两个 SkGainmapInfo 是否相等
- **参数**: `other` - 要比较的对象
- **返回值**: 所有成员都相等返回 true
- **说明**: 使用浮点数精确比较,颜色空间使用 SkColorSpace::Equals

#### `bool operator!=(const SkGainmapInfo& other) const`
- **功能**: 不等比较运算符
- **参数**: `other` - 要比较的对象
- **返回值**: 不相等返回 true

## 内部实现细节

### ISO 21496-1 编码格式

ISO 标准定义的二进制格式结构(简化描述):

```
[Header]
  - Version (uint32_t)
  - Flags (uint32_t)

[Gainmap Parameters]
  - GainmapRatioMin (float[3])
  - GainmapRatioMax (float[3])
  - GainmapGamma (float[3])
  - OffsetSdr (float[3])  // fEpsilonSdr
  - OffsetHdr (float[3])  // fEpsilonHdr
  - HDR Capacity Min (float)  // fDisplayRatioSdr
  - HDR Capacity Max (float)  // fDisplayRatioHdr
  - BaseImageType (uint8_t)

[Optional Fields]
  - Alternate Color Space (CICP codes)
```

Parse 和 serialize 方法处理这种二进制格式的转换。

### 参数验证

isUltraHDRv1Compatible 检查以下限制:
- fGainmapGamma 的三个分量必须相等
- fGainmapRatioMin/Max 的三个分量必须相等
- fEpsilonSdr/Hdr 必须为零或满足特定条件
- fBaseImageType 必须是 kSDR
- fType 必须是 kDefault
- fDisplayRatioSdr 必须是 1.0

这些限制简化了编码和解码实现。

### 颜色空间语义

fGainmapMathColorSpace 的含义:
- **nullptr**: 使用基础图像的色彩原色(只用原色,忽略传输函数)
- **非 nullptr**: 在指定的颜色空间的色彩原色下进行 Gainmap 计算

Gainmap 数学始终在线性光照空间进行,颜色空间只影响色彩原色。

### Epsilon 参数的作用

fEpsilonSdr 和 fEpsilonHdr 防止数值问题:
- 避免 log(0) 导致的负无穷
- 避免除以零
- 在接近黑色的区域提供平滑过渡

通常设为很小的值(如 0.001)或零(如果输入保证非零)。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkColor.h` | SkColor4f 颜色表示 |
| `include/core/SkColorSpace.h` | 颜色空间定义 |
| `include/core/SkRefCnt.h` | sk_sp 智能指针 |
| `include/core/SkData.h` | 二进制数据容器 |

### 被依赖的模块

- **SkGainmapShader**: 使用此结构体执行渲染
- **SkJpegMetadataDecoder**: 解析 JPEG 中的 Gainmap 元数据
- **SkJpegGainmapEncoder**: 编码 UltraHDR JPEG
- **SkCodec**: 图像解码器携带 Gainmap 信息
- **SkImageGenerator**: 生成 HDR 图像时使用

## 设计模式与设计决策

### POD 结构体设计

SkGainmapInfo 设计为 Plain Old Data (POD) 结构体:
- **值语义**: 拷贝和赋值是直接的
- **简单性**: 无虚函数,无复杂继承
- **可序列化**: 易于序列化和反序列化

### 分量独立设计

使用 SkColor4f 表示 RGB 独立参数:
- **色彩自适应**: 不同颜色通道可以有不同的增益
- **灵活性**: 支持复杂的色调映射
- **标准对齐**: 符合 Adobe Gainmap 规范

### 类型枚举的演进

Type 枚举允许支持多种 Gainmap 变体:
- **向后兼容**: 新类型不影响现有代码
- **显式转换**: 明确何时需要格式转换
- **扩展性**: 未来可以添加更多类型

### 默认值选择

默认值的设计考虑:
- fGainmapRatioMin = 1.0: 无增益的下限
- fGainmapRatioMax = 2.0: 2 倍亮度的上限(常见 HDR 范围)
- fDisplayRatioSdr/Hdr = 1.0/2.0: 匹配增益范围
- fGainmapGamma = 1.0: 线性编码
- Epsilon = 0.0: 假设输入非零

这些默认值适用于简单的 HDR 使用场景。

## 性能考量

### 结构体大小

SkGainmapInfo 的内存占用:
- 5 个 SkColor4f: 5 × 16 = 80 字节
- 2 个 float: 8 字节
- 2 个 enum: 2 字节
- sk_sp<SkColorSpace>: 8 字节(指针)
- 对齐填充: ~10 字节
- 总计: 约 110 字节

这是可接受的大小,可以直接作为函数参数传递(通过 const 引用)。

### 参数访问

所有成员变量都是公开的:
- **零开销**: 无 getter/setter 调用开销
- **直接访问**: 编译器可以充分优化
- **简单性**: 代码更清晰易读

### 序列化性能

- Parse: 线性时间 O(n),n 是数据大小(~100 字节)
- serialize: 常数时间 O(1),只需写入固定字段
- 通常在微秒级完成

## 典型使用场景

### 创建 UltraHDR 图像

```cpp
SkGainmapInfo info;
info.fGainmapRatioMin = SkColor4f{1.0f, 1.0f, 1.0f, 1.0f};
info.fGainmapRatioMax = SkColor4f{4.0f, 4.0f, 4.0f, 1.0f};
info.fGainmapGamma = SkColor4f{1.0f, 1.0f, 1.0f, 1.0f};
info.fDisplayRatioHdr = 4.0f;
info.fBaseImageType = SkGainmapInfo::BaseImageType::kSDR;

// 编码为 JPEG
SkJpegGainmapEncoder::EncodeHDRGM(..., info);
```

### 解析 JPEG 元数据

```cpp
auto decoder = SkJpegMetadataDecoder::Make(jpegData);
auto isoData = decoder->getISOGainmapMetadata(false);

SkGainmapInfo info;
if (SkGainmapInfo::Parse(isoData.get(), info)) {
    // 使用 info 创建着色器
}
```

### 检查兼容性

```cpp
if (info.isUltraHDRv1Compatible()) {
    // 可以安全编码为 UltraHDR v1
} else {
    // 需要其他格式或降级
}
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/codec/SkGainmapInfo.cpp` | 实现文件 |
| `include/private/SkGainmapShader.h` | 使用此结构体渲染 |
| `include/private/SkJpegMetadataDecoder.h` | 解析 Gainmap 元数据 |
| `include/private/SkJpegGainmapEncoder.h` | 编码 Gainmap 图像 |
| `tests/GainmapInfoTest.cpp` | 单元测试 |
| `include/core/SkColor.h` | SkColor4f 定义 |
