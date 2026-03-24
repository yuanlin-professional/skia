# SkHdrMetadata - HDR 元数据管理

> 源文件: `src/codec/SkHdrMetadata.cpp`

## 概述

`SkHdrMetadata.cpp` 实现了 Skia 的 HDR（High Dynamic Range）元数据管理功能。该文件包含三个核心类的实现：`ContentLightLevelInformation`（CLLI，内容光照级别信息）、`MasteringDisplayColorVolume`（MDCV，母版显示色彩体积）以及 `Metadata`（聚合容器）。这些元数据来源于 HDR 视频和图像标准（如 SMPTE ST 2086、CEA-861-G），用于指导色调映射和显示适配。文件支持通用二进制格式和 PNG 特有的 CLLI/MDCV chunk 格式的双向序列化。

## 架构位置

该文件位于 `src/codec/` 目录下，是 Skia HDR 处理管线的元数据层。`Metadata` 类作为 CLLI、MDCV 和 AGTM 的统一容器，被 `SkEncodedInfo` 持有，贯穿整个解码和渲染流程。`makeToneMapColorFilter` 方法将元数据转换为可执行的色调映射滤镜。

## 主要类与结构体

### `skhdr::ContentLightLevelInformation`（CLLI）
描述内容的最大光照级别：
- `fMaxCLL`: 最大内容光照级别（nits）
- `fMaxFALL`: 最大帧平均光照级别（nits）

### `skhdr::MasteringDisplayColorVolume`（MDCV）
描述母版显示器的色彩能力：
- `fDisplayPrimaries`: 显示器色度坐标（RGBW 各 XY，共 8 个值）
- `fMaximumDisplayMasteringLuminance`: 最大母版亮度（nits）
- `fMinimumDisplayMasteringLuminance`: 最小母版亮度（nits）

### `skhdr::Metadata`
HDR 元数据聚合容器，管理可选的 CLLI、MDCV 和 AGTM。

## 公共 API 函数

### ContentLightLevelInformation
- `parse(const SkData*)`: 从 4 字节数据解析（两个 BE uint16）
- `serialize() const`: 序列化为 4 字节数据
- `parsePngChunk(const SkData*)`: 从 PNG cLLi chunk 解析（两个 BE uint32，除以 10000）
- `serializePngChunk() const`: 序列化为 PNG cLLi chunk 格式
- `toString() const`: 返回可读字符串
- `getUint16MaxCLL()/getUint16MaxFALL()`: 获取整数值

### MasteringDisplayColorVolume
- `parse(const SkData*)`: 从 24 字节数据解析（8 个 BE uint16 色度 + 2 个 BE uint32 亮度）
- `serialize() const`: 序列化为 24 字节数据
- `toString() const`: 返回可读字符串

### Metadata
- `MakeEmpty()`: 创建空元数据
- `get/setContentLightLevelInformation()`: CLLI 访问器
- `get/setMasteringDisplayColorVolume()`: MDCV 访问器
- `get/setAdaptiveGlobalToneMap()`: AGTM 访问器
- `getSerializedAgtm()`: 获取序列化的 AGTM 数据
- `setSerializedAgtm(sk_sp<const SkData>)`: 从二进制数据设置 AGTM
- `makeToneMapColorFilter(float targetedHdrHeadroom, const SkColorSpace*)`: 创建色调映射颜色滤镜
- `toString() const`: 返回所有元数据的可读字符串
- `operator==`: 相等比较

## 内部实现细节

### CLLI 编解码
- **通用格式**: 两个 BE uint16，直接存储整数 nits 值
- **PNG 格式**: 两个 BE uint32，值为 `float * 10000`（`clli_png_luminance_divisor = 10000.f`）
- 序列化使用 `std::llroundf` 进行四舍五入

### MDCV 编解码
- **色度值**: 8 个 BE uint16，值为 `float * 50000`（`mdcv_chrominance_divisor = 50000.f`）
- **亮度值**: 2 个 BE uint32，值为 `float * 10000`（`mdcv_luminance_divisor = 10000.f`）
- 数据总大小固定为 24 字节

### Metadata 色调映射
`makeToneMapColorFilter()` 的实现流程：
1. 调用 `AgtmHelpers::PopulateToneMapAgtmParams` 获取 AGTM 参数和缩放因子
2. 如果有有效的 `HeadroomAdaptiveToneMap`，调用 `AgtmHelpers::MakeColorFilter` 创建滤镜
3. 无有效 HATM 时返回 nullptr（TODO: 添加默认色调映射）

### 序列化 AGTM 桥接
`setSerializedAgtm()` 通过 `AdaptiveGlobalToneMap::parse()` 解析二进制数据，失败时重置 AGTM。`getSerializedAgtm()` 通过 `AdaptiveGlobalToneMap::serialize()` 生成二进制数据。

### 相等比较
所有三个类都实现了 `operator==`，CLLI 和 MDCV 使用精确浮点比较（因为值来自固定精度的整数编码），AGTM 通过 `optional` 的比较运算符。

## 依赖关系

- `include/private/SkHdrMetadata.h`: 类定义
- `include/core/SkColorFilter.h`: 色调映射滤镜
- `include/core/SkStream.h`, `SkString.h`: 流和字符串
- `src/codec/SkHdrAgtmPriv.h`: AGTM 辅助函数
- `src/core/SkStreamPriv.h`: 大端读写

## 设计模式与设计决策

1. **可选值语义**: CLLI、MDCV 和 AGTM 都作为 `std::optional` 存储在 `Metadata` 中，支持检测元数据是否存在。

2. **双格式序列化**: CLLI 支持通用格式和 PNG 格式两种编解码，通过不同的 parse/serialize 方法对区分。

3. **固定精度编码**: 使用整数 * 除数的方式编码浮点值，精度由除数决定（50000 = 0.00002 精度，10000 = 0.0001 精度）。

4. **色调映射集成**: `Metadata` 直接提供 `makeToneMapColorFilter` 方法，简化了上层调用。

## 性能考量

- **紧凑二进制格式**: CLLI 仅 4 字节，MDCV 仅 24 字节
- **惰性色调映射**: 色调映射滤镜仅在调用 `makeToneMapColorFilter` 时创建
- **流式序列化**: 使用 `SkDynamicMemoryWStream` 避免预分配
- **精确相等比较**: 使用 `==` 而非误差范围比较，因为值来自固定精度编码

## 相关文件

- `include/private/SkHdrMetadata.h`: 类定义
- `src/codec/SkHdrAgtmPriv.h`: AGTM 辅助函数
- `src/codec/SkHdrAgtm.cpp`: AGTM 色调映射实现
- `src/codec/SkHdrAgtmParse.cpp`: AGTM 二进制解析
- `include/private/SkEncodedInfo.h`: 编码信息（持有 Metadata）
