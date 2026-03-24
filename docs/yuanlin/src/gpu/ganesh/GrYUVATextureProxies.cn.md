# GrYUVATextureProxies

> 源文件
> - `src/gpu/ganesh/GrYUVATextureProxies.h`
> - `src/gpu/ganesh/GrYUVATextureProxies.cpp`

## 概述

`GrYUVATextureProxies` 是 Ganesh GPU 后端中用于管理 YUVA(亮度-色度-透明度)格式纹理代理集合的容器类。该类封装了将 YUVA 平面图像数据转换为 GPU 纹理所需的所有信息,包括平面布局、通道映射、采样器配置和 mipmap 支持。

YUVA 格式在视频解码、图像压缩和某些相机格式中广泛使用,因为它比 RGBA 格式更符合人眼感知特性,能更高效地存储和传输图像数据。该模块的核心职责是正确处理各种 YUVA 平面配置(1-4 个平面)及其到 GPU 纹理的映射关系。

## 架构位置

```
Skia 图像处理流水线
├── SkImage (公共 API 层)
│   └── SkImage_Ganesh_YUVA     # YUVA 格式的 GPU 图像
│       ├── SkYUVAInfo          # YUVA 格式描述信息
│       └── GrYUVATextureProxies # 【本模块】GPU 纹理代理集合
│           ├── GrSurfaceProxy[4] # 最多 4 个平面的纹理代理
│           └── SkYUVAInfo::YUVALocations # 通道在各平面中的位置
├── GrFragmentProcessor
│   └── GrYUVtoRGBEffect        # 使用 YUVA 纹理生成 RGB 输出
└── GPU 后端
    └── GrTexture               # 实际的 GPU 纹理资源
```

该模块位于 YUVA 图像的高层表示与底层 GPU 纹理资源之间,负责正确建立平面-通道-纹理的映射关系。

## 主要类与结构体

### GrYUVATextureProxies

YUVA 纹理代理集合的封装类,支持默认构造、拷贝和移动语义。

**继承关系**
- 无继承关系,为独立的值类型

**关键成员变量**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fYUVAInfo` | `SkYUVAInfo` | YUVA 格式描述信息(色彩空间、平面配置、子采样等) |
| `fProxies` | `std::array<sk_sp<GrSurfaceProxy>, 4>` | 最多 4 个平面的纹理代理(实际数量由 `SkYUVAInfo` 决定) |
| `fTextureOrigin` | `GrSurfaceOrigin` | 纹理坐标原点(上左或下左) |
| `fMipmapped` | `skgpu::Mipmapped` | 是否所有平面都支持 mipmap |
| `fYUVALocations` | `SkYUVAInfo::YUVALocations` | 各 YUVA 通道在平面中的具体位置 |

### 构造函数变体

**构造函数 1: 基础构造**

```cpp
GrYUVATextureProxies(
    const SkYUVAInfo& yuvaInfo,
    sk_sp<GrSurfaceProxy> proxies[SkYUVAInfo::kMaxPlanes],
    GrSurfaceOrigin textureOrigin
);
```

假设所有平面使用默认的 RGBA 通道映射,直接从代理数组构造。

**构造函数 2: 高级构造(处理通道映射)**

```cpp
GrYUVATextureProxies(
    const SkYUVAInfo& yuvaInfo,
    GrSurfaceProxyView views[SkYUVAInfo::kMaxPlanes],
    GrColorType colorTypes[SkYUVAInfo::kMaxPlanes]
);
```

考虑纹理上传时的通道重排列(swizzle),通过 `GrSurfaceProxyView` 的 swizzle 信息正确计算最终的通道位置。

## 公共 API 函数

### 查询方法

```cpp
// 获取 YUVA 格式信息
const SkYUVAInfo& yuvaInfo() const;

// 获取平面数量(1-4)
int numPlanes() const;

// 获取纹理坐标原点
GrSurfaceOrigin textureOrigin() const;

// 查询 mipmap 支持(所有平面都有 mipmap 时返回 kYes)
skgpu::Mipmapped mipmapped() const;

// 获取第 i 个平面的纹理代理(裸指针)
GrSurfaceProxy* proxy(int i) const;

