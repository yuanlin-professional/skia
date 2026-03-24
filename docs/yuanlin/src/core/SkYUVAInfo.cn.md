# SkYUVAInfo

> 源文件: include/core/SkYUVAInfo.h, src/core/SkYUVAInfo.cpp

## 概述

`SkYUVAInfo` 是 Skia 中用于描述 YUV（亮度-色度）图像平面结构的核心类，支持可选的 Alpha 通道。它定义了 YUV 数据如何在多个平面（plane）之间分布、色度子采样方式、色度采样点位置以及图像方向等元信息。该类本身不包含实际的像素数据，而是作为元数据描述符，配合外部纹理或 pixmap 使用。

YUV 格式广泛应用于视频编解码、图像传输和 GPU 纹理压缩，因其相比 RGB 格式能显著减少带宽和存储需求。`SkYUVAInfo` 为 Skia 提供了统一的 YUV 格式抽象，支持从 JPEG、视频帧、硬件解码器等多种来源创建图像。

## 架构位置

`SkYUVAInfo` 在 Skia 图像处理架构中扮演"格式描述符"角色：

```
图像来源 (JPEG, 视频解码器, 相机)
         ↓
  YUV 平面数据 (纹理/pixmap)
         ↓
  SkYUVAInfo (格式描述) ← 本模块
         ↓
  SkImage::MakeFromYUVATextures/Pixmaps
         ↓
  GPU/CPU 渲染管线
```

它作为"配置对象"存在，告诉 Skia 如何解释外部的 YUV 数据，但不负责数据的存储和传输。

## 主要类与结构体

### SkYUVAInfo

YUV(A) 图像平面结构的描述符。

**继承关系**
- 无继承（值类型）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDimensions` | `SkISize` | 全分辨率图像尺寸（显示方向） |
| `fPlaneConfig` | `PlaneConfig` | 平面配置（Y/U/V/A 如何分布） |
| `fSubsampling` | `Subsampling` | 色度子采样方式 |
| `fYUVColorSpace` | `SkYUVColorSpace` | YUV 色彩空间（如 BT.601, BT.709） |
| `fOrigin` | `SkEncodedOrigin` | EXIF 方向信息 |
| `fSitingX` | `Siting` | 色度水平采样点位置 |
| `fSitingY` | `Siting` | 色度垂直采样点位置 |

### PlaneConfig 枚举

定义 Y、U、V、A 通道如何分布在平面中。

```cpp
enum class PlaneConfig {
    kUnknown,
    kY_U_V,      // 平面 0: Y, 平面 1: U, 平面 2: V
    kY_V_U,      // 平面 0: Y, 平面 1: V, 平面 2: U
    kY_UV,       // 平面 0: Y, 平面 1: UV
    kY_VU,       // 平面 0: Y, 平面 1: VU
    kYUV,        // 平面 0: YUV
    kUYV,        // 平面 0: UYV
    kY_U_V_A,    // 平面 0: Y, 平面 1: U, 平面 2: V, 平面 3: A
    kY_V_U_A,    // 平面 0: Y, 平面 1: V, 平面 2: U, 平面 3: A
    kY_UV_A,     // 平面 0: Y, 平面 1: UV, 平面 2: A
    kY_VU_A,     // 平面 0: Y, 平面 1: VU, 平面 2: A
    kYUVA,       // 平面 0: YUVA
    kUYVA,       // 平面 0: UYVA
};
```

**通道映射规则**
- **A (Alpha)**: `0:A`
- **Luminance/Gray**: `0:Gray`
- **Gray + Alpha**: `0:Gray, 1:A`
- **RG**: `0:R, 1:G`
- **RGB**: `0:R, 1:G, 2:B`
- **RGBA**: `0:R, 1:G, 2:B, 3:A`

### Subsampling 枚举

定义色度子采样方式（使用 J:a:b 标记）。

```cpp
enum class Subsampling {
    kUnknown,
    k444,    // 无子采样，每个 Y 对应一组 UV
    k422,    // 水平 1/2 子采样（每 2x1 块 Y 对应一组 UV）
    k420,    // 水平和垂直 1/2 子采样（每 2x2 块 Y 对应一组 UV）
    k440,    // 垂直 1/2 子采样（每 1x2 块 Y 对应一组 UV）
    k411,    // 水平 1/4 子采样（每 4x1 块 Y 对应一组 UV）
    k410,    // 水平 1/4 垂直 1/2 子采样（每 4x2 块 Y 对应一组 UV）
};
```

**常见用途**
- `k444`: 高质量图像、无损压缩
- `k422`: 广播视频、专业视频编辑
- `k420`: 消费级视频（H.264, VP9）、JPEG
- `k411`: DV 格式

### Siting 枚举

定义子采样色度值相对于亮度值的采样点位置。

```cpp
enum class Siting {
    kCentered,  // 色度采样点位于对应 Y 块的中心
};
```

**注**：当前仅支持中心采样，未来可能扩展支持其他采样点位置（如左对齐、上对齐）。

## 公共 API 函数

### 构造函数

```cpp
SkYUVAInfo(SkISize dimensions,
           PlaneConfig,
           Subsampling,
           SkYUVColorSpace,
           SkEncodedOrigin origin = kTopLeft_SkEncodedOrigin,
           Siting sitingX = Siting::kCentered,
           Siting sitingY = Siting::kCentered)
