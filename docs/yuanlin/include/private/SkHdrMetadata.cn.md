# SkHdrMetadata

> 源文件: `include/private/SkHdrMetadata.h`

## 概述

SkHdrMetadata 定义了 HDR(高动态范围)图像和视频的元数据结构,包括内容光级信息(CLLI)、主显示器色彩体积(MDCV)和自适应全局色调映射(AGTM)。这些元数据遵循国际标准(SMPTE、ITU、CTA 等),用于正确显示和处理 HDR 内容。该模块是 Skia HDR 渲染管线的核心组件。

## 架构位置

SkHdrMetadata 位于 Skia 的 HDR 图像处理层,在 skhdr 命名空间下。它为 HDR 图像编解码、色调映射和显示适配提供标准化的元数据接口。该模块与图像解码器、颜色管理系统和 GPU 渲染器紧密协作,确保 HDR 内容在不同显示设备上的正确呈现。

## 主要类与结构体

### ContentLightLevelInformation

内容光级信息,描述图像或视频的亮度特性。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fMaxCLL | float | 最大内容光级(Maximum Content Light Level),单位 cd/m² |
| fMaxFALL | float | 最大帧平均光级(Maximum Frame Average Light Level),单位 cd/m² |

**标准依据**:
- ANSI/CTA-861-H Annex P
- ITU-T H.265 D.2.35
- PNG Specification 11.3.2.8 cLLI

**公共方法**:

#### `bool parse(const SkData* data)`
- **功能**: 从 AV1/H.265 二进制格式解析 CLLI 数据
- **返回值**: 解析成功返回 true,失败返回 false

#### `sk_sp<SkData> serialize() const`
- **功能**: 序列化为 AV1/H.265 二进制格式
- **返回值**: 包含序列化数据的 SkData

#### `bool parsePngChunk(const SkData* data)`
- **功能**: 从 PNG cLLI chunk 格式解析
- **返回值**: 解析成功返回 true,失败返回 false
- **说明**: PNG 格式与 AV1 格式不等价

#### `sk_sp<SkData> serializePngChunk() const`
- **功能**: 序列化为 PNG cLLI chunk 格式
- **返回值**: 包含 PNG chunk 数据的 SkData

#### `static ContentLightLevelInformation MakeUint16(uint16_t maxCLL, uint16_t maxFALL)`
- **功能**: 从 uint16_t 值创建 CLLI 对象(CTA 语义)
- **参数**: maxCLL 和 maxFALL 的整数值(0-65535)

#### `uint16_t getUint16MaxCLL() const`
- **功能**: 获取 MaxCLL 的 uint16_t 表示,范围裁剪到 [0, 65535]
- **返回值**: 四舍五入并限制范围后的 uint16_t 值

#### `SkString toString() const`
- **功能**: 生成人类可读的描述字符串
- **返回值**: 格式化的描述信息

### MasteringDisplayColorVolume

主显示器色彩体积,描述内容制作时使用的参考显示器特性。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fDisplayPrimaries | SkColorSpacePrimaries | 显示器的 RGB 和白点色度坐标 |
| fMaximumDisplayMasteringLuminance | float | 最大显示亮度,单位 cd/m² |
| fMinimumDisplayMasteringLuminance | float | 最小显示亮度,单位 cd/m² |

**标准依据**:
- SMPTE ST 2086:2018

**公共方法**:

#### `bool parse(const SkData* data)`
- **功能**: 从 AV1/H.265/PNG 标准二进制格式解析
- **返回值**: 解析成功返回 true,失败返回 false
- **说明**: 三种格式等价

#### `sk_sp<SkData> serialize() const`
- **功能**: 序列化为标准二进制格式
- **返回值**: 包含序列化数据的 SkData

#### `SkString toString() const`
- **功能**: 生成人类可读的描述字符串
- **返回值**: 包含色彩坐标和亮度范围的描述

### AdaptiveGlobalToneMap

自适应全局色调映射元数据,支持多个 HDR 动态范围的色调映射。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fHdrReferenceWhite | float | HDR 参考白点亮度,默认 203 cd/m² |
| fHeadroomAdaptiveToneMap | std::optional<HeadroomAdaptiveToneMap> | 动态范围自适应色调映射参数 |

**标准依据**:
- SMPTE ST 2094-50 Application #5 (草案)

**嵌套结构**:

#### GainCurve
增益曲线,定义亮度映射函数。

**成员**:
- `std::vector<ControlPoint> fControlPoints`: 控制点数组(1-32 个)

**ControlPoint 结构**:
```cpp
struct ControlPoint {
    float fX;  // 输入亮度
    float fY;  // 输出亮度
    float fM;  // 斜率
};
```

#### ComponentMixingFunction
分量混合函数,定义如何混合 RGB 分量。

**成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fRed | float | 红色分量权重 |
| fGreen | float | 绿色分量权重 |
| fBlue | float | 蓝色分量权重 |
| fMax | float | 最大值权重 |
| fMin | float | 最小值权重 |
| fComponent | float | 分量系数 |