// 获取所有代理的数组引用
const std::array<sk_sp<GrSurfaceProxy>, SkYUVAInfo::kMaxPlanes>& proxies() const;

// 获取第 i 个平面的代理(智能指针)
sk_sp<GrSurfaceProxy> refProxy(int i) const;

// 为第 i 个平面创建视图(使用默认 RGBA swizzle)
GrSurfaceProxyView makeView(int i) const;

// 检查对象是否有效
bool isValid() const;

// 获取 YUVA 通道位置映射
const SkYUVAInfo::YUVALocations& yuvaLocations() const;
```

### 构造和赋值

```cpp
// 默认构造(无效对象)
GrYUVATextureProxies() = default;

// 拷贝和移动语义
GrYUVATextureProxies(const GrYUVATextureProxies&) = default;
GrYUVATextureProxies(GrYUVATextureProxies&&) = default;
GrYUVATextureProxies& operator=(const GrYUVATextureProxies&) = default;
GrYUVATextureProxies& operator=(GrYUVATextureProxies&&) = default;
```

## 内部实现细节

### 构造函数 1: 简单构造逻辑

**核心流程**(第 39-78 行):

1. **初始化和验证**:
```cpp
int n = yuvaInfo.numPlanes();
if (n == 0) {
    *this = {};  // 无效配置,重置为空
    SkASSERT(!this->isValid());
    return;
}
```

2. **获取通道掩码**:
```cpp
uint32_t textureChannelMasks[SkYUVAInfo::kMaxPlanes];
for (int i = 0; i < n; ++i) {
    if (!proxies[i]) {
        *this = {};  // 任一代理为空则失败
        return;
    }
    textureChannelMasks[i] = proxies[i]->backendFormat().channelMask();
}
```

3. **计算 YUVA 通道位置**:
```cpp
fYUVALocations = yuvaInfo.toYUVALocations(textureChannelMasks);
if (fYUVALocations[0].fPlane < 0) {
    *this = {};  // 无法确定有效的通道映射
    return;
}
```

4. **检测 mipmap 支持**:
```cpp
fMipmapped = skgpu::Mipmapped::kYes;
for (size_t i = 0; i < static_cast<size_t>(n); ++i) {
    SkASSERT(proxies[i]->asTextureProxy());
    if (proxies[i]->asTextureProxy()->mipmapped() == skgpu::Mipmapped::kNo) {
        fMipmapped = skgpu::Mipmapped::kNo;  // 任一平面无 mipmap 则整体无
    }
    fProxies[i] = std::move(proxies[i]);
}
```

### 构造函数 2: 处理 Swizzle 的复杂逻辑

**核心流程**(第 80-137 行):

1. **初始化和平面验证**:
```cpp
uint32_t pixmapChannelMasks[SkYUVAInfo::kMaxPlanes];
int n = yuvaInfo.numPlanes();
for (int i = 0; i < n; ++i) {
    pixmapChannelMasks[i] = GrColorTypeChannelFlags(colorTypes[i]);
    SkASSERT(num_channels(pixmapChannelMasks[i]) <=
             num_channels(views[i].proxy()->backendFormat().channelMask()));
    if (!views[i] || views[i].origin() != views[0].origin()) {
        *this = {};  // 所有视图必须有相同的原点
        return;
    }
}
```

2. **计算初始通道位置**(基于 CPU pixmap 的通道布局):
```cpp
fYUVALocations = yuvaInfo.toYUVALocations(pixmapChannelMasks);
if (fYUVALocations[0].fPlane < 0) {
    *this = {};
    return;
}
```

3. **应用 swizzle 转换**(将 CPU 通道映射到 GPU 纹理通道):
```cpp
for (int i = 0; i < SkYUVAInfo::kYUVAChannelCount; ++i) {
    int plane = fYUVALocations[i].fPlane;
    if (plane >= 0) {
        int chanAsIdx = static_cast<int>(fYUVALocations[i].fChannel);
        switch (views[plane].swizzle()[chanAsIdx]) {
            case 'r': fYUVALocations[i].fChannel = SkColorChannel::kR; break;
            case 'g': fYUVALocations[i].fChannel = SkColorChannel::kG; break;
            case 'b': fYUVALocations[i].fChannel = SkColorChannel::kB; break;
            case 'a': fYUVALocations[i].fChannel = SkColorChannel::kA; break;
            default:
                SkDEBUGFAILF("Unexpected swizzle value: %c", views[i].swizzle()[chanAsIdx]);
                *this = {};
                return;
        }
    }
}
```

这是核心逻辑:当 CPU pixmap 的通道 A 映射到纹理的通道 B 时(通过 swizzle),需要更新 `YUVALocations` 中的通道位置。

**示例场景**:
- CPU pixmap: 单通道灰度数据(通道掩码 = `kGray`)
- GPU 纹理: Alpha8 格式(数据实际存储在 alpha 通道)
- Swizzle: `aaaa`(将 alpha 通道映射到所有通道)
- 结果: `fYUVALocations[Y].fChannel` 从 `kR` 更新为 `kA`

### Mipmap 检测逻辑

所有平面都必须有 mipmap 才认为整体支持 mipmap:

```cpp
fMipmapped = skgpu::Mipmapped::kYes;
for (size_t i = 0; i < static_cast<size_t>(n); ++i) {
    if (views[i].proxy()->asTextureProxy()->mipmapped() == skgpu::Mipmapped::kNo) {
        fMipmapped = skgpu::Mipmapped::kNo;
        break;  // 提前退出
    }
}
```

### 调试验证函数

仅在 Debug 模式下编译的通道数量验证(第 22-36 行):

```cpp
#ifdef SK_DEBUG
static int num_channels(uint32_t channelFlags) {
    switch (channelFlags) {
        case kRed_SkColorChannelFlag        : return 1;
        case kAlpha_SkColorChannelFlag      : return 1;
        case kGray_SkColorChannelFlag       : return 1;
        case kGrayAlpha_SkColorChannelFlags : return 2;
        case kRG_SkColorChannelFlags        : return 2;
        case kRGB_SkColorChannelFlags       : return 3;
        case kRGBA_SkColorChannelFlags      : return 4;
        default:
            SkDEBUGFAILF("Unexpected channel combination 0x%08x", channelFlags);
            return 0;
    }
}
#endif
```

确保 CPU 数据的通道数不超过 GPU 纹理格式的通道数。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkYUVAInfo` | 描述 YUVA 格式的配置信息(色彩空间、平面数、子采样等) |
| `SkYUVAInfoLocation` | 定义 YUVA 通道在平面中的位置映射 |
| `GrSurfaceProxy` | GPU 纹理代理基类 |
| `GrSurfaceProxyView` | 纹理代理视图(包含 origin 和 swizzle) |
| `GrTextureProxy` | 纹理代理(用于查询 mipmap 状态) |
| `GrBackendSurface` | 后端纹理格式信息(用于获取通道掩码) |
| `skgpu::Swizzle` | 通道重排列工具 |
| `skgpu::Mipmapped` | Mipmap 支持枚举 |
| `GrTypesPriv` | 内部类型定义(如 `GrColorTypeChannelFlags`) |
| `SkColorChannel` | Skia 颜色通道枚举 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `SkImage_Ganesh` | 存储和使用 YUVA 纹理代理集合 |
| `GrYUVtoRGBEffect` | 从 YUVA 纹理代理创建片段处理器,进行颜色空间转换 |
| `GrYUVAImageTexturesMaker` | 负责从 YUVA pixmap 创建纹理代理集合 |
| `GrImageContextPriv` | 管理 YUVA 图像的内部上下文 |
| `GrDrawOpAtlas` | 可能缓存 YUVA 纹理用于 atlas 渲染 |