```
创建 YUV 图像信息对象。

**参数说明**
- `dimensions`: 全分辨率图像尺寸（已应用方向变换后的显示尺寸）
- `PlaneConfig`: 平面配置
- `Subsampling`: 子采样方式
- `SkYUVColorSpace`: 色彩空间（如 `kRec601_SkYUVColorSpace`）
- `origin`: EXIF 方向（用于旋转/镜像）
- `sitingX/Y`: 色度采样点位置

**验证规则**
- 尺寸不能为空
- 平面配置必须与子采样方式兼容
- 非 k444 子采样要求 Y 与 UV 在不同平面

### 静态工具方法

```cpp
static std::tuple<int, int> SubsamplingFactors(Subsampling)
```
返回子采样的水平和垂直因子。例如 `k420` 返回 `{2, 2}`。

```cpp
static std::tuple<int, int> PlaneSubsamplingFactors(PlaneConfig, Subsampling, int planeIdx)
```
返回指定平面的子采样因子。对于 U/V 平面返回子采样因子，对于 Y/A 平面返回 `{1, 1}`。

```cpp
static int PlaneDimensions(SkISize imageDimensions,
                           PlaneConfig,
                           Subsampling,
                           SkEncodedOrigin,
                           SkISize planeDimensions[kMaxPlanes])
```
计算各平面的尺寸（内存存储尺寸，可能旋转）。返回平面数量，并填充 `planeDimensions` 数组。

```cpp
static constexpr int NumPlanes(PlaneConfig)
```
返回给定平面配置的平面数量。

```cpp
static constexpr int NumChannelsInPlane(PlaneConfig, int i)
```
返回第 i 个平面中的通道数量。

```cpp
static YUVALocations GetYUVALocations(PlaneConfig, const uint32_t* planeChannelFlags)
```
将平面配置和通道标志转换为 `YUVALocations` 表示（内部使用）。

```cpp
static bool HasAlpha(PlaneConfig)
```
检查平面配置是否包含 Alpha 通道。

### 实例方法

```cpp
bool isValid() const
```
检查对象是否有效（平面配置不为 `kUnknown`）。

```cpp
PlaneConfig planeConfig() const
Subsampling subsampling() const
SkISize dimensions() const
int width() const
int height() const
SkYUVColorSpace yuvColorSpace() const
SkEncodedOrigin origin() const
Siting sitingX() const
Siting sitingY() const
bool hasAlpha() const
```
访问器方法。

```cpp
int planeDimensions(SkISize planeDimensions[kMaxPlanes]) const
```
计算各平面尺寸，返回平面数量。

```cpp
size_t computeTotalBytes(const size_t rowBytes[kMaxPlanes],
                         size_t planeSizes[kMaxPlanes] = nullptr) const