#### ColorGainFunction
颜色增益函数,组合混合函数和增益曲线。

**成员**:
- `ComponentMixingFunction fComponentMixing`
- `GainCurve fGainCurve`

#### AlternateImage
备选图像参数,定义特定 HDR 动态范围的映射。

**成员**:
- `float fHdrHeadroom`: 该备选图像的 HDR 动态范围
- `ColorGainFunction fColorGainFunction`: 色调映射函数

#### HeadroomAdaptiveToneMap
动态范围自适应色调映射主结构。

**成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fBaselineHdrHeadroom | float | 基准 HDR 动态范围 |
| fGainApplicationSpacePrimaries | SkColorSpacePrimaries | 增益应用的色彩空间 |
| fAlternateImages | std::vector<AlternateImage> | 备选图像数组(最多 4 个) |

**公共方法**:

#### `bool parse(const SkData* data)`
- **功能**: 从 SMPTE ST 2094-50 Annex C 格式解析
- **返回值**: 解析成功返回 true,失败返回 false

#### `sk_sp<SkData> serialize() const`
- **功能**: 序列化为 SMPTE ST 2094-50 格式
- **返回值**: 包含序列化数据的 SkData

#### `SkString toString() const`
- **功能**: 生成人类可读的描述字符串
- **返回值**: 详细的参数描述

### Metadata 类

HDR 元数据容器,整合所有类型的 HDR 元数据。

**私有成员**:
- `std::optional<ContentLightLevelInformation> fContentLightLevelInformation`
- `std::optional<MasteringDisplayColorVolume> fMasteringDisplayColorVolume`
- `std::optional<AdaptiveGlobalToneMap> fAdaptiveGlobalToneMap`

**公共方法**:

#### `static Metadata MakeEmpty()`
- **功能**: 创建空的元数据容器
- **返回值**: 不包含任何元数据的 Metadata 对象

#### `bool getContentLightLevelInformation(ContentLightLevelInformation* clli) const`
- **功能**: 获取 CLLI 元数据
- **参数**: clli - 输出参数,可为 nullptr(仅检查存在性)
- **返回值**: 存在返回 true,不存在返回 false

#### `void setContentLightLevelInformation(const ContentLightLevelInformation& clli)`
- **功能**: 设置 CLLI 元数据
- **参数**: clli - 要设置的 CLLI 数据

#### `bool getMasteringDisplayColorVolume(MasteringDisplayColorVolume* mdcv) const`
- **功能**: 获取 MDCV 元数据
- **参数**: mdcv - 输出参数,可为 nullptr
- **返回值**: 存在返回 true,不存在返回 false

#### `void setMasteringDisplayColorVolume(const MasteringDisplayColorVolume& mdcv)`
- **功能**: 设置 MDCV 元数据
- **参数**: mdcv - 要设置的 MDCV 数据

#### `bool getAdaptiveGlobalToneMap(AdaptiveGlobalToneMap* agtm) const`
- **功能**: 获取 AGTM 元数据
- **参数**: agtm - 输出参数,可为 nullptr
- **返回值**: 存在返回 true,不存在返回 false

#### `void setAdaptiveGlobalToneMap(const AdaptiveGlobalToneMap& agtm)`
- **功能**: 设置 AGTM 元数据
- **参数**: agtm - 要设置的 AGTM 数据

#### `sk_sp<const SkData> getSerializedAgtm() const`
- **功能**: 获取序列化的 AGTM 数据
- **返回值**: 序列化的二进制数据,无数据时返回 nullptr

#### `void setSerializedAgtm(sk_sp<const SkData>)`
- **功能**: 设置序列化的 AGTM 数据
- **参数**: 序列化的 AGTM 二进制数据

#### `sk_sp<SkColorFilter> makeToneMapColorFilter(float targetedHdrHeadroom, const SkColorSpace* inputColorSpace) const`
- **功能**: 创建色调映射颜色滤镜
- **参数**:
  - targetedHdrHeadroom: 目标显示器的 HDR 动态范围
  - inputColorSpace: 输入图像的颜色空间(可为 nullptr)
- **返回值**: 色调映射滤镜
- **说明**:
  - 如果输入是 PQ 或 HLG,会重新解释为元数据指定的 HDR 参考白点
  - 如果无 AGTM,会根据 CLLI/MDCV 推断基准动态范围并使用默认映射

#### `SkString toString() const`
- **功能**: 生成所有元数据的描述字符串
- **返回值**: 包含所有设置元数据的描述

## 内部实现细节

### CLLI 数据编码

AV1/H.265 格式编码结构:
```
[2 bytes] max_content_light_level (大端序)
[2 bytes] max_pic_average_light_level (大端序)
```

PNG cLLI 格式编码结构:
```
[4 bytes] MaxCLL (大端序,单位 1/10000 cd/m²)
[4 bytes] MaxFALL (大端序,单位 1/10000 cd/m²)
```