## 设计模式与设计决策

### 1. 值语义设计

`GrYUVATextureProxies` 采用值类型设计:
- 支持默认构造、拷贝和移动
- 不使用继承,避免多态开销
- 通过 `std::array` 和智能指针管理资源

**优势**:
- 易于复制和传递
- 无需关注生命周期管理
- 适合作为其他类的成员变量

### 2. RAII 资源管理

通过 `sk_sp<GrSurfaceProxy>` 自动管理纹理代理的生命周期:
- 构造函数验证失败时自动清理所有代理
- 析构函数自动释放引用

### 3. Fail-Fast 原则

构造函数中任何验证失败都立即重置对象为无效状态:
```cpp
if (/* 验证失败 */) {
    *this = {};
    SkASSERT(!this->isValid());
    return;
}
```

调用者通过 `isValid()` 检查是否构造成功。

### 4. 不可变性

构造后对象状态不再改变:
- 所有查询方法都是 `const`
- 无公共修改接口
- 确保线程安全和状态一致性

### 5. 适配器模式

该类是 `SkYUVAInfo`(格式描述)和 `GrSurfaceProxy`(GPU 资源)之间的适配器:
- 将 Skia 层的 YUVA 格式映射到 Ganesh GPU 纹理
- 处理通道重排列和原点差异