```
根据每个平面的行字节数计算总内存需求。可选地返回各平面大小。溢出时返回 `SIZE_MAX`。

```cpp
SkMatrix originMatrix() const
SkMatrix inverseOriginMatrix() const
```
返回 EXIF 方向变换矩阵及其逆矩阵。

```cpp
SkYUVAInfo makeSubsampling(Subsampling) const
```
创建相同但子采样方式不同的副本。

```cpp
SkYUVAInfo makeDimensions(SkISize) const
```
创建相同但尺寸不同的副本。

```cpp
bool operator==(const SkYUVAInfo&) const
bool operator!=(const SkYUVAInfo&) const
```
相等性比较。

## 内部实现细节

### 平面配置与子采样兼容性

并非所有平面配置都支持子采样：

```cpp
static bool is_plane_config_compatible_with_subsampling(
    SkYUVAInfo::PlaneConfig config,
    SkYUVAInfo::Subsampling subsampling) {
    if (config == kUnknown || subsampling == kUnknown) {
        return false;
    }
    return subsampling == k444 ||
           (config != kYUV  && config != kYUVA &&
            config != kUYV  && config != kUYVA);
}
```

**规则**
- k444 子采样与所有配置兼容
- 其他子采样要求 Y 与 UV 在不同平面（不能使用 kYUV/kUYV/kYUVA/kUYVA）

**原因**：单平面格式中 UV 与 Y 在同一纹理，无法有不同的分辨率。

### 平面尺寸计算

`PlaneDimensions()` 根据子采样和方向计算各平面尺寸：

```cpp
int SkYUVAInfo::PlaneDimensions(SkISize imageDimensions,
                                PlaneConfig planeConfig,
                                Subsampling subsampling,
                                SkEncodedOrigin origin,
                                SkISize planeDimensions[kMaxPlanes]) {
    int w = imageDimensions.width();
    int h = imageDimensions.height();
    if (origin >= kLeftTop_SkEncodedOrigin) {
        swap(w, h);  // 旋转 90/270 度时交换宽高
    }

    auto down2 = [](int x) { return (x + 1) / 2; };
    auto down4 = [](int x) { return (x + 3) / 4; };

    SkISize uvSize;
    switch (subsampling) {
        case k444: uvSize = {w, h};           break;
        case k422: uvSize = {down2(w), h};    break;
        case k420: uvSize = {down2(w), down2(h)}; break;
        case k440: uvSize = {w, down2(h)};    break;
        case k411: uvSize = {down4(w), h};    break;
        case k410: uvSize = {down4(w), down2(h)}; break;
    }

    // 根据平面配置分配尺寸...
}
```

**关键点**
- 图像尺寸是显示尺寸（已应用方向变换）
- 平面尺寸是存储尺寸（可能旋转）
- 子采样使用向上取整除法（保守分配）

### 通道索引到 SkColorChannel 的映射

`channel_index_to_channel()` 将平面的通道索引映射到 `SkColorChannel` 枚举：

```cpp
static bool channel_index_to_channel(uint32_t channelFlags,
                                     int channelIdx,
                                     SkColorChannel* channel) {
    switch (channelFlags) {
        case kGray_SkColorChannelFlag:
        case kRed_SkColorChannelFlag:
            if (channelIdx == 0) {
                *channel = SkColorChannel::kR;
                return true;
            }
            return false;
        case kRG_SkColorChannelFlags:
            if (channelIdx == 0 || channelIdx == 1) {
                *channel = static_cast<SkColorChannel>(channelIdx);
                return true;
            }
            return false;
        // ...
    }
}
```

**用途**：将抽象的平面/通道索引转换为具体的纹理通道（R/G/B/A）。

### YUVALocations 转换

`GetYUVALocations()` 是 Skia GPU 渲染使用的内部格式：

```cpp
struct YUVALocation {
    int plane;                // 平面索引（-1 表示不存在）
    SkColorChannel channel;   // 通道（R/G/B/A）
};
using YUVALocations = std::array<YUVALocation, 4>;  // [Y, U, V, A]
```

**示例**：`kY_UV` 配置
- Y: `{plane: 0, channel: R}`
- U: `{plane: 1, channel: R}`
- V: `{plane: 1, channel: G}`
- A: `{plane: -1, channel: R}` (不存在)

### 内存需求计算

`computeTotalBytes()` 计算所有平面的总内存需求：

```cpp
size_t SkYUVAInfo::computeTotalBytes(const size_t rowBytes[kMaxPlanes],
                                     size_t planeSizes[kMaxPlanes]) const {
    SkSafeMath safe;
    size_t totalBytes = 0;
    SkISize planeDimensions[kMaxPlanes];
    int n = this->planeDimensions(planeDimensions);
    for (int i = 0; i < n; ++i) {
        size_t size = safe.mul(rowBytes[i], planeDimensions[i].height());
        if (planeSizes) {
            planeSizes[i] = size;
        }
        totalBytes = safe.add(totalBytes, size);
    }
    return safe.ok() ? totalBytes : SIZE_MAX;
}
```

**安全性**
- 使用 `SkSafeMath` 检测整数溢出
- 溢出时返回 `SIZE_MAX`，避免分配不足

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkImageInfo` | 色彩空间和 Alpha 类型 |
| `SkSize` | 图像和平面尺寸 |
| `SkMatrix` | 方向变换矩阵 |
| `SkEncodedOrigin` | EXIF 方向信息 |
| `SkColorChannel` | 通道枚举（内部） |
| `SkSafeMath` | 安全整数运算 |