### MDCV 数据编码

标准格式编码结构(24 字节):
```
[2 bytes] display_primaries_x[0] (G)
[2 bytes] display_primaries_y[0] (G)
[2 bytes] display_primaries_x[1] (B)
[2 bytes] display_primaries_y[1] (B)
[2 bytes] display_primaries_x[2] (R)
[2 bytes] display_primaries_y[2] (R)
[2 bytes] white_point_x
[2 bytes] white_point_y
[4 bytes] max_display_mastering_luminance
[4 bytes] min_display_mastering_luminance
```

坐标值范围: [0, 50000],表示 [0.0, 1.0]
亮度值范围: [0, 4294967295],单位 0.0001 cd/m²

### 色调映射算法

makeToneMapColorFilter 的处理流程:

1. **确定源动态范围**:
   - 如果有 AGTM,使用 fBaselineHdrHeadroom
   - 如果有 CLLI,使用 fMaxCLL 推断
   - 如果有 MDCV,使用 fMaximumDisplayMasteringLuminance

2. **选择映射函数**:
   - 如果有 AGTM 且有匹配的 AlternateImage,使用其 ColorGainFunction
   - 否则使用默认的 Reinhard 或 ACES 色调映射

3. **构建 SkColorFilter**:
   - 将映射函数转换为着色器代码
   - 应用颜色空间转换(如果需要)
   - 返回组合的颜色滤镜

### GainCurve 插值

控制点定义的分段 Hermite 插值:
```
对于输入 x 在 [x[i], x[i+1]] 区间:
t = (x - x[i]) / (x[i+1] - x[i])
h00 = 2*t^3 - 3*t^2 + 1
h10 = t^3 - 2*t^2 + t
h01 = -2*t^3 + 3*t^2
h11 = t^3 - t^2
y = h00*y[i] + h10*m[i]*(x[i+1]-x[i]) + h01*y[i+1] + h11*m[i+1]*(x[i+1]-x[i])
```

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkColorSpace.h` | 颜色空间和色度坐标 |
| `include/core/SkData.h` | 二进制数据容器 |
| `include/private/base/SkAPI.h` | API 导出宏 |
| `<algorithm>`, `<cmath>` | 数学函数 |
| `<optional>`, `<vector>` | 标准容器 |

### 被依赖的模块

- **SkCodec**: 图像解码器使用此模块解析 HDR 元数据
- **SkImageGenerator**: 生成 HDR 图像时携带元数据
- **GPU 渲染器**: 使用 makeToneMapColorFilter 创建色调映射着色器
- **颜色管理**: HDR 颜色空间转换

## 设计模式与设计决策

### Optional 模式

使用 std::optional 表示元数据的存在性:
- **明确语义**: 清晰表达"无元数据"与"元数据为零值"的区别
- **节省空间**: 不需要为所有元数据分配空间
- **类型安全**: 编译期检查元数据访问

### 标准对齐设计

严格遵循国际标准:
- **互操作性**: 与其他媒体工具和播放器兼容
- **精确定义**: 避免歧义和实现差异
- **未来扩展**: 可以随标准演进而更新

### 序列化/反序列化分离

parse 和 serialize 方法对称设计:
- **往返一致性**: serialize(parse(data)) 应等于 data
- **容错解析**: parse 尽量容忍格式错误
- **严格写入**: serialize 总是生成符合规范的数据

### 色调映射抽象

makeToneMapColorFilter 提供高层抽象:
- **隐藏复杂性**: 用户无需了解 AGTM 的细节
- **自动回退**: 无 AGTM 时自动使用默认算法
- **性能优化**: 返回的 SkColorFilter 可以在 GPU 上高效执行

## 性能考量

### 元数据大小

各类元数据的典型大小:
- CLLI: 4 字节(AV1/H.265)或 8 字节(PNG)
- MDCV: 24 字节
- AGTM: 几十到几百字节(取决于控制点数量)

总计通常不超过 500 字节,对整体文件大小影响很小。

### 解析性能

- parse 方法都是线性时间 O(n)
- 通常在微秒级完成
- AGTM 解析稍慢,但仍然很快(通常 <100μs)

### 色调映射性能

makeToneMapColorFilter 的性能:
- **创建开销**: 几微秒到几毫秒(取决于 AGTM 复杂度)
- **执行开销**: 主要在 GPU,每像素几纳秒
- **优化策略**: 创建的 SkColorFilter 可以缓存重用

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/codec/SkHdrMetadata.cpp` | 实现文件 |
| `include/core/SkColorSpace.h` | 颜色空间定义 |
| `src/core/SkColorFilter.cpp` | 色调映射滤镜实现 |
| `src/codec/SkAvifCodec.cpp` | AVIF 解码器使用此模块 |
| `src/codec/SkJpegCodec.cpp` | JPEG XL 使用此模块 |
| `tests/HdrMetadataTest.cpp` | 单元测试 |