### 6. 组合优于继承

通过组合 `SkYUVAInfo` 和 `GrSurfaceProxy` 数组,而非继承任何基类:
- 灵活性高,易于扩展
- 避免虚函数调用开销
- 明确各组件的职责

### 7. 类型安全的数组访问

使用 `std::array` 而非原始数组:
- 编译期大小检查
- 支持 range-based for 循环
- 标准库容器接口

## 性能考量

### 1. 编译期常量

使用 `SkYUVAInfo::kMaxPlanes` (值为 4) 作为数组大小:
- 避免动态分配
- 栈上分配,访问速度快
- 编译器可优化数组访问

### 2. 智能指针开销最小化

使用 `std::array<sk_sp<>, 4>` 而非 `std::vector`:
- 无堆分配
- 无容量管理开销
- 固定大小,缓存友好

### 3. Mipmap 检测提前退出

一旦发现某个平面无 mipmap 立即设置结果:
```cpp
if (proxies[i]->asTextureProxy()->mipmapped() == skgpu::Mipmapped::kNo) {
    fMipmapped = skgpu::Mipmapped::kNo;
    // 继续循环存储其他代理,但不再检查 mipmap
}
```

### 4. 内联访问器

简单的查询方法可被编译器内联:
```cpp
const SkYUVAInfo& yuvaInfo() const { return fYUVAInfo; }
int numPlanes() const { return fYUVAInfo.numPlanes(); }
```

### 5. 移动语义避免拷贝

构造函数参数使用数组传递,内部使用 `std::move`:
```cpp
fProxies[i] = std::move(proxies[i]);
```

避免智能指针的引用计数操作。

### 6. 懒惰验证

仅在 Debug 模式下执行通道数量检查:
```cpp
#ifdef SK_DEBUG
SkASSERT(num_channels(pixmapChannelMasks[i]) <=
         num_channels(views[i].proxy()->backendFormat().channelMask()));
#endif
```

Release 模式下跳过额外验证。

### 7. 局部性优化

成员变量布局紧凑:
- `fYUVAInfo`: 约 20 字节
- `fProxies`: 4 * 8 = 32 字节(指针)
- `fTextureOrigin`: 4 字节
- `fMipmapped`: 1 字节
- `fYUVALocations`: 8 字节

总计约 65 字节,适合单个缓存行。

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `include/core/SkYUVAInfo.h` | YUVA 格式描述信息类 |
| `src/core/SkYUVAInfoLocation.h` | YUVA 通道位置映射定义 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 纹理代理基类 |
| `src/gpu/ganesh/GrSurfaceProxyView.h` | 纹理代理视图 |
| `src/gpu/ganesh/GrTextureProxy.h` | 纹理代理(支持 mipmap 查询) |
| `src/gpu/Swizzle.h` | 通道重排列工具 |
| `include/gpu/GpuTypes.h` | GPU 公共类型定义 |
| `include/gpu/ganesh/GrTypes.h` | Ganesh 类型定义 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端纹理表面 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | Ganesh 内部类型 |
| `src/image/SkImage_Ganesh.h` | Ganesh GPU 图像实现 |
| `src/gpu/ganesh/effects/GrYUVtoRGBEffect.h` | YUVA 到 RGB 转换效果 |
| `include/core/SkColorChannel.h` | 颜色通道枚举定义 |