**被依赖的模块**

| 模块 | 依赖原因 |
|------|----------|
| `SkImage` | `MakeFromYUVATextures/Pixmaps` |
| `GrYUVABackendTextures` | GPU YUV 纹理绑定 |
| `SkYUVAPixmaps` | CPU YUV 像素映射 |
| `SkCodec` | JPEG/WebP 解码器 |
| `GrTextureProxy` | GPU 纹理代理 |

## 设计模式与设计决策

### 设计模式

1. **值对象模式**
   - `SkYUVAInfo` 是轻量级值类型
   - 可复制、移动、比较
   - 无动态分配

2. **描述符模式**
   - 仅包含元数据，不包含实际数据
   - 与数据分离，支持多种数据源

3. **静态工厂方法**
   - 提供丰富的静态计算方法
   - 避免创建对象仅为使用工具函数

4. **不可变对象模式（部分）**
   - 提供 `makeSubsampling()` 等方法创建变体
   - 避免修改现有对象

### 设计决策

#### 1. 元数据与数据分离

**设计**
- `SkYUVAInfo` 仅描述格式
- 实际数据在 `GrYUVABackendTextures` 或 `SkYUVAPixmaps` 中

**优点**
- 格式信息可独立验证和传递
- 支持多种数据后端（GPU 纹理、CPU 内存、文件）
- 轻量级，适合作为函数参数

#### 2. 平面配置枚举而非位掩码

**设计**：使用强类型枚举 `PlaneConfig`

**优点**
- 类型安全，编译时检查
- 枚举值有清晰语义（如 `kY_UV`）
- 易于添加新配置

**缺点**
- 枚举值数量多（12 个）
- 需要为每个配置编写处理代码

**替代方案**：位掩码表示（如 `HAS_Y | HAS_UV | HAS_ALPHA`）
- 更灵活但类型安全性差
- 需要运行时组合验证

#### 3. 子采样因子的计算方式

**向上取整除法**
```cpp
auto down2 = [](int x) { return (x + 1) / 2; };
auto down4 = [](int x) { return (x + 3) / 4; };
```

**原因**
- 保守分配内存，避免不足
- 奇数尺寸图像的边缘处理
- 例如：3x3 图像的 k420 子采样 → UV 平面 2x2（而非 1x1）

#### 4. 兼容性验证策略

**设计**：构造函数验证配置有效性，无效时重置为 `kUnknown`

```cpp
if (!is_plane_config_compatible_with_subsampling(...)) {
    *this = {};  // 重置为无效状态
}
```

**优点**
- 不抛出异常，符合 Skia 风格
- 调用者可通过 `isValid()` 检查
- 避免创建半有效对象

**缺点**
- 静默失败，可能难以调试
- 需要调用者显式检查

#### 5. EXIF 方向支持

**设计**：将方向作为 `SkYUVAInfo` 的一部分

**原因**
- YUV 数据常来自 JPEG（支持 EXIF）
- 避免在解码时旋转（性能开销）
- 在 GPU 渲染时应用变换（几乎无开销）

**实现**
- `originMatrix()` 返回变换矩阵
- GPU 着色器使用矩阵采样纹理
- 平面尺寸根据方向调整（存储尺寸 vs 显示尺寸）

#### 6. 仅支持 Centered Siting

**当前限制**：`Siting` 枚举仅有 `kCentered`

**原因**
- 大多数视频格式使用中心采样
- 简化初始实现

**未来扩展**
```cpp
enum class Siting {
    kCentered,
    kCosited,     // 色度与左上角 Y 对齐
    kMidpoint,    // 色度在相邻 Y 的中点
};
```

需要在 GPU 着色器中调整采样偏移量。

## 性能考量

### 内存效率

1. **紧凑的值类型**
   - 对象大小约 32 字节
   - 适合栈分配和值传递
   - 无动态分配

2. **子采样节省内存**
   - k420 子采样：UV 平面各为 Y 平面的 1/4
   - 总内存约为 RGB 的 50%
   - 适合高分辨率图像和视频

### 计算效率

1. **constexpr 方法**
   - `NumPlanes()` 和 `NumChannelsInPlane()` 是 `constexpr`
   - 编译时求值，运行时零开销

2. **静态计算方法**
   - 无需创建对象即可使用工具方法
   - 适合验证和预计算场景

3. **缓存友好的布局**
   - 成员变量按大小排序，减少填充
   - 适合作为数组元素

### YUV 格式的性能优势

1. **带宽节省**
   - k420 YUV 比 RGBA 节省 50% 带宽
   - GPU 纹理上传和采样更快

2. **硬件加速**
   - 现代 GPU 原生支持 YUV 格式
   - 视频解码器直接输出 YUV
   - 避免 CPU 上的 YUV→RGB 转换

3. **视频压缩友好**
   - H.264/VP9 等编解码器原生使用 YUV
   - 无需转换，直接渲染

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `include/core/SkImage.h` | 使用者 | `MakeFromYUVATextures/Pixmaps` |
| `include/gpu/GrYUVABackendTextures.h` | 配合使用 | GPU YUV 纹理绑定 |
| `include/core/SkYUVAPixmaps.h` | 配合使用 | CPU YUV 像素数据 |
| `src/core/SkYUVAInfoLocation.h` | 内部依赖 | YUVALocation 定义 |
| `include/core/SkImageInfo.h` | 依赖 | 色彩空间和 Alpha 类型 |
| `include/codec/SkEncodedOrigin.h` | 依赖 | EXIF 方向枚举 |
| `src/codec/SkJpegCodec.cpp` | 使用者 | JPEG 解码器 |
| `src/gpu/ganesh/GrYUVATextureProxies.cpp` | 使用者 | GPU YUV 纹理代理 |
| `include/core/SkMatrix.h` | 依赖 | 方向变换矩阵 |
